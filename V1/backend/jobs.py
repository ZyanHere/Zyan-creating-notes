"""Work that outlives an HTTP request.

Generation is a model call plus a browser render: minutes on a good day, and on
the free tier it has returned an empty body twice in a row and cost two calls
doing it. A browser fetch held open for that is unusable and, worse, undebuggable
-- the failure arrives as a dead socket with nothing said about why.

So the request starts the work and returns; the client polls. That is the whole
of this module.

**Not a job queue.** No persistence, no retries, no fan-out, no worker pool --
Architecture puts those at M4, when a set of members makes them earn their keep.
What is here is the smallest thing that lets a browser watch a long call: a
thread, a status, and a result. When M4 arrives this is replaced, not extended.

One deliberate consequence: a restart loses running jobs. Finished ones survive,
because their artifact is on disk and the file is the record -- so the failure
mode is "you have to press it again", never "it silently half-happened".
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Job:
    """One unit of long work, and what became of it."""

    key: str
    state: str = "running"  # running | done | failed
    result: Any = None
    error: str | None = None
    detail: str | None = None
    """The traceback, for the log and for us. Never for the user -- `error` is
    what a person reads, and a stack trace in a UI is an apology, not an
    explanation."""

    started_at: float = 0.0
    finished_at: float = 0.0

    def to_json(self) -> dict:
        return {
            "state": self.state,
            "error": self.error,
            "seconds": round((self.finished_at or _now()) - self.started_at, 1),
        }


def _now() -> float:
    import time

    return time.monotonic()


class Jobs:
    """One job per key. Starting a key that is already running is a no-op.

    Idempotent by key rather than by request, because the client polls and a
    double-click on Generate must not spend two model calls.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, key: str, work: Callable[[], Any]) -> Job:
        with self._lock:
            existing = self._jobs.get(key)
            if existing is not None and existing.state == "running":
                return existing
            job = Job(key=key, started_at=_now())
            self._jobs[key] = job

        def run() -> None:
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001 - the boundary; nothing above catches
                job.error = str(exc) or exc.__class__.__name__
                job.detail = traceback.format_exc()
                job.state = "failed"
            else:
                job.result = result
                job.state = "done"
            finally:
                job.finished_at = _now()

        threading.Thread(target=run, name=f"job:{key}", daemon=True).start()
        return job

    def get(self, key: str) -> Job | None:
        with self._lock:
            return self._jobs.get(key)

    def forget(self, key: str) -> None:
        """Drop a finished job so the same key can be run again."""
        with self._lock:
            job = self._jobs.get(key)
            if job is not None and job.state != "running":
                del self._jobs[key]


JOBS = Jobs()
