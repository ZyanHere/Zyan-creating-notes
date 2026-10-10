"""The clock, as a port.

Every lease, every expiry, every quota window reads time through this. Not for
elegance: the concurrency suite has to force a lease to expire while a worker is still
alive, and the only alternative is `sleep()`. Those are the tests that must never be
skipped, so they must never be slow.

So the rule is narrow and absolute: nothing outside this module calls
`datetime.now()`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, always timezone-aware UTC."""
        ...


class SystemClock:
    """The real one."""

    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """A clock the tests move by hand.

    Lives beside the real one rather than in a test fixture because a lease test and
    a quota-window test need the same behaviour, and two copies of a fake clock
    eventually disagree.
    """

    __slots__ = ("_now",)

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float = 0, **kwargs: float) -> datetime:
        """Move time forward. `advance(seconds=61)` expires a 60s lease."""
        self._now += timedelta(seconds=seconds, **kwargs)
        return self._now
