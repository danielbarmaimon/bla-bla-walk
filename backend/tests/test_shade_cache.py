"""Cache lifecycle and concurrency checks without timing-dependent sleeps."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from bla_bla_walk.shade_cache import ShadeBusy, ShadeCache


def test_byte_budget_lru_and_oversized_results():
    cache = ShadeCache(6, 1)
    assert cache.get_or_compute("a", lambda: b"aaa") == (b"aaa", False)
    cache.get_or_compute("b", lambda: b"bbb")
    assert cache.get_or_compute("a", lambda: pytest.fail("Unexpected miss"))[1]
    cache.get_or_compute("c", lambda: b"ccc")
    assert not cache.get_or_compute("b", lambda: b"bbb")[1]
    assert cache.size_bytes == 6
    assert not cache.get_or_compute("huge", lambda: b"x" * 7)[1]
    assert not cache.get_or_compute("huge", lambda: b"x" * 7)[1]
    assert cache.size_bytes == 6


def test_failed_calculations_release_capacity_and_are_not_cached():
    cache = ShadeCache(100, 1)

    def fail():
        raise ValueError("Missing geometry")

    with pytest.raises(ValueError, match="Missing"):
        cache.get_or_compute("a", fail)
    assert cache.get_or_compute("a", lambda: b"ok") == (b"ok", False)
    with pytest.raises(TypeError):
        cache.get_or_compute("mutable", lambda: bytearray(b"no"))
    assert cache.get_or_compute("mutable", lambda: b"ok")[0] == b"ok"


def test_identical_misses_coalesce_and_other_misses_are_bounded():
    cache = ShadeCache(100, 1)
    started, release = Event(), Event()

    def slow():
        started.set()
        assert release.wait(5)
        return b"same"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get_or_compute, "a", slow)
        assert started.wait(5)
        second = pool.submit(
            cache.get_or_compute, "a", lambda: pytest.fail("Duplicated")
        )
        with pytest.raises(ShadeBusy):
            cache.get_or_compute("b", lambda: b"other")
        release.set()
        assert first.result() == (b"same", False)
        assert second.result() == (b"same", True)


def test_coalesced_failure_reaches_waiters_then_retry_succeeds():
    cache = ShadeCache(100, 1)
    started, release, joined = Event(), Event(), Event()

    def fail():
        started.set()
        assert release.wait(5)
        raise OSError("Absent")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get_or_compute, "a", fail)
        assert started.wait(5)
        # Instrument the pending future to signal a waiter has joined.
        future = cache._pending["a"]
        original = future.result

        def waiting():
            joined.set()
            return original()

        future.result = waiting
        second = pool.submit(cache.get_or_compute, "a", lambda: b"unexpected")
        assert joined.wait(5)
        release.set()
        for task in (first, second):
            with pytest.raises(OSError, match="Absent"):
                task.result()
    assert cache.get_or_compute("a", lambda: b"recovered") == (b"recovered", False)
