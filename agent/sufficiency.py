"""How much does the system need to know before it starts planning?

A semi-system: the **policy** is code and the **judgment** is the model's.

    POLICY      which situation axes may ever be asked about, which one is a
                prerequisite, and what the question budget is. Derived from
                locked semantics; not re-decided per request.

    JUDGMENT    what each axis currently reads as, what supports that reading,
                and whether a different answer would change the plan.

The decider combines them and produces a record that answers three questions
about every axis: **why did we ask**, **why did we not ask**, and **what would
materially differ**. That record is persisted with `intake_strategy`, so the
judgment is inspectable after the fact rather than trusted at the time.

Nothing here calls a model. Everything here is testable without one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

AxisName = Literal[
    "subject",
    "purpose",
    "entry_point",
    "target_capability",
    "capacity",
    "depth_register",
    "artifact_type",
    "template",
]

AXES: tuple[AxisName, ...] = (
    "subject",
    "purpose",
    "entry_point",
    "target_capability",
    "capacity",
    "depth_register",
    "artifact_type",
    "template",
)


@dataclass(frozen=True, slots=True)
class AxisPolicy:
    """What the system is permitted to do about one axis, and why.

    `because` cites the locked claim. A change here is a change to the product
    semantics, not a tuning decision.
    """

    askable: bool
    blocking: bool
    prerequisite: bool
    priority: int  # lower is asked first when the budget binds
    because: str


# Semantics §1's axis table, read as policy. The user-set axes are the only
# candidates; everything the *system* sets (job, coverage, depth allocation,
# structure, representation, extent) is never a question by construction.
POLICY: dict[AxisName, AxisPolicy] = {
    "subject": AxisPolicy(
        askable=True,
        blocking=True,
        prerequisite=True,
        priority=0,
        because="Semantics §1 — binding, and nothing exists to plan without it. "
        "Obtained before planning rather than weighed against other axes.",
    ),
    "purpose": AxisPolicy(
        askable=True,
        blocking=False,
        prerequisite=False,
        priority=1,
        because="Semantics §5 LOCKED — purpose is the arbiter; it decides every "
        "trade-off downstream, so a wrong reading misdirects the whole plan.",
    ),
    "entry_point": AxisPolicy(
        askable=True,
        blocking=False,
        prerequisite=False,
        priority=2,
        because="Semantics §1 — binding. It fixes what may be assumed, and "
        "assuming wrongly is not recoverable by any later decision.",
    ),
    "target_capability": AxisPolicy(
        askable=True,
        blocking=False,
        prerequisite=False,
        priority=3,
        because="Semantics §2 LOCKED — a useful follow-up, but the target may not "
        "exist yet and that is a legitimate state. Asked, never blocking.",
    ),
    "capacity": AxisPolicy(
        askable=False,
        blocking=False,
        prerequisite=False,
        priority=90,
        because="Semantics §1 LOCKED — optional, and the corollary: deriving the "
        "plan and reporting its extent is what CAUSES a capacity to be stated. "
        "Asking upfront asks for a number the learner cannot honestly give.",
    ),
    "depth_register": AxisPolicy(
        askable=False,
        blocking=False,
        prerequisite=False,
        priority=91,
        because="Semantics §1 — biasing, not binding. A default is always defensible.",
    ),
    "artifact_type": AxisPolicy(
        askable=False,
        blocking=False,
        prerequisite=False,
        priority=92,
        because="Semantics §2 — a preset over a job. The system derives the job; "
        "the preset has a sane default.",
    ),
    "template": AxisPolicy(
        askable=False,
        blocking=False,
        prerequisite=False,
        priority=93,
        because="Presentation-Boundary rule 1 — internal. Users never select one.",
    ),
}


# ---------------------------------------------------------------------------
# What the model returns
# ---------------------------------------------------------------------------


class Span(BaseModel):
    """A reference into testimony, not a description of it.

    Free-text evidence cannot be checked -- a model can write "supported by the
    request" over nothing at all. A span names an utterance and quotes from it,
    and the quote is verified against the stored text before the support counts.
    Unverifiable support is discarded, which demotes the reading to a guess.
    """

    utterance_ord: int = Field(description="Which utterance, by its order in the transcript.")
    quote: str = Field(description="Text copied VERBATIM from that utterance. Short.")


class AxisReading(BaseModel):
    """The model's reading of one axis."""

    axis: AxisName
    value: str | None = Field(default=None, description="The reading. Null if unknown.")
    source: Literal["stated", "inferred", "unknown"] = Field(
        description=(
            "'stated': the user said it. 'inferred': you concluded it from "
            "something they said -- cite the span. 'unknown': nothing supports "
            "any reading, and you are about to guess."
        )
    )
    supported_by: list[Span] = Field(
        default_factory=list,
        description="Spans supporting this reading. Required for stated and inferred.",
    )
    would_differ: str | None = Field(
        default=None,
        description=(
            "If this reading is wrong, what would the plan look like instead? "
            "Concrete -- different concepts, different depth, different units. "
            "Null only when nothing would change."
        ),
    )
    materiality: Literal["changes_the_plan", "changes_details", "no_effect"] = Field(
        description="How much a different answer would move the plan."
    )


# ---------------------------------------------------------------------------
# What the decider produces
# ---------------------------------------------------------------------------

Strength = Literal["stated", "inferred", "guessed", "unknown"]


@dataclass(frozen=True, slots=True)
class AxisVerdict:
    axis: AxisName
    value: str | None
    strength: Strength
    verified: tuple[Span, ...]
    unverified: tuple[str, ...]
    material: bool
    would_differ: str | None
    askable: bool
    asked: bool
    reason: str

    @property
    def weak(self) -> bool:
        return self.strength in ("guessed", "unknown")

    def to_json(self) -> dict:
        return {
            "axis": self.axis,
            "value": self.value,
            "strength": self.strength,
            "verified": [s.model_dump() for s in self.verified],
            "unverified": list(self.unverified),
            "material": self.material,
            "would_differ": self.would_differ,
            "askable": self.askable,
            "asked": self.asked,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class Sufficiency:
    verdict: Literal["needs_subject", "ask", "sufficient"]
    axes: tuple[AxisVerdict, ...]
    asking: tuple[AxisName, ...]
    over_budget: tuple[AxisName, ...]
    budget: int

    def by_axis(self, axis: AxisName) -> AxisVerdict | None:
        return next((a for a in self.axes if a.axis == axis), None)

    def to_json(self) -> dict:
        return {
            "verdict": self.verdict,
            "budget": self.budget,
            "asking": list(self.asking),
            "over_budget": list(self.over_budget),
            "axes": [a.to_json() for a in self.axes],
        }


# ---------------------------------------------------------------------------
# The decider
# ---------------------------------------------------------------------------

DEFAULT_BUDGET = 2


def decide(
    readings: list[AxisReading],
    utterances: list[str],
    *,
    budget: int = DEFAULT_BUDGET,
) -> Sufficiency:
    """Combine the model's readings with the policy, and say what to ask.

    `budget` is a conversational constraint, not an architectural one: how many
    questions this product is willing to spend before planning. Every weak,
    plan-changing, askable axis is asked *within* it, in policy priority order.
    Anything that does not fit is recorded as over-budget rather than dropped
    silently -- it becomes visible in the plan as an assumption instead.
    """
    seen = {r.axis: r for r in readings}
    verdicts: list[AxisVerdict] = []

    for axis in AXES:
        policy = POLICY[axis]
        reading = seen.get(axis)
        if reading is None:
            verdicts.append(
                AxisVerdict(
                    axis=axis,
                    value=None,
                    strength="unknown",
                    verified=(),
                    unverified=(),
                    material=False,
                    would_differ=None,
                    askable=policy.askable,
                    asked=False,
                    reason="not read",
                )
            )
            continue

        verified, unverified = _verify(reading.supported_by, utterances)
        strength = _strength(reading, verified)
        material = reading.materiality == "changes_the_plan"

        verdicts.append(
            AxisVerdict(
                axis=axis,
                value=reading.value,
                strength=strength,
                verified=verified,
                unverified=unverified,
                material=material,
                would_differ=reading.would_differ,
                askable=policy.askable,
                asked=False,
                reason="",
            )
        )

    # Subject is a prerequisite, not a competitor for the budget: with no
    # subject there is nothing to plan, so it is obtained first and alone.
    subject = next(v for v in verdicts if v.axis == "subject")
    if subject.weak:
        return Sufficiency(
            verdict="needs_subject",
            axes=tuple(_explain(v, asked=v.axis == "subject", over_budget=False) for v in verdicts),
            asking=("subject",),
            over_budget=(),
            budget=budget,
        )

    candidates = sorted(
        (v for v in verdicts if POLICY[v.axis].askable and v.weak and v.material),
        key=lambda v: POLICY[v.axis].priority,
    )
    asking = tuple(v.axis for v in candidates[:budget])
    over = tuple(v.axis for v in candidates[budget:])

    return Sufficiency(
        verdict="ask" if asking else "sufficient",
        axes=tuple(
            _explain(v, asked=v.axis in asking, over_budget=v.axis in over) for v in verdicts
        ),
        asking=asking,
        over_budget=over,
        budget=budget,
    )


def _verify(spans: list[Span], utterances: list[str]) -> tuple[tuple[Span, ...], tuple[str, ...]]:
    """A span counts only if its quote is really in the utterance it names."""
    verified: list[Span] = []
    unverified: list[str] = []
    for span in spans:
        if 0 <= span.utterance_ord < len(utterances) and _contains(
            utterances[span.utterance_ord], span.quote
        ):
            verified.append(span)
        else:
            unverified.append(span.quote)
    return tuple(verified), tuple(unverified)


def _contains(text: str, quote: str) -> bool:
    return bool(quote.strip()) and quote.strip().casefold() in text.casefold()


def _strength(reading: AxisReading, verified: tuple[Span, ...]) -> Strength:
    """A claim of support with nothing behind it is a guess, whatever it says."""
    if reading.source == "unknown" or reading.value is None:
        return "unknown"
    if not verified:
        return "guessed"
    return "stated" if reading.source == "stated" else "inferred"


def _explain(verdict: AxisVerdict, *, asked: bool, over_budget: bool) -> AxisVerdict:
    """Give every axis a reason a test can assert on."""
    policy = POLICY[verdict.axis]

    if not policy.askable:
        reason = f"never asked — {policy.because}"
    elif verdict.strength == "stated":
        reason = "the user said so"
    elif verdict.strength == "inferred":
        quotes = " · ".join(f"{s.quote!r}" for s in verdict.verified)
        reason = f"inferred, supported by {quotes}"
    elif not verdict.material:
        reason = (
            f"weak ({verdict.strength}) but a different answer would not change "
            f"the plan materially"
        )
    elif over_budget:
        reason = (
            f"weak ({verdict.strength}) and would change the plan, but over the "
            f"question budget — carried as an assumption instead"
        )
    elif asked:
        reason = f"weak ({verdict.strength}) and a different answer would change the plan"
    else:
        reason = f"weak ({verdict.strength})"

    if verdict.unverified:
        reason += f" · discarded unverifiable support: {list(verdict.unverified)}"

    return AxisVerdict(
        axis=verdict.axis,
        value=verdict.value,
        strength=verdict.strength,
        verified=verdict.verified,
        unverified=verdict.unverified,
        material=verdict.material,
        would_differ=verdict.would_differ,
        askable=verdict.askable,
        asked=asked,
        reason=reason,
    )
