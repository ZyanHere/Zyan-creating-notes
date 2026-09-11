"""M1: one request in, one Document out.

Deliberately a single model call. Splitting it into the decision taxonomy is M3;
doing that now would mean building the seams before we know the output is worth
building anything around.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from agent.contracts import Document, Section
from agent.fulfilment import (
    Fulfilment,
    UnitReport,
    check_document,
    check_unit,
    requirements,
)
from agent.providers import Completion, Provider, select_provider

PROMPT_VERSION = "document_v2"
PROMPT_FROM_PLAN = "document_v3"
PROMPT_UNIT = "unit_v1"
MAX_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "32000"))
_PROMPTS = Path(__file__).parent / "prompts"


@dataclass(frozen=True, slots=True)
class Generated:
    """A document plus what it cost to produce it.

    Cost is recorded from M1 because it can never be backfilled, and by M6 it is
    what makes a correction's price quotable before the user pays it.
    """

    document: Document
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    repairs: int = 0
    calls: int = 1
    fulfilment: Fulfilment | None = None
    """Whether the artifact delivers the approved plan. `None` only when there
    was no plan to deliver -- generation from a bare request has no contract to
    check against, which is precisely why the plan gate exists."""


@lru_cache(maxsize=8)
def _system_prompt(version: str) -> str:
    return (_PROMPTS / f"{version}.md").read_text(encoding="utf-8")


def generate_document(
    request: str,
    *,
    plan: dict | None = None,
    provider: Provider | None = None,
) -> Generated:
    """Produce one educational artifact.

    Two modes, and the difference is what the document is answerable to.

    Without `plan`, the request is the whole brief and the model decides scope
    for itself. That is M1's shape and it stays available.

    With `plan`, an **approved plan** is the brief. The user has already agreed
    what is covered, in what order, at what depth, and what is deliberately left
    out -- so the model is writing *that document*, not choosing one. This is
    what makes approval mean something: without it the user approves a plan and
    then receives whatever the generator felt like, which is worse than not
    asking.
    """
    provider = provider or select_provider()
    if plan is not None:
        return _from_plan(request, plan, provider=provider)

    schema = Document.model_json_schema()
    version = PROMPT_VERSION
    system = _system_prompt(version)
    user = request

    completion = provider.complete(
        system=system, user=user, schema=schema, max_tokens=MAX_TOKENS
    )
    document, repairs, completion = _parse_or_repair(
        completion, provider=provider, system=system, request=user, schema=schema
    )

    return Generated(
        document=document,
        provider=completion.provider,
        model=completion.model,
        prompt_version=version,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        repairs=repairs,
    )


def _from_plan(request: str, plan: dict, *, provider: Provider) -> Generated:
    """One approved plan in; one document that delivers it, or a report saying
    how it does not.

        units → generate each independently → verify each against its own
        approved scope → assemble → final completeness check

    Per unit, not per document, for a reason beyond fitting in a context window:
    each call is answerable for a small, checkable promise. A model asked for
    nineteen pages in one shot wrote one part of six and declared itself done,
    and nothing downstream could tell. A model asked for one part either
    produces that part's concepts or visibly does not.

    The system, not the model, is answerable for the artifact matching the plan.
    So a unit that comes back short is asked again, once, with exactly what is
    missing -- and if it is still short, that survives into the report rather
    than being smoothed over.
    """
    modules = ((plan.get("partition") or {}).get("modules")) or []
    if len(modules) > 1:
        # A curriculum is several PDFs. Writing it as one document with a thin
        # section per module would deliver something the plan did not promise --
        # the exact failure `fulfilment.py` exists to prevent, committed by the
        # generator itself. Refuse until set generation is built.
        titles = ", ".join(m.get("title", "?") for m in modules)
        raise ValueError(
            f"This plan is a curriculum of {len(modules)} modules ({titles}), and "
            "each is meant to become its own PDF. Generating a set is not built "
            "yet — writing them into one document would not be the artifact you "
            "approved."
        )

    orders = requirements(plan)
    if not orders:
        raise ValueError("the approved plan has nothing to write")

    situation = plan.get("interpret_situation") or {}
    schema = Section.model_json_schema()
    system = _system_prompt(PROMPT_UNIT)

    sections: list[Section] = []
    reports: list[UnitReport] = []
    calls = repairs = tokens_in = tokens_out = 0
    model = provider.model
    name = provider.name

    for order in orders:
        section: Section | None = None
        report: UnitReport | None = None
        failure: str | None = None

        for attempt in range(2):
            missing = report.concepts_missing if report is not None else ()
            user = _unit_brief(request, situation, order, missing=missing)
            try:
                completion = provider.complete(
                    system=system, user=user, schema=schema, max_tokens=MAX_TOKENS
                )
            except Exception as exc:
                # One unit failing must not cost the other five. It is recorded
                # as ungenerated, which the final check treats as a problem.
                #
                # The reason travels with it. Swallowing it produced a document
                # reported only as "doesn't match what was approved", which
                # reads as a model that omitted a part -- when the actual cause
                # was a call that never succeeded, most often a spent rate
                # limit on the free tier. Same symptom, opposite fix.
                failure = f"{type(exc).__name__}: {exc}"
                break

            calls += 1
            tokens_in += completion.input_tokens
            tokens_out += completion.output_tokens
            model, name = completion.model, completion.provider

            try:
                candidate = _load_section(completion.text)
            except (ValidationError, ValueError):
                repairs += 1
                continue

            candidate.heading = order["heading"]  # the heading is the plan's, not the model's
            trial = check_unit(order, candidate)
            # Keep the better attempt: a retry that covers less than the first
            # would otherwise make asking again actively harmful.
            if section is None or len(trial.concepts_covered) > len(report.concepts_covered):
                section, report = candidate, trial
            if trial.satisfied:
                break

        if section is not None and report is not None:
            sections.append(section)
            reports.append(report)
        else:
            reports.append(check_unit(order, None, reason=failure))

    if not sections:
        raise ValueError(
            f"{name}/{model} produced no usable part for any of the "
            f"{len(orders)} approved units."
        )

    document = _assemble(plan, situation, sections)
    fulfilment = check_document(plan, document, reports)

    return Generated(
        document=document,
        provider=name,
        model=model,
        prompt_version=PROMPT_UNIT,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        repairs=repairs,
        calls=calls,
        fulfilment=fulfilment,
    )


def _assemble(plan: dict, situation: dict, sections: list[Section]) -> Document:
    """Front matter from the approved plan, body from the units.

    The title, who it is for and what they will be able to do are the *plan's*
    answers, already shown to the user and agreed. Asking a model to restate them
    would let them drift from what was approved for no gain.
    """
    exclusions = (plan.get("consequence") or {}).get("exclusions", [])
    return Document(
        title=situation.get("subject") or "Study notes",
        subtitle=situation.get("purpose"),
        assumed_entry=situation.get("entry_point")
        or "Not stated — this document assumes no particular background.",
        target_capability=situation.get("target_capability")
        or "Understand the material covered here.",
        sections=sections,
        deliberate_omissions=[
            {
                "topic": e.get("topic", ""),
                "consequence": e.get("consequence", ""),
                "when_to_learn": e.get("when_to_learn", ""),
            }
            for e in exclusions
            if e.get("topic")
        ],
    )


def _unit_brief(
    request: str, situation: dict, order: dict, *, missing: tuple[str, ...] = ()
) -> str:
    """One work order. This unit's concepts, and nothing else from the plan.

    Deliberately not the whole plan: the other units are not this call's
    business, and including them is what let a model wander off and write a
    different part than the one asked for.
    """
    out: list[str] = [f"The learner asked for: {request}", ""]

    for label, key in (
        ("Why they want it", "purpose"),
        ("What they already know", "entry_point"),
        ("What they should be able to do after", "target_capability"),
    ):
        if situation.get(key):
            out.append(f"- {label}: {situation[key]}")
    for stated in situation.get("stated", []):
        out.append(f"- They explicitly asked for: {stated}")

    out += ["", f"## Write this part: {order['heading']}"]
    if order.get("why_here"):
        out.append(f"Why these belong together: {order['why_here']}")
    if order.get("extent"):
        out.append(f"Approved size for this part: {order['extent']}.")

    out += ["", "### Concepts this part must cover"]
    for concept in order["concepts"]:
        line = f"- {concept['concept']} — depth: {concept.get('depth', 'explain')}"
        if concept.get("why"):
            line += f" — why it's here: {concept['why']}"
        out.append(line)

    if missing:
        out += [
            "",
            "### Your previous attempt left these out — they are required",
            *(f"- {c}" for c in missing),
            "",
            "Write the whole part again, covering every concept above. Name each "
            "one explicitly so the reader can find it.",
        ]

    return "\n".join(out)


def _load_section(text: str) -> Section:
    """Parse one section, repairing the same envelope slips a document gets."""
    import json

    payload = json.loads(_strip_fence(text))
    # A model told "output one section object" sometimes wraps it anyway.
    if isinstance(payload, dict) and "sections" in payload and "heading" not in payload:
        sections = payload.get("sections") or []
        if not sections:
            raise ValueError("no section in the reply")
        payload = sections[0]
    if isinstance(payload, list):
        payload = {"heading": "", "blocks": payload}
    _retag(payload)
    return Section.model_validate(payload)


def _brief(request: str, plan: dict) -> str:
    """The approved plan, as the brief the document is written against.

    Prose rather than the raw snapshot. The snapshot is a decision table and
    reads like one; what the model needs is the agreement -- these concepts, in
    these units, in this order, at these depths, and these things deliberately
    left out. Handing over JSON invites the model to treat it as reference
    material it may improve on, which is exactly the freedom approval removed.

    Order follows `traversal`, because the sequence is itself an approved
    decision and rebuilding it from `partition` alone would lose it.
    """
    situation = plan.get("interpret_situation") or {}
    scope = plan.get("scope") or {}
    partition = plan.get("partition") or {}
    traversal = plan.get("traversal") or {}
    consequence = plan.get("consequence") or {}
    extent = plan.get("extent") or {}

    depth = {c["concept"]: c.get("depth", "explain") for c in scope.get("covered", [])}
    units = {u["heading"]: u for u in partition.get("units", [])}
    order = [h for h in traversal.get("sequence", []) if h in units] or list(units)

    out: list[str] = [f"The learner asked for: {request}", ""]

    out.append("## Who this is for")
    for label, key in (
        ("Subject", "subject"),
        ("Why they want it", "purpose"),
        ("What they already know", "entry_point"),
        ("What they should be able to do after", "target_capability"),
        ("Time they have", "capacity"),
    ):
        if situation.get(key):
            out.append(f"- {label}: {situation[key]}")
    for stated in situation.get("stated", []):
        out.append(f"- They explicitly asked for: {stated}")

    out.append("")
    out.append("## What was approved — write exactly this")
    if traversal.get("why"):
        out.append(f"Order: {traversal['why']}")
    for heading in order:
        unit = units[heading]
        out.append("")
        out.append(f"### {heading}")
        out.append(f"Why these belong together: {unit.get('why_here', '')}")
        for concept in unit.get("covers", []):
            out.append(f"- {concept} — treat at depth: {depth.get(concept, 'explain')}")

    orphans = [c for c in depth if not any(c in u.get("covers", []) for u in units.values())]
    if orphans:
        out.append("")
        out.append("### Also covered (not yet grouped)")
        out.extend(f"- {c} — treat at depth: {depth[c]}" for c in orphans)

    exclusions = consequence.get("exclusions", [])
    if exclusions:
        out.append("")
        out.append("## Deliberately out of scope — do not cover these")
        for item in exclusions:
            out.append(
                f"- {item.get('topic')} — consequence: {item.get('consequence')} "
                f"(they need it when: {item.get('when_to_learn')})"
            )
        out.append(
            "Put each of these in `deliberate_omissions`, with its consequence and "
            "when they must learn it. They were approved as omissions, so they are "
            "marked, not silently absent."
        )

    if extent.get("pages") or extent.get("study_time"):
        out.append("")
        out.append(
            f"## Agreed size\n{extent.get('pages', '')} · {extent.get('study_time', '')}. "
            "Write to this. Materially shorter is a different document from the one "
            "they approved."
        )

    return "\n".join(out)


def _parse_or_repair(
    completion: Completion,
    *,
    provider: Provider,
    system: str,
    request: str,
    schema: dict,
) -> tuple[Document, int, Completion]:
    """Validate; on failure, hand the model its own error once.

    Pydantic is the guarantee, not the provider. Native structured output makes
    the first attempt succeed more often; it does not change what is authoritative.
    """
    try:
        return _load(completion.text)[0], 0, completion
    except (ValidationError, ValueError) as first_error:
        # "Reply with the corrected JSON object" sitting next to an error that
        # names `sections.0.blocks.3` reads as "send me that block" -- and a
        # model has done exactly that, replying with a bare
        # `{"kind": "prose", ...}` and losing a whole document to a one-field
        # mistake. The dotted paths are a location, not a request.
        repair_request = (
            f"{request}\n\n"
            "Your previous reply did not validate.\n\n"
            "Reply with the COMPLETE document again — the whole top-level JSON "
            "object, including `title`, `assumed_entry`, `target_capability` "
            "and every section — changing only what the errors below name. The "
            "dotted paths say WHERE each problem is; they are not a request to "
            "send that fragment on its own. JSON only, no prose, no fence.\n\n"
            f"{str(first_error)[:2000]}"
        )
        retry = provider.complete(
            system=system, user=repair_request, schema=schema, max_tokens=MAX_TOKENS
        )
        try:
            document = _load(retry.text)[0]
        except (ValidationError, ValueError) as second_error:
            raise ValueError(
                f"{provider.name}/{provider.model} produced invalid output twice.\n"
                f"first:  {str(first_error)[:600]}\n"
                f"second: {str(second_error)[:600]}\n"
                f"head:   {retry.text[:300]!r}"
            ) from second_error

        merged = Completion(
            text=retry.text,
            input_tokens=completion.input_tokens + retry.input_tokens,
            output_tokens=completion.output_tokens + retry.output_tokens,
            model=retry.model,
            provider=retry.provider,
        )
        return document, 1, merged


# The discriminator tag and the class name differ for four blocks, and a model
# under load reaches for the class name it can see in the schema: `CheckQuestion`
# becomes "checkquestion" rather than "question". That is a serialization slip,
# not a wrong educational decision -- the intent is unambiguous -- so it is
# repaired here like a markdown fence, rather than spent on another model call.
#
# Only class-name derivations are listed. Nothing is guessed: "paragraph" does
# not become "prose", because a model that wrote it may have meant something
# else, and silently deciding for it is how a wrong document looks right.
_KIND_ALIASES: dict[str, str] = {
    "checkquestion": "question",
    "workedexample": "example",
    "bulletlist": "list",
    "relationalstructure": "relation",
    "relationalblock": "relation",
}


def _canonical(kind: str) -> str:
    return "".join(ch for ch in kind.lower() if ch.isalnum())


def _retag(data: object) -> int:
    """Rewrite alias `kind` tags in place. Returns how many were rewritten.

    Counted rather than swallowed: a rising count means the prompt is not
    naming the tags clearly enough, and that is a finding, not noise.
    """
    fixed = 0
    if isinstance(data, dict):
        kind = data.get("kind")
        if isinstance(kind, str):
            target = _KIND_ALIASES.get(_canonical(kind))
            if target is not None and target != kind:
                data["kind"] = target
                fixed += 1
        for value in data.values():
            fixed += _retag(value)
    elif isinstance(data, list):
        for item in data:
            fixed += _retag(item)
    return fixed


def _load(text: str) -> tuple[Document, int]:
    """Parse, repair the envelope, validate. Raises like `model_validate_json`."""
    import json

    payload = json.loads(_strip_fence(text))
    retagged = _retag(payload)
    return Document.model_validate(payload), retagged


def _strip_fence(text: str) -> str:
    """Some models wrap JSON in a markdown fence despite being told not to."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.split("\n", 1)[1] if "\n" in stripped else ""
    if body.rstrip().endswith("```"):
        body = body.rstrip()[: -len("```")]
    return body.strip()
