import a


class Foo(a.Service):
	
	def initialize(self):
		print('Foo initilized')

	def run(self):
		print('Running')