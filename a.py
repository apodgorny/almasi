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
	def __new__(mcls, name, bases, namespace, path=None, plugins=None):
		module_name  = namespace.get('__module__')
		module       = sys.modules[module_name]
		lib_file     = os.path.realpath(module.__file__)
		lib_path     = os.path.dirname(lib_file)
		path         = os.path.abspath(os.path.join(lib_path, path or 'root'))  # Relative or absolute path is accepted
		plugins_path = os.path.join(lib_path, 'plugins')

		if not os.path.exists(path):
			raise ValueError(f'Could not define class `{name}`. Path `{path}` does not exist')

		cls = super().__new__(mcls, name, bases, namespace)

		instance              = object.__new__(cls)
		instance.__name__     = module_name #name.lower()
		instance.__spec__     = None
		instance.__children__ = {}

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

		instance.initialize()

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
			value = instance.__children__.get(name)
			if value is not None:
				break

			value = instance.__resolve__(name, instance.__path__, self.__name__, source_lib=instance)
			if value is not None:
				instance.__children__[name] = value
				break

		if value is None:
			raise AttributeError(f'Library `{self.__name__}` has no attribute `{name}`')

		return value.load()

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
				yield cls.__instance__

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
	# PUBLIC METHODS
	# ======================================================================

	# Called when library is fully assembled and ready to work
	# ----------------------------------------------------------------------
	def initialize(self):
		pass

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
