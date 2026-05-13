import a


class TestPlugins(a.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def test_data_plugin_loads_json_fixture(cls):
		value = a.tests.fixtures.Fixture

		assert isinstance(value, dict)
		assert value['name'] == 'fixture'
		assert value['items'] == [1, 2, 3]
		assert value['meta'] == {'kind' : 'simple', 'active' : True}


if __name__ == '__main__':
	TestPlugins.run()
