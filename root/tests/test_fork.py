# ==============================================================================
# TEST LIBRARY FORKS
# ==============================================================================
# Verify fork isolation through genuine Almasi module and service resolution.
# ==============================================================================

import importlib
import importlib.util
import os
import sys
import tempfile

from contextlib import contextmanager

import a


class TestFork(a.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Write a source carrier into the temporary library's root.
	# ----------------------------------------------------------------------
	@staticmethod
	def _write(root, name, source):
		path = os.path.join(root, name)
		os.makedirs(os.path.dirname(path), exist_ok=True)

		with open(path, 'w', encoding='utf-8') as stream:
			stream.write(source)

		return path

	# Exercise a published library while keeping its Python modules disposable.
	# ----------------------------------------------------------------------
	@staticmethod
	@contextmanager
	def _runtime():
		name = 'almasi_fork_fixture'

		with tempfile.TemporaryDirectory(prefix='almasi-fork-') as folder:
			root = os.path.join(folder, 'root')
			os.makedirs(os.path.join(root, 'services'))

			TestFork._write(folder, name + '.py', (
				'import a\n'
				+ name + ' = a.extend(\'' + name + '\')\n'
			))
			TestFork._write(root, 'item.py', '''
import almasi_fork_fixture


class Item(almasi_fork_fixture.Module):

	def owner(self):
		return almasi_fork_fixture

	def service(self):
		return eval('almasi_fork_fixture.services.Counter')
''')
			TestFork._write(root, 'import_sample.py', '''
from almasi_fork_fixture import services
import almasi_fork_fixture


class ImportSample(almasi_fork_fixture.Module):

	def service(self):
		return services.Counter
''')
			TestFork._write(root, 'qualified_import.py', '''
import almasi_fork_fixture.services


class QualifiedImport(almasi_fork_fixture.Module):

	def service(self):
		return almasi_fork_fixture.services.Counter
''')
			TestFork._write(root, 'services/counter.py', '''
import almasi_fork_fixture


class Counter(almasi_fork_fixture.Service):

	def initialize(self):
		self.value = 0

	def increment(self):
		self.value += 1
		return self.value
''')
			spec         = importlib.util.spec_from_file_location(name, os.path.join(folder, name + '.py'))
			module       = importlib.util.module_from_spec(spec)
			previous_lib = (a.Undefined.__lib__, a.Imports.__lib__, a.Tester.__lib__)

			sys.modules[name] = module

			try:
				spec.loader.exec_module(module)
				yield sys.modules[name], root
			finally:
				a.Undefined.__lib__, a.Imports.__lib__, a.Tester.__lib__ = previous_lib

				for module_name in tuple(sys.modules):
					if module_name == name or module_name.startswith(os.path.realpath(root) + os.sep):
						sys.modules.pop(module_name, None)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Keep the default library canonical and reject duplicate fork names.
	# ----------------------------------------------------------------------
	@classmethod
	def test_named_forks_and_default(cls):
		with cls._runtime() as (library, root):
			alice = library.fork('alice')
			bob   = library.fork('bob')
			error = None

			try:
				library.fork('alice')
			except ValueError as exception:
				error = exception

			assert library['default'] is library
			assert library['alice'] is alice
			assert library['bob'] is bob
			assert alice is not bob
			assert error is not None
			assert sys.modules[library.__name__] is library

	# Bind ordinary imports and eval() to the current fork's module globals.
	# ----------------------------------------------------------------------
	@classmethod
	def test_internal_imports_and_eval(cls):
		with cls._runtime() as (library, root):
			alice = library.fork('alice')
			bob   = library.fork('bob')

			assert library.Item().owner() is library
			assert alice.Item().owner() is alice
			assert bob.Item().owner() is bob
			assert alice.Item is not bob.Item
			assert alice.Item is not library.Item
			assert alice.Item.owner.__code__ is bob.Item.owner.__code__
			assert alice.Item().service() is alice.services.Counter
			assert bob.Item().service() is bob.services.Counter
			assert alice.ImportSample().service() is alice.services.Counter
			assert alice.QualifiedImport().service() is alice.services.Counter
			assert importlib.import_module(library.__name__) is library

	# Keep the service class and its singleton separate for each fork.
	# ----------------------------------------------------------------------
	@classmethod
	def test_independent_service_state(cls):
		with cls._runtime() as (library, root):
			alice = library.fork('alice')
			bob   = library.fork('bob')

			default_service = library.services.Counter
			alice_service   = alice.services.Counter
			bob_service     = bob.services.Counter

			default_service.initialize()
			alice_service.initialize()
			bob_service.initialize()

			assert type(alice_service) is not type(bob_service)
			assert type(alice_service) is not type(default_service)
			assert alice_service is type(alice_service)()
			assert bob_service is type(bob_service)()
			assert alice_service.increment() == 1
			assert alice_service.increment() == 2
			assert bob_service.increment() == 1
			assert default_service.value == 0
			assert alice_service.value == 2

	# Capture the parent's configuration but allocate fresh class identities.
	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_forks_and_configuration(cls):
		with cls._runtime() as (library, root):
			library.settings = {'values' : [1]}
			parent           = library.fork('parent')
			parent_item      = parent.Item
			child            = parent.fork('child')

			parent.settings['values'].append(2)
			child.settings['values'].append(3)

			assert parent['child'] is child
			assert library['parent'] is parent
			assert parent.Item is parent_item
			assert child.Item is not parent.Item
			assert child.Item().owner() is child
			assert library.settings == {'values' : [1]}
			assert parent.settings == {'values' : [1, 2]}
			assert child.settings == {'values' : [1, 3]}

	# Keep another fork's loaded methods and service state through hot reload.
	# ----------------------------------------------------------------------
	@classmethod
	def test_reload_is_fork_local(cls):
		with cls._runtime() as (library, root):
			alice = library.fork('alice')
			bob   = library.fork('bob')

			alice_service = alice.services.Counter
			bob_service   = bob.services.Counter

			alice_service.initialize()
			bob_service.initialize()
			assert alice_service.increment() == 1

			cls._write(root, 'services/counter.py', '''
import almasi_fork_fixture


class Counter(almasi_fork_fixture.Service):

	def initialize(self):
		raise AssertionError('Already initialized')

	def increment(self):
		self.value += 10
		return self.value
''')
			assert alice_service.__reload__() is alice_service
			assert alice.services.Counter is alice_service
			assert type(alice_service)() is alice_service
			assert alice_service.increment() == 11
			assert bob.services.Counter is bob_service
			assert bob_service.increment() == 1


if __name__ == '__main__':
	TestFork.run()
