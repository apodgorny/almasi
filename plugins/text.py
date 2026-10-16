import os

from functools import partial

import a


class Text(a.Plugin):

	EXTENSIONS = ('txt', 'md')

	# Resolve text file
	# ----------------------------------------------------------------------
	def __resolve__(self, name, parent_path):
		file_path = None
		names     = [name] if os.path.splitext(name)[1] else [name, self.lib.String.camel_to_snake(name)]

		for base_name in names:
			extension  = os.path.splitext(base_name)[1].lstrip('.')
			candidates = []

			if extension in self.EXTENSIONS:
				candidates = [base_name]
			elif not extension:
				candidates = [f'{base_name}.{ext}' for ext in self.EXTENSIONS]

			for candidate in candidates:
				current_path = os.path.join(parent_path, candidate)
				if os.path.isfile(current_path):
					file_path = current_path
					break

			if file_path is not None:
				break

		return file_path

	# Resolve text carrier
	# ----------------------------------------------------------------------
	def __call__(self, name, parent_path, parent_route):
		file_path = self.__resolve__(name, parent_path)
		route     = f'{parent_route}.{name}'
		file      = None

		if file_path is not None:
			file = self.lib.File(
				self.lib, file_path, route,
				partial(self.load, file_path),
				partial(os.path.getmtime, file_path)
			)

		return file

	# Load text file
	# ----------------------------------------------------------------------
	def load(self, file_path):
		value = None

		if file_path is not None:
			with open(file_path, 'r', encoding='utf-8') as file:
				value = file.read()

		return value

	# Write UTF-8 text.
	# ----------------------------------------------------------------------
	def write(self, path, value):
		if isinstance(value, str):
			with open(path, 'w', encoding='utf-8') as file:
				file.write(value)
		else:
			raise TypeError('Text content must be a string')
