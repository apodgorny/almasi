import os


class File:

	# Keep identity separate from the filesystem namespace.
	# ----------------------------------------------------------------------
	def __init__(self, lib, path, route, load_method=None, hash_method=None):
		self.__lib__   = lib
		self.__path__  = os.path.realpath(path)
		self.__route__ = route

		self._data   = None
		self._hash   = None
		self._loaded = False

		self._load_method = load_method
		self._hash_method = hash_method

	# Describe the carrier without realizing its content.
	# ----------------------------------------------------------------------
	def __repr__(self):
		return f'<{type(self).__name__} `{self.get_route()}` path=`{self.get_path()}`>'

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Forget content after a successful filesystem mutation.
	# ----------------------------------------------------------------------
	def _invalidate(self):
		self._data   = None
		self._hash   = None
		self._loaded = False

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Get the canonical physical path.
	# ----------------------------------------------------------------------
	def get_path(self):
		return self.__path__

	# Get the logical namespace route.
	# ----------------------------------------------------------------------
	def get_route(self):
		return self.__route__

	# Get the owning library.
	# ----------------------------------------------------------------------
	def get_lib(self):
		return self.__lib__

	# Get the physical filename or directory name.
	# ----------------------------------------------------------------------
	def get_name(self):
		return os.path.basename(self.__path__)

	# Distinguish file carriers from directory carriers.
	# ----------------------------------------------------------------------
	def is_directory(self):
		return False

	# Memoize legitimate null values as well as other plugin results.
	# ----------------------------------------------------------------------
	def load(self):
		if not self._loaded and self._load_method is not None:
			self._data   = self._load_method()
			self._loaded = True

		return self._data
