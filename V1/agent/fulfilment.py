"""Does this document deliver the plan the user approved?

The plan gate's promise to the reader is *what gets written is what you just
read*. Until now nothing enforced it: a run produced one of six approved units,
omitted fifteen of seventeen concepts, wrote a PDF and reported success.

So this module is not a check on the model. It is the system's side of a
contract. The LLM supplies educational content; **we** are answerable for the
artifact matching the agreement, and a promise nothing can falsify is not a
promise.

Pure and model-free, like `sufficiency.py` and `treatment.py`: policy in code,
content from the model. Everything here is computable from the approved snapshot
and the produced document, so it is testable without a provider and cannot
itself hallucinate.

**What it checks: completeness.** Was every approved part written, and does each
cover the concepts it was approved to cover.

**What it deliberately does not check: treatment.** Which treatment a concept
deserves depends on artifact type, purpose and subject together, and that has not
had its design pass. Enforcing a rule here now -- "work through must produce a
trace", say -- would fix a taxonomy by accident, in the one place it is hardest
to see. `treatments_anticipated` and `treatments_produced` are recorded per unit
as *evidence* for that pass. Neither makes a document unsatisfied.

**What it can and cannot see.** Coverage is decided by whether a concept is
named in the unit's text. That reliably catches *omission*, which is the failure
this exists for. It does not verify that a concept was treated *well* -- naming a
thing is not teaching it. Where the check is weaker than the claim, the report
says so rather than implying more than it knows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Words too common to identify a concept. A concept whose every significant word
# is one of these is matched on the whole phrase instead.
_NOISE = frozenset(
    """a an and are as at be by for from in into is of on or the to via with
    using between within over under than then that this these those it its""".split()
)

_PARENTHETICAL = re.compile(r"\([^)]*\)")
_NON_WORD = re.compile(r"[^a-z0-9\s]+")
_SPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Casefold, drop punctuation, collapse whitespace. Not stemming -- a match
    here should be obvious to a human reading both strings."""
    return _SPACE.sub(" ", _NON_WORD.sub(" ", text.lower())).strip()


def _significant(concept: str) -> list[str]:
    return [w for w in _normalize(concept).split() if w not in _NOISE and len(w) > 2]


def section_text(section) -> str:
    """Every string a section puts in front of the reader.

    Walks the blocks generically rather than per kind: a new block type must not
    silently become invisible to the check, which is the same failure mode as a
    template with no `{% else %}`.
    """
    parts: list[str] = [_get(section, "heading") or ""]

    def walk(value) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key != "diagnosis":  # machinery, not reader-facing text
                    walk(item)
        elif hasattr(value, "model_dump"):
            walk(value.model_dump())

    for block in _get(section, "blocks") or []:
        walk(block)
    return _normalize(" ".join(parts))


def _get(obj, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def covers(text: str, concept: str) -> bool:
    """Is this concept named in this text?

    Two ways, because approved concept names carry qualifiers a writer would not
    repeat verbatim: "Topological Sort (Kahn's BFS)" is covered by a section that
    says "topological sort". The parenthetical is a note to the planner, not a
    string the document owes.
    """
    bare = _normalize(_PARENTHETICAL.sub(" ", concept))
    if bare and bare in text:
        return True
    words = _significant(concept)
    if not words:
        return bool(bare) and bare in text
    return all(w in text for w in words)


def diagnoses(section) -> set[str]:
    found: set[str] = set()
    for block in _get(section, "blocks") or []:
        value = _get(block, "diagnosis")
        if isinstance(value, str) and value.strip():
            found.add(value.strip())
    return found


def departures(section) -> int:
    """Blocks that are not prose. Counted as an observation about how the unit
    was written -- what that count *should* be for a given depth, artifact type
    and subject is the treatment design pass's question, not this module's."""
    return sum(1 for b in _get(section, "blocks") or [] if _get(b, "kind") != "prose")


@dataclass(frozen=True, slots=True)
class UnitReport:
    """One approved unit, and what came back for it."""

    heading: str
    generated: bool
    concepts_required: tuple[str, ...] = ()
    concepts_covered: tuple[str, ...] = ()
    concepts_missing: tuple[str, ...] = ()

    # ---- observations, deliberately not requirements -----------------------
    # Recorded because the treatment design pass will need evidence about what
    # treatments requests actually call for and what models actually produce.
    # NOT enforced: which treatment suits which artifact type, purpose and
    # subject is an open question, and answering it by accident here would fix
    # a taxonomy before it has been designed.
    treatments_anticipated: tuple[str, ...] = ()
    treatments_produced: tuple[str, ...] = ()
    depths_required: tuple[str, ...] = ()
    blocks: int = 0
    departures: int = 0
    words: int = 0
    notes: tuple[str, ...] = ()
    """Observations worth reading. Never problems -- see `check_document`."""

    @property
    def satisfied(self) -> bool:
        """Completeness only: was this part written, and does it cover what it
        was approved to cover."""
        return self.generated and not self.concepts_missing

    def to_json(self) -> dict:
        return {
            "heading": self.heading,
            "generated": self.generated,
            "satisfied": self.satisfied,
            "concepts_required": list(self.concepts_required),
            "concepts_covered": list(self.concepts_covered),
            "concepts_missing": list(self.concepts_missing),
            "treatments_anticipated": list(self.treatments_anticipated),
            "treatments_produced": list(self.treatments_produced),
            "depths_required": list(self.depths_required),
            "blocks": self.blocks,
            "departures": self.departures,
            "words": self.words,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class Fulfilment:
    """Whether the artifact delivers the approved plan, and where it does not."""

    units: tuple[UnitReport, ...] = ()
    units_approved: tuple[str, ...] = ()
    units_generated: tuple[str, ...] = ()
    units_missing: tuple[str, ...] = ()
    concepts_required: tuple[str, ...] = ()
    concepts_covered: tuple[str, ...] = ()
    concepts_missing: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    """Sections in the document that no approved unit asked for. Not necessarily
    wrong -- but it is a change to what was agreed, and agreeing to X is not
    agreeing to X plus whatever else seemed good."""

    problems: tuple[str, ...] = ()

    @property
    def satisfied(self) -> bool:
        """The whole point. False must be reachable, or the check is decoration."""
        return not self.problems

    @property
    def coverage(self) -> float:
        if not self.concepts_required:
            return 1.0
        return len(self.concepts_covered) / len(self.concepts_required)

    def to_json(self) -> dict:
        return {
            "satisfied": self.satisfied,
            "coverage": round(self.coverage, 3),
            "units_approved": list(self.units_approved),
            "units_generated": list(self.units_generated),
            "units_missing": list(self.units_missing),
            "concepts_required": list(self.concepts_required),
            "concepts_covered": list(self.concepts_covered),
            "concepts_missing": list(self.concepts_missing),
            "changed": list(self.changed),
            "problems": list(self.problems),
            "units": [u.to_json() for u in self.units],
        }


def requirements(plan: dict) -> list[dict]:
    """The approved plan, reshaped as one work order per part.

    This is what makes per-part generation possible without handing the whole
    plan to every call: each order carries its own concepts, depths and
    anticipated treatments, and nothing else.

    Reads `partition.modules` (a curriculum's modules, each destined to be its
    own PDF) and falls back to legacy `partition.units`.
    """
    scope = plan.get("scope") or {}
    partition = plan.get("partition") or {}
    traversal = plan.get("traversal") or {}
    extent = (plan.get("extent") or {}).get("per_unit") or {}

    by_concept = {c["concept"]: c for c in scope.get("covered", [])}
    units = {p["title"]: p for p in partition.get("modules") or []} or {
        # Legacy: plans written before the curriculum layer, whose `units` were
        # sections of one document. Read so old projects still work; never
        # re-labelled modules, because the planner never made that decomposition.
        u["heading"]: u
        for u in partition.get("units") or []
    }
    order = [h for h in traversal.get("sequence", []) if h in units] or list(units)
    for heading in units:
        if heading not in order:
            order.append(heading)

    placed = {c for u in units.values() for c in u.get("covers", [])}
    orders: list[dict] = []
    for heading in order:
        unit = units[heading]
        concepts = [by_concept[c] for c in unit.get("covers", []) if c in by_concept]
        orders.append(
            {
                "heading": heading,
                "why_here": unit.get("why_here", ""),
                "concepts": concepts,
                "extent": extent.get(heading),
            }
        )

    # A covered concept in no unit would silently vanish. The plan page surfaces
    # these as "Also covered", so the user may well have approved one.
    orphans = [by_concept[c] for c in by_concept if c not in placed]
    if orphans:
        orders.append(
            {
                "heading": "Also covered",
                "why_here": "Approved, but not grouped into a part.",
                "concepts": orphans,
                "extent": None,
            }
        )
    return orders


def check_unit(order: dict, section, *, reason: str | None = None) -> UnitReport:
    """One work order against the section produced for it.

    `reason` is why no section exists, when the caller knows. A unit can be
    missing because the model answered badly or because the call never
    succeeded at all -- a spent rate limit, a refused model -- and those need
    different things from the reader. Without it the report could only say the
    part was absent, which reads as "the model omitted this" even when the
    truth is that nobody was ever asked.
    """
    required = [c["concept"] for c in order["concepts"]]
    if section is None:
        return UnitReport(
            heading=order["heading"],
            generated=False,
            concepts_required=tuple(required),
            concepts_missing=tuple(required),
            notes=(
                (f"no section was produced for this unit: {reason}",)
                if reason
                else ("no section was produced for this unit",)
            ),
        )

    text = section_text(section)
    covered = [c for c in required if covers(text, c)]
    missing = [c for c in required if c not in covered]

    # Observation only. What the plan anticipated, and what the model actually
    # produced -- side by side, so the treatment design pass has evidence rather
    # than intuition. Nothing here decides `satisfied`.
    anticipated = sorted(
        {
            c["anticipates"]
            for c in order["concepts"]
            if (c.get("anticipates") or "none") != "none"
        }
    )
    depths = sorted({c.get("depth", "explain") for c in order["concepts"]})

    return UnitReport(
        heading=order["heading"],
        generated=True,
        concepts_required=tuple(required),
        concepts_covered=tuple(covered),
        concepts_missing=tuple(missing),
        treatments_anticipated=tuple(anticipated),
        treatments_produced=tuple(sorted(diagnoses(section))),
        depths_required=tuple(depths),
        blocks=len(_get(section, "blocks") or []),
        departures=departures(section),
        words=len(text.split()),
    )


def check_document(plan: dict, document, unit_reports: list[UnitReport]) -> Fulfilment:
    """The final gate. Assembled document against the approved plan."""
    orders = requirements(plan)
    approved = [o["heading"] for o in orders]
    produced_headings = [_get(s, "heading") for s in _get(document, "sections") or []]

    generated = [r.heading for r in unit_reports if r.generated]
    missing_units = [h for h in approved if h not in generated]
    changed = [h for h in produced_headings if h not in approved]

    required = [c for o in orders for c in [x["concept"] for x in o["concepts"]]]
    covered = sorted({c for r in unit_reports for c in r.concepts_covered})
    still_missing = [c for c in required if c not in covered]

    problems: list[str] = []
    if missing_units:
        problems.append(
            f"{len(missing_units)} approved part(s) missing: " + ", ".join(missing_units)
        )
    if still_missing:
        problems.append(
            f"{len(still_missing)} of {len(required)} approved concepts not covered: "
            + ", ".join(still_missing[:8])
            + (" …" if len(still_missing) > 8 else "")
        )
    # Treatment is NOT checked here. Which treatment a concept deserves depends
    # on artifact type, purpose and subject together, and that has not had its
    # design pass -- enforcing a rule now would fix a taxonomy by accident.
    # `treatments_anticipated` and `treatments_produced` are recorded per unit as
    # evidence for that pass; neither is a problem.
    if changed:
        problems.append("sections not in the approved plan: " + ", ".join(changed))

    return Fulfilment(
        units=tuple(unit_reports),
        units_approved=tuple(approved),
        units_generated=tuple(generated),
        units_missing=tuple(missing_units),
        concepts_required=tuple(required),
        concepts_covered=tuple(covered),
        concepts_missing=tuple(still_missing),
        changed=tuple(changed),
        problems=tuple(problems),
    )
