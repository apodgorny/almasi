import os

from .file import File


class Directory(File):

	# Init
	# ----------------------------------------------------------------------
	def __init__(self, lib, path, route):
		super().__init__(lib, path, route)
		self.is_directory = True
		self.__children__ = {}

	# Resolve attribute access through resolver.
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		value = self.__resolve__(name)

		if value is None:
			raise AttributeError(f'Module `{self.route}.{name}` does not exist or no loading method is provided')

		return value.load()

	# Iterate contents
	# ----------------------------------------------------------------------
	def __iter__(self):
		for entry in os.listdir(self.path):
			if not entry.startswith('.'):
				value = self.__resolve__(entry)
				if value is not None:
					yield value

		# Resolve and cache on attr
	# ----------------------------------------------------------------------
	def __resolve__(self, name):
		value = self.__children__.get(name)

		if value is None:
			path  = os.path.realpath(self.path)
			route = None

			for instance in self.lib.__instances__():
				root       = os.path.realpath(instance.__path__)
				is_in_root = os.path.commonpath([path, root]) == root

				# Find relative route in first matching root
				# - - - - - - - - - - - - - - - - - - - - - - - -
				if route is None and is_in_root:
					route = os.path.relpath(path, root)

				# Resolve same route through current and parent roots
				# - - - - - - - - - - - - - - - - - - - - - - - -
				if route is not None:
					parent_path = os.path.realpath(os.path.join(root, route))
					is_root     = route != '.'
					is_dir      = os.path.isdir(parent_path)

					if is_dir and (is_root or parent_path == path):
						value = self.lib.__resolve__(name, parent_path, self.route)

						if value is not None:
							self.__children__[name] = value
							break
		return value

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create nested directories and return the resolved directory.
	# ----------------------------------------------------------------------
	def mkdir(self, *parts):
		names = []

		if parts:
			for part in parts:
				if isinstance(part, str) and part and not os.path.isabs(part):
					names.extend(part.split(os.sep))
				else:
					raise ValueError(f'Invalid directory path: {part}')

			if all(name not in ('', '.', '..') for name in names):
				directory = self

				for name in names:
					path = os.path.join(directory.path, name)

					if not os.path.islink(path):
						os.makedirs(path, exist_ok=True)
						directory = getattr(directory, name)

						if not isinstance(directory, Directory):
							raise TypeError(f'Not a directory: {path}')
					else:
						raise ValueError(f'Symbolic link is not allowed: {path}')
			else:
				raise ValueError('Invalid directory path components')
		else:
			raise ValueError('Directory path is empty')

		return directory

	# Write a file using the plugin responsible for its format.
	# ----------------------------------------------------------------------
	def write(self, name, value):
		if isinstance(name, str) and name and os.path.basename(name) == name and name not in ('.', '..'):
			path = os.path.join(self.path, name)
			ext  = os.path.splitext(name)[1].lstrip('.')

			plugin = None

			for instance in self.lib.__instances__():
				for candidate in instance.__PLUGINS__.values():
					if ext in candidate.EXTENSIONS:
						plugin = candidate
						break
				if plugin is not None:
					break

			if plugin is not None:
				if not os.path.islink(path):
					plugin.write(path, value)
					self.__children__.clear()
				else:
					raise ValueError(f'Symbolic link is not allowed: {path}')
			else:
				raise ValueError(f'Unsupported file extension: {ext}')
		else:
			raise ValueError(f'Invalid file name: {name}')

	# Create symlink
	# ----------------------------------------------------------------------
	def link(self, name, path):
		link_path   = os.path.join(self.path, name)
		target_path = os.path.realpath(path)

		if os.path.lexists(link_path):
			if not os.path.islink(link_path):
				raise FileExistsError(f'Non-link entry already exists at `{link_path}`')

			if target_path != os.path.realpath(link_path):
				os.remove(link_path)
				os.symlink(target_path, link_path)
		else:
			os.symlink(target_path, link_path)

	# Load
	# ----------------------------------------------------------------------
	def load(self):
		return self
