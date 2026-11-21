# ==============================================================================
# RELOADABLE
# ==============================================================================
# Observe source changes and notify consumers of live instances.
# ==============================================================================

import asyncio
import gc
import inspect
import logging
import os
import sys
import threading
import types

from functools import wraps
from time import monotonic

from .module    import Module, ModuleMeta
from .singleton import Singleton


class ReloadableMeta(ModuleMeta):

	# Notify opt-in lifecycle listeners only after instance initialization.
	# ----------------------------------------------------------------------
	def __call__(cls, *args, **kwargs):
		instance = super().__call__(*args, **kwargs)

		if not instance.__dict__.get('_reloadable_loaded', False):
			instance.__dict__['_reloadable_loaded'] = True
			Reloadable._notify(instance)

		return instance


class Reloadable:

	# ==========================================================================
	# PRIVATE METHODS
	# ==========================================================================

	# Wrap methods at class creation, never at attribute lookup.
	# ----------------------------------------------------------------------
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)

		methods = tuple(
			(name, member) for name, member in cls.__dict__.items()
			if (inspect.isfunction(member) or isinstance(member, (classmethod, staticmethod)))
			and name not in ('__new__', '__init_subclass__', '__getattribute__', '__reload__', '__del__')
		)

		if methods or cls.__dict__.get('__has_own_module__', False):
			type.__setattr__(cls, '_reload_gate', {
				'condition'   : threading.Condition(),
				'reload_lock' : threading.Lock(),
				'owners'      : {},
				'paused'      : False,
				'maintainer'  : None,
				'waiters'     : [],
			})

		for name, member in methods:
			method = member.__func__ if isinstance(member, (classmethod, staticmethod)) else member
			wrapped = Reloadable._wrap_async(cls, method) if inspect.iscoroutinefunction(method) else Reloadable._wrap_sync(cls, method)

			if isinstance(member, classmethod):
				wrapped = classmethod(wrapped)
			elif isinstance(member, staticmethod):
				wrapped = staticmethod(wrapped)

			# O TMeta treats public setattr as an ontology-field mutation.
			# --------------------------------------------------------------
			type.__setattr__(cls, name, wrapped)

	# Replace source-backed behavior only after active methods finish.
	# ----------------------------------------------------------------------
	@classmethod
	def __reload__(cls, commit=None, timeout=30.0):
		if cls.__dict__.get('__has_own_module__', False) and isinstance(cls, ModuleMeta):
			gate = cls._reload_gate

			with gate['reload_lock']:
				key    = cls.__dict__.get('__original_module__', cls.__module__)
				module = sys.modules.get(key)
				path   = os.path.realpath(module.__file__) if module is not None else os.path.realpath(key)

				if module is not None and module.__dict__.get(cls.__name__) is cls:
					fresh = cls.__lib__.Imports.prepare_module(cls.__lib__, path, cls.__route__)
					new   = fresh.__dict__.get(cls.__name__)

					if isinstance(new, ModuleMeta) and new.__bases__ == cls.__bases__:
						Reloadable._pause(gate, timeout)

						try:
							instances   = [item for item in gc.get_objects() if type(item) is cls]
							descendants = [child for child in type.__subclasses__(cls) if isinstance(child, ModuleMeta)]
							switched    = []
							rebased     = []

							type.__setattr__(new, '_reload_gate', gate)

							try:
								for instance in instances:
									object.__setattr__(instance, '__class__', new)
									switched.append(instance)

								for child in descendants:
									bases = child.__bases__
									type.__setattr__(child, '__bases__', tuple(new if base is cls else base for base in bases))
									rebased.append((child, bases))

								if commit is not None:
									commit(cls, new)
							except Exception:
								for child, bases in reversed(rebased):
									type.__setattr__(child, '__bases__', bases)

								for instance in switched:
									object.__setattr__(instance, '__class__', cls)

								raise

							sys.modules[key] = fresh
							directory = cls.__lib__.Directory(
								cls.__lib__,
								os.path.dirname(path),
								cls.__route__.rsplit('.', 1)[0]
							)
							directory.invalidate(
								os.path.basename(path),
								local = cls.__lib__.__dict__.get('__fork_source__') is not None
							)
							result = new
						finally:
							Reloadable._resume(gate)
					else:
						raise TypeError(f'Incompatible replacement class: {cls.__route__}')
				else:
					raise RuntimeError(f'Source module is not current: {cls.__route__}')
		else:
			raise TypeError(f'Hot reload requires a source-backed a.Module: {cls.__name__}')

		return result


	@classmethod
	def __on_load__(cls, file):
		cls._observe_reload(file)

	# The observed class owns one subscription, inherited by its replacements.
	# ----------------------------------------------------------------------
	@classmethod
	def _observe_reload(cls, file):
		if '_reload_subscription' not in cls.__dict__:
			def changed(changes):
				nonlocal cls

				if os.path.isfile(file.get_path()):
					try:
						current = cls
						target  = current() if issubclass(current, Singleton) else current
						fresh   = target.__reload__()
						cls     = type(fresh) if isinstance(fresh, Singleton) else fresh

						cls._reload_subscription = subscription
						callback = current.__dict__.get('__reload_callback__')
						if callback is not None:
							cls.__reload_callback__ = callback

						for instance in gc.get_objects():
							if type(instance) is cls:
								Reloadable._notify(instance)
					except Exception:
						logging.exception('Reloadable source update failed: %s', file.get_path())

			subscription = file.subscribe(changed)
			cls._reload_subscription = subscription

	# Separate asynchronous owners from threads on the same event loop.
	# ----------------------------------------------------------------------
	@staticmethod
	def _owner():
		try:
			task = asyncio.current_task()
		except RuntimeError:
			task = None

		owner = task if task is not None else threading.get_ident()
		return owner

	# Admit ordinary sync calls without locking the common execution path.
	# ----------------------------------------------------------------------
	@staticmethod
	def _enter_sync(gate):
		owner  = threading.get_ident()
		owners = gate['owners']
		depth  = owners.get(owner, 0)

		if not gate['paused'] or depth or gate['maintainer'] == owner:
			owners[owner] = depth + 1

			if gate['paused'] and not depth and gate['maintainer'] != owner:
				owners.pop(owner)
				with gate['condition']:
					gate['condition'].notify_all()
				owner = Reloadable._wait_sync(gate, owner)
		else:
			owner = Reloadable._wait_sync(gate, owner)

		return owner

	# Coordinate sync callers only while admission is paused.
	# ----------------------------------------------------------------------
	@staticmethod
	def _wait_sync(gate, owner):
		try:
			task = asyncio.current_task()
		except RuntimeError:
			task = None

		with gate['condition']:
			if task is not None and task in gate['owners']:
				owner = task

			if owner not in gate['owners'] and gate['maintainer'] != threading.get_ident():
				if task is not None:
					raise RuntimeError('Synchronous calls cannot wait for reload on an event-loop thread')

				while gate['paused']:
					gate['condition'].wait()

			gate['owners'][owner] = gate['owners'].get(owner, 0) + 1

		return owner

	# Suspend new async calls without blocking the event loop.
	# ----------------------------------------------------------------------
	@staticmethod
	async def _enter_async(gate, owner):
		entered = False
		loop    = asyncio.get_running_loop()

		while not entered:
			waiter = None

			with gate['condition']:
				depth = gate['owners'].get(owner, 0)

				if depth or not gate['paused']:
					gate['owners'][owner] = depth + 1
					entered = True
				else:
					waiter = loop.create_future()
					gate['waiters'].append((loop, waiter))

			if waiter is not None:
				try:
					await waiter
				finally:
					with gate['condition']:
						if (loop, waiter) in gate['waiters']:
							gate['waiters'].remove((loop, waiter))

	# Release nested calls, waking a reloader only when necessary.
	# ----------------------------------------------------------------------
	@staticmethod
	def _leave(gate, owner):
		owners = gate['owners']
		depth  = owners[owner] - 1

		if depth:
			owners[owner] = depth
		else:
			del owners[owner]

		if gate['paused']:
			with gate['condition']:
				gate['condition'].notify_all()

	# Preserve bound-method identity while accounting for active sync calls.
	# ----------------------------------------------------------------------
	@staticmethod
	def _wrap_sync(cls, method):
		@wraps(method)
		def invoke(*args, **kwargs):
			gate  = cls._reload_gate
			owner = Reloadable._enter_sync(gate)

			try:
				result = method(*args, **kwargs)
			finally:
				Reloadable._leave(gate, owner)

			return result

		return invoke

	# Include await suspension in the lifetime of async calls.
	# ----------------------------------------------------------------------
	@staticmethod
	def _wrap_async(cls, method):
		@wraps(method)
		async def invoke(*args, **kwargs):
			gate  = cls._reload_gate
			owner = Reloadable._owner()
			await Reloadable._enter_async(gate, owner)

			try:
				result = await method(*args, **kwargs)
			finally:
				Reloadable._leave(gate, owner)

			return result

		return invoke

	# Close admission before waiting for all old-version calls to finish.
	# ----------------------------------------------------------------------
	@staticmethod
	def _pause(gate, timeout):
		deadline = monotonic() + timeout
		owner    = Reloadable._owner()

		try:
			with gate['condition']:
				if owner in gate['owners']:
					raise RuntimeError('Cannot reload within an active method of the same class')

				if gate['owners']:
					try:
						loop = asyncio.get_running_loop()
					except RuntimeError:
						loop = None

					if loop is not None:
						raise RuntimeError('Reload must drain from outside the running event loop')

				gate['paused']     = True
				gate['maintainer'] = threading.get_ident()

				while gate['owners']:
					remaining = deadline - monotonic()

					if remaining <= 0:
						raise TimeoutError('Reload timed out waiting for active methods')

					gate['condition'].wait(remaining)
		except BaseException:
			Reloadable._resume(gate)
			raise

	# Wake a future only if cancellation did not complete it first.
	# ----------------------------------------------------------------------
	@staticmethod
	def _wake(waiter):
		if not waiter.done():
			waiter.set_result(None)

	# Symmetrically reopen admission for waiting threads and tasks.
	# ----------------------------------------------------------------------
	@staticmethod
	def _resume(gate):
		with gate['condition']:
			gate['paused']     = False
			gate['maintainer'] = None
			waiters            = tuple(gate['waiters'])
			gate['waiters'].clear()
			gate['condition'].notify_all()

		for loop, waiter in waiters:
			if not loop.is_closed():
				loop.call_soon_threadsafe(Reloadable._wake, waiter)

	# Report an instance to its nearest inherited callback.
	# ----------------------------------------------------------------------
	@classmethod
	def _notify(cls, instance):
		callback = getattr(type(instance), '__reload_callback__', None)
		if callback is not None:
			try:
				callback(instance)
			except Exception:
				logging.exception('Reloadable callback failed')

	# ==========================================================================
	# FRAMEWORK METHODS
	# ==========================================================================

	# Set the sole callback for this class and its inheriting subclasses.
	# ----------------------------------------------------------------------
	@classmethod
	def __on_reload__(cls, callback):
		if not callable(callback):
			raise TypeError('Reload callback must be callable')

		cls.__reload_callback__ = callback


class ReloadableModule(Reloadable, Module, metaclass=ReloadableMeta):
	pass


class ReloadableSingleton(Reloadable, Singleton, metaclass=ReloadableMeta):
	# Keep the initialized singleton and its instance-owned initializer.
	# ----------------------------------------------------------------------
	def __reload__(self, timeout=30.0):
		fresh = super().__reload__(timeout=timeout)

		fresh.__instance__ = self
		self.__dict__['_initialize'] = getattr(fresh, 'initialize', None)
		self.__dict__['initialize']  = types.MethodType(fresh._initialize, self)

		return self

