"""Thread-safe TTL cache and per-request-key duplicate work suppression."""
from functools import wraps
from inspect import signature
from threading import RLock
import time


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


_guard, _flights = RLock(), {}


def singleflight(function):
    sig = signature(function)

    @wraps(function)
    def wrapped(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        key = (function.__name__, tuple(bound.arguments.items()))
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
