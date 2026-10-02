import os
import sys
import subprocess
import ast
import importlib.util


def get_parent_lib(name):
	spec = importlib.util.find_spec(name)
	if spec is None or spec.origin is None or not os.path.isfile(spec.origin):
		return None
	with open(spec.origin) as file:
		tree = ast.parse(file.read())
	for node in tree.body:
		if not isinstance(node, ast.ClassDef):
			continue
		if not node.bases:
			continue
		base = node.bases[0]
		if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
			return base.value.id
		if isinstance(base, ast.Name):
			return base.id
	return None


def get_lib_chain(name, lib):
	chain = [name]
	while lib:
		chain.append(lib)
		if lib == 'a':
			break
		lib = get_parent_lib(lib)
	return chain


def to_class_name(name):
	return ''.join(part.capitalize() for part in name.split('_'))


def create_root(path):
	os.makedirs(os.path.join(path, 'root'))


def create_module(path, name, kind, lib):
	class_name = to_class_name(name)

	if lib == 'a':
		import_line = 'import a'
		base = 'a.A' if kind == 'Lib' else 'a.A'
	else:
		import_line = f'import {lib}'
		base = f'{lib}.{to_class_name(lib)}'

	with open(os.path.join(path, f'{name}.py'), 'w') as file:
		file.write(
			f'{import_line}\n\n'
			f"class {class_name}({base}, path='root'):\n"
			'\tpass\n'
		)


def create_demo_class(path, name, lib):
	class_name = 'DemoClass'
	file_name  = 'demo_class'

	if lib == 'a':
		import_line = 'import a'
		base = 'a.Module'
	else:
		import_line = f'import {lib}'
		base = f'{lib}.Module'

	with open(os.path.join(path, 'root', f'{file_name}.py'), 'w') as file:
		file.write(
			f'{import_line}\n\n'
			f'class {class_name}({base}):\n'
			'\n'
			'\tdef hello(self):\n'
			f"\t\tprint('Hello from {name}')\n"
		)


def create_pyproject(path, name, lib):
	dependencies = "['a']" if lib == 'a' else f"['{lib}']"

	with open(os.path.join(path, 'pyproject.toml'), 'w') as file:
		file.write(
			'[build-system]\n'
			"requires = ['setuptools>=80']\n"
			"build-backend = 'setuptools.build_meta'\n\n"
			'[project]\n'
			f"name = '{name}'\n"
			"version = '0.1.0'\n"
			"requires-python = '>=3.11'\n"
			f'dependencies = {dependencies}\n\n'
			'[tool.setuptools]\n'
			f"py-modules = ['{name}']\n"
		)


def create_main(path, name, lib):
	chain = get_lib_chain(name, lib)
	with open(os.path.join(path, 'main.py'), 'w') as file:
		for module in chain:
			file.write(f'import {module}\n')
		file.write('\n')
		for module in chain:
			file.write(f'{module}.DemoClass().hello()\n')

def install(path):
	subprocess.run(
		[sys.executable, '-m', 'pip', 'install', '-e', path],
		check=True
	)


def create(name, kind, lib='a'):
	path = os.path.abspath(name)

	if os.path.exists(path):
		raise ValueError(f'Path already exists: {path}')

	os.makedirs(path)
	create_root(path)
	create_module(path, name, kind, lib)
	create_demo_class(path, name, lib)
	create_main(path, name, lib)

	if kind == 'Lib':
		create_pyproject(path, name, lib)
		install(path)

	print(f'{kind} \'{name}\' created at {path}')


def validate_name(name):
	if not name or name[0].isdigit() or any(
		not (char.isalnum() or char == '_')
		for char in name
	):
		raise ValueError(f'Invalid name: {name}')


def main():
	if len(sys.argv) < 3 or len(sys.argv) > 4:
		print('Usage: almasi lib <name> [lib] | almasi app <name> [lib]')
		sys.exit(1)

	kind = sys.argv[1]
	name = sys.argv[2]
	lib = sys.argv[3] if len(sys.argv) == 4 else 'a'

	if kind not in ('lib', 'app'):
		print('Usage: almasi lib <name> [lib] | almasi app <name> [lib]')
		sys.exit(1)

	validate_name(name)
	validate_name(lib)

	kind = kind.capitalize()

	create(name, kind, lib)


if __name__ == '__main__':
	main()
