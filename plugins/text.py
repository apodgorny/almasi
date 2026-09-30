import os

import a


class Text(a.Plugin):

	EXTENSIONS = ('txt', 'md')

	# Resolve text file
	# ----------------------------------------------------------------------
	def __resolve__(self, name, parent_path):
		file_path = None
		names     = [name, self.lib.String.camel_to_snake(name)]

		for base_name in names:
			for ext in self.EXTENSIONS:
				current_path = os.path.join(parent_path, f'{base_name}.{ext}')

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
			def load_method(): return self.load(file_path)
			def hash_method(): return os.path.getmtime(file_path)

			file = self.lib.File(
				self.lib,
				file_path,
				route,
				load_method,
				hash_method,
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
