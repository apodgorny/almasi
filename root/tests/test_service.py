import os
import shutil
import sys

import a


class TestService(a.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Prepare source carriers for the native resolver.
	# ----------------------------------------------------------------------
	@classmethod
	def _source_root(cls):
		path = os.path.join(a.__path__, 'tests_runtime')
		os.makedirs(path, exist_ok=True)
		return path

	# Write one corresponding class into each source carrier.
	# ----------------------------------------------------------------------
	@classmethod
	def _write_source(cls, file_name, source):
		path = os.path.join(cls._source_root(), file_name)

		with open(path, 'w') as file:
			file.write(source)

		return path

	# Remove the disposable carriers and their native cache entries.
	# ----------------------------------------------------------------------
	@classmethod
	def _remove_runtime(cls):
		path = os.path.join(a.__path__, 'tests_runtime')

		if os.path.isdir(path):
			for module_name in list(sys.modules):
				if module_name.startswith(os.path.realpath(path)):
					del sys.modules[module_name]

			shutil.rmtree(path)

		a.__children__.pop('tests_runtime', None)
		a.__dict__.pop('tests_runtime', None)
		a.__cached_names__.discard('tests_runtime')

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Preserve explicit initialization and canonical singleton identity.
	# ----------------------------------------------------------------------
	@classmethod
	def test_service_is_singleton_and_initializes_on_explicit_call(cls):
		cls._remove_runtime()

		try:
			cls._write_source(
				'counting_service.py',
				(
					'import a\n\n'
					'class CountingService(a.Service):\n'
					'\tcount = 0\n\n'
					'\tdef initialize(self):\n'
					'\t\ttype(self).count += 1\n'
					'\t\tself.value = 13\n'
				)
			)
			one = a.tests_runtime.CountingService
			two = a.tests_runtime.CountingService

			error      = None
			init_error = None

			try:
				one.value
			except RuntimeError as e:
				error = e

			one.initialize()

			try:
				two.initialize()
			except RuntimeError as e:
				init_error = e

			assert one is two
			assert error is not None
			assert init_error is not None
			assert 'not initialized' in str(error)
			assert 'already initialized' in str(init_error)
			assert one.value == 13
			assert type(one).count == 1
		finally:
			cls._remove_runtime()

	# Permit ordinary missing-attribute defaults while initialization runs.
	# ----------------------------------------------------------------------
	@classmethod
	def test_service_allows_default_getattr_during_initialize(cls):
		cls._remove_runtime()

		try:
			cls._write_source(
				'initializing_service.py',
				(
					'import a\n\n'
					'class InitializingService(a.Service):\n\n'
					'\tdef initialize(self):\n'
					'\t\tself.value = getattr(self, ' + repr('missing') + ', 17)\n'
				)
			)
			service = a.tests_runtime.InitializingService

			service.initialize()

			assert service.value == 17
		finally:
			cls._remove_runtime()

	# Separate parent, child and sibling instances in either creation order.
	# ----------------------------------------------------------------------
	@classmethod
	def test_service_singletons_follow_concrete_classes(cls):
		for child_first in (False, True):
			class Parent(a.Service):
				pass

			class Child(Parent):
				pass

			class Sibling(Parent):
				pass

			if child_first:
				child  = Child()
				parent = Parent()
			else:
				parent = Parent()
				child  = Child()

			sibling = Sibling()
			assert type(parent) is Parent
			assert type(child) is Child
			assert type(sibling) is Sibling
			assert parent is Parent()
			assert child is Child()
			assert sibling is Sibling()
			assert parent is not child
			assert parent is not sibling
			assert child is not sibling

	# Resolve three levels through service instances and retain normal super().
	# ----------------------------------------------------------------------
	@classmethod
	def test_namespace_service_inheritance_and_initialization(cls):
		for parent_initialized in (False, True):
			cls._remove_runtime()

			try:
				cls._write_source(
					'base_service.py',
					'import a\n\n\n'
					'class BaseService(a.Service):\n'
					'\tdef initialize(self, value):\n'
					'\t\tself.value = value\n\n'
					'\tdef describe(self):\n'
					'\t\treturn (self.value,)\n'
				)
				cls._write_source(
					'middle_service.py',
					'import a\n\n\n'
					'class MiddleService(a.tests_runtime.BaseService):\n'
					'\tdef initialize(self, value):\n'
					'\t\tsuper().initialize(value + 1)\n\n'
					'\tdef describe(self):\n'
					'\t\treturn super().describe() + (17,)\n'
				)
				cls._write_source(
					'leaf_service.py',
					'import a\n\n\n'
					'class LeafService(a.tests_runtime.MiddleService):\n'
					'\tdef describe(self):\n'
					'\t\treturn super().describe() + (23,)\n'
				)
				base = a.tests_runtime.BaseService
				if parent_initialized:
					base.initialize(3)

				leaf   = a.tests_runtime.LeafService
				middle = a.tests_runtime.MiddleService
				error  = None

				try:
					leaf.value
				except RuntimeError as exception:
					error = exception

				assert error is not None
				assert 'not initialized' in str(error)
				assert type(leaf).__bases__ == (type(middle),)
				assert type(middle).__bases__ == (type(base),)
				assert leaf is a.tests_runtime.LeafService
				assert middle is a.tests_runtime.MiddleService
				assert base is a.tests_runtime.BaseService
				assert leaf is not middle
				assert middle is not base

				leaf.initialize(value=7)
				middle.initialize(11)
				if not parent_initialized:
					base.initialize(3)

				assert leaf.describe() == (8, 17, 23)
				assert middle.describe() == (12, 17)
				assert base.describe() == (3,)

				error = None
				try:
					leaf.initialize(19)
				except RuntimeError as exception:
					error = exception

				assert error is not None
				assert 'already initialized' in str(error)
				assert leaf.value == 8
			finally:
				cls._remove_runtime()

	# Retain inherited initialization and retry after its first failure.
	# ----------------------------------------------------------------------
	@classmethod
	def test_inherited_initializer_can_retry_after_failure(cls):
		class Parent(a.Service):

			# ======================================================================
			# PUBLIC METHODS
			# ======================================================================

			# Leave a failed initializer available for an explicit retry.
			# ----------------------------------------------------------------------
			def initialize(self, ready):
				if ready:
					self.value = getattr(self, 'missing', 29)
				else:
					raise ValueError('Not ready')

		class Child(Parent):
			pass

		child = Child()
		error = None

		try:
			child.initialize(False)
		except ValueError as exception:
			error = exception

		assert error is not None
		assert str(error) == 'Not ready'

		error = None
		try:
			child.value
		except RuntimeError as exception:
			error = exception

		assert error is not None
		assert 'not initialized' in str(error)
		child.initialize(True)
		assert child.value == 29
		assert child is Child()

	# Keep services with no initializer ready, including inherited services.
	# ----------------------------------------------------------------------
	@classmethod
	def test_namespace_service_inheritance_without_initializer(cls):
		cls._remove_runtime()

		try:
			cls._write_source(
				'ready_service.py',
				'import a\n\n\n'
				'class ReadyService(a.Service):\n'
				'\tdef read(self):\n'
				'\t\treturn 31\n'
			)
			cls._write_source(
				'ready_child.py',
				'import a\n\n\n'
				'class ReadyChild(a.tests_runtime.ReadyService):\n'
				'\tpass\n'
			)
			child  = a.tests_runtime.ReadyChild
			parent = a.tests_runtime.ReadyService
			error  = None

			assert child.read() == 31
			assert parent.read() == 31
			assert child is not parent

			try:
				child.initialize()
			except RuntimeError as exception:
				error = exception

			assert error is not None
			assert 'already initialized' in str(error)
		finally:
			cls._remove_runtime()

	# Preserve plugin ownership when creating a carrier.
	# ----------------------------------------------------------------------
	@classmethod
	def test_plugin_receives_owning_lib(cls):
		def call(self, name, parent_path, parent_route, source_lib):
			value = None

			if name == 'RuntimeThing':
				value = self.lib.File(
					self.lib,
					__file__,
					f'{parent_route}.{name}',
					lambda: self.lib.__name__,
				)

			return value

		RuntimePlugin = type('RuntimePlugin', (a.Plugin,), {'__call__' : call})

		plugin = RuntimePlugin(a)
		file   = plugin('RuntimeThing', a.__path__, 'a', source_lib=a)

		assert plugin.lib is a
		assert file.get_route() == 'a.RuntimeThing'
		assert file.load() == 'a'

	# Require the owning plugin to supply its execution contract.
	# ----------------------------------------------------------------------
	@classmethod
	def test_base_plugin_contract_raises(cls):
		plugin = a.Plugin(a)
		error  = None

		try:
			plugin('Name', a.__path__, 'a', source_lib=a)
		except NotImplementedError as e:
			error = e

		assert error is not None
		assert 'must implement __call__()' in str(error)


if __name__ == '__main__':
	TestService.run()
