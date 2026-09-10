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

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_serializer,
    model_validator,
)

from agent.providers import Completion, Provider, select_provider
from agent.sufficiency import AxisName, AxisReading
from agent.treatment import ProseFailure, shortfalls, weight

PROMPT_INTERPRET = "interpret_v1"
PROMPT_ASK = "ask_v1"
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


class StatedConstraint(BaseModel):
    """Something the user actually said, and which axis it constrains.

    The attribution is what makes Semantics §1 enforceable rather than
    aspirational. "from scratch" is a statement *about the entry point*; without
    saying so, nothing could notice when the entry point came back asserting the
    opposite -- which is exactly what happened, and it removed every foundational
    concept from the landscape before any other decision ran.
    """

    text: str = Field(description="What they said, in their words.")
    axis: AxisName | None = Field(
        default=None,
        description=(
            "Which situation axis this constrains, if it clearly constrains one: "
            "subject · purpose · entry_point · target_capability · capacity · "
            "depth_register · artifact_type · template. Null if it constrains "
            "none of them or several. A constraint you attribute to an axis MUST "
            "be honoured by your reading of that axis."
        ),
    )


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
    stated: list[StatedConstraint] = Field(
        default_factory=list,
        description="Constraints the user actually said. Never inferred ones.",
    )

    inferred: list[str] = Field(
        default_factory=list,
        description=(
            "What was decided for them because the request was silent. Semantics §3: "
            "silence is the system's decision, and a decision the user cannot see is "
            "one they cannot correct."
        ),
    )

    @field_validator("stated", mode="before")
    @classmethod
    def _accept_bare_strings(cls, value):
        """Legacy plans stored `stated` as plain strings, with no attribution.
        They load, and they bind nothing -- which is the behaviour they were
        written under."""
        if isinstance(value, list):
            return [{"text": v, "axis": None} if isinstance(v, str) else v for v in value]
        return value


class Concept(BaseModel):
    name: str
    built_from: list[str] = Field(
        default_factory=list, description="Concepts in this list that must come first."
    )
    family: str = Field(
        default="",
        description=(
            "The kind of thing this is, in your own words -- e.g. 'core mechanism', "
            "'failure mode', 'applied case', 'tooling', 'evaluation', 'emerging "
            "standard'. Not a fixed vocabulary: name what is true of THIS subject. "
            "It makes the landscape's shape inspectable, so a whole kind of "
            "material going missing is visible."
        ),
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
    anticipates: ProseFailure = Field(
        default="none",
        description=(
            "Which failure of prose this concept's content is expected to hit, "
            "from Architecture §13's seven. NOT a choice of diagram -- that is "
            "decided later, per placement. This says only that prose alone will "
            "not carry it, and in which way. 'none' when prose is sufficient."
        ),
    )


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

    @field_validator("exclusions", mode="after")
    @classmethod
    def _one_entry_per_topic(cls, value: list[Exclusion]) -> list[Exclusion]:
        """The same topic excluded twice is one exclusion, not two.

        Models emit a topic twice often enough -- usually with two phrasings of
        the same consequence -- and nothing downstream treats it as anything but
        a repeat: the plan lists it twice, the brief hands the writer the same
        exclusion twice, and the reader is told the same thing twice. First
        occurrence wins, because the plan's ordering is the model's own
        priority ordering and reordering it here would be a second decision.
        """
        seen: set[str] = set()
        kept: list[Exclusion] = []
        for exclusion in value:
            key = exclusion.topic.strip().casefold()
            if key in seen:
                continue
            seen.add(key)
            kept.append(exclusion)
        return kept


class Module(BaseModel):
    """One module of the curriculum. **Becomes its own PDF.**

    Architecture decision 9. Not a chapter and not a section -- those are
    decision 10, and they live *inside* a module. The test for whether something
    is a module rather than a chapter is `capability`: a module corresponds to
    something the learner would exercise on its own.
    """

    title: str = Field(description="The module's name. Becomes the document's title.")
    covers: list[str] = Field(description="Which covered concepts land in this module.")
    why_here: str = Field(description="Why these belong together as one module.")
    capability: str = Field(
        description=(
            "What the learner can do after this module that they could not "
            "before. Concrete and exercisable on its own -- this is what makes "
            "it a module rather than a chapter of a bigger one."
        )
    )


class Unit(BaseModel):
    """LEGACY: a section of a single document.

    Kept only so plans written before the curriculum layer existed still open.
    These were never modules, and are not re-labelled as modules -- doing so
    would claim a decomposition the planner never made.
    """

    heading: str
    covers: list[str] = Field(description="Which covered concepts land here.")
    why_here: str = Field(description="Why these belong together as one unit.")


class Partition(BaseModel):
    """`partition` — how the in-scope material divides into modules.

    Architecture: *universal, may resolve to one member*. One module is a
    perfectly good answer for a narrow request; a broad one divides into many.
    The count is derived from the scope, never fixed.
    """

    modules: list[Module] = Field(default_factory=list)
    units: list[Unit] = Field(
        default_factory=list, description="LEGACY. Do not produce these."
    )

    @model_validator(mode="after")
    def _one_shape_or_the_other(self):
        if not self.modules and not self.units:
            raise ValueError("partition must divide the scope into at least one module")
        return self

    @model_serializer(mode="wrap")
    def _drop_the_empty_shape(self, handler):
        """A stored record carries only the shape it actually is.

        Writing `"units": []` into every new decision would put a legacy field in
        records that have no legacy, and a reader six months from now would
        reasonably wonder which one is authoritative.
        """
        data = handler(self)
        for key in ("modules", "units"):
            if not data.get(key):
                data.pop(key, None)
        return data

    @property
    def is_legacy(self) -> bool:
        return not self.modules and bool(self.units)

    @property
    def parts(self) -> list[tuple[str, list[str]]]:
        """(title, covered concepts) for each part, whichever shape this is.

        The one place the two are treated alike, and only for arithmetic that
        does not care -- page counts and coverage. Anything that means "this is
        a separate PDF" must ask `modules` directly.
        """
        if self.modules:
            return [(m.title, m.covers) for m in self.modules]
        return [(u.heading, u.covers) for u in self.units]


class Traversal(BaseModel):
    """`traversal` — the order the modules should be taken in."""

    sequence: list[str] = Field(
        description="Module titles, in the order they should be read."
    )
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
    """What the request says. The first thing that happens, and a fast one.

    Architecture §4 puts the intake loop first and terminates it on sufficiency.
    Decision 0 cannot judge what is worth asking without a reading to judge
    against, so the loop closes through interpretation: read -> ask -> the answer
    is new testimony -> read again.

    **Questions are NOT produced here.** They used to be, and every one whose
    axis the decider did not choose was thrown away -- all of them whenever the
    verdict was `sufficient`, which is the common case. Authoring 2-4 options
    with their implications for eight axes is most of this call's output, and it
    was speculative work. Now `decide()` runs first, in code, and `ask()` writes
    questions for exactly the axes it named.
    """

    interpret_situation: Situation
    axes: list[AxisReading] = Field(
        description=(
            "One reading per situation axis, with what supports it. The decider "
            "combines these with policy; the model does not choose what is asked."
        )
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


def conversational_provider() -> Provider:
    """The model that talks to the user.

    Reading a request and writing the next question is a comprehension task and
    the user is sitting there waiting for it. Deriving a curriculum is a design
    task nobody watches. `INTERPRET_MODEL` lets them be different models; unset,
    everything behaves as before.
    """
    return select_provider(os.environ.get("INTERPRET_MODEL") or None)


def interpret(transcript: str, *, provider: Provider | None = None) -> Call:
    """`interpret_situation` — what the request says. The turn the user waits on.

    Reads only. Questions are written by `ask()`, after `decide()` has said which
    axes are worth one.
    """
    provider = provider or conversational_provider()
    result, completion = _call(provider, PROMPT_INTERPRET, transcript, Reading)
    return _as_call(result.model_dump(), completion, PROMPT_INTERPRET, Reading)


def ask(
    situation: Situation,
    asking: "list[str] | tuple[str, ...]",
    *,
    provider: Provider | None = None,
) -> Call:
    """`intake_strategy` — write a question for each axis the decider named.

    Only called when there is something to ask, and only ever for the axes named.
    That is the whole saving: the model used to author questions for every weak
    axis it could see, and `_read` discarded the ones policy did not choose --
    every one of them whenever the verdict was `sufficient`.

    Which axes get asked is still decided from the model's own readings by
    `sufficiency.decide()`, never from a fixed order. This call writes the
    wording; it does not choose the subject of the conversation.
    """
    provider = provider or conversational_provider()
    user = (
        f"The learner's situation as you read it:\n\n"
        f"{situation.model_dump_json(indent=2)}\n\n"
        f"Write one question for each of these axes, and no others: "
        f"{', '.join(asking)}"
    )
    result, completion = _call(provider, PROMPT_ASK, user, Intake)
    return _as_call(result.model_dump(), completion, PROMPT_ASK, Intake)


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
        # "Reply with the corrected JSON object" beside an error naming
        # `interpret_situation` reads as "send me that object" -- and the model
        # did exactly that, returning a bare Situation where a Reading was
        # required, twice, and taking the whole request down with it. The field
        # paths are a location, not a request.
        #
        # The required keys are read off the schema rather than written out, so
        # this stays true for every call that uses it: Reading, Landscape,
        # PlanBody, Routing.
        required = ", ".join(
            f"`{key}`" for key in model.model_json_schema().get("required", [])
        )
        retry = provider.complete(
            system=system,
            user=(
                f"{user}\n\nYour previous reply did not validate.\n\n"
                "Reply with the COMPLETE top-level JSON object again"
                + (f", whose keys are {required}" if required else "")
                + ". Fix only what the errors below name. Their dotted paths say "
                "WHERE each problem is; they are not a request to send that part "
                "on its own. JSON only, no prose, no fence.\n\n"
                f"{str(first)[:2000]}"
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

# Pages per concept at each depth. Multiplied by a treatment weight, because
# content is not prose-equivalent: a concept whose meaning is spatial does not
# cost the same page as a definition taken to the same depth. Both coefficients
# are guesses -- nothing has measured them -- but they are tied to the depth and
# treatment actually allocated rather than to a page count someone wanted, which
# is what Architecture §11 requires.
_DEPTH_PAGES = {"mention": 0.15, "explain": 0.5, "work through": 1.0}
_DEPTH_MINUTES = {"mention": 2, "explain": 8, "work through": 20}


def _depth(value: str) -> str:
    return value.strip().lower()


def _pages(covered) -> float:
    return sum(
        _DEPTH_PAGES.get(_depth(c.depth), 0.5) * weight(getattr(c, "anticipates", "none"))
        for c in covered
    )


def _round_pages(pages: float) -> str:
    return f"~{pages:.0f} pages" if pages >= 1.5 else "~1 page"


def derive_extent(scope: Scope, partition: Partition) -> dict:
    """Architecture §14: reporting extent is an obligation, not a field.

    Computed from the depths and treatments actually allocated, so it moves when
    either moves and cannot claim "about two pages" with nothing behind it.
    Reported per unit as well, because a contents page is where a reader judges
    size.
    """
    pages = max(_pages(scope.covered), 0.5)
    minutes = sum(
        _DEPTH_MINUTES.get(_depth(c.depth), 8) * weight(getattr(c, "anticipates", "none"))
        for c in scope.covered
    )

    by_concept = {c.concept: c for c in scope.covered}
    per_unit: dict[str, str] = {}
    for title, covers in partition.parts:
        covered = [by_concept[name] for name in covers if name in by_concept]
        if covered:
            per_unit[title] = _round_pages(max(_pages(covered), 0.5))

    study = f"{minutes:.0f} min" if minutes < 90 else f"about {minutes / 60:.0f} hours"

    # Architecture §11: extent is derived per part and summed. Never
    # capacity divided by the number of parts -- sizes emerge from what each
    # capability requires, and a count is not a budget.
    return {
        "total": f"{_round_pages(pages)} · {study}",
        "pages": _round_pages(pages),
        "study_time": study,
        "parts": len(partition.parts),
        "modules": len(partition.modules),
        "per_unit": per_unit,
    }


def derive_feasibility(scope: Scope) -> dict:
    """What this build cannot do for this content, before it is approved.

    Architecture §13 and §14: an unservable prose failure must be reported, not
    silently answered with prose. Derived, never written by the model -- the
    model says what the content needs, code says what we can serve.
    """
    gaps = shortfalls(scope.covered)
    return {
        "serves_everything": not gaps,
        "shortfalls": [g.to_json() for g in gaps],
    }
