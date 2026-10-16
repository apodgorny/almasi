import os
import json

from functools import partial

import a


class Json(a.Plugin):

	EXTENSIONS = ('json',)

	# Resolve data file
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

		return file_path, os.path.splitext(file_path)[1].lstrip('.') if file_path is not None else None

	# Resolve data carrier
	# ----------------------------------------------------------------------
	def __call__(self, name, parent_path, parent_route):
		file_path, ext = self.__resolve__(name, parent_path)
		route          = f'{parent_route}.{name}'
		file           = None

		if file_path is not None:
			file = self.lib.File(
				self.lib, file_path, route,
				partial(self.load, file_path, ext),
				partial(os.path.getmtime, file_path)
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

	# Serialize data into a JSON file.
	# ----------------------------------------------------------------------
	def write(self, path, value):
		with open(path, 'w', encoding='utf-8') as file:
			json.dump(value, file, indent=2, ensure_ascii=False)
			file.write('\n')
