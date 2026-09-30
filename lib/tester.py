import os
import shutil
import sys

from .module import Module


def to_human(s):
	text = 'Test'

	if s.lower() != 'tester':
		text = s
		text = text.replace('tester', '')
		text = text.replace('Tester', '')
		text = text.strip('_')
		text = text.strip()

		if text:
			text = text[0].lower() + text[1:]
			text = text.replace('_', ' ')
			text = ''.join(
				f' {char.lower()}' if char.isupper() else char
				for char in text
			).strip()
			text = text.capitalize()
		else:
			text = 'Test'

	return text

def subheader(s):
	print('-' * 70)
	print(s)
	print('-' * 70)

def header(s, center=False):
	print('\n' + ('=' * 70) + '\n')
	print(s.center(70) if center else s)
	print('\n' + ('=' * 70) + '\n')


class Tester(Module):

	__lib__ = None

	# Iterate all loaded library roots
	# ----------------------------------------------------------------------
	@classmethod
	def roots(cls):
		seen = set()
		for instance in cls.__lib__.__instances__():
			path = getattr(instance, '__path__', None)
			if isinstance(path, str) and path not in seen:
				seen.add(path)
				yield path

	# Remove stale test runtime folders
	# ----------------------------------------------------------------------
	@classmethod
	def clean_fs(cls):
		for root in cls.roots():
			for path in ['__tmp__', 'tests_runtime']:
				path = os.path.join(root, '__tmp__')
				if os.path.isdir(path):
					shutil.rmtree(path)

	# Resolve test route
	# ----------------------------------------------------------------------
	@classmethod
	def _get_route(cls):
		module       = sys.modules.get(cls.__module__)
		route        = getattr(cls, '__route__', None)
		module_route = getattr(module, '__route__', None)
		file_path    = getattr(module, '__file__', None)

		if not cls._is_named_route(route): route = module_route
		if not cls._is_named_route(route): route = cls._get_route_from_file(file_path)
		if not cls._is_named_route(route): route = f'{cls.__lib__.__name__}.{cls.__name__}'

		return route

	# Check route shape
	# ----------------------------------------------------------------------
	@classmethod
	def _is_named_route(cls, route):
		if isinstance(route, str):
			return route not in ('', '__main__') and not route.endswith('.py')
		return False

	# Build route from source file
	# ----------------------------------------------------------------------
	@classmethod
	def _get_route_from_file(cls, file_path):
		route = None

		if isinstance(file_path, str):
			file_path = os.path.realpath(file_path)

			for instance in cls.__lib__.__instances__():
				root = os.path.realpath(instance.__path__)

				if os.path.commonpath([file_path, root]) == root:
					relative_dir = os.path.relpath(os.path.dirname(file_path), root)
					route = f'{instance.__name__}.{cls.__name__}'

					if relative_dir != '.':
						route = f'{instance.__name__}.{relative_dir.replace(os.sep, ".")}.{cls.__name__}'

					break

		return route

	# Run all tests for one library layer
	# ----------------------------------------------------------------------
	@classmethod
	def run_layer(cls, instance):
		test_count   = 0
		method_count = 0
		tests_dir    = None

		header(f'TESTING LIBRARY `{instance.__name__}`', center=True)

		if os.path.isdir(os.path.join(instance.__path__, 'tests')):
			tests_dir = instance.tests

		if tests_dir is not None:
			for test in tests_dir:
				if test.name.startswith('test'):
					t_cls = test.load()

					if isinstance(t_cls, type) and issubclass(t_cls, cls) and t_cls is not cls:
						method_count += t_cls.run()
						test_count   += 1

		if method_count == 0:
			print('-- No tests found --'.center(70))

		return test_count, method_count

	# Run all tests or current test class
	# ----------------------------------------------------------------------
	@classmethod
	def run(cls):
		result = None
		cls.clean_fs()

		try:
			if cls is Tester:
				test_count   = 0
				method_count = 0
				instances    = list(cls.__lib__.__instances__())

				instances.reverse()

				for instance in instances:
					layer_test_count, layer_method_count = cls.run_layer(instance)
					test_count   += layer_test_count
					method_count += layer_method_count

				header(f'✅ All {test_count} tests passed ({method_count} methods ran)')

				result = test_count, method_count
			else:
				test_class_name = to_human(cls.__name__)
				method_count    = 0
				route           = cls._get_route()

				subheader(f'{test_class_name}: {route}')

				for name, member in cls.__dict__.items():
					if name.startswith('test') and isinstance(member, classmethod):
						method = getattr(cls, name)
						method()
						method_count += 1
						print(f' ✅ {to_human(name)}')

				result = method_count
		finally:
			cls.clean_fs()

		return result
