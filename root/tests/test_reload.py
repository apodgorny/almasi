# ==============================================================================
# TEST MODULE RELOAD
# ==============================================================================
# Exercise live code replacement with retained state, callbacks and inheritance.
# ==============================================================================

import asyncio
import os
import sys
import tempfile

from contextlib import contextmanager
from unittest import TestCase

import a

from lib.events   import Events
from lib.function import Function


class TestReload(a.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Keep source edits isolated while exercising the real filesystem loader.
	# ----------------------------------------------------------------------
	@staticmethod
	@contextmanager
	def _runtime():
		with tempfile.TemporaryDirectory(dir=a.__path__, prefix='__reload_') as path:
			directory = a.Directory(a, path, f'a.{os.path.basename(path)}')

			try:
				yield directory
			finally:
				for name in tuple(sys.modules):
					if name.startswith(os.path.realpath(path) + os.sep):
						del sys.modules[name]

	# Simulate a source deployment without invoking Almasi's write API.
	# ----------------------------------------------------------------------
	@staticmethod
	def _write(directory, name, source):
		path = directory.join(name + '.py')

		with open(path, 'w', encoding='utf-8') as stream:
			stream.write(source)

		return path

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Preserve a service's identity and mutable session state across deployments.
	# ----------------------------------------------------------------------
	@classmethod
	def test_service_state_and_namespace(cls):
		with cls._runtime() as directory:
			path = cls._write(directory, 'session_store', '''
import a

class SessionStore(a.Service):
	def initialize(self):
		self.sessions = {}
		self.requests = 0

	def handle(self, key):
		self.requests += 1
		return self.sessions[key]
''')
			service = directory.SessionStore
			service.initialize()
			service.sessions['guest'] = {'history': ['started']}
			alias    = service
			identity = id(service)

			assert service.handle('guest') == {'history': ['started']}

			cls._write(directory, 'session_store', '''
import a

class SessionStore(a.Service):
	def initialize(self):
		raise AssertionError('Initialization must not run again')

	def handle(self, key):
		self.requests += 10
		return (self.sessions[key], self.requests)
''')
			assert service.__reload__() is service
			assert id(service) == identity
			assert alias is service
			assert service.handle('guest') == ({'history': ['started']}, 11)
			assert directory.SessionStore is service
			assert type(service)() is service
			assert type(service).__module__ == os.path.realpath(path)

			with TestCase().assertRaisesRegex(RuntimeError, 'already initialized'):
				service.initialize()

	# Keep several independently referenced ordinary module instances alive.
	# ----------------------------------------------------------------------
	@classmethod
	def test_module_instances_and_removed_methods(cls):
		with cls._runtime() as directory:
			cls._write(directory, 'message_handler', '''
import a

class MessageHandler(a.Module):
	def process(self, value):
		return 'old:' + value

	def obsolete(self):
		return True
''')
			old_class = directory.MessageHandler
			one       = old_class()
			two       = old_class()
			one.queue = ['a']
			two.queue = ['b']
			old_ids   = (id(one), id(two))

			cls._write(directory, 'message_handler', '''
import a

class MessageHandler(a.Module):
	def process(self, value):
		return 'new:' + value.upper()
''')
			new_class = old_class.__reload__()

			assert directory.MessageHandler is new_class
			assert new_class is not old_class
			assert type(one) is new_class
			assert type(two) is new_class
			assert (id(one), id(two)) == old_ids
			assert one.queue == ['a']
			assert two.queue == ['b']
			assert one.process('go') == 'new:GO'
			assert two.process('go') == 'new:GO'
			assert not hasattr(one, 'obsolete')

	# New classes must see the same singleton as all existing consumers.
	# ----------------------------------------------------------------------
	@classmethod
	def test_repeated_service_reload(cls):
		with cls._runtime() as directory:
			cls._write(directory, 'counter_service', '''
import a

class CounterService(a.Service):
	def increment(self):
		self.value = getattr(self, 'value', 0) + 1
		return self.value
''')
			counter  = directory.CounterService
			identity = id(counter)

			for step in (2, 3, 4):
				cls._write(directory, 'counter_service', f'''
import a

class CounterService(a.Service):
	def increment(self):
		self.value = getattr(self, 'value', 0) + {step}
		return self.value
''')
				counter.__reload__()
				assert directory.CounterService is counter
				assert type(counter)() is counter
				assert id(counter) == identity

			assert counter.increment() == 4

	# Existing subclasses keep their identities and resolve the new base logic.
	# ----------------------------------------------------------------------
	@classmethod
	def test_inherited_methods_and_super(cls):
		with cls._runtime() as directory:
			cls._write(directory, 'base_operation', '''
import a

class BaseOperation(a.Module):
	def execute(self, value):
		return value + 1
''')
			Parent = directory.BaseOperation

			class SpecializedOperation(Parent):
				def execute(self, value):
					return super().execute(value) * 2

			class FinalOperation(SpecializedOperation):
				def execute(self, value):
					return super().execute(value) + 3

			child       = SpecializedOperation()
			grandchild  = FinalOperation()
			old_identity = id(child)

			assert child.execute(4) == 10
			assert grandchild.execute(4) == 13

			cls._write(directory, 'base_operation', '''
import a

class BaseOperation(a.Module):
	def execute(self, value):
		return value + 10
''')
			new_parent = Parent.__reload__()

			assert SpecializedOperation.__bases__ == (new_parent,)
			assert type(child) is SpecializedOperation
			assert id(child) == old_identity
			assert child.execute(4) == 28
			assert grandchild.execute(4) == 31

	# Previously registered callbacks must dispatch the current implementation.
	# ----------------------------------------------------------------------
	@classmethod
	def test_registered_callbacks_and_detach(cls):
		with cls._runtime() as directory:
			cls._write(directory, 'notification_service', '''
import a

class NotificationService(a.Service):
	def announce(self, payload):
		return payload

	def receive(self, payload):
		self.received = getattr(self, 'received', []) + [('old', payload)]
''')
			service  = directory.NotificationService
			events   = Events()
			events.initialize()
			callback = Function(service.receive)

			events.on(service.announce, service.receive)
			events.trigger(service.announce)
			assert service.received == [('old', {'foo': 'bar'})]

			cls._write(directory, 'notification_service', '''
import a

class NotificationService(a.Service):
	def announce(self, payload):
		return payload

	def receive(self, payload):
		self.received.append(('new', payload))
''')
			service.__reload__()
			events.trigger(service.announce)
			callback({'direct': True})

			assert service.received == [
				('old', {'foo': 'bar'}),
				('new', {'foo': 'bar'}),
				('new', {'direct': True}),
			]

			events.off(service.announce, service.receive)
			events.trigger(service.announce)
			assert len(service.received) == 3

	# A completed async callback is replaced without changing its owner.
	# ----------------------------------------------------------------------
	@classmethod
	def test_async_callback_after_completion(cls):
		with cls._runtime() as directory:
			cls._write(directory, 'job_service', '''
import a

class JobService(a.Service):
	async def run(self, value):
		return value + 1
''')
			service  = directory.JobService
			callback = Function(service.run)
			assert asyncio.run(callback(10)) == 11

			cls._write(directory, 'job_service', '''
import a

class JobService(a.Service):
	async def run(self, value):
		return value + 2
''')
			service.__reload__()
			assert asyncio.run(callback(10)) == 12

	# Unchanged timestamps and file sizes must not return stale Python bytecode.
	# ----------------------------------------------------------------------
	@classmethod
	def test_same_timestamp_and_length(cls):
		with cls._runtime() as directory:
			path = cls._write(directory, 'same_source', '''
import a

class SameSource(a.Module):
	def text(self):
		return 'one'
''')
			source = directory.SameSource()
			mtime  = os.stat(path).st_mtime_ns

			cls._write(directory, 'same_source', '''
import a

class SameSource(a.Module):
	def text(self):
		return 'two'
''')
			os.utime(path, ns=(mtime, mtime))
			source.__reload__()

			assert source.text() == 'two'

	# A syntax failure must preserve old code, identity and published caches.
	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_source_keeps_old_version(cls):
		with cls._runtime() as directory:
			path = cls._write(directory, 'safe_handler', '''
import a

class SafeHandler(a.Module):
	def respond(self):
		return 'working'
''')
			old_class = directory.SafeHandler
			handler   = old_class()
			old_module = sys.modules[os.path.realpath(path)]

			cls._write(directory, 'safe_handler', 'class SafeHandler(a.Module):\n\tdef respond(\n')

			with TestCase().assertRaises(SyntaxError):
				handler.__reload__()

			assert type(handler) is old_class
			assert directory.SafeHandler is old_class
			assert sys.modules[os.path.realpath(path)] is old_module
			assert handler.respond() == 'working'

	# Missing class or incompatible inheritance must not publish a replacement.
	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_class_contract_keeps_old_version(cls):
		with cls._runtime() as directory:
			cls._write(directory, 'task_processor', '''
import a

class TaskProcessor(a.Module):
	def execute(self):
		return 17
''')
			old_class = directory.TaskProcessor
			task      = old_class()

			for source in (
				'import a\nclass WrongName(a.Module):\n\tpass\n',
				'import a\nclass TaskProcessor(a.Service):\n\tpass\n',
			):
				cls._write(directory, 'task_processor', source)

				with TestCase().assertRaises(TypeError):
					task.__reload__()

				assert directory.TaskProcessor is old_class
				assert type(task) is old_class
				assert task.execute() == 17

	# Reject changed instance layout and leave every existing instance intact.
	# ----------------------------------------------------------------------
	@classmethod
	def test_incompatible_layout_rolls_back(cls):
		with cls._runtime() as directory:
			cls._write(directory, 'buffer_owner', '''
import a

class BufferOwner(a.Module):
	def read(self):
		return self.buffer
''')
			old_class = directory.BufferOwner
			one       = old_class()
			two       = old_class()
			one.buffer = ['pending']
			two.buffer = ['queued']

			cls._write(directory, 'buffer_owner', '''
import a

class BufferOwner(a.Module):
	__slots__ = ('slot',)

	def read(self):
		return self.buffer
''')
			with TestCase().assertRaises(TypeError):
				old_class.__reload__()

			assert directory.BufferOwner is old_class
			assert type(one) is old_class
			assert type(two) is old_class
			assert one.read() == ['pending']
			assert two.read() == ['queued']

	# A runtime-only class has no source authority for a reload.
	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_class_rejected(cls):
		class InMemory(a.Module):
			pass

		with TestCase().assertRaisesRegex(TypeError, 'source-backed'):
			InMemory.__reload__()


if __name__ == '__main__':
	TestReload.run()
