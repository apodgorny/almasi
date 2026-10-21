# ==============================================================================
# TEST OWNERSHIP
# ==============================================================================
# Keep a component attached to the library that supplies its source.
# Check late loading and inheritance without replacing the native resolver.
# ==============================================================================


import os
import sys
import tempfile
import types

import a

from contextlib    import contextmanager
from unittest.mock import patch


class TestOwnership(a.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Create ordinary native libraries inside a disposable filesystem.
	# ----------------------------------------------------------------------
	@staticmethod
	def _library(name, root, ancestor):
		path              = os.path.join(root, name)
		module            = types.ModuleType(name)
		module.__file__   = path + '.py'
		sys.modules[name] = module

		os.makedirs(path)
		library = type(a.A)(name.title(), (ancestor,), {'__module__': name}, path=path)
		return library.__instance__

	# Restore the process globals after exercising real library creation.
	# ----------------------------------------------------------------------
	@staticmethod
	@contextmanager
	def _runtime():
		state = a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__
		try:
			with tempfile.TemporaryDirectory() as root, patch.dict(sys.modules):
				yield root
		finally:
			a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__ = state

	# Write a valid source carrier without executing it during preparation.
	# ----------------------------------------------------------------------
	@staticmethod
	def _source(library, name, ancestor='Module'):
		directory = library.mkdir('api')
		filename  = directory.join(library.String.camel_to_snake(name) + '.py')
		with open(filename, 'w') as stream:
			stream.write('import a\n\n\nclass ' + name + '(a.' + ancestor + '):\n\tpass\n')
		return filename

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Discovery before another import must not give the later load a new owner.
	# ----------------------------------------------------------------------
	@classmethod
	def test_deferred_source_and_resource_ownership(cls):
		with cls._runtime() as root:
			owner    = cls._library('ownership_owner', root, a.A)
			filename = cls._source(owner, 'Probe')
			carrier  = next(iter(owner.api))
			foreign  = cls._library('ownership_foreign', root, a.A)
			assert a.Imports.__lib__ is foreign
			probe = carrier.load()
			assert carrier.get_lib() is owner
			assert sys.modules[probe.__module__].__lib__ is owner
			assert owner.api.Probe is probe
			assert owner.Imports.load_module(foreign, filename).__lib__ is owner

			owner.write('notes.md', 'owner text')
			owner.write('data.json', {'owner': True})
			owner.write('clip.bin', b'owner bytes')
			assert owner.notes == 'owner text'
			assert owner.data == {'owner': True}
			assert owner.clip == b'owner bytes'
			assert all(item.get_lib() is owner for item in owner)
			assert a.__PLUGINS__['Py'].lib is a

	# A child reuses parent classes and services but owns its local overrides.
	# ----------------------------------------------------------------------
	@classmethod
	def test_inherited_identity_and_local_overrides(cls):
		for parent_first in (False, True):
			with cls._runtime() as root:
				parent = cls._library('ownership_parent', root, a.A)
				cls._source(parent, 'Probe')
				cls._source(parent, 'Shared', 'Service')
				cls._source(parent, 'Local')
				if parent_first:
					parent.api.Probe
				child = cls._library('ownership_child', root, type(parent))
				cls._source(child, 'Local')
				cls._library('ownership_other', root, a.A)
				assert child.api.Probe is parent.api.Probe
				assert sys.modules[child.api.Probe.__module__].__lib__ is parent
				assert child.api.Shared is parent.api.Shared
				assert sys.modules[type(child.api.Shared).__module__].__lib__ is parent
				assert child.api.Local is not parent.api.Local
				assert sys.modules[child.api.Local.__module__].__lib__ is child
