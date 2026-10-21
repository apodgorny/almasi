from .module import Module


class Plugin(Module):

	EXTENSIONS = []

	# Create plugin with lib of it's layer
	# ------------------------------------------------------------------
	def __init__(self, lib):
		self.lib = lib

	# Try to materialize file carrier from candidate
	# source_lib owns the file being loaded; self.lib owns this loader.
	# ------------------------------------------------------------------
	def __call__(self, name, parent_path, parent_route, source_lib):
		raise NotImplementedError(f'Plugin `{type(self).__name__}` must implement __call__()')