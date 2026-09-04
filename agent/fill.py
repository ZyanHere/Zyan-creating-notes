"""fill — the model writes block content, and nothing else.

Contract, in both directions:

* It is **stated in the prompt**: exact block list, types, order, caps, the two
  inline constructs, no HTML.
* It is **checked on the way back**: same count, same types in the same order,
  no markup, then the engine's own Pydantic models. A prompt alone is a
  request; the check is what makes it a contract.

The model never sees HTML and never chooses structure. Given a plan of N blocks
it returns content for exactly those N blocks — it cannot add one, drop one, or
change a type. Anything else is a failure and is retried with the reason
attached.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from engine.schema import (
    Badge,
    Callout,
    CheatSheet,
    Code,
    Document,
    LayerStack,
    ListBlock,
    Para,
    Section,
    Subheading,
)
from pydantic import ValidationError

from .client import Client
from .models import PROSE_TYPES, DocumentPlan, SectionPlan

MAX_ATTEMPTS = 3

# A model that emits markup has misunderstood the job: the template owns
# presentation. Catch it here rather than letting it reach a page as escaped
# angle brackets.
_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


class FillError(RuntimeError):
    """The model could not produce content matching the plan."""


@dataclass
class Finding:
    """Something worth surfacing that is not a hard failure — an overrun cap.

    Caps are guidance for the writer, not structural requirements: a 95-word
    paragraph against a 90-word cap is a note, not a broken document. Structure
    is what fails.
    """

    section: int
    block: int
    kind: str
    detail: str


@dataclass
class FillResult:
    document: Document
    findings: list[Finding] = field(default_factory=list)
    attempts: int = 1


# ------------------------------------------------------------------ prompt

SYSTEM = """You write the content of pre-defined document blocks.

You are given a numbered list of blocks. Return content for exactly those \
blocks, in the same order, with the same types. You may not add a block, \
remove one, reorder them, or change a type.

Return JSON only. No prose before or after, no markdown fences.

Shape:
{"blocks": [{"id": 0, "type": "para", "text": "..."}, ...]}

Fields by type:
  para        -> text
  subheading  -> text
  code        -> text          (source only; no fences, no commentary)
  callout     -> text
  list        -> items         (array of strings)
  badge       -> text

Rules:
- Never write HTML. The template handles all presentation.
- Two inline constructs are available inside text, and only these two:
    `code`      for an identifier, path, flag or short expression
    **bold**    for a term being introduced
- Respect each block's cap. It is a budget, not a target.
- Write for the stated audience. Be concrete. No filler, no restating the \
brief back."""


def _spec_line(i: int, spec) -> str:
    parts = [f'{i}. type={spec.type}']
    if spec.type == "code":
        parts.append(f"lang={spec.lang}")
        if spec.file:
            parts.append(f"file={spec.file}")
        parts.append(f"max_lines={spec.max_lines}")
    elif spec.type == "list":
        parts.append(f"exactly {spec.count} items")
        parts.append(f"max {spec.max_words_per_item} words each")
    elif spec.type == "callout":
        parts.append(f"label={spec.label}")
        parts.append(f"max_words={spec.max_words}")
    else:
        parts.append(f"max_words={spec.max_words}")
    return "  ".join(parts) + f"\n     brief: {spec.brief}"


def build_prompt(plan: DocumentPlan, section: SectionPlan, index: int) -> str:
    prose = [(i, s) for i, s in enumerate(section.blocks) if s.type in PROSE_TYPES]
    head = section.heading
    lines = [
        f"DOCUMENT: {plan.title}" + (f" — {plan.subtitle}" if plan.subtitle else ""),
    ]
    if plan.context:
        lines.append(f"AUDIENCE AND PURPOSE: {plan.context}")
    lines.append("")
    lines.append(f"SECTION {index + 1}" + (f" [{section.label}]" if section.label else ""))
    if head:
        lines.append(
            "HEADING: " + head.lead + (f" {head.accent}" if head.accent else "")
        )
    lines.append("")
    lines.append(f"BLOCKS TO WRITE ({len(prose)}):")
    for i, spec in prose:
        lines.append(_spec_line(i, spec))
    lines.append("")
    lines.append(
        "Return JSON with a \"blocks\" array holding exactly these "
        f"{len(prose)} entries, ids {[i for i, _ in prose]}, in this order."
    )
    return "\n".join(lines)


# ------------------------------------------------------------- validation


def _extract_json(raw: str) -> dict:
    text = _FENCE.sub("", raw.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some models wrap the object in commentary despite instructions.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise FillError("response contained no JSON object")
        return json.loads(text[start : end + 1])


def _build_block(spec, payload: dict):
    """Turn one model response entry into a real Block, or raise."""
    kind = spec.type
    if kind == "para":
        return Para(text=payload["text"])
    if kind == "subheading":
        return Subheading(text=payload["text"])
    if kind == "badge":
        return Badge(text=payload["text"])
    if kind == "code":
        return Code(lang=spec.lang, file=spec.file, text=payload["text"])
    if kind == "callout":
        return Callout(
            label=spec.label, subtitle=spec.subtitle, text=payload["text"]
        )
    if kind == "list":
        return ListBlock(marker=spec.marker, items=list(payload["items"]))
    raise FillError(f"{kind!r} is not a prose block")


def _passthrough(spec):
    if spec.type == "figure":
        return LayerStack(
            layers=spec.layers, caption=spec.caption, number=spec.number
        )
    if spec.type == "cheatsheet":
        return CheatSheet(rows=spec.rows)
    raise FillError(f"{spec.type!r} is not a pass-through block")


def _words(block) -> int:
    if block.type == "list":
        return max((len(i.split()) for i in block.items), default=0)
    return len(getattr(block, "text", "").split())


def validate_section(section: SectionPlan, data: dict, index: int):
    """Check a model response against the plan. Returns (blocks, findings).

    Raises FillError with a message written to be fed straight back to the
    model on retry.
    """
    prose = [(i, s) for i, s in enumerate(section.blocks) if s.type in PROSE_TYPES]

    if not isinstance(data, dict) or "blocks" not in data:
        raise FillError('response must be an object with a "blocks" array')
    got = data["blocks"]
    if not isinstance(got, list):
        raise FillError('"blocks" must be an array')
    if len(got) != len(prose):
        raise FillError(
            f"expected exactly {len(prose)} blocks, received {len(got)}. "
            "Do not add or omit blocks."
        )

    by_id = {}
    for entry in got:
        if not isinstance(entry, dict) or "id" not in entry:
            raise FillError('every block needs an integer "id" matching the plan')
        by_id[entry["id"]] = entry

    blocks, findings = [], []
    for pos, (i, spec) in enumerate(prose):
        entry = by_id.get(i)
        if entry is None:
            raise FillError(f"block id {i} is missing")
        if entry.get("type") != spec.type:
            raise FillError(
                f"block {i} must be type {spec.type!r}, received "
                f"{entry.get('type')!r}. Types are fixed by the plan."
            )
        try:
            block = _build_block(spec, entry)
        except KeyError as e:
            raise FillError(f"block {i} ({spec.type}) is missing field {e}") from None
        except ValidationError as e:
            raise FillError(f"block {i} failed validation: {e}") from None

        text = " ".join(block.items) if block.type == "list" else block.text
        if _TAG.search(text):
            raise FillError(
                f"block {i} contains HTML. Write plain text; the template "
                "handles presentation."
            )

        # Caps are guidance — record, do not fail.
        if spec.type == "list":
            if len(block.items) != spec.count:
                findings.append(Finding(index, i, "count",
                    f"{len(block.items)} items, plan said {spec.count}"))
            over = _words(block) - spec.max_words_per_item
            if over > 0:
                findings.append(Finding(index, i, "cap",
                    f"longest item {over} words over"))
        elif spec.type == "code":
            over = len(block.text.splitlines()) - spec.max_lines
            if over > 0:
                findings.append(Finding(index, i, "cap", f"{over} lines over"))
        else:
            over = _words(block) - spec.max_words
            if over > 0:
                findings.append(Finding(index, i, "cap", f"{over} words over"))

        blocks.append((i, block))

    # Slot the pass-through blocks back into their planned positions.
    out = []
    filled = dict(blocks)
    for i, spec in enumerate(section.blocks):
        out.append(filled[i] if i in filled else _passthrough(spec))
    return out, findings


# ------------------------------------------------------------------- fill


def fill(plan: DocumentPlan, client: Client, attempts: int = MAX_ATTEMPTS) -> FillResult:
    """Write every prose block in the plan. One model call per section."""
    sections, findings, used = [], [], 1

    for index, section in enumerate(plan.sections):
        prose = [s for s in section.blocks if s.type in PROSE_TYPES]
        if not prose:
            blocks = [_passthrough(s) for s in section.blocks]
        else:
            prompt = build_prompt(plan, section, index)
            last = None
            for attempt in range(1, attempts + 1):
                used = max(used, attempt)
                ask = prompt if last is None else (
                    f"{prompt}\n\nYour previous reply was rejected: {last}\n"
                    "Return corrected JSON only."
                )
                raw = client.complete(SYSTEM, ask)
                try:
                    blocks, found = validate_section(section, _extract_json(raw), index)
                    findings.extend(found)
                    break
                except (FillError, json.JSONDecodeError) as e:
                    last = str(e)
            else:
                raise FillError(
                    f"section {index + 1} failed after {attempts} attempts: {last}"
                )

        sections.append(
            Section(
                label=section.label,
                heading=section.heading,
                blocks=blocks,
                rule_before=section.rule_before,
            )
        )

    doc = Document(
        title=plan.title,
        subtitle=plan.subtitle,
        eyebrow=plan.eyebrow,
        running_title=plan.running_title,
        footer_text=plan.footer_text,
        cover=plan.cover,
        build_stamp=plan.build_stamp,
        sections=sections,
    )
    return FillResult(document=doc, findings=findings, attempts=used)
