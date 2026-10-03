"""Byte-bounded LRU with coalesced requests and bounded simultaneous workers."""

from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Future
from threading import Lock


class ShadeBusy(Exception):
    """No calculation worker is available; clients can retry later."""


class ShadeCache:
    """Cache immutable serialized results, never failures or mutable arrays.

    Identical concurrent misses share one calculation. Different misses are
    rejected when workers are occupied, bounding memory instead of queueing
    arbitrary geometry loads. Completed entries are evicted by serialized bytes.
    """

    def __init__(self, max_bytes: int, workers: int):
        if max_bytes <= 0 or workers <= 0:
            raise ValueError("Positive cache budget and worker count are required")
        self.max_bytes = max_bytes
        self.workers = workers
        self._entries: OrderedDict[str, bytes] = OrderedDict()
        self._pending: dict[str, Future] = {}
        self._bytes = 0
        self._lock = Lock()

    @property
    def size_bytes(self):
        with self._lock:
            return self._bytes

    def get_or_compute(self, key: str, calculate: Callable[[], bytes]):
        """Return (serialized result, reused); propagate errors without caching."""
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key], True
            future = self._pending.get(key)
            owner = future is None
            if owner:
                if len(self._pending) >= self.workers:
                    raise ShadeBusy("Shade workers busy; retry this request")
                future = Future()
                self._pending[key] = future
        if not owner:
            return future.result(), True
        try:
            result = calculate()
            if not isinstance(result, bytes):
                raise TypeError("Shade cache results must be immutable bytes")
            with self._lock:
                if len(result) <= self.max_bytes:
                    while self._bytes + len(result) > self.max_bytes:
                        _, removed = self._entries.popitem(last=False)
                        self._bytes -= len(removed)
                    self._entries[key] = result
                    self._bytes += len(result)
                # Publish completion before another request can claim this key.
                future.set_result(result)
                del self._pending[key]
            return result, False
        except BaseException as error:
            with self._lock:
                future.set_exception(error)
                del self._pending[key]
            raise
