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

	# ----------------------------------------------------------------------
	@classmethod
	def test_text_plugin_loads_txt_fixture(cls):
		value = a.tests.fixtures.FixtureText

		assert isinstance(value, str)
		assert value == 'fixture text body\n'

	# ----------------------------------------------------------------------
	@classmethod
	def test_text_plugin_loads_markdown_fixture(cls):
		value = a.tests.fixtures.FixtureMarkdown

		assert isinstance(value, str)
		assert value.startswith('# Fixture Markdown')
		assert 'Fixture markdown body.' in value


if __name__ == '__main__':
	TestPlugins.run()
