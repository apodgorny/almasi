import os
import sys
import importlib.util


class Imports:

	# Load module
	# ----------------------------------------------------------------------
	@classmethod
	def load_module(cls, lib, path, route=None, namespace=None):
		path   = os.path.realpath(path)
		module = sys.modules.get(path)

		if module is None:
			spec   = importlib.util.spec_from_file_location(path, path)
			module = importlib.util.module_from_spec(spec)

			module.__lib__   = cls.__lib__
			module.__route__ = route
			module.__mtime__ = os.path.getmtime(path)
			module.__dict__['UNDEFINED'] = cls.__lib__.Undefined

			sys.modules[path] = module

			spec.loader.exec_module(module)

		return module

	# Get class
	# ----------------------------------------------------------------------
	@classmethod
	def get_class(cls, lib, class_name, path, route=None, namespace=None):
		file_path = path
		
		if not path.endswith('.py'):
			file_name = lib.String.camel_to_snake(class_name) + '.py'
			file_path = os.path.realpath(os.path.join(path, file_name))

		module = cls.load_module(lib, file_path, route, namespace)
		return getattr(module, class_name)
