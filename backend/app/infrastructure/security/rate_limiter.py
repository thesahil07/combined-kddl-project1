"""Rate limiters for authentication requests."""

from threading import Lock
from time import monotonic

from redis import Redis


class RedisRateLimiter:
    def __init__(self, client: Redis, limit: int = 5, window_seconds: int = 60) -> None:
        self._client, self._limit, self._window = client, limit, window_seconds

    def allow(self, key: str) -> bool:
        count = self._client.incr(key)
        if count == 1:
            self._client.expire(key, self._window)
        return count <= self._limit


class InMemoryRateLimiter:
    """Single-process limiter permitted exclusively for local development.

    This intentionally is not suitable for production or multiple API workers:
    each process has its own counters. Production uses ``RedisRateLimiter``.
    """

    def __init__(self, limit: int = 5, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._requests: dict[str, tuple[int, float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = monotonic()
        with self._lock:
            count, window_start = self._requests.get(key, (0, now))
            if now - window_start >= self._window:
                count, window_start = 0, now
            count += 1
            self._requests[key] = (count, window_start)
            return count <= self._limit
