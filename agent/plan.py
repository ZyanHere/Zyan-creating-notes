"""The plan gate: request in, an approvable plan out, corrections routed.

Eight decisions in three classes (Plan-Gate-Milestone §2), all of them rows:

    plan         interpret_situation · scope · consequence · traversal · partition
    upstream     derive_structure · relevance
    interaction  intake_strategy

The upstream two are recorded even though they have no plan section, because
routing needs them. "You've missed X entirely" is a `derive_structure` fault --
X was never in the graph -- and scope can only cut or keep what relevance handed
it, so routing that to scope leaves it unfixable by any later correction.

`extent` is not a decision. Architecture §14 makes reporting it an obligation;
it is derived from the scope and partition actually agreed, never written freely
by the model.

Deliberately NOT here: invalidation topology, verification classes, decision
versioning, the closure walk. This milestone proves the conversation converges.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from agent.providers import Completion, Provider, select_provider
from agent.sufficiency import AxisName, AxisReading

PROMPT_INTERPRET = "interpret_v1"
PROMPT_DERIVE = "derive_v1"
PROMPT_PLAN = "plan_v3"
PROMPT_REVISE = "plan_revise_v2"
MAX_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "32000"))
_PROMPTS = Path(__file__).parent / "prompts"

# Names are `decision_kind` values from Build-Spec §3, not inventions.
PLAN_DECISIONS = ("interpret_situation", "scope", "consequence", "traversal", "partition")
UPSTREAM_DECISIONS = ("derive_structure", "relevance")
INTERACTION_DECISIONS = ("intake_strategy",)
ALL_DECISIONS = PLAN_DECISIONS + UPSTREAM_DECISIONS + INTERACTION_DECISIONS

DecisionKind = Literal[
    "interpret_situation",
    "derive_structure",
    "relevance",
    "scope",
    "consequence",
    "traversal",
    "partition",
    "intake_strategy",
]


# ---------------------------------------------------------------------------
# Decision outputs. One model per decision, because one row holds one of these.
# ---------------------------------------------------------------------------


class Situation(BaseModel):
    """`interpret_situation` — what the system read the request as."""

    subject: str
    job: str = Field(description="orient · construct · retrieve · rehearse.")
    entry_point: str = Field(description="What the reader is assumed to know already.")
    purpose: str = Field(description="Why they want it — exam, build something, decide something.")
    target_capability: str = Field(description="What they can do afterwards. Concrete.")
    capacity: str | None = Field(
        default=None, description="Any stated limit on time, length or effort. Null if none."
    )
    stated: list[str] = Field(
        default_factory=list, description="Constraints the user actually said. Never inferred ones."
    )
    inferred: list[str] = Field(
        default_factory=list,
        description=(
            "What was decided for them because the request was silent. Semantics §3: "
            "silence is the system's decision, and a decision the user cannot see is "
            "one they cannot correct."
        ),
    )


class Concept(BaseModel):
    name: str
    built_from: list[str] = Field(
        default_factory=list, description="Concepts in this list that must come first."
    )


class Structure(BaseModel):
    """`derive_structure` — what concepts exist and what is built from what.

    The whole landscape of the subject at this level, before anything is cut.
    A concept absent here cannot be restored by any later decision.
    """

    concepts: list[Concept]


class Judgement(BaseModel):
    concept: str
    in_play: bool
    why: str = Field(description="Why it is or is not in play for THIS learner's situation.")


class Relevance(BaseModel):
    """`relevance` — what is in play for this situation. Every derived concept judged."""

    judgements: list[Judgement]


class Covered(BaseModel):
    concept: str
    depth: str = Field(description="How far this is taken: mention · explain · work through.")
    why: str = Field(description="What it contributes to the target capability.")


class Scope(BaseModel):
    """`scope` — depth allocation and the cut, over what relevance put in play."""

    covered: list[Covered]
    cut: list[str] = Field(
        default_factory=list,
        description="Concepts that were in play and were cut anyway. Names only.",
    )


class Exclusion(BaseModel):
    topic: str
    consequence: str = Field(description="What goes wrong if they act without it.")
    when_to_learn: str


class Consequence(BaseModel):
    """`consequence` — what omitting each cut thing costs. Semantics §12: three parts."""

    exclusions: list[Exclusion]


class Unit(BaseModel):
    heading: str
    covers: list[str] = Field(description="Which covered concepts land here.")
    why_here: str = Field(description="Why these belong together as one unit.")


class Partition(BaseModel):
    """`partition` — how in-scope material divides."""

    units: list[Unit]


class Traversal(BaseModel):
    """`traversal` — teachable order over the units."""

    sequence: list[str] = Field(description="Unit headings, in the order they should be read.")
    why: str = Field(description="Why this order, in one or two sentences.")


class Option(BaseModel):
    label: str = Field(description="The choice itself. One to four words.")
    implication: str = Field(
        description="What the plan does if they pick this. Concrete, and different "
        "from every sibling -- if two options imply the same plan they are one option."
    )


class Question(BaseModel):
    """Objective, not open-ended.

    Semantics §1: the learner cannot reliably *specify* their entry point or
    target -- that would require already understanding the subject -- but they
    can *recognise* their situation when it is put in front of them. An open
    question asks them to author what §1 says they cannot; options ask them to
    choose, which they can.

    The options must be genuinely different plans. Two options producing the
    same scope are one option wearing two labels, and asking is then noise.
    """

    axis: AxisName = Field(description="The situation axis this question resolves.")
    question: str
    why_it_matters: str = Field(description="What in the plan would differ between the answers.")
    options: list[Option] = Field(
        description="Two to four. Each must lead to a materially different plan."
    )
    default_label: str = Field(
        description="The option taken if they skip. A question is never a blocker."
    )


class Intake(BaseModel):
    """`intake_strategy` — what to ask next, or nothing.

    An interaction decision: its output is evidence, not a claim about the
    artifact, and it is not part of what approval commits.
    """

    questions: list[Question] = Field(
        default_factory=list,
        description="At most three, and only where two answers give materially different plans.",
    )


# ---------------------------------------------------------------------------
# Call envelopes
# ---------------------------------------------------------------------------


class Reading(BaseModel):
    """What the request says, and what is still worth asking about it.

    These two run together and before anything else. Architecture §4 puts the
    intake loop first and terminates it on sufficiency; decision 0 cannot judge
    what is worth asking without a reading of the situation to judge against, so
    the loop closes through interpretation: read -> ask -> the answer is new
    testimony -> read again.
    """

    interpret_situation: Situation
    axes: list[AxisReading] = Field(
        description=(
            "One reading per situation axis, with what supports it. The decider "
            "combines these with policy; the model does not choose what is asked."
        )
    )
    proposed_questions: list[Question] = Field(
        default_factory=list,
        description=(
            "One per axis you read as weak and plan-changing. Propose freely -- "
            "policy and the question budget decide which survive."
        ),
    )


class Landscape(BaseModel):
    """What exists, and what is in play. Architecture §4 puts relevance
    immediately after structure derivation, and they share a call because
    relevance must judge every concept the same pass derived."""

    derive_structure: Structure
    relevance: Relevance


class PlanBody(BaseModel):
    """The four decisions the plan gate shows.

    Split from the landscape for a runtime reason, which System Design §1 makes
    explicitly a CHOICE: six decisions in one response truncated -- the model
    emitted `derive_structure` and stopped. Only scope+partition are
    architecturally joint (Architecture §4); the grouping around them is ours.
    Four separate records either way, which is what a correction targets.
    """

    traversal: Traversal
    consequence: Consequence
    scope: Scope
    partition: Partition


class Routing(BaseModel):
    """Where a correction goes, and the new outputs for exactly those decisions.

    `targets` is the router's judgment about *this* plan, not a lookup from
    phrases to decisions. A capacity change moves scope and extent, and may or
    may not move partition — that depends on the plan in front of it.
    """

    targets: list[DecisionKind] = Field(
        default_factory=list, description="Decisions this correction actually changes."
    )
    out_of_scope: str | None = Field(
        default=None,
        description=(
            "Set when the correction belongs to a later gate — appearance, or how one "
            "idea gets treated. Name which stage owns it. Null when it routes cleanly."
        ),
    )
    reading: str = Field(description="What the correction was understood to mean, one sentence.")
    interpret_situation: Situation | None = None
    derive_structure: Structure | None = None
    relevance: Relevance | None = None
    scope: Scope | None = None
    consequence: Consequence | None = None
    partition: Partition | None = None
    traversal: Traversal | None = None
    intake_strategy: Intake | None = None

    def revised(self) -> dict[str, BaseModel]:
        """Only the decisions that came back non-null."""
        return {k: v for k in ALL_DECISIONS if (v := getattr(self, k)) is not None}


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Call:
    outputs: dict[str, BaseModel]
    routing: Routing | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    provider: str = ""
    model: str = ""
    prompt_version: str = ""


@lru_cache(maxsize=8)
def _prompt(version: str) -> str:
    return (_PROMPTS / f"{version}.md").read_text(encoding="utf-8")


def interpret(transcript: str, *, provider: Provider | None = None) -> Call:
    """interpret_situation · intake_strategy. Runs first, and again per answer."""
    provider = provider or select_provider()
    result, completion = _call(provider, PROMPT_INTERPRET, transcript, Reading)
    return _as_call(result.model_dump(), completion, PROMPT_INTERPRET, Reading)


def derive(situation: Situation, *, provider: Provider | None = None) -> Call:
    """derive_structure · relevance."""
    provider = provider or select_provider()
    user = f"The learner's situation:\n\n{situation.model_dump_json(indent=2)}"
    result, completion = _call(provider, PROMPT_DERIVE, user, Landscape)
    return _as_call(result.model_dump(), completion, PROMPT_DERIVE, Landscape)


def plan(situation: Situation, landscape: Landscape, *, provider: Provider | None = None) -> Call:
    """traversal · consequence · scope · partition."""
    provider = provider or select_provider()
    user = (
        f"The learner's situation:\n\n{situation.model_dump_json(indent=2)}\n\n"
        f"What exists and what is in play:\n\n{landscape.model_dump_json(indent=2)}"
    )
    result, completion = _call(provider, PROMPT_PLAN, user, PlanBody)
    return _as_call(result.model_dump(), completion, PROMPT_PLAN, PlanBody)


def revise(
    decisions: dict[str, dict], correction: str, *, provider: Provider | None = None
) -> Call:
    """Route a natural-language correction, and revise only what it routed to."""
    import json

    provider = provider or select_provider()
    user = (
        "Current decisions:\n\n"
        f"{json.dumps(decisions, indent=2, ensure_ascii=False)}\n\n"
        f"The user says:\n\n{correction}"
    )
    routing, completion = _call(provider, PROMPT_REVISE, user, Routing)
    call = _as_call({}, completion, PROMPT_REVISE, Routing)
    return Call(
        outputs={k: v.model_dump() for k, v in routing.revised().items()},
        routing=routing,
        input_tokens=call.input_tokens,
        output_tokens=call.output_tokens,
        provider=call.provider,
        model=call.model,
        prompt_version=PROMPT_REVISE,
    )


def _as_call(outputs, completion: Completion, version: str, _model) -> Call:
    return Call(
        outputs=outputs,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        provider=completion.provider,
        model=completion.model,
        prompt_version=version,
    )


def _call(provider: Provider, version: str, user: str, model):
    """One call, validated. On failure the model is handed its own error once."""
    system = _prompt(version)
    completion = provider.complete(
        system=system, user=user, schema=model.model_json_schema(), max_tokens=MAX_TOKENS
    )
    try:
        return model.model_validate_json(_strip_fence(completion.text)), completion
    except (ValidationError, ValueError) as first:
        retry = provider.complete(
            system=system,
            user=(
                f"{user}\n\nYour previous reply did not validate. Fix exactly this and "
                f"reply with the corrected JSON object only:\n\n{str(first)[:2000]}"
            ),
            schema=model.model_json_schema(),
            max_tokens=MAX_TOKENS,
        )
        try:
            return model.model_validate_json(_strip_fence(retry.text)), Completion(
                text=retry.text,
                input_tokens=completion.input_tokens + retry.input_tokens,
                output_tokens=completion.output_tokens + retry.output_tokens,
                model=retry.model,
                provider=retry.provider,
            )
        except (ValidationError, ValueError) as second:
            raise ValueError(
                f"{provider.name}/{provider.model} produced invalid output twice for "
                f"{version}.\nfirst:  {str(first)[:500]}\nsecond: {str(second)[:500]}"
            ) from second


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.split("\n", 1)[1] if "\n" in stripped else ""
    if body.rstrip().endswith("```"):
        body = body.rstrip()[: -len("```")]
    return body.strip()


# ---------------------------------------------------------------------------
# Derived, not decided
# ---------------------------------------------------------------------------

_DEPTH_PAGES = {"mention": 0.15, "explain": 0.5, "work through": 1.0}


def derive_extent(scope: Scope, partition: Partition) -> str:
    """Architecture §14: reporting extent is an obligation, not a field.

    Computed from the depths actually allocated, so it moves when scope moves
    and cannot claim "about two pages" with nothing behind it. Crude on purpose
    -- a real estimate needs a rendered page, which this gate does not have.
    """
    pages = sum(_DEPTH_PAGES.get(c.depth.strip().lower(), 0.5) for c in scope.covered)
    pages = max(pages, 0.5)
    low, high = round(pages * 0.8, 1), round(pages * 1.3, 1)
    return (
        f"about {low:g}–{high:g} pages — {len(scope.covered)} concepts across "
        f"{len(partition.units)} unit(s), at the depths allocated above"
    )
