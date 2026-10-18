import os

from functools import partial

import a


class Bytes(a.Plugin):

	EXTENSIONS = ('bin', 'webm', 'mp4', 'wav', 'mp3')

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Resolve binary resources through the same native carriers as other formats.
	# ----------------------------------------------------------------------
	def __call__(self, name, parent_path, parent_route):
		file  = None
		bases = [name] if os.path.splitext(name)[1] else [name, self.lib.String.camel_to_snake(name)]
		for base in bases:
			names = [base] if os.path.splitext(base)[1] else [f'{base}.{ext}' for ext in self.EXTENSIONS]
			for candidate in names:
				path = os.path.join(parent_path, candidate)
				if os.path.splitext(candidate)[1].lstrip('.') in self.EXTENSIONS and os.path.isfile(path):
					file = self.lib.File(
						self.lib, path, f'{parent_route}.{name}',
						partial(self.load, path),
						partial(os.path.getmtime, path),
					)
					break
			if file is not None:
				break
		return file

	# Return the original bytes without decoding or conversion.
	# ----------------------------------------------------------------------
	def load(self, path):
		with open(path, 'rb') as file:
			value = file.read()
		return value

	# Let Directory own atomic publication and carrier invalidation.
	# ----------------------------------------------------------------------
	def write(self, path, value):
		if isinstance(value, bytes):
			with open(path, 'wb') as file:
				file.write(value)
		else:
			raise TypeError('Binary content must be bytes')
