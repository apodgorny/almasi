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
