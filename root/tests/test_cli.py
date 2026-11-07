# ==============================================================================
# TEST CLI
# ==============================================================================
# Ensure generated libraries use canonical extend declarations and inheritance.
# ==============================================================================

import importlib
import importlib.util
import os
import sys
import tempfile

from unittest.mock import patch

import a


class TestCli(a.Tester):

	# Generate a parent and child and import them through their native namespaces.
	# ----------------------------------------------------------------------
	@classmethod
	def test_scaffold_uses_extend(cls):
		spec = importlib.util.spec_from_file_location('almasi_cli', os.path.join(a.__lib_path__, 'cli.py'))
		cli  = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(cli)

		state = a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__
		try:
			with tempfile.TemporaryDirectory() as root, patch.dict(sys.modules), patch.object(sys, 'path', list(sys.path)):
				parent = os.path.join(root, 'cli_parent')
				child  = os.path.join(root, 'cli_child')
				for directory, name, ancestor in ((parent, 'cli_parent', 'a'), (child, 'cli_child', 'cli_parent')):
					os.makedirs(directory)
					cli.create_root(directory)
					cli.create_module(directory, name, ancestor)

				sys.path[:0] = [child, parent]
				assert cli.get_parent_lib('cli_parent') == 'a'
				assert cli.get_parent_lib('cli_child') == 'cli_parent'
				assert cli.get_lib_chain('cli_child', 'cli_parent') == ['cli_child', 'cli_parent', 'a']

				child_lib  = importlib.import_module('cli_child')
				parent_lib = importlib.import_module('cli_parent')
				assert type(child_lib).__bases__ == (type(parent_lib),)
				assert sys.modules['cli_child'] is child_lib
		finally:
			a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__ = state
