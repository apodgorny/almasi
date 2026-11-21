# ==============================================================================
# RELOADABLE
# ==============================================================================
# Observe source changes and notify consumers of live instances.
# ==============================================================================

import gc
import logging
import os
import sys
import types

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

	# Replace source-backed behavior while keeping live object identity and state.
	# Invoke at a quiescent execution boundary; in-flight methods are not tracked.
	# ----------------------------------------------------------------------
	@classmethod
	def __reload__(cls, commit=None):
		if cls.__dict__.get('__has_own_module__', False) and isinstance(cls, ModuleMeta):
			key    = cls.__dict__.get('__original_module__', cls.__module__)
			module = sys.modules.get(key)
			path   = os.path.realpath(module.__file__) if module is not None else os.path.realpath(key)

			if module is not None and module.__dict__.get(cls.__name__) is cls:
				fresh = cls.__lib__.Imports.prepare_module(cls.__lib__, path, cls.__route__)
				new   = fresh.__dict__.get(cls.__name__)

				if isinstance(new, ModuleMeta) and new.__bases__ == cls.__bases__:
					instances   = [item for item in gc.get_objects() if type(item) is cls]
					descendants = [child for child in type.__subclasses__(cls) if isinstance(child, ModuleMeta)]
					switched    = []
					rebased     = []

					try:
						for instance in instances:
							object.__setattr__(instance, '__class__', new)
							switched.append(instance)

						# Existing children retain their class identity and super() chain.
						# --------------------------------------------------------------
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
	def __reload__(self):
		fresh = super().__reload__()

		fresh.__instance__ = self
		self.__dict__['_initialize'] = getattr(fresh, 'initialize', None)
		self.__dict__['initialize']  = types.MethodType(fresh._initialize, self)

		return self

