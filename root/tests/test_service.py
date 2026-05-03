import os
import shutil
import sys

import a


class TestService(a.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def _source_root(cls):
		path = os.path.join(a.__path__, 'tests_runtime')
		os.makedirs(path, exist_ok=True)
		return path

	# ----------------------------------------------------------------------
	@classmethod
	def _write_source(cls, file_name, source):
		path = os.path.join(cls._source_root(), file_name)

		with open(path, 'w') as file:
			file.write(source)

		return path

	# ----------------------------------------------------------------------
	@classmethod
	def _remove_runtime(cls):
		path = os.path.join(a.__path__, 'tests_runtime')

		if os.path.isdir(path):
			for module_name in list(sys.modules):
				if module_name.startswith(os.path.realpath(path)):
					del sys.modules[module_name]

			shutil.rmtree(path)

		if 'tests_runtime' in a.__children__:
			del a.__children__['tests_runtime']

	# ----------------------------------------------------------------------
	@classmethod
	def test_service_is_singleton_and_initializes_once(cls):
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

			assert one is two
			assert one.value == 13
			assert type(one).count == 1
		finally:
			cls._remove_runtime()

	# ----------------------------------------------------------------------
	@classmethod
	def test_plugin_receives_owning_lib(cls):
		def call(self, name, parent_path, parent_route):
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
		file   = plugin('RuntimeThing', a.__path__, 'a')

		assert plugin.lib is a
		assert file.route == 'a.RuntimeThing'
		assert file.load() == 'a'

	# ----------------------------------------------------------------------
	@classmethod
	def test_base_plugin_contract_raises(cls):
		plugin = a.Plugin(a)
		error  = None

		try:
			plugin('Name', a.__path__, 'a')
		except NotImplementedError as e:
			error = e

		assert error is not None
		assert 'must implement __call__()' in str(error)
