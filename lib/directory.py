import os
import stat
import sys
import tempfile

from functools import partial

from .file import File


class Directory(File):

	# Share the existing root face cache when representing that same root.
	# ----------------------------------------------------------------------
	def __init__(self, lib, path, route):
		super().__init__(lib, path, route)
		self.__children__ = lib.__children__ if self.get_path() == os.path.realpath(lib.__path__) else {}

	# Realize resolved children without exposing their carriers.
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		value = self.__resolve__(name)

		if value is None:
			raise AttributeError(f'Module `{self.get_route()}.{name}` does not exist or no loading method is provided')

		return value.load()

	# Discover visible carriers without loading their content.
	# ----------------------------------------------------------------------
	def __iter__(self):
		for entry in os.listdir(self.get_path()):
			if not entry.startswith('.'):
				value = self.__resolve__(entry)
				if value is not None:
					yield value

	# Resolve local children before matching inherited namespace layers.
	# ----------------------------------------------------------------------
	def __resolve__(self, name):
		value = self.__children__.get(name)

		if value is None:
			path  = self.get_path()
			route = None

			for instance in self.get_lib().__instances__():
				root       = os.path.realpath(instance.__path__)
				is_in_root = os.path.commonpath([path, root]) == root

				if route is None and is_in_root:
					route = os.path.relpath(path, root)

				if route is not None:
					parent_path = os.path.realpath(os.path.join(root, route))
					is_dir      = os.path.isdir(parent_path)

					if is_dir:
						library = instance if route == '.' else self.get_lib()
						value   = library.__resolve__(name, parent_path, self.get_route())

						if value is not None:
							self.__children__[name] = value
							break

			if route is None:
				value = self.get_lib().__resolve__(name, path, self.get_route())

				if value is not None:
					self.__children__[name] = value

		return value

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Accept one visible basename and refuse symbolic-link destinations.
	# ----------------------------------------------------------------------
	def _destination(self, name):
		if not isinstance(name, str) or not name or name in ('.', '..') or os.path.basename(name) != name:
			raise ValueError(f'Invalid file name: {name}')

		path = self.join(name)
		if os.path.islink(os.path.join(self.get_path(), name)):
			raise ValueError(f'Symbolic link is not allowed: {path}')

		return path

	# Select the format owner in the existing library and plugin order.
	# ----------------------------------------------------------------------
	def _plugin(self, name):
		ext    = os.path.splitext(name)[1].lstrip('.')
		plugin = None

		for instance in self.get_lib().__instances__():
			for candidate in instance.__PLUGINS__.values():
				if ext in candidate.EXTENSIONS:
					plugin = candidate
					break
			if plugin is not None:
				break

		if plugin is None:
			raise ValueError(f'Unsupported file extension: {ext}')

		return plugin

	# Refresh affected carriers and bindings while preserving unrelated content.
	# ----------------------------------------------------------------------
	def _invalidate_children(self, path):
		stem = os.path.splitext(os.path.basename(path))[0]

		for name, child in list(self.__children__.items()):
			if child.get_path() == path:
				child._invalidate()

			if child.get_path() == path or name == stem or self.get_lib().String.camel_to_snake(name) == stem:
				del self.__children__[name]

	# Publish a completed temporary file; never expose a partial destination.
	# ----------------------------------------------------------------------
	def _replace(self, path, write):
		extension        = os.path.splitext(path)[1]
		descriptor, temp = tempfile.mkstemp(prefix='.almasi-', suffix=extension, dir=self.get_path())

		try:
			os.close(descriptor)
			write(temp)
			os.replace(temp, path)
		finally:
			if os.path.lexists(temp):
				error = sys.exc_info()[1]
				try:
					os.unlink(temp)
				except OSError as cleanup_error:
					if error is None:
						raise
					error.add_note(f'Temporary file cleanup failed: {cleanup_error}')

		self._invalidate_children(path)

	# Stream bytes without invoking a format plugin.
	# ----------------------------------------------------------------------
	def _copy(self, source, destination):
		with open(source, 'rb') as incoming:
			if not stat.S_ISREG(os.fstat(incoming.fileno()).st_mode):
				raise ValueError(f'Not a regular file: {source}')

			with open(destination, 'wb') as outgoing:
				for chunk in iter(partial(incoming.read, 1024 * 1024), b''):
					outgoing.write(chunk)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Distinguish directories through the public carrier contract.
	# ----------------------------------------------------------------------
	def is_directory(self):
		return True

	# Join relative components without creating or requiring the result.
	# ----------------------------------------------------------------------
	def join(self, *parts):
		path = self.get_path()

		for part in parts:
			if not isinstance(part, str) or not part or os.path.isabs(part):
				raise ValueError(f'Invalid relative path: {part}')

			path = os.path.abspath(os.path.join(path, part))
			if os.path.commonpath([self.get_path(), path]) != self.get_path():
				raise ValueError(f'Path escapes directory: {part}')
			if os.path.commonpath([self.get_path(), os.path.realpath(path)]) != self.get_path():
				raise ValueError(f'Symbolic link escapes directory: {part}')

		return path

	# Create nested directories through native namespace resolution.
	# ----------------------------------------------------------------------
	def mkdir(self, *parts):
		if not parts:
			raise ValueError('Directory path is empty')

		self.join(*parts)
		names = [name for part in parts for name in part.split(os.sep)]
		if any(name in ('', '.', '..') for name in names):
			raise ValueError('Invalid directory path components')

		directory = self

		for name in names:
			path = directory.join(name)
			if os.path.islink(path):
				raise ValueError(f'Symbolic link is not allowed: {path}')

			os.makedirs(path, exist_ok=True)
			child = directory.__children__.get(name)
			if child is not None and child.get_path() != path:
				directory._invalidate_children(path)

			directory = directory.__resolve__(name).load()
			if not directory.is_directory():
				raise TypeError(f'Not a directory: {path}')

		return directory

	# Read one exact filename through its registered format plugin.
	# ----------------------------------------------------------------------
	def read(self, name):
		self._destination(name)
		self._plugin(name)
		file = self.__resolve__(name)

		if file is None:
			raise FileNotFoundError(self.join(name))
		if file.is_directory():
			raise IsADirectoryError(file.get_path())

		return file.load()

	# Serialize through the format owner and atomically replace the destination.
	# ----------------------------------------------------------------------
	def write(self, name, value=''):
		path   = self._destination(name)
		plugin = self._plugin(name)

		self._replace(path, partial(plugin.write, value=value))

	# Copy a regular file byte-for-byte and atomically replace the destination.
	# ----------------------------------------------------------------------
	def copy(self, name, source):
		path = self._destination(name)
		mode = os.stat(source).st_mode

		if not stat.S_ISREG(mode):
			raise ValueError(f'Not a regular file: {source}')
		if os.path.exists(path) and os.path.samefile(source, path):
			raise ValueError(f'Source and destination are the same file: {path}')

		self._replace(path, partial(self._copy, source))

	# Create or retarget an explicit filesystem mount.
	# ----------------------------------------------------------------------
	def link(self, name, path):
		if not isinstance(name, str) or not name or name in ('.', '..') or os.path.basename(name) != name:
			raise ValueError(f'Invalid link name: {name}')

		link_path   = os.path.join(self.get_path(), name)
		target_path = os.path.realpath(path)

		if os.path.lexists(link_path):
			if not os.path.islink(link_path):
				raise FileExistsError(f'Non-link entry already exists at `{link_path}`')

			if target_path != os.path.realpath(link_path):
				os.remove(link_path)
				os.symlink(target_path, link_path)
		else:
			os.symlink(target_path, link_path)

		self._invalidate_children(link_path)

	# Realize a directory as its native namespace face.
	# ----------------------------------------------------------------------
	def load(self):
		return self
