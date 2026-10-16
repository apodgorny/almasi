import os
import sys
import tempfile
import types

from functools import partial
from unittest import TestCase
from unittest.mock import Mock, patch

import a


class TestFilesystem(a.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Construct isolated native library faces without changing real roots.
	# ----------------------------------------------------------------------
	@classmethod
	def _library(cls, name, root, ancestor):
		module            = types.ModuleType(name)
		module.__file__   = root + '.py'
		sys.modules[name] = module

		state = a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__
		try:
			library = type(a.A)(name.title(), (ancestor,), {'__module__': name}, path=root)
		finally:
			a.Imports.__lib__, a.Tester.__lib__, a.Undefined.__lib__ = state

		return library.__instance__

	# Fail after a writer has already produced partial temporary content.
	# ----------------------------------------------------------------------
	@classmethod
	def _fail_write(cls, path, value):
		with open(path, 'w') as stream:
			stream.write('partial')
		raise OSError('Interrupted serialization')

	# Fail after copying some bytes into the temporary destination.
	# ----------------------------------------------------------------------
	@classmethod
	def _fail_copy(cls, source, destination):
		with open(destination, 'wb') as stream:
			stream.write(b'partial')
		raise OSError('Interrupted copy')

	# Inspect the namespace while the plugin owns a hidden temporary file.
	# ----------------------------------------------------------------------
	@classmethod
	def _observe_write(cls, directory, path, value):
		assert list(directory) == []
		assert path.endswith('.md')
		with open(path, 'w') as stream:
			stream.write(value)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Derive carrier metadata without ordinary property aliases.
	# ----------------------------------------------------------------------
	@classmethod
	def test_identity_getters(cls):
		with tempfile.TemporaryDirectory() as root:
			file      = a.File(a, os.path.join(root, 'notes.txt'), 'a.notes')
			directory = a.Directory(a, root, 'a.files')

			for item, name, route, is_directory in (
				(file, 'notes.txt', 'a.notes', False),
				(directory, os.path.basename(root), 'a.files', True),
			):
				assert item.get_lib() is a
				assert item.get_name() == name
				assert item.get_route() == route
				assert item.get_path() == os.path.realpath(os.path.join(root, name) if item is file else root)
				assert item.is_directory() is is_directory
				assert all(not hasattr(item, alias) for alias in ('path', 'route', 'lib', 'name', 'data', 'hash', 'load_method', 'hash_method'))

			assert a.Directory.get_path is a.File.get_path
			assert a.Directory.get_route is a.File.get_route
			assert a.Directory.get_lib is a.File.get_lib
			assert a.Directory.get_name is a.File.get_name

	# Keep a legitimate null result memoized without freshness probes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_null_memoization(cls):
		load = Mock(return_value=None)
		hash = Mock(side_effect=AssertionError('Unexpected freshness probe'))
		file = a.File(a, __file__, 'a.null', load, hash)

		assert file.load() is None
		assert file.load() is None
		load.assert_called_once_with()
		hash.assert_not_called()

	# Resolve former metadata names on both root and nested faces.
	# ----------------------------------------------------------------------
	@classmethod
	def test_namespace_names(cls):
		with tempfile.TemporaryDirectory() as root, patch.dict(sys.modules):
			library   = cls._library('filesystem_names', root, a.A)
			directory = library.mkdir('nested')

			for face in (library, directory):
				for name in ('path', 'route', 'lib', 'name', 'data', 'hash', 'load_method', 'hash_method'):
					face.write(name + '.md', name)
					assert getattr(face, name) == name
					assert face.read(name + '.md') == name

				face.write('is_directory.md', 'reserved')
				assert callable(face.is_directory) if face is directory else face.is_directory == 'reserved'
				assert face.read('is_directory.md') == 'reserved'

	# Join missing paths without creating them or resolving ordinary namespace names.
	# ----------------------------------------------------------------------
	@classmethod
	def test_join(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')

			assert directory.join() == os.path.realpath(root)
			assert directory.join('notes.md') == os.path.join(os.path.realpath(root), 'notes.md')
			assert directory.join('images', 'cover.png') == os.path.join(os.path.realpath(root), 'images', 'cover.png')
			assert os.listdir(root) == []

	# Reject traversal, absolute components and escaping symlinks.
	# ----------------------------------------------------------------------
	@classmethod
	def test_join_boundaries(cls):
		with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
			directory = a.Directory(a, root, 'a.files')
			os.symlink(outside, directory.join('escape'))

			for parts in (('/absolute',), ('..',), ('nested', '../../escape'), ('escape', 'notes.md'), (None,), ('',)):
				with TestCase().assertRaises(ValueError):
					directory.join(*parts)

	# Keep mkdir native even when a directory name coincides with a method.
	# ----------------------------------------------------------------------
	@classmethod
	def test_mkdir_and_link(cls):
		with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
			directory = a.Directory(a, root, 'a.files')
			child     = directory.mkdir('read', 'nested')

			assert child.is_directory()
			assert child.get_path() == directory.join('read', 'nested')
			assert directory.mkdir('read', 'nested') is child
			directory.link('mounted', outside)
			assert directory.mounted.get_path() == os.path.realpath(outside)

			with TestCase().assertRaises(ValueError):
				directory.mkdir('mounted', 'escape')
			with TestCase().assertRaises(ValueError):
				directory.link('../escape', outside)

	# Read exact formats independently of stem-based extension priority.
	# ----------------------------------------------------------------------
	@classmethod
	def test_exact_read_and_iteration(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			values    = {'notes.txt': 'text', 'notes.md': 'markdown', 'notes.json': None}

			for name, value in values.items():
				directory.write(name, value)
				assert directory.read(name) == value

			assert directory.notes is None
			assert {item.get_name(): item.load() for item in directory} == values

			plugin = a.__PLUGINS__['Json']
			directory.write('empty.json', None)
			with patch.object(plugin, 'load', wraps=plugin.load) as load:
				assert directory.read('empty.json') is None
				assert directory.read('empty.json') is None
				load.assert_called_once()

	# Reject unsupported and missing reads without interpreting another format.
	# ----------------------------------------------------------------------
	@classmethod
	def test_read_errors(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			directory.write('missing.md.txt', 'other file')
			directory.write('snake_name.md', 'different filename')

			for name in ('../notes.md', 'notes.bin', '/absolute.md'):
				with TestCase().assertRaises(ValueError):
					directory.read(name)
			for name in ('missing.md', 'SnakeName.md'):
				with TestCase().assertRaises(FileNotFoundError):
					directory.read(name)

	# Reset affected retained carriers while preserving unrelated cached values.
	# ----------------------------------------------------------------------
	@classmethod
	def test_selective_cache_invalidation(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			directory.write('notes.json', {'version': 1})
			directory.write('other.json', {'stable': True})

			assert directory.notes == {'version': 1}
			stable  = directory.other
			carrier = next(item for item in directory if item.get_name() == 'notes.json')

			assert carrier.load() == {'version': 1}
			directory.write('notes.json', {'version': 2})
			assert directory.notes == {'version': 2}
			assert carrier.load() == {'version': 2}
			assert directory.other is stable
			assert directory.read('notes.json') == {'version': 2}

	# Preserve destinations and cache identity when serialization or replacement fails.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_failures(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			plugin    = a.__PLUGINS__['Json']

			directory.write('notes.json', {'old': True})
			old = directory.notes

			for target, attribute, failure in (
				(plugin, 'write', cls._fail_write),
				(os, 'replace', OSError('Replacement failed')),
			):
				with patch.object(target, attribute, side_effect=failure):
					with TestCase().assertRaises(OSError):
						directory.write('notes.json', {'new': True})

				assert directory.notes is old
				assert directory.read('notes.json') == {'old': True}
				assert os.listdir(root) == ['notes.json']

			with TestCase().assertRaises(TypeError):
				directory.write('notes.json', {'not_json': {1}})
			assert directory.read('notes.json') == {'old': True}
			assert os.listdir(root) == ['notes.json']

	# Hide temporary content from normal discovery until publication.
	# ----------------------------------------------------------------------
	@classmethod
	def test_temporary_visibility(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			plugin    = a.__PLUGINS__['Text']

			with patch.object(plugin, 'write', side_effect=partial(cls._observe_write, directory)):
				directory.write('notes.md', 'complete')

			assert directory.notes == 'complete'
			assert os.listdir(root) == ['notes.md']

	# Preserve text and arbitrary bytes without format plugins.
	# ----------------------------------------------------------------------
	@classmethod
	def test_copy_bytes(cls):
		with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as sources:
			directory = a.Directory(a, root, 'a.files')

			for name, data in (('notes.txt', 'Привет'.encode()), ('sound.wav', bytes(range(256))), ('opaque.unknown', b'\x00\xff\x10')):
				source = os.path.join(sources, name)
				with open(source, 'wb') as stream:
					stream.write(data)

				for repeat in range(2):
					with patch.object(a.__PLUGINS__['Text'], 'write', side_effect=AssertionError('Plugin invoked')):
						directory.copy(name, source)
					with open(directory.join(name), 'rb') as stream:
						assert stream.read() == data

	# Reject invalid sources and same-file copies before altering the destination.
	# ----------------------------------------------------------------------
	@classmethod
	def test_copy_source_errors(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			directory.write('notes.txt', 'original')
			source = directory.join('notes.txt')

			for invalid in (source, root):
				with TestCase().assertRaises(ValueError):
					directory.copy('notes.txt', invalid)
			with TestCase().assertRaises(FileNotFoundError):
				directory.copy('notes.txt', directory.join('missing'))
			assert directory.notes == 'original'
			assert os.listdir(root) == ['notes.txt']

	# Leave old bytes and caches intact after unreadable, interrupted or failed copies.
	# ----------------------------------------------------------------------
	@classmethod
	def test_copy_failures(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			directory.write('source.txt', 'new')
			directory.write('notes.txt', 'old')
			source = directory.join('source.txt')

			for target, attribute, failure in (
				('builtins', 'open', PermissionError('Unreadable source')),
				(directory, '_copy', cls._fail_copy),
				(os, 'replace', OSError('Replacement failed')),
			):
				old = directory.notes
				context = patch(target + '.' + attribute, side_effect=failure) if isinstance(target, str) else patch.object(target, attribute, side_effect=failure)

				with context:
					with TestCase().assertRaises(OSError):
						directory.copy('notes.txt', source)

				assert directory.notes is old
				assert directory.read('notes.txt') == 'old'
				assert sorted(os.listdir(root)) == ['notes.txt', 'source.txt']

	# Apply identical destination rules to copies and plugin writes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_copy_boundaries(cls):
		with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
			directory = a.Directory(a, root, 'a.files')
			directory.write('source.txt', 'source')
			source = directory.join('source.txt')

			os.symlink(source, directory.join('linked.txt'))
			os.symlink(os.path.join(outside, 'missing'), directory.join('dangling'))

			for name in ('../escape', '/absolute', 'nested/file', 'linked.txt', 'dangling', '', '.', '..'):
				with TestCase().assertRaises(ValueError):
					directory.copy(name, source)

	# Reuse the root face cache for join, read, copy and atomic writes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_root_delegation(cls):
		with tempfile.TemporaryDirectory() as root, patch.dict(sys.modules):
			library = cls._library('filesystem_root', root, a.A)

			assert library.join() == os.path.realpath(root)
			library.write('source.txt', 'new')
			library.write('notes.txt', 'old')
			assert library.notes == 'old'

			library.copy('notes.txt', library.join('source.txt'))
			assert library.notes == 'new'
			assert library.read('notes.txt') == 'new'
			assert library.mkdir('images').get_path() == library.join('images')

	# Preserve local-first inheritance and refresh a newly introduced local override.
	# ----------------------------------------------------------------------
	@classmethod
	def test_inheritance(cls):
		with tempfile.TemporaryDirectory() as parent_root, tempfile.TemporaryDirectory() as child_root, patch.dict(sys.modules):
			parent = cls._library('filesystem_parent', parent_root, a.A)
			child  = cls._library('filesystem_child', child_root, type(parent))

			parent.write('root.md', 'inherited root')
			parent.mkdir('nested').write('notes.md', 'inherited')
			directory = child.mkdir('nested')

			assert all(item.get_name() != 'test.py' for item in child)
			with TestCase().assertRaises(AttributeError):
				child.test
			assert child.root == 'inherited root'
			assert directory.notes == 'inherited'
			assert directory.read('notes.md') == 'inherited'

			directory.write('notes.txt', 'local')
			assert directory.notes == 'local'
			assert parent.nested.notes == 'inherited'
			assert child.read('root.md') == 'inherited root'

			child.write('root.md', 'local root')
			assert child.root == 'local root'
			assert parent.root == 'inherited root'

	# Invalidate retained JSON carriers after byte copying without serialization.
	# ----------------------------------------------------------------------
	@classmethod
	def test_copy_refreshes_carriers(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			directory.write('notes.json', None)
			directory.write('source.json', {'copied': True})
			carrier = next(item for item in directory if item.get_name() == 'notes.json')

			assert carrier.load() is None
			assert directory.notes is None
			directory.copy('notes.json', directory.join('source.json'))

			assert carrier.load() == {'copied': True}
			assert directory.notes == {'copied': True}
			assert directory.read('notes.json') == {'copied': True}

	# Recognize same-file aliases before creating a temporary destination.
	# ----------------------------------------------------------------------
	@classmethod
	def test_copy_source_aliases(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			directory.write('notes.txt', 'original')
			source = directory.join('notes.txt')

			os.link(source, directory.join('hard.txt'))
			os.symlink(source, directory.join('symbolic.txt'))

			for name in ('hard.txt', 'symbolic.txt'):
				with TestCase().assertRaises(ValueError):
					directory.copy('notes.txt', directory.join(name))
			assert directory.notes == 'original'
			assert sorted(os.listdir(root)) == ['hard.txt', 'notes.txt', 'symbolic.txt']

	# Propagate format and read failures without memoizing an unsuccessful load.
	# ----------------------------------------------------------------------
	@classmethod
	def test_read_failure_recovery(cls):
		with tempfile.TemporaryDirectory() as root:
			directory = a.Directory(a, root, 'a.files')
			directory.write('notes.json', {'ready': True})

			with patch('builtins.open', side_effect=PermissionError('Unreadable file')):
				with TestCase().assertRaises(PermissionError):
					directory.read('notes.json')
			assert directory.read('notes.json') == {'ready': True}

			with open(directory.join('invalid.json'), 'w') as stream:
				stream.write('{')
			with TestCase().assertRaises(ValueError):
				directory.read('invalid.json')
			directory.write('invalid.json', None)
			assert directory.read('invalid.json') is None
