from .module import Module


class Plugin(Module):

	EXTENSIONS = []

	# Create plugin with lib of it's layer
	# ------------------------------------------------------------------
	def __init__(self, lib):
		self.lib = lib

	# Try to materialize file carrier from candidate
	# ------------------------------------------------------------------
	def __call__(self, name, parent_path, parent_route):
		raise NotImplementedError(f'Plugin `{type(self).__name__}` must implement __call__()')