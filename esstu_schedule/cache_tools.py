"""Thread-safe TTL cache and per-request-key duplicate work suppression."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from inspect import signature
from threading import RLock


class TTLCache:
    def __init__(self):
        self._data = {}
        self._guard = RLock()

    def get(self, key, ttl):
        with self._guard:
            entry = self._data.get(key)
            if entry and time.time() - entry[0] < ttl:
                return entry[1]
            return None

    def put(self, key, value):
        with self._guard:
            self._data[key] = (time.time(), value)

    def clear(self):
        with self._guard:
            self._data.clear()

    def entry(self, key):
        with self._guard:
            return self._data.get(key)


_guard, _flights = RLock(), {}


def singleflight(function):
    sig = signature(function)

    @wraps(function)
    def wrapped(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        key = (
            function.__module__,
            function.__qualname__,
            tuple(
                (name, value)
                for name, value in bound.arguments.items()
                if name not in ("loader", "force", "force_refresh")
            ),
        )
        with _guard:
            entry = _flights.setdefault(key, [RLock(), 0])
            entry[1] += 1
        try:
            with entry[0]:
                return function(*args, **kwargs)
        finally:
            with _guard:
                entry[1] -= 1
                if not entry[1]:
                    del _flights[key]

    return wrapped


_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="schedule-refresh")
_refreshing, _service_cache = set(), TTLCache()


def stale_while_revalidate(function):
    """Fresh 15 min; stale up to 1 h while exactly one refresh runs per key.

    Cold/too-old/forced requests wait for singleflight. Refresh failure keeps
    the old timestamp, so an error can never turn stale data into fresh data.
    """
    sig = signature(function)

    @wraps(function)
    def wrapped(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        force = bound.arguments.get("force_refresh", False)
        key = (
            function.__name__,
            tuple((k, v) for k, v in bound.arguments.items() if k != "force_refresh"),
        )

        def load():
            value = function(*args, **kwargs)
            if not (
                isinstance(value, dict)
                and value.get("is_stale_fallback")
                and _service_cache.entry(key)
            ):
                _service_cache.put(key, value)
            return value

        def background():
            try:
                _load_service(key, load)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Refresh failed for %s", key, exc_info=True
                )
            finally:
                with _guard:
                    _refreshing.discard(key)

        entry = _service_cache.entry(key)
        age = time.time() - entry[0] if entry else float("inf")
        if not force and age < 900:
            return entry[1]
        if not force and age < 3600:
            with _guard:
                if key not in _refreshing:
                    _refreshing.add(key)
                    _executor.submit(background)
            from copy import deepcopy

            result = deepcopy(entry[1])
            if isinstance(result, dict):
                result["cache_state"] = "stale_while_revalidate"
                result["is_stale_fallback"] = True
            return result
        return _load_service(key, load, force)

    return wrapped


@singleflight
def _load_service(key, loader, force=False):
    entry = _service_cache.entry(key)
    if not force and entry and time.time() - entry[0] < 900:
        return entry[1]
    return loader()
