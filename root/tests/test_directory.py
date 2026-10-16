import json
import os
import tempfile
import uuid

from unittest import TestCase
from unittest.mock import patch

import a


class TestDirectory(a.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create and resolve children in an explicitly supplied external directory.
	# ----------------------------------------------------------------------
	@classmethod
	def test_external_directory(cls):
		with tempfile.TemporaryDirectory() as path:
			directory = a.Directory(a, path, 'a.output')
			workspace = directory.mkdir('lesson', 'workspace')

			workspace.write('scenario.json', {'title': 'External output'})

			assert workspace.get_path() == os.path.realpath(os.path.join(path, 'lesson', 'workspace'))
			assert directory.lesson.workspace.scenario == {'title': 'External output'}

	# Round-trip supported text formats through the native namespace.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_text(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')

			for name, value in (('intro.md', '# Привет 🐍\n'), ('notes.txt', 'Hello, world!')):
				directory.write(name, value)

				assert getattr(directory, os.path.splitext(name)[0]) == value
				with open(os.path.join(path, name), encoding='utf-8') as file:
					assert file.read() == value

	# Preserve JSON data and readable UTF-8 formatting.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_json(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')
			value     = {'title': 'Урок 🐍', 'scenes': [], 'active': True}

			directory.write('scenario.json', value)

			assert directory.scenario == value
			with open(os.path.join(path, 'scenario.json'), encoding='utf-8') as file:
				assert file.read() == json.dumps(value, indent=2, ensure_ascii=False) + '\n'

	# Resolve a replacement carrier after writing through the same directory.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_refreshes_own_children(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')

			for name, before, after in (
				('notes.txt', 'before', 'after'),
				('scenario.json', {'value': 1}, {'value': 2}),
			):
				stem = os.path.splitext(name)[0]

				directory.write(name, before)
				assert getattr(directory, stem) == before

				directory.write(name, after)
				assert getattr(directory, stem) == after

	# Keep the resolver's existing extension priority when stems coincide.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_preserves_extension_priority(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')

			directory.write('notes.md', 'markdown')
			assert directory.notes == 'markdown'

			directory.write('notes.txt', 'text')
			assert directory.notes == 'text'

			directory.write('notes.md', 'updated markdown')
			assert directory.notes == 'text'
			with open(os.path.join(path, 'notes.md'), encoding='utf-8') as file:
				assert file.read() == 'updated markdown'

	# Reject invalid names and formats before creating a file.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_rejects_invalid_names(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')

			for name in ('', '.', '..', '../escape.txt', '/absolute.txt', 'nested/file.txt', None, 42):
				with TestCase().assertRaises(ValueError):
					directory.write(name, 'text')

			for name in ('notes', 'notes.yaml'):
				with TestCase().assertRaises(ValueError):
					directory.write(name, 'text')

			assert os.listdir(path) == []

	# Reject a non-string before opening an existing text file for writing.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_rejects_non_text(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')

			directory.write('notes.txt', 'original')

			with TestCase().assertRaises(TypeError):
				directory.write('notes.txt', {'value': 1})

			assert directory.notes == 'original'
			with open(os.path.join(path, 'notes.txt'), encoding='utf-8') as file:
				assert file.read() == 'original'

	# Refuse both live and dangling symbolic-link destinations.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_rejects_symbolic_links(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')
			target    = os.path.join(path, 'target.txt')

			directory.write('target.txt', 'original')
			os.symlink(target, os.path.join(path, 'notes.txt'))
			os.symlink(os.path.join(path, 'missing.txt'), os.path.join(path, 'missing_link.txt'))

			for name in ('notes.txt', 'missing_link.txt'):
				with TestCase().assertRaises(ValueError):
					directory.write(name, 'replacement')

			with open(target, encoding='utf-8') as file:
				assert file.read() == 'original'
			assert not os.path.exists(os.path.join(path, 'missing.txt'))

	# Use the owning plugin's serializer without bypassing library lineage.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_delegates_to_plugin(cls):
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__write_') as path:
			directory = a.Directory(a, path, 'a.write_test')
			plugin    = a.__PLUGINS__['Text']

			with patch.object(plugin, 'write', wraps=plugin.write) as write:
				directory.write('notes.txt', 'text')

				assert write.call_count == 1
				assert os.path.dirname(write.call_args.args[0]) == path
				assert os.path.basename(write.call_args.args[0]).startswith('.almasi-')
				assert write.call_args.args[0].endswith('.txt')
				assert write.call_args.kwargs == {'value': 'text'}

	# Delegate root writes and replace the library's cached child carrier.
	# ----------------------------------------------------------------------
	@classmethod
	def test_library_write(cls):
		name = '__write_' + uuid.uuid4().hex
		path = os.path.join(a.__path__, name + '.json')

		try:
			a.write(name + '.json', {'value': 1})
			assert getattr(a, name) == {'value': 1}

			a.write(name + '.json', {'value': 2})
			assert getattr(a, name) == {'value': 2}
		finally:
			if os.path.isfile(path):
				os.unlink(path)
			a.__children__.pop(name, None)


if __name__ == '__main__':
	TestDirectory.run()
