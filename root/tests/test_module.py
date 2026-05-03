import os
import shutil
import sys

import a


class TestModule(a.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def _source_root(cls):
		path = os.path.join(a.__path__, 'tests_runtime')
		os.makedirs(path, exist_ok=True)
		return path

	# ----------------------------------------------------------------------
	@classmethod
	def _source_path(cls, file_name):
		return os.path.join(cls._source_root(), file_name)

	# ----------------------------------------------------------------------
	@classmethod
	def _write_source(cls, file_name, source):
		path = cls._source_path(file_name)

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
	def test_source_carrier_gets_route_lib_and_own_module(cls):
		cls._remove_runtime()

		try:
			path = cls._write_source(
				'source_carrier.py',
				(
					'import a\n\n'
					'class SourceCarrier(a.Module):\n'
					'\tvalue = 7\n'
				)
			)
			SourceCarrier = a.tests_runtime.SourceCarrier
			module        = sys.modules[os.path.realpath(path)]

			assert module.__lib__ is a.Imports.__lib__
			assert module.__route__ == 'a.tests_runtime.SourceCarrier'
			assert SourceCarrier.__route__ == 'a.tests_runtime.SourceCarrier'
			assert SourceCarrier.__has_own_module__ == True
			assert SourceCarrier.value == 7
			assert repr(SourceCarrier) == '<class \'a.tests_runtime.SourceCarrier\'>'
		finally:
			cls._remove_runtime()

	# ----------------------------------------------------------------------
	@classmethod
	def test_file_name_to_class_name_law_is_enforced(cls):
		cls._remove_runtime()
		error = None

		try:
			cls._write_source(
				'wrong_name.py',
				(
					'import a\n\n'
					'class NotWrongName(a.Module):\n'
					'\tpass\n'
				)
			)

			try:
				a.tests_runtime.WrongName
			except AttributeError as e:
				error = e

			assert error is not None
			assert 'WrongName' in str(error)
		finally:
			cls._remove_runtime()

	# ----------------------------------------------------------------------
	@classmethod
	def test_module_law_is_enforced(cls):
		cls._remove_runtime()
		error = None

		try:
			cls._write_source(
				'plain_carrier.py',
				(
					'class PlainCarrier:\n'
					'\tpass\n'
				)
			)

			try:
				a.tests_runtime.PlainCarrier
			except Exception as e:
				error = e

			assert error is not None
			assert 'does not extend from `Module`' in str(error)
		finally:
			cls._remove_runtime()

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_class_without_route_is_not_own_module(cls):
		RuntimeOnly = type('RuntimeOnly', (a.Module,), {'value' : 1})

		assert RuntimeOnly.__has_own_module__ == False
		assert '__route__' not in RuntimeOnly.__dict__
		assert RuntimeOnly.value == 1
