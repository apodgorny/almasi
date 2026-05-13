import asyncio
import time

import a
from lib.events import Events
from lib.function import Function


class TestCore(a.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def test_undefined_surface(cls):
		error    = None
		expected = f'{a.Undefined.__lib__.__name__}.Undefined'

		assert bool(a.Undefined) == False
		assert repr(a.Undefined) == expected
		assert str(a.Undefined) == expected

		try:
			a.Undefined.foo
		except AttributeError as e:
			error = e

		assert error is not None
		assert str(error) == '`Undefined` has no attribute `foo`'

	# ----------------------------------------------------------------------
	@classmethod
	def test_undefined_rejects_use_as_value(cls):
		errors = []

		for action in [
			lambda: a.Undefined(),
			lambda: a.Undefined['x'],
			lambda: len(a.Undefined),
			lambda: iter(a.Undefined),
		]:
			try:
				action()
			except TypeError as e:
				errors.append(str(e))

		assert errors == [
			'`Undefined` is not callable',
			'`Undefined` is not subscriptable',
			'`Undefined` has no len()',
			'`Undefined` is not iterable',
		]

	# ----------------------------------------------------------------------
	@classmethod
	def test_string_naming_conversions(cls):
		assert a.String.snake_to_camel('almasi') == 'Almasi'
		assert a.String.snake_to_camel('almasi', capitalize=False) == 'almasi'
		assert a.String.camel_to_snake('Almasi') == 'almasi'
		assert a.String.camel_to_snake('VectorDB') == 'vector_d_b'
		assert a.String.camel_to_snake('VectorDB', allow_consequent_caps=True) == 'vector_db'
		assert a.String.normalize_whitespace('  one\n\t two   ') == 'one two'

	# ----------------------------------------------------------------------
	@classmethod
	def test_string_formatting(cls):
		assert a.String.indent('a\n\nb', prefix='> ') == '> a\n\n> b'
		assert a.String.underlined('x') == f'{a.String.UNDERLINE}x{a.String.RESET}'
		assert a.String.italic('x') == f'{a.String.ITALIC}x{a.String.RESET}'
		assert a.String.strikethrough('x') == f'{a.String.STRIKETHROUGH}x{a.String.RESET}'
		assert a.String.color('x') == 'x'
		assert a.String.color('x', a.String.RED, 'bu') == (
			f'{a.String.BOLD}{a.String.UNDERLINE}{a.String.RED}x{a.String.RESET}'
		)

	# ----------------------------------------------------------------------
	@classmethod
	def test_string_hash_shape(cls):
		one = a.String.hash('almasi', digits=12)
		two = a.String.hash('almasi', digits=12)

		assert one == two
		assert isinstance(one, int)
		assert len(str(one)) == 12

	# ----------------------------------------------------------------------
	@classmethod
	def test_function_identity_and_call(cls):
		def init(self):
			self.value = 3

		def instance(self, x):
			return self.value + x

		def klass(cls, x):
			return x + 4

		def static(x):
			return x + 5

		Example = type(
			'Example',
			(),
			{
				'__init__' : init,
				'instance' : instance,
				'klass'    : classmethod(klass),
				'static'   : staticmethod(static),
			}
		)

		example      = Example()
		instance_one = Function(example.instance)
		instance_two = Function(example.instance)
		klass        = Function(Example.klass)
		static       = Function(Example.static)

		assert instance_one == instance_two
		assert hash(instance_one) == hash(instance_two)
		assert instance_one(4) == 7
		assert klass(4) == 8
		assert static(4) == 9
		assert Function(instance_one) == instance_one

	# ----------------------------------------------------------------------
	@classmethod
	def test_function_async_call(cls):
		async def run(x):
			return x + 1

		result = asyncio.run(Function(run)(4))

		assert result == 5
		assert Function(run).is_async() == True

	# ----------------------------------------------------------------------
	@classmethod
	def test_timer_accumulates_and_resets(cls):
		a.Timer.reset()
		a.Timer.start('almasi-test')
		time.sleep(0.001)
		a.Timer.stop('almasi-test')

		assert a.Timer.get_time('almasi-test') > 0

		a.Timer.reset()

		assert a.Timer.get_time('almasi-test') == 0


if __name__ == '__main__':
	TestCore.run()
