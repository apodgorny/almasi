import os
import sys
import importlib.util


class Imports:

	__fork_codes__ = {}

	# Give each fork its own module identity while retaining legacy keys.
	# ----------------------------------------------------------------------
	@classmethod
	def module_key(cls, lib, path):
		path = os.path.realpath(path)
		key  = f'{path}#fork-{id(lib)}' if lib.__dict__.get('__fork_source__') is not None else path
		return key

	# Share compiled code objects without sharing the module's globals.
	# ----------------------------------------------------------------------
	@classmethod
	def _execute_fork_module(cls, module, path):
		stat   = os.stat(path)
		stamp  = (stat.st_mtime_ns, stat.st_size)
		cached = cls.__fork_codes__.get(path)

		if cached is None or cached[0] != stamp:
			with open(path, 'rb') as source:
				code = compile(source.read(), path, 'exec')
			cls.__fork_codes__[path] = (stamp, code)
		else:
			code = cached[1]

		exec(code, module.__dict__)

	# Discard source code after a known filesystem mutation.
	# ----------------------------------------------------------------------
	@classmethod
	def invalidate_code(cls, path):
		cls.__fork_codes__.pop(os.path.realpath(path), None)

	# Load once with the explicitly supplied library, never the last imported one.
	# ----------------------------------------------------------------------
	@classmethod
	def load_module(cls, lib, path, route=None, namespace=None):
		path   = os.path.realpath(path)
		key    = cls.module_key(lib, path)
		module = sys.modules.get(key)

		if module is None:
			spec   = importlib.util.spec_from_file_location(key, path)
			module = importlib.util.module_from_spec(spec)

			module.__lib__   = lib
			module.__route__ = route
			module.__mtime__ = os.path.getmtime(path)
			module.__dict__['UNDEFINED'] = lib.Undefined

			if lib.__dict__.get('__fork_source__') is not None:
				module.__dict__['__builtins__'] = lib.__fork_builtins__

			sys.modules[key] = module

			try:
				if lib.__dict__.get('__fork_source__') is not None:
					cls._execute_fork_module(module, path)
				else:
					spec.loader.exec_module(module)
			except Exception:
				sys.modules.pop(key, None)
				raise

		return module

	# Stage fresh source without changing the published Python module.
	# Read the source directly so unchanged file timestamps cannot reuse bytecode.
	# ----------------------------------------------------------------------
	@classmethod
	def prepare_module(cls, lib, path, route):
		path     = os.path.realpath(path)
		key      = cls.module_key(lib, path)
		previous = sys.modules.get(key)
		spec     = importlib.util.spec_from_file_location(key, path)
		module   = importlib.util.module_from_spec(spec)

		module.__lib__   = lib
		module.__route__ = route
		module.__mtime__ = os.path.getmtime(path)
		module.__dict__['UNDEFINED'] = lib.Undefined

		if lib.__dict__.get('__fork_source__') is not None:
			module.__dict__['__builtins__'] = lib.__fork_builtins__

		sys.modules[key] = module

		try:
			with open(path, 'rb') as source:
				exec(compile(source.read(), path, 'exec'), module.__dict__)
		finally:
			if previous is not None:
				sys.modules[key] = previous
			else:
				sys.modules.pop(key, None)

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
