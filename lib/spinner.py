import sys


class Spinner:

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Load terminal rendering only when progress is requested.
	# ----------------------------------------------------------------------
	def __init__(self, *args, done_label=None, failure_label=None, **kwargs):
		from yaspin import yaspin
		self._spinner   = yaspin(*args, **kwargs)
		self.done_label = done_label
		self.failure_label = failure_label

	# Keep the cursor hidden while the operation is active.
	# ----------------------------------------------------------------------
	def __enter__(self):
		self._spinner.__enter__()
		if sys.stdout.isatty():
			print('\033[?25l', end='', flush=True)
		return self._spinner

	# Restore terminal state on every exit and report success only.
	# ----------------------------------------------------------------------
	def __exit__(self, exc_type, exc_value, traceback):
		self._spinner.__exit__(exc_type, exc_value, traceback)
		if exc_type is None:
			print('\033[1;32m✔\033[0m ' + self._spinner.text if self.done_label is None else self.done_label)
		elif self.failure_label is not None:
			print(self.failure_label)

	# Share the same entry lifecycle with asynchronous operations.
	# ----------------------------------------------------------------------
	async def __aenter__(self):
		return self.__enter__()

	# Preserve exception and cancellation propagation in asynchronous contexts.
	# ----------------------------------------------------------------------
	async def __aexit__(self, exc_type, exc_value, traceback):
		self.__exit__(exc_type, exc_value, traceback)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================


	# Refresh the active label without starting another terminal renderer.
	# ----------------------------------------------------------------------
	def update(self, text):
		self._spinner.text = text

	# Report persisted work without starting a spinner.
	# ----------------------------------------------------------------------
	@staticmethod
	def skipped(text):
		print('\033[90m✔ ' + text + ' — skipped\033[0m')
