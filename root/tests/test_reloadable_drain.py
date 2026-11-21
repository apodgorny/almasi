# ==============================================================================
# TEST RELOADABLE DRAIN
# ==============================================================================
# PURPOSE:
# Verify the shared reload gate preserves synchronous and asynchronous calls.
# ==============================================================================
import asyncio
import inspect
import threading

from concurrent.futures import ThreadPoolExecutor

import a


class TestReloadableDrain(a.Tester):

	# Block until a reload has closed admission, without using worker sleeps.
	# ----------------------------------------------------------------------
	@classmethod
	def _wait_paused(cls, gate):
		with gate['condition']:
			while not gate['paused']:
				gate['condition'].wait(0.01)

	# Check that a frozen class finishes old calls before admitting new ones.
	# ----------------------------------------------------------------------
	@classmethod
	def test_sync_drain(cls):
		class Worker(a.ReloadableModule):
			def work(self, started, release):
				started.set()
				assert release.wait(5)
				return 'done'

		worker       = Worker()
		started      = threading.Event()
		release      = threading.Event()
		next_started = threading.Event()
		next_release = threading.Event()
		gate         = Worker._reload_gate

		with ThreadPoolExecutor(max_workers=3) as pool:
			active  = pool.submit(worker.work, started, release)
			assert started.wait(2)
			paused  = pool.submit(a.Reloadable._pause, gate, 3)
			cls._wait_paused(gate)
			waiting = pool.submit(worker.work, next_started, next_release)

			assert not next_started.wait(0.05)
			release.set()
			paused.result(timeout=2)
			assert active.result(timeout=2) == 'done'

			a.Reloadable._resume(gate)
			assert next_started.wait(2)
			next_release.set()
			assert waiting.result(timeout=2) == 'done'

	# Verify async callers wait without blocking the event loop.
	# ----------------------------------------------------------------------
	@classmethod
	async def _async_drain(cls):
		class Worker(a.ReloadableModule):
			async def work(self, started, release):
				started.set()
				await release.wait()
				return 'done'

		worker       = Worker()
		started      = asyncio.Event()
		release      = asyncio.Event()
		next_started = asyncio.Event()
		next_release = asyncio.Event()
		gate         = Worker._reload_gate
		active       = asyncio.create_task(worker.work(started, release))

		await started.wait()

		with ThreadPoolExecutor(max_workers=1) as pool:
			paused = pool.submit(a.Reloadable._pause, gate, 3)

			while not gate['paused']:
				await asyncio.sleep(0)

			waiting = asyncio.create_task(worker.work(next_started, next_release))
			await asyncio.sleep(0.02)
			assert not next_started.is_set()
			release.set()
			assert await active == 'done'

			await asyncio.wait_for(asyncio.wrap_future(paused), 2)
			a.Reloadable._resume(gate)
			await asyncio.wait_for(next_started.wait(), 2)
			next_release.set()
			assert await waiting == 'done'

	# Run the asynchronous case on an isolated event loop.
	# ----------------------------------------------------------------------
	@classmethod
	def test_async_drain(cls):
		asyncio.run(cls._async_drain())

	# Keep descriptors ordinary and protect special and class methods.
	# ----------------------------------------------------------------------
	@classmethod
	def test_method_identity(cls):
		class Counter(a.ReloadableModule):
			def value(self):
				return 3

			@classmethod
			def triple(cls, value):
				return value * 3

			@staticmethod
			def add_one(value):
				return value + 1

			def __getitem__(self, key):
				return key + 4

		counter = Counter()
		bound   = counter.value

		assert inspect.ismethod(bound)
		assert bound.__self__ is counter
		assert counter.value() == 3
		assert Counter.triple(3) == 9
		assert Counter.add_one(4) == 5
		assert counter[1] == 5

	# A timeout releases the barrier for future synchronous invocations.
	# ----------------------------------------------------------------------
	@classmethod
	def test_timeout_restores_admission(cls):
		class Worker(a.ReloadableModule):
			def work(self, started, release):
				started.set()
				assert release.wait(5)

		worker  = Worker()
		started = threading.Event()
		release = threading.Event()
		gate    = Worker._reload_gate

		with ThreadPoolExecutor(max_workers=1) as pool:
			active = pool.submit(worker.work, started, release)
			assert started.wait(2)

			try:
				a.Reloadable._pause(gate, 0.01)
			except TimeoutError:
				assert not gate['paused']
			else:
				raise AssertionError('Expected timeout')

			release.set()
			active.result(timeout=2)


if __name__ == '__main__':
	TestReloadableDrain.run()
