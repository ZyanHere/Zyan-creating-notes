"""Structured events to stdout.

One line of JSON per event, because at T1 the deployment target's log viewer is the
only consumer and a metrics system is a dependency we have no number to justify yet.

The event set this has to carry is fixed by the design, and every field in it exists
because a specific question was hard to answer in V1 -- "was that the model or the
quota", "why did this project cost 46 calls", "where did 11,537 seconds go". So the
helpers below are named after the questions rather than after the subsystems.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any


def _emit(event: str, **fields: Any) -> None:
    line = {"ts": round(time.time(), 3), "event": event, **_clean(fields)}
    print(json.dumps(line, separators=(",", ":"), default=str), file=sys.stdout, flush=True)


def _clean(fields: dict[str, Any]) -> dict[str, Any]:
    """Drop Nones so a line carries only what is known.

    Bytes become hex: every identity in this system is 16 or 32 bytes, and a log line
    that prints b'\\x9f...' is a log line nobody greps.
    """
    out: dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        out[key] = value.hex() if isinstance(value, (bytes, bytearray)) else value
    return out


def info(event: str, **fields: Any) -> None:
    _emit(event, level="info", **fields)


def warn(event: str, **fields: Any) -> None:
    _emit(event, level="warn", **fields)


def error(event: str, **fields: Any) -> None:
    _emit(event, level="error", **fields)


# ── the questions the design requires an answer to ────────────────────────────────

def derivation(
    *,
    result_domain: str,
    result_identity: bytes | str,
    reused: bool,
    reconciled: bool = False,
    claim_epoch: int | None = None,
    fenced: bool = False,
) -> None:
    """Answers: why did this project cost N calls?

    `result_identity`, never `envelope` -- render, source_extract and routing are claim
    domains with no envelope, and a field that only sometimes applies is a field that
    gets misread.
    """
    info(
        "derivation",
        result_domain=result_domain,
        result_identity=result_identity,
        reused=reused,
        reconciled=reconciled,
        claim_epoch=claim_epoch,
        fenced=fenced,
    )


def model_attempt(
    *,
    operation: str,
    origin: str,
    provider: str,
    model_id: str,
    outcome: str,
    wall_ms: int,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    attempt: int = 1,
    retry_after_s: float | None = None,
    task_id: str | None = None,
) -> None:
    """Answers: was that the model, or the quota?

    V1's lesson in one line -- a spent rate limit and an omitting model produced the
    same report, and the fixes are opposite.
    """
    info(
        "model_attempt",
        operation=operation,
        origin=origin,
        provider=provider,
        model_id=model_id,
        outcome=outcome,
        wall_ms=wall_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        attempt=attempt,
        retry_after_s=retry_after_s,
        task_id=task_id,
    )


def task_transition(
    *,
    task_id: str,
    kind: str,
    state: str,
    epoch: int,
    reason: str | None = None,
) -> None:
    """Answers: where did the time go?"""
    info(
        "task_transition",
        task_id=task_id, kind=kind, state=state, epoch=epoch, reason=reason,
    )
