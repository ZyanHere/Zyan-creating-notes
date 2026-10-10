"""Provider wrappers. Both are instruments -- neither changes what V1 decides.

`Counting` delegates every call to the real provider and records what it cost.
`Stub` answers from canned payloads so the whole harness can be exercised end to
end without spending a request, which is how the plumbing gets proved before a
50-requests-a-day budget is spent on it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallRecord:
    ok: bool
    seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    schema: str = ""

    def to_json(self) -> dict:
        return {
            "ok": self.ok,
            "seconds": round(self.seconds, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "schema": self.schema,
            "error": self.error,
        }


class Counting:
    """Wraps a real provider. Records every call; changes none of them.

    V1 retries inside `agent.plan._call` on a validation failure, so one logical
    decision can be two calls here. That is deliberate: the record shows the true
    number of requests, which is what a rate limit counts.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.name = inner.name
        self.model = inner.model
        self.calls: list[CallRecord] = []

    def complete(self, *, system: str, user: str, schema: dict, max_tokens: int):
        started = time.monotonic()
        title = (schema or {}).get("title", "")
        try:
            completion = self._inner.complete(
                system=system, user=user, schema=schema, max_tokens=max_tokens
            )
        except Exception as exc:
            self.calls.append(
                CallRecord(
                    ok=False,
                    seconds=time.monotonic() - started,
                    error=f"{type(exc).__name__}: {exc}",
                    schema=title,
                )
            )
            raise
        self.calls.append(
            CallRecord(
                ok=True,
                seconds=time.monotonic() - started,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
                schema=title,
            )
        )
        return completion

    def totals(self) -> dict:
        return {
            "model_calls": len(self.calls),
            "failed_calls": sum(1 for c in self.calls if not c.ok),
            "input_tokens": sum(c.input_tokens for c in self.calls),
            "output_tokens": sum(c.output_tokens for c in self.calls),
            "seconds": round(sum(c.seconds for c in self.calls), 2),
            "calls": [c.to_json() for c in self.calls],
        }


@dataclass
class Stub:
    """Schema-shaped answers with no model behind them.

    Exists to prove the harness drives V1 correctly -- case loading, the intake
    routing, corrections, approval, the record schema -- before any of it is run
    against a paid or rate-limited provider. The plans it produces are nonsense
    and must never be analysed as a baseline.
    """

    subject: str = "Stubbed subject"
    name: str = "stub"
    model: str = "stub-1"
    calls: list = field(default_factory=list)

    def complete(self, *, system: str, user: str, schema: dict, max_tokens: int):
        from agent.providers import Completion  # noqa: PLC0415 - after attach()

        title = (schema or {}).get("title", "")
        payload = self._payload(title)
        self.calls.append(CallRecord(ok=True, seconds=0.0, schema=title))
        return Completion(
            text=json.dumps(payload),
            input_tokens=0,
            output_tokens=0,
            model=self.model,
            provider=self.name,
        )

    def totals(self) -> dict:
        return {
            "model_calls": len(self.calls),
            "failed_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "seconds": 0.0,
            "calls": [c.to_json() for c in self.calls],
            "stub": True,
        }

    # -- canned shapes -------------------------------------------------------

    _CONCEPTS = ("Alpha", "Beta", "Gamma")

    def _situation(self) -> dict:
        return {
            "subject": self.subject,
            "job": "orient",
            "entry_point": "Nothing assumed.",
            "purpose": "Stub run.",
            "target_capability": "Prove the harness works.",
            "capacity": None,
            "stated": [],
            "inferred": [],
        }

    def _payload(self, title: str) -> dict:
        if title == "Reading":
            return {
                "interpret_situation": self._situation(),
                "axes": [
                    {
                        "axis": axis,
                        "value": self.subject if axis == "subject" else "stub",
                        "source": "inferred",
                        "supported_by": [],
                        "would_differ": "nothing, this is a stub",
                        "materiality": "no_effect",
                    }
                    for axis in (
                        "subject", "purpose", "entry_point", "target_capability",
                        "capacity", "depth_register", "artifact_type", "template",
                    )
                ],
            }
        if title == "Intake":
            return {"questions": []}
        if title == "Landscape":
            return {
                "derive_structure": {
                    "concepts": [
                        {"name": c, "built_from": [], "family": "stub"}
                        for c in self._CONCEPTS
                    ]
                },
                "relevance": {
                    "judgements": [
                        {"concept": c, "in_play": True, "why": "stub"}
                        for c in self._CONCEPTS
                    ]
                },
            }
        if title == "PlanBody":
            return {
                "traversal": {"sequence": ["First", "Second"], "why": "stub"},
                "consequence": {"exclusions": []},
                "scope": {
                    "covered": [
                        {"concept": c, "depth": "explain", "why": "stub",
                         "anticipates": "none"}
                        for c in self._CONCEPTS
                    ],
                    "cut": [],
                },
                "partition": {
                    "modules": [
                        {"title": "First", "covers": ["Alpha"], "why_here": "stub",
                         "capability": "Do the first stub thing."},
                        {"title": "Second", "covers": ["Beta", "Gamma"],
                         "why_here": "stub",
                         "capability": "Do the second stub thing."},
                    ]
                },
            }
        if title == "Routing":
            return {"targets": [], "reading": "stubbed correction", "out_of_scope": None}
        if title == "Section":
            return {
                "heading": "stub",
                "eyebrow": None,
                "heading_tail": None,
                "blocks": [{"kind": "prose", "text": "Alpha Beta Gamma stub prose."}],
            }
        raise RuntimeError(f"stub has no payload for schema {title!r}")
