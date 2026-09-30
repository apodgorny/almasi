# ======================================================================
# CLASS Service
# ======================================================================

import types

from .module import Module


class Service(Module):

	__instance__ = None

	# New.
	# ------------------------------------------------------------------
	def __new__(cls):
		instance = cls.__instance__

		if instance is None:
			instance = super().__new__(cls)
			initialize = cls.__dict__.get('initialize')

			instance.__dict__['_initialize']     = initialize
			instance.__dict__['_is_initialized'] = initialize is None
			instance.__dict__['_is_initializing'] = False
			instance.__dict__['initialize']      = types.MethodType(cls._initialize, instance)

			cls.__instance__ = instance

		return instance

	# Initialize.
	# ------------------------------------------------------------------
	def _initialize(self, *args, **kwargs):
		initialize = self.__dict__['_initialize']

		if self.__dict__['_is_initialized']:
			raise RuntimeError(f'Service `{self.__class__.__name__}` is already initialized')

		if initialize is not None:
			self.__dict__['_is_initializing'] = True

			try:
				initialize(self, *args, **kwargs)
				self.__dict__['_is_initialized'] = True
			finally:
				self.__dict__['_is_initializing'] = False

	# Get service attribute.
	# ------------------------------------------------------------------
	def __getattr__(self, name):
		if not self.__dict__.get('_is_initialized', True) and not self.__dict__.get('_is_initializing', False):
			raise RuntimeError(f'Service `{self.__class__.__name__}` is not initialized. Call `initialize()` before use.')

		return super().__getattr__(name)

# import types


# class Service(Module):

# 	# Serve service item
# 	# ------------------------------------------------------------------
# 	@classmethod
# 	def serve(cls, service_cls):
# 		instance   = service_cls()
# 		initialize = service_cls.__dict__.get('initialize')

# 		instance.__dict__['__initialize__']     = initialize
# 		instance.__dict__['__is_is_initialized__'] = initialize is None
# 		instance.__dict__['initialize']         = types.MethodType(cls.initialize, instance)

# 		return instance

# 	# Initialize service item
# 	# ------------------------------------------------------------------
# 	def initialize(self, *args, **kwargs):
# 		if not self.__dict__.get('__is_is_initialized__', True):
# 			self.__dict__['__initialize__'](self, *args, **kwargs)
# 			self.__dict__['__is_is_initialized__'] = True

# 	# Get service attribute
# 	# ------------------------------------------------------------------
# 	def __getattr__(self, name):
# 		if not self.__dict__.get('__is_is_initialized__', True):
# 			raise RuntimeError(f'Service `{self.__class__.__name__}` is not initialized. Call `initialize(args)` before use.')

# 		raise AttributeError(f'`{self.__class__.__name__}` has no attribute `{name}`')
