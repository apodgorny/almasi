import os


class File:

	# Create file.
	# ------------------------------------------------------------------
	def __init__(self, lib, path, route, load_method=None, hash_method=None):
		self.lib          = lib
		self.path         = os.path.realpath(path)
		self.route        = route
		self.is_directory = False
		self.name         = os.path.basename(self.path)

		self.data         = None
		self.hash         = None

		self.load_method  = load_method
		self.hash_method  = hash_method

	# String representation.
	# ------------------------------------------------------------------
	def __repr__(self):
		cls_name = type(self).__name__
		return f'<{cls_name} `{self.route}` path=`{self.path}`>'

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Load file into target object.
	# ------------------------------------------------------------------
	def load(self):
		# data = self.data

		if self.load_method is not None:
			# if self.hash_method is not None:
			# 	fresh_hash = self.hash_method()
			# 	if fresh_hash != self.hash:
			# 		self.data = self.load_method()
			# 		self.hash = fresh_hash
			# 	data = self.data
			# else:
			# 	data = self.load_method()
			if self.data is None:
				self.data = self.load_method()
			return self.data

		return None