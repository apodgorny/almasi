# ==============================================================================
# ALMASI LIBRARY
# ==============================================================================
# Build canonical libraries with inherited filesystem namespaces.
# ==============================================================================

import builtins
import copy
import keyword
import os, sys

from lib.imports   import Imports
from lib.module    import Module, ModuleMeta
from lib.service   import Service
from lib.logger    import Logger
from lib.string    import String
from lib.file      import File
from lib.directory import Directory
from lib.plugin    import Plugin
from lib.undefined import Undefined
from lib.dual      import DualMethod, DualProperty
from lib.timer     import Timer
from lib.spinner   import Spinner
from lib.tester    import Tester


class AMeta(type):

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Create class
	# ----------------------------------------------------------------------
	def __new__(mcls, name, bases, namespace, path=None, plugins=None, is_created_using_extend=False):
		module_name  = namespace.get('__module__')
		module       = sys.modules[module_name]
		lib_file     = os.path.realpath(module.__file__)
		lib_path     = os.path.dirname(lib_file)
		path         = os.path.abspath(os.path.join(lib_path, path or 'root'))  # Relative or absolute path is accepted
		plugins_path = os.path.join(lib_path, 'plugins')

		# Only the bootstrap A class may be declared directly.
		# ----------------------------------------------------------------------
		if not is_created_using_extend and (name != 'A' or module_name != 'a'):
			raise TypeError('Declare libraries with a.extend(), not a class declaration')

		if not os.path.exists(path):
			raise ValueError(f'Could not define class `{name}`. Path `{path}` does not exist')

		cls = super().__new__(mcls, name, bases, namespace)

		instance                  = object.__new__(cls)
		instance.__name__         = module_name
		if is_created_using_extend and module_name == '__main__':
			instance.__name__ = String.camel_to_snake(name)
		instance.__spec__         = None
		instance.__children__     = {}
		instance.__cached_names__ = set()
		instance.__forks__       = {}

		# Track live library namespaces for targeted cache invalidation.
		Directory.__namespace_faces__.add(instance)

		Undefined.__lib__ = instance
		Imports.__lib__   = instance
		Tester.__lib__    = instance
		
		# Publish library name for import
		module.__dict__[instance.__name__] = instance
		sys.modules[instance.__name__]     = instance

		module.__dict__['UNDEFINED'] = Undefined

		cls.__path__     = path
		cls.__lib_file__ = lib_file
		cls.__lib_path__ = lib_path
		cls.__instance__ = instance
		cls.__PLUGINS__  = {}

		cls.Tester       = Tester
		cls.tester       = Tester

		setattr(cls, name, cls)   # Make class available for import via instance

		for plugin_cls_name in plugins or []:
			plugin_route = f'{instance.__name__}.plugins.{plugin_cls_name}'
			plugin_cls   = Imports.get_class(instance, plugin_cls_name, plugins_path, plugin_route)
			if plugin_cls is not None:
				cls.__PLUGINS__[plugin_cls_name] = plugin_cls(instance)

		return cls


class A(metaclass=AMeta, plugins=['Py', 'Json', 'Text', 'Bytes']):
	ModuleMeta    = ModuleMeta
	Module        = Module
	Logger        = Logger
	File          = File
	Directory     = Directory
	Plugin        = Plugin
	Service       = Service
	Imports       = Imports
	Undefined     = Undefined
	String        = String
	Timer         = Timer
	Spinner       = Spinner

	__app__       = None

	dual_method   = DualMethod
	dual_property = DualProperty

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Resolve attribute
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		value = None

		for instance in self.__instances__():
			owner = self if self.__dict__.get('__fork_source__') is not None else instance
			value = owner.__children__.get(name)
			if value is not None:
				break

			value = owner.__resolve__(name, instance.__path__, self.__name__, source_lib=owner)
			if value is not None:
				owner.__children__[name] = value
				break

		if value is None:
			raise AttributeError(f'Library `{self.__name__}` has no attribute `{name}`')

		result = value.load()
		self.__dict__[name] = result
		self.__cached_names__.add(name)
		return result

	# Resolve a named fork without changing the canonical Python import.
	# ----------------------------------------------------------------------
	def __getitem__(self, name):
		result = self if name == 'default' else self.__forks__[name]
		return result

	# String representation
	# ----------------------------------------------------------------------
	def __repr__(self):
		return f'<Library `{self.__name__}`>'

	# Iterate lineage layers
	# ----------------------------------------------------------------------
	def __iter__(self):
		return Directory(self, self.__path__, self.__name__).__iter__()

	# Iterate lineage layers
	# ----------------------------------------------------------------------
	def __instances__(self):
		for cls in type(self).__mro__:
			if cls != object:
				instance = self if cls is type(self) and self.__dict__.get('__fork_source__') is not None else cls.__instance__
				yield instance

	# Resolve using the existing plugin order.
	# source_lib owns the file; the selected plugin may belong to another library.
	# ----------------------------------------------------------------------
	def __resolve__(self, name, parent_path, parent_route, source_lib):
		value = None
		path  = os.path.realpath(os.path.join(parent_path, name))

		if parent_path == self.__path__ and name in ['test', 'test.py']:
			value = None
		elif os.path.isdir(path):
			value = Directory(self, path, f'{parent_route}.{name}')
		else:
			for instance in self.__instances__():
				for plugin_name, plugin in instance.__PLUGINS__.items():
					value = plugin(name, parent_path, parent_route, source_lib=source_lib)
					if value is not None: break
				if value is not None: break
		return value

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Check whether extend() was called from the Python entry module.
	# ----------------------------------------------------------------------
	def _is_main(self):
		return sys._getframe(2).f_globals['__name__'] == '__main__'

	# Accept canonical snake_case library names.
	# ----------------------------------------------------------------------
	def _is_valid_library_name(self, name):
		return (
			isinstance(name, str)
			and name.isidentifier()
			and not keyword.iskeyword(name)
			and name == self.String.camel_to_snake(self.String.snake_to_camel(name))
		)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Extend the namespace through an explicit, canonical library name.
	# Initialization belongs to the caller after extend() returns.
	# ----------------------------------------------------------------------
	def extend(self, name, path='root', plugins=None):
		caller      = sys._getframe(1).f_globals
		module_name = caller['__name__']
		module      = sys.modules[module_name]
		is_main     = self._is_main()
		source_name = module_name.rsplit('.', 1)[-1]

		if is_main:
			source_name = os.path.splitext(os.path.basename(module.__file__))[0]

		if self._is_valid_library_name(name):
			full_name = name if is_main else module_name

			if source_name == name:
				is_name_available = full_name not in sys.modules or sys.modules[full_name] is module

				if is_name_available:
					library_class = type(type(self))(
						self.String.snake_to_camel(name),
						(type(self),),
						{'__module__' : module_name},
						path                    = path,
						plugins                 = plugins,
						is_created_using_extend = True
					)
				else:
					raise ValueError(f'Library `{full_name}` is already published')
			else:
				raise ValueError(f'Library `{name}` must match its Python module name')
		else:
			raise ValueError(f'Invalid library name: `{name}`')

		if is_main:
			A.__app__ = library_class.__instance__

		return library_class.__instance__

	# Create a fresh runtime namespace without publishing a Python library.
	# Source files and compiled code are shared; loaded classes and state are not.
	# ----------------------------------------------------------------------
	def fork(self, name):
		if not isinstance(name, str) or not name or name == 'default':
			raise ValueError(f'Invalid fork name: {name}')

		if name in self.__forks__:
			raise ValueError(f'Fork `{name}` already exists')

		fork = object.__new__(type(self))

		# Copy ordinary configuration without carrying resolved classes or services.
		# ----------------------------------------------------------------------
		for key, value in self.__dict__.items():
			if not key.startswith('_') and key not in self.__cached_names__ and not callable(value):
				fork.__dict__[key] = copy.deepcopy(value)

		fork.__name__         = self.__name__
		fork.__spec__         = None
		fork.__fork_source__  = self
		fork.__fork_name__    = name
		fork.__forks__        = {}
		fork.__children__     = {}
		fork.__cached_names__ = set()
		fork.__PLUGINS__      = {key: type(plugin)(fork) for key, plugin in type(self).__PLUGINS__.items()}

		# Localize imports of this library and inherited libraries at load time.
		# Other Python imports retain their ordinary process-wide meaning.
		# ----------------------------------------------------------------------
		fork.__fork_import_names__ = {
			instance.__name__ for instance in fork.__instances__()
			if instance.__name__ != 'a' or fork.__name__ == 'a'
		}

		def fork_import(module, globals=None, locals=None, fromlist=(), level=0):
			result = None

			if level == 0:
				for library_name in fork.__fork_import_names__:
					if module == library_name or module.startswith(library_name + '.'):
						result = fork

						if module != library_name:
							for part in module[len(library_name) + 1:].split('.'):
								result = getattr(result, part)

							if not fromlist:
								result = fork

						break

			if result is None:
				result = builtins.__import__(module, globals, locals, fromlist, level)

			return result

		fork.__fork_builtins__ = builtins.__dict__.copy()
		fork.__fork_builtins__['__import__'] = fork_import

		Directory.__namespace_faces__.add(fork)
		self.__forks__[name] = fork

		return fork

	# Join relative paths without mutating the library root.
	# ----------------------------------------------------------------------
	def join(self, *parts):
		return Directory(self, self.__path__, self.__name__).join(*parts)

	# Create directories relative to the library root.
	# ----------------------------------------------------------------------
	def mkdir(self, *parts):
		return Directory(self, self.__path__, self.__name__).mkdir(*parts)

	# Read an exact filename through the root namespace.
	# ----------------------------------------------------------------------
	def read(self, name):
		return Directory(self, self.__path__, self.__name__).read(name)

	# Write a file into the library root.
	# ----------------------------------------------------------------------
	def write(self, name, value):
		Directory(self, self.__path__, self.__name__).write(name, value)

	# Copy file bytes into the library root.
	# ----------------------------------------------------------------------
	def copy(self, name, source):
		Directory(self, self.__path__, self.__name__).copy(name, source)

	# Create symlink
	# ----------------------------------------------------------------------
	def link(self, name, path):
		Directory(self, self.__path__, self.__name__).link(name, path)
