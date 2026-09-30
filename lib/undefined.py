class UndefinedMeta(type):

	def __repr__(cls)                  : return cls.__lib__.__name__ + '.Undefined'
	def __str__(cls)                   : return cls.__lib__.__name__ + '.Undefined'
	def __bool__(cls)                  : return False
	def __getattr__(cls, name)         : raise AttributeError(f'`Undefined` has no attribute `{name}`')
	def __getitem__(cls, key)          : raise TypeError(f'`Undefined` is not subscriptable')
	def __call__(cls, *args, **kwargs) : raise TypeError(f'`Undefined` is not callable')
	def __delattr__(cls, name)         : raise AttributeError(f'`Undefined` has no attribute `{name}`')
	def __setitem__(cls, key, value)   : raise TypeError(f'`Undefined` does not support item assignment')
	def __delitem__(cls, key)          : raise TypeError(f'`Undefined` does not support item deletion')
	def __len__(cls)                   : raise TypeError(f'`Undefined` has no len()')
	def __iter__(cls)                  : raise TypeError(f'`Undefined` is not iterable')

	def __setattr__(cls, name, value):
		if name == '__lib__':
			type.__setattr__(cls, name, value)
		else:
			raise AttributeError(f'`Undefined` has no attribute `{name}`')


class Undefined(metaclass=UndefinedMeta):
	__lib__ = None
