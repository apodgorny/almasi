import os
import sys


def create_root(path):
	os.makedirs(os.path.join(path, 'root'))


def create_module(path, name, libraries=[]):
	class_name = ''.join(part.capitalize() for part in name.split('_'))

	imports = ''.join(f'import {library}\n' for library in libraries)

	with open(os.path.join(path, f'{name}.py'), 'w') as file:
		file.write(
			f'{imports}\n' if imports else ''
			f'from a import A\n\n'
			f'class {class_name}(A):\n'
			f'\tpass\n'
		)


def create_pyproject(path, name):
	with open(os.path.join(path, 'pyproject.toml'), 'w') as file:
		file.write(
			'[build-system]\n'
			'requires = ["setuptools>=80"]\n'
			'build-backend = "setuptools.build_meta"\n\n'
			'[project]\n'
			f'name = "{name}"\n'
			'version = "0.1.0"\n'
			'requires-python = ">=3.11"\n'
			'dependencies = []\n\n'
			'[tool.setuptools]\n'
			f'py-modules = ["{name}"]\n'
		)


def create_lib(name):
	path = os.path.join(os.getcwd(), name)

	if os.path.exists(path):
		print(f'Already exists: {path}')
		return 1

	os.makedirs(path)

	create_root(path)
	create_module(path, name)
	create_pyproject(path, name)

	print(f'Created library: {path}')
	return 0


def create_app(name, libraries):
	path = os.path.join(os.getcwd(), name)

	if os.path.exists(path):
		print(f'Already exists: {path}')
		return 1

	os.makedirs(path)

	create_root(path)
	create_module(path, name, libraries)
	create_pyproject(path, name)

	print(f'Created app: {path}')
	return 0


def main():
	if len(sys.argv) < 2:
		print('Usage: almasi <command> [args]')
		return 1

	command = sys.argv[1]

	if command == 'lib':
		if len(sys.argv) != 3:
			print('Usage: almasi lib <name>')
			return 1

		return create_lib(sys.argv[2])

	if command == 'app':
		if len(sys.argv) < 3:
			print('Usage: almasi app <name> [libraries...]')
			return 1

		return create_app(sys.argv[2], sys.argv[3:])

	print(f'Unknown command: {command}')
	return 1


if __name__ == '__main__':
	sys.exit(main())