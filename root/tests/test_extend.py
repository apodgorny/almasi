# ==============================================================================
# TEST LIBRARY EXTENSION
# ==============================================================================
# Verify canonical identity, inherited loading, and explicit initialization.
# ==============================================================================

import importlib
import os
import runpy
import sys
import tempfile

import a

from contextlib    import contextmanager
from unittest.mock import patch


class TestExtend(a.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Isolate module publication and restore shared library ownership.
	# ----------------------------------------------------------------------
	@staticmethod
	@contextmanager
	def _runtime():
		state = a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__

		try:
			with tempfile.TemporaryDirectory() as root, patch.dict(sys.modules), patch.object(sys, 'path', list(sys.path)):
				yield root
		finally:
			a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__ = state

	# Write an importable library with its own filesystem root.
	# ----------------------------------------------------------------------
	@staticmethod
	def _source(root, name, code):
		directory = os.path.join(root, name)
		os.makedirs(os.path.join(directory, 'root'))
		path = os.path.join(directory, f'{name}.py')

		with open(path, 'w') as file:
			file.write(code)

		return directory

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Preserve native imports, MRO, source ownership, and service identity.
	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_preserves_library_resolution(cls):
		with cls._runtime() as root:
			parent_dir = cls._source(root, 'extend_parent', '''import a

extend_parent = a.extend('extend_parent')
''')
			child_dir  = cls._source(root, 'extend_child', '''import extend_parent

extend_child = extend_parent.extend('extend_child')
''')
			os.makedirs(os.path.join(parent_dir, 'root', 'api'))

			with open(os.path.join(parent_dir, 'root', 'api', 'shared.py'), 'w') as file:
				file.write('import a\n\nclass Shared(a.Service):\n\tpass\n')

			sys.path[:0] = [child_dir, parent_dir]
			child  = importlib.import_module('extend_child')
			parent = importlib.import_module('extend_parent')

			assert sys.modules['extend_parent'] is parent
			assert sys.modules['extend_child'] is child
			assert type(child).__bases__ == (type(parent),)
			assert child.__path__ == os.path.join(child_dir, 'root')
			assert parent.api.Shared is child.api.Shared
			assert sys.modules[type(child.api.Shared).__module__].__lib__ is parent

	# Do not invoke an inherited initializer a second time.
	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_skips_inherited_initialize(cls):
		with cls._runtime() as root:
			parent_dir = cls._source(root, 'extend_legacy', '''import a

class ExtendLegacy(a.A):
\tdef initialize(self):
\t\tself.ready = True
''')
			child_dir  = cls._source(root, 'extend_child', '''import extend_legacy

extend_child = extend_legacy.extend('extend_child')
''')
			sys.path[:0] = [child_dir, parent_dir]
			child  = importlib.import_module('extend_child')
			parent = importlib.import_module('extend_legacy')

			assert parent.ready is True
			assert 'ready' not in child.__dict__
			assert type(child).__bases__ == (type(parent),)

	# Keep __main__ intact and run entry-point code only for direct execution.
	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_from_main(cls):
		with cls._runtime() as root:
			app_dir = cls._source(root, 'extend_app', '''import a

extend_app = a.extend('extend_app')

if __name__ == '__main__':
\textend_app.started = True
''')
			main   = sys.modules['__main__']
			result = runpy.run_path(os.path.join(app_dir, 'extend_app.py'), run_name='__main__')
			app    = result['extend_app']

			assert sys.modules['__main__'] is main
			assert sys.modules['extend_app'] is app
			assert app.started is True
			assert app.__name__ == 'extend_app'

	# Reject names unrelated to the source module.
	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_rejects_mismatched_source(cls):
		with cls._runtime() as root:
			directory = cls._source(root, 'extend_named', '''import a

extend_named = a.extend('another_name')
''')
			sys.path.insert(0, directory)
			error = None

			try:
				importlib.import_module('extend_named')
			except ValueError as exception:
				error = str(exception)

			assert error is not None
			assert 'must match' in error

	# Reject noncanonical snake_case names before publishing anything.
	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_rejects_invalid_name(cls):
		with cls._runtime() as root:
			directory = cls._source(root, 'extend_invalid', '''import a

extend_invalid = a.extend('InvalidName')
''')
			sys.path.insert(0, directory)
			error = None

			try:
				importlib.import_module('extend_invalid')
			except ValueError as exception:
				error = str(exception)

			assert error is not None
			assert 'Invalid library name' in error
