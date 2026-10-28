# ======================================================================
# Route standard logging into dynamically scoped Almasi directories.
# ======================================================================

import contextvars
import logging
import os
import re
import threading

from contextlib import contextmanager

from .module import Module


class LogRoute(logging.Handler):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Route each event using the emitting task's context.
	# ----------------------------------------------------------------------
	def emit(self, record):
		contexts = Logger._contexts.get()
		if contexts:
			owner, directory = contexts[-1]
			message = record.getMessage()
			if hasattr(record, 'artifact_name'):
				filename = owner._artifact(directory, record)
				message = f'Artifact created: {filename}'
			if record.exc_info:
				message += '\n' + logging.Formatter().formatException(record.exc_info)

			line = logging.Formatter('%(asctime)s').format(record) + f' {record.levelname} {record.name}: {message}\n'
			seen = set()
			for owner, directory in contexts:
				path = directory.join('log.txt')
				if path not in seen:
					with open(path, 'a', encoding='utf-8') as output:
						output.write(line)
					seen.add(path)
			contexts[-1][0]._log_event(record)


class LogTerminalFilter(logging.Filter):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Existing handlers remain available outside file logging contexts.
	# ----------------------------------------------------------------------
	def filter(self, record):
		result = not Logger._contexts.get()
		return result


class Logger(Module):

	_contexts = contextvars.ContextVar('almasi_log_directories', default=())
	_lock     = threading.RLock()
	_users    = 0
	_handler  = None
	_filters  = ()
	_level    = None
	_loggers  = ()

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Preserve extensions and number independently for each event name.
	# ----------------------------------------------------------------------
	def _artifact(self, directory, record):
		name = record.artifact_name
		if self._is_artifact_name(name):
			stem, extension = os.path.splitext(name)
			stem            = re.sub(r'[^\w.-]', '_', stem)
			pattern         = re.compile(re.escape(stem) + r'_(\d+)' + re.escape(extension) + r'\Z')
			number          = 0
			for child in directory:
				match = pattern.fullmatch(child.get_name())
				if match:
					number = max(number, int(match[1]))
			filename = f'{stem}_{number + 1:03d}{extension}'
			directory.write(filename, record.artifact_data)
		else:
			raise ValueError(f'Invalid artifact name: {name}')
		return filename

	# Require a named serializable artifact with a preserved extension.
	# ----------------------------------------------------------------------
	@staticmethod
	def _is_artifact_name(name):
		result = isinstance(name, str) and bool(os.path.splitext(name)[0]) and os.path.splitext(name)[1] in ('.txt', '.json')
		return result

	# Subclasses may consume event metadata without changing routing.
	# ----------------------------------------------------------------------
	def _log_event(self, record):
		pass

	# Install one router for all active contexts, preserving existing handlers.
	# ----------------------------------------------------------------------
	@classmethod
	def _install(cls):
		with Logger._lock:
			if Logger._users == 0:
				root             = logging.getLogger()
				Logger._level    = root.level
				Logger._handler  = LogRoute(logging.INFO)
				terminal_filter  = LogTerminalFilter()
				handlers         = set(root.handlers)
				for candidate in logging.Logger.manager.loggerDict.values():
					if isinstance(candidate, logging.Logger):
						handlers.update(candidate.handlers)
				Logger._loggers = tuple((candidate, candidate.level) for candidate in logging.Logger.manager.loggerDict.values() if isinstance(candidate, logging.Logger))
				for candidate, level in Logger._loggers:
					candidate.setLevel(min(level, logging.INFO))
					if not candidate.propagate:
						candidate.addHandler(Logger._handler)
				Logger._filters = tuple((handler, terminal_filter) for handler in handlers)
				for handler, event_filter in Logger._filters:
					handler.addFilter(event_filter)
				root.addHandler(Logger._handler)
				root.setLevel(min(root.level, logging.INFO))
			Logger._users += 1

	# Restore the logging configuration after the last context exits.
	# ----------------------------------------------------------------------
	@classmethod
	def _remove(cls):
		with Logger._lock:
			Logger._users -= 1
			if Logger._users == 0:
				root = logging.getLogger()
				root.removeHandler(Logger._handler)
				Logger._handler.close()
				for handler, event_filter in Logger._filters:
					handler.removeFilter(event_filter)
				for candidate, level in Logger._loggers:
					candidate.removeHandler(Logger._handler)
					candidate.setLevel(level)
				Logger._loggers = ()
				root.setLevel(Logger._level)
				Logger._handler = None
				Logger._filters = ()

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Nest directories while routing artifacts only to the innermost scope.
	# ----------------------------------------------------------------------
	@contextmanager
	def logging(self, directory):
		parent = directory.get_lib().Directory(directory.get_lib(), os.path.dirname(directory.get_path()), directory.get_route())
		parent.mkdir(directory.get_name())
		self._install()
		token = Logger._contexts.set(Logger._contexts.get() + ((self, directory),))
		try:
			yield directory
		finally:
			Logger._contexts.reset(token)
			self._remove()
