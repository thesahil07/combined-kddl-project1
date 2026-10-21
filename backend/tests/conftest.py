"""Test configuration.

Tests use SQLite only for fast, isolated API tests.  MySQL remains the
authoritative migration target because SQLite does not reproduce MySQL stored
generated-column or ENUM semantics.
"""

import pytest

from app.main import app


class FakeRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, int] = {}

    def allow(self, key: str) -> bool:
        self._attempts[key] = self._attempts.get(key, 0) + 1
        return self._attempts[key] <= 5


@pytest.fixture(autouse=True)
def redis_rate_limiter() -> None:
    app.state.rate_limiter = FakeRateLimiter()
    yield
    del app.state.rate_limiter
