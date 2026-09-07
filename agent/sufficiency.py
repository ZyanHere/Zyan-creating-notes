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
    "artifact_type": AxisPolicy(
        askable=True,
        blocking=False,
        prerequisite=False,
        priority=3,
        because="Semantics §1 — user-set and binding. §2 uses long notes vs short "
        "notes as its own example of two presets over one job that produce "
        "materially different plans. Often established by the wording ('quick "
        "revision sheet', 'detailed notes'), so inferred far more often than asked.",
    ),
    "target_capability": AxisPolicy(
        askable=True,
        blocking=False,
        prerequisite=False,
        priority=4,
        because="Semantics §2 LOCKED — a useful follow-up, but the target may not "
        "exist yet and that is a legitimate state; §1 also notes it is often "
        "implied by purpose. Asked last of the four, never blocking.",
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

# A ceiling on one turn, not a target and not a definition of readiness.
# Sufficiency decides how many questions actually appear; this only bounds a
# model that marks everything material. Set to the number of askable axes so a
# genuinely bare request can be resolved in ONE turn rather than several --
# fewest conversational turns is the goal, not fewest questions.
DEFAULT_BUDGET = 4


STRENGTH_RANK = {"unknown": 0, "guessed": 1, "inferred": 2, "stated": 3}


def improved(before: "Sufficiency | None", after: "Sufficiency") -> bool:
    """Did the last answer move any axis forward?

    Sufficiency, not a turn count, decides when to stop asking. But a model that
    keeps asking about an axis the user has now answered would loop forever, so
    the second exit is *no progress*: if nothing strengthened, asking again will
    not help and the plan is derived on what is known.
    """
    if before is None:
        return True
    old = {a.axis: STRENGTH_RANK[a.strength] for a in before.axes}
    return any(STRENGTH_RANK[a.strength] > old.get(a.axis, -1) for a in after.axes)


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
        text = (
            utterances[span.utterance_ord]
            if 0 <= span.utterance_ord < len(utterances)
            else None
        )
        if text is not None and _contains(text, span.quote) and _discriminating(text, span.quote):
            verified.append(span)
        else:
            unverified.append(span.quote)
    return tuple(verified), tuple(unverified)


# A span that quotes nearly the whole utterance points at nothing in particular.
# Observed: for "i need notes on signal and system" the model cited "need notes
# on signal and system" as support for purpose, entry point AND target -- all
# three resolved, all three read as `inferred`, and nothing was asked. Evidence
# that supports every reading equally is evidence for none of them.
#
# Only applied to utterances long enough for the choice to mean something: a
# two-word answer legitimately IS the whole evidence for what it answers.
_DISCRIMINATING_MIN_WORDS = 5
_DISCRIMINATING_MAX_SHARE = 0.7


def _contains(text: str, quote: str) -> bool:
    return bool(quote.strip()) and quote.strip().casefold() in text.casefold()


def _discriminating(text: str, quote: str) -> bool:
    whole = len(text.split())
    if whole < _DISCRIMINATING_MIN_WORDS:
        return True
    return len(quote.split()) / whole <= _DISCRIMINATING_MAX_SHARE


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


def from_json(blob: dict) -> Sufficiency | None:
    """Rehydrate a stored record, so the next turn can ask whether the last
    answer actually moved anything."""
    if not blob or "axes" not in blob:
        return None
    return Sufficiency(
        verdict=blob["verdict"],
        budget=blob.get("budget", DEFAULT_BUDGET),
        asking=tuple(blob.get("asking", ())),
        over_budget=tuple(blob.get("over_budget", ())),
        axes=tuple(
            AxisVerdict(
                axis=a["axis"],
                value=a.get("value"),
                strength=a["strength"],
                verified=tuple(Span(**v) for v in a.get("verified", [])),
                unverified=tuple(a.get("unverified", ())),
                material=a.get("material", False),
                would_differ=a.get("would_differ"),
                askable=a.get("askable", False),
                asked=a.get("asked", False),
                reason=a.get("reason", ""),
            )
            for a in blob["axes"]
        ),
    )
