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

	# Using new to avoid having to call super().__init__() everywhere
	# ----------------------------------------------------------------------
	def __new__(cls, *args, **kwargs):
		self = super().__new__(cls)

		Module._instance_counter += 1
		self.__instance_id__ = Module._instance_counter

		return self

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
