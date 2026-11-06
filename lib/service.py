# ======================================================================
# CLASS Service
# ======================================================================

import types

from .module import Module


class Service(Module):

	__instance__ = None

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# New.
	# ----------------------------------------------------------------------
	def __new__(cls):
		instance = cls.__dict__.get('__instance__')

		if instance is None:
			instance   = super().__new__(cls)
			initialize = getattr(cls, 'initialize', None)

			instance.__dict__['_initialize']      = initialize
			instance.__dict__['_is_initialized']  = initialize is None
			instance.__dict__['_is_initializing'] = False
			instance.__dict__['initialize']       = types.MethodType(cls._initialize, instance)

			cls.__instance__ = instance

		return instance

	# Use the service class when a namespace instance appears as a base.
	# ----------------------------------------------------------------------
	def __mro_entries__(self, bases):
		return (type(self),)

	# Get service attribute.
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		if self.__dict__.get('_is_initialized', True) or self.__dict__.get('_is_initializing', False):
			result = super().__getattr__(name)
		else:
			raise RuntimeError(f'Service `{self.__class__.__name__}` is not initialized. Call `initialize()` before use.')

		return result

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Initialize.
	# ----------------------------------------------------------------------
	def _initialize(self, *args, **kwargs):
		initialize = self.__dict__['_initialize']

		if not self.__dict__['_is_initialized']:
			if initialize is not None:
				self.__dict__['_is_initializing'] = True

				try:
					initialize(self, *args, **kwargs)
					self.__dict__['_is_initialized'] = True
				finally:
					self.__dict__['_is_initializing'] = False
		else:
			raise RuntimeError(f'Service `{self.__class__.__name__}` is already initialized')
