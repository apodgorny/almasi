import os
import json

import a


class Json(a.Plugin):

	EXTENSIONS = ('json',)

	# Resolve data file
	# ----------------------------------------------------------------------
	def __resolve__(self, name, parent_path):
		file_path = None
		ext       = None
		names     = [name, self.lib.String.camel_to_snake(name)]

		for base_name in names:
			for current_ext in self.EXTENSIONS:
				current_path = os.path.join(parent_path, f'{base_name}.{current_ext}')

				if os.path.isfile(current_path):
					file_path = current_path
					ext       = current_ext
					break

			if file_path is not None:
				break

		return file_path, ext

	# Resolve data carrier
	# ----------------------------------------------------------------------
	def __call__(self, name, parent_path, parent_route):
		file_path, ext = self.__resolve__(name, parent_path)
		route          = f'{parent_route}.{name}'
		file           = None

		if file_path is not None:
			def load_method(): return self.load(file_path, ext)
			def hash_method(): return os.path.getmtime(file_path)

			file = self.lib.File(
				self.lib,
				file_path,
				route,
				load_method,
				hash_method,
			)

		return file

	# Load data file
	# ----------------------------------------------------------------------
	def load(self, file_path, ext):
		value = None

		if file_path is not None:
			with open(file_path, 'r', encoding='utf-8') as file:
				content = file.read()

			if content.strip() == '':
				raise ValueError(f'Data file `{file_path}` is empty')

			try:
				value = json.loads(content)
			except json.JSONDecodeError as error:
				raise ValueError(f'Invalid JSON in `{file_path}`: {error}') from error

		return value