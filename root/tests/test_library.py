import os
import sys

import a


class TestLibrary(a.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def test_published_face_is_canonical_instance(cls):
		import a as imported

		assert imported is a
		assert sys.modules['a'] is a
		assert type(a).__name__ == 'A'
		assert type(a).__instance__ is a
		assert a.A is type(a)

	# ----------------------------------------------------------------------
	@classmethod
	def test_library_paths_are_separate(cls):
		lib_path  = os.path.dirname(os.path.realpath(a.__lib_file__))
		root_path = os.path.join(lib_path, 'root')

		assert os.path.realpath(a.__path__) == root_path
		assert os.path.realpath(a.__lib_path__) == lib_path
		assert os.path.basename(a.__lib_file__) == 'a.py'
		assert a.__path__ != a.__lib_path__

	# ----------------------------------------------------------------------
	@classmethod
	def test_kernel_names_are_intrinsic(cls):
		assert a.Module is a.A.Module
		assert a.ModuleMeta is a.A.ModuleMeta
		assert a.File is a.A.File
		assert a.Directory is a.A.Directory
		assert a.Plugin is a.A.Plugin
		assert a.Service is a.A.Service
		assert a.Imports is a.A.Imports
		assert a.Undefined is a.A.Undefined
		assert a.String is a.A.String
		assert a.Timer is a.A.Timer
		assert a.Tester is a.A.Tester
		assert a.tester is a.Tester

	# ----------------------------------------------------------------------
	@classmethod
	def test_shared_lib_contract_points_to_instance(cls):
		instance = a.Tester.__lib__

		assert a.Imports.__lib__ is instance
		assert a.Tester.__lib__ is instance
		assert a.Undefined.__lib__ is instance
		assert instance in list(instance.__instances__())

	# ----------------------------------------------------------------------
	@classmethod
	def test_instances_iterate_lineage_heads(cls):
		instances = list(a.__instances__())

		assert instances == [a]
		assert instances[0].__name__ == 'a'
		assert instances[0].__spec__ is None
		assert isinstance(instances[0].__children__, dict)

	# ----------------------------------------------------------------------
	@classmethod
	def test_repr_and_missing_attribute(cls):
		error = None

		assert repr(a) == '<Library `a`>'

		try:
			a.NoSuchAlmasiThing
		except AttributeError as e:
			error = e

		assert error is not None
		assert str(error) == 'Library `a` has no attribute `NoSuchAlmasiThing`'

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_test_entrypoint_is_not_resolved_as_namespace_child(cls):
		error = None

		try:
			a.test
		except AttributeError as e:
			error = e

		assert error is not None
		assert 'test' in str(error)


if __name__ == '__main__':
	TestLibrary.run()
