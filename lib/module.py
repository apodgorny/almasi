import gc
import os
import sys

from .function import Function
# from .events   import Events


class ModuleMeta(type):

	# Get module object
	# ----------------------------------------------------------------------
	@classmethod
	def module(mcls, namespace):
		return sys.modules.get(namespace.get('__module__'))

	# Get current library
	# ----------------------------------------------------------------------
	@classmethod
	def module_lib(mcls, namespace):
		return getattr(mcls.module(namespace), '__lib__', None)

	# Get carrier class name from route
	# ----------------------------------------------------------------------
	@classmethod
	def module_class_name(mcls, namespace):
		class_name = None
		route      = mcls.module_route(namespace)

		if route is not None:
			class_name = route.split('.')[-1]

		return class_name

	# Get module route from library resolver
	# ----------------------------------------------------------------------
	@classmethod
	def module_route(mcls, namespace):
		return getattr(mcls.module(namespace), '__route__', None)

	# Get module mtime from loader
	# ----------------------------------------------------------------------
	@classmethod
	def module_mtime(mcls, namespace):
		return getattr(mcls.module(namespace), '__mtime__', None)

	# Does class come from source file?
	# ----------------------------------------------------------------------
	@classmethod
	def has_own_module(mcls, namespace):
		class_name = mcls.module_class_name(namespace)
		short_name = namespace.get('__qualname__', '').split('.')[-1]

		if class_name is not None:
			return short_name == class_name

		return False

	# Class creation
	# ----------------------------------------------------------------------
	def __new__(mcls, name, bases, namespace, **kwargs):
		namespace['__has_own_module__'] = mcls.has_own_module(namespace)
		if mcls.module_lib(namespace) is not None:
			namespace['__lib__'] = mcls.module_lib(namespace)

		if namespace['__has_own_module__']:
			namespace['__route__'] = mcls.module_route(namespace)
			namespace['__mtime__'] = mcls.module_mtime(namespace)

		return super().__new__(mcls, name, bases, namespace)

	# String representation
	# ----------------------------------------------------------------------
	def __repr__(cls):
		text  = cls.__name__
		route = getattr(cls, '__route__', None)

		if isinstance(route, str):
			text = route

		return f'<class \'{text}\'>'


class Module(metaclass=ModuleMeta):

	_instance_counter = 0

	# Read the currently selected application without binding it at import time.
	# ----------------------------------------------------------------------
	@property
	def __app__(self):
		import a
		return a.__app__

	# Using new to avoid having to call super().__init__() everywhere
	# ----------------------------------------------------------------------
	def __new__(cls, *args, **kwargs):
		self = super().__new__(cls)

		Module._instance_counter += 1
		self.__instance_id__ = Module._instance_counter

		return self

	# Replace source-backed behavior while keeping live object identity and state.
	# Invoke at a quiescent execution boundary; in-flight methods are not tracked.
	# ----------------------------------------------------------------------
	@classmethod
	def __reload__(cls):
		is_source = cls.__dict__.get('__has_own_module__', False)

		if is_source and type(cls) is ModuleMeta:
			key    = cls.__module__
			module = sys.modules.get(key)
			path   = os.path.realpath(module.__file__) if module is not None else os.path.realpath(key)

			if module is not None and module.__dict__.get(cls.__name__) is cls:
				fresh = cls.__lib__.Imports.prepare_module(cls.__lib__, path, cls.__route__)
				new   = fresh.__dict__.get(cls.__name__)

				if type(new) is ModuleMeta and new.__bases__ == cls.__bases__:
					instances   = [item for item in gc.get_objects() if type(item) is cls]
					descendants = [child for child in cls.__subclasses__() if type(child) is ModuleMeta]
					switched    = []
					rebased     = []

					try:
						for instance in instances:
							instance.__class__ = new
							switched.append(instance)

						# Existing children retain their class identity and super() chain.
						# --------------------------------------------------------------
						for child in descendants:
							bases = child.__bases__
							child.__bases__ = tuple(new if base is cls else base for base in bases)
							rebased.append((child, bases))
					except Exception:
						for child, bases in reversed(rebased):
							child.__bases__ = bases

						for instance in switched:
							instance.__class__ = cls

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

	# Intercept method access to inject event hooks
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		from .events import Events
		attr = object.__getattribute__(self, name)

		if not name.startswith('_') and callable(attr) and Events.has(attr):
			def wrapped(*args, **kwargs):
				Events.trigger(attr)
				fn = Function(attr)
				return fn(*args, **kwargs)

			return wrapped

		return attr

	# String representation
	# ----------------------------------------------------------------------
	def __repr__(cls):
		text  = cls.__class__.__name__
		route = getattr(cls, '__route__', None)

		if isinstance(route, str):
			text = route

		return f'<Module \'{text}\'>'

	# Attach callback to foreign method execution
	# ----------------------------------------------------------------------
	# def on(self, foreign_method, own_method):
	# 	Events.on(foreign_method, own_method)

	# Namespaced debug print
	# ----------------------------------------------------------------------
	def print(self, *args, **kwargs):
		gray         = '\033[38;5;242m'
		reset        = '\033[0m'

		if getattr(self, 'verbose', False):
			print(f'{gray}{self.__route__}:{reset}', *args, **kwargs)

	# Note
	# ----------------------------------------------------------------------
	def note(self, *args, **kwargs):
		word_color  = '\033[38;5;39m'
		reset       = '\033[0m'

		args = list(args)
		args.insert(0, f'ℹ️ {word_color}Note:{reset}')
		return self.print(*args, **kwargs)

	# Warning
	# ----------------------------------------------------------------------
	def warn(self, *args, **kwargs):
		word_color  = '\033[38;5;172m'
		reset       = '\033[0m'

		args = list(args)
		args.insert(0, f'⚠️{word_color} WARNING:{reset}')
		return self.print(*args, **kwargs)

	# Error
	# ----------------------------------------------------------------------
	def error(self, *args, **kwargs):
		word_color  = '\033[38;5;210m'
		reset       = '\033[0m'

		args = list(args)
		args.insert(0, f'🚫{word_color}ERROR:{reset}')
		self.print(*args, **kwargs)
		exit(0)
