"""The approved curriculum, read one module at a time.

A curriculum's `partition` names N modules and each becomes its own PDF. The user
generates them **one at a time**, in their own order, whenever they want the next
one -- so this module answers two questions and nothing else:

    modules(plan)        what modules did the user approve, in what order
    plan_for(plan, i)    the plan for writing module i, and only module i

**The approved plan is the source of truth and is never rewritten.** `plan_for`
derives a narrowed *view* of it; nothing here plans, re-plans, or decides
anything. Generating module 4 must not be able to change what module 5 was
approved to contain.

### A module's concepts become its sections

Decision 10 -- how a document divides into sections -- is not yet a planned
decision. Rather than invent one here, each approved concept in the module
becomes one section of that module's document. That reuses the per-part
generation and fulfilment pipeline exactly as it stands: one work order per
section, verified against the concept it was approved to cover.

This is deliberately the smallest thing that works. When decision 10 gets its own
planning step, it replaces the mapping in `plan_for` and nothing else moves.

### What is deliberately absent

**Predecessor handling.** Architecture §5 makes a module's assumed entry a
function of its predecessors, so module 5 written after a changed module 3 rests
on a moved premise. That is real and it is not here: every module is written
against the curriculum's own entry point, and the ordering in `traversal` is
carried for display only. Introducing it would be a new curriculum rule, which
this layer must not add.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Covered:
    """One concept this module covers, at the depth it was approved at."""

    concept: str
    depth: str
    why: str


@dataclass(frozen=True, slots=True)
class ModuleRef:
    """One approved module, as something that can be generated."""

    index: int
    title: str
    capability: str
    why_here: str
    concepts: tuple[str, ...]
    extent: str | None
    coverage: tuple[Covered, ...] = ()
    """`concepts` with the depth and reason each was approved at.

    Carried so a client can show what a module contains without re-deriving it
    from the plan: the generation screen used to list the modules and then,
    below, the whole plan again -- the same modules a second time, from the
    *current* decisions rather than from the approved snapshot. Two lists of one
    thing, and only one of them was the promise that was actually made.

    A concept in `concepts` with no entry in the plan's `scope` is absent here
    rather than guessed at, so this can be shorter than `concepts`.
    """

    def to_json(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "capability": self.capability,
            "why_here": self.why_here,
            "concepts": list(self.concepts),
            "extent": self.extent,
            "coverage": [
                {"concept": c.concept, "depth": c.depth, "why": c.why}
                for c in self.coverage
            ],
        }


def modules(plan: dict | None) -> list[ModuleRef]:
    """The approved modules, in the approved order.

    A plan with no modules -- one written before the curriculum layer, whose
    `units` were sections of a single document -- yields exactly one module
    covering the whole plan. That is what those plans always were, so the caller
    has one shape to handle rather than two.
    """
    if not plan:
        return []

    partition = plan.get("partition") or {}
    # An approved snapshot is frozen at the shape it had when it was approved,
    # and `extent` used to be the prose sentence shown to the user rather than
    # the structured record it is now. One such commitment still exists on disk.
    # Reading it as a dict raised `AttributeError` from inside a list endpoint,
    # so one legacy project took down the whole project index.
    raw_extent = plan.get("extent")
    extent_doc = raw_extent if isinstance(raw_extent, dict) else {}
    extent = extent_doc.get("per_unit") or {}
    approved = partition.get("modules") or []

    # `scope` is where a concept's depth and reason live; `partition` only names
    # which module it landed in. Joining them here is what lets a client show a
    # module's contents without re-reading the whole plan.
    by_concept = {
        c["concept"]: Covered(
            concept=c["concept"], depth=c.get("depth", ""), why=c.get("why", "")
        )
        for c in (plan.get("scope") or {}).get("covered", [])
        if isinstance(c, dict) and c.get("concept")
    }

    def _coverage(names) -> tuple[Covered, ...]:
        return tuple(by_concept[n] for n in names if n in by_concept)

    if approved:
        by_title = {m["title"]: m for m in approved}
        order = [t for t in (plan.get("traversal") or {}).get("sequence", []) if t in by_title]
        order += [t for t in by_title if t not in order]
        return [
            ModuleRef(
                index=i,
                title=title,
                capability=by_title[title].get("capability", ""),
                why_here=by_title[title].get("why_here", ""),
                concepts=tuple(by_title[title].get("covers") or []),
                extent=extent.get(title),
                coverage=_coverage(by_title[title].get("covers") or []),
            )
            for i, title in enumerate(order, 1)
        ]

    situation = plan.get("interpret_situation") or {}
    covered = [c["concept"] for c in (plan.get("scope") or {}).get("covered", [])]
    if not covered:
        return []
    return [
        ModuleRef(
            index=1,
            title=situation.get("subject") or "Study notes",
            capability=situation.get("target_capability", ""),
            why_here="",
            concepts=tuple(covered),
            extent=extent_doc.get("pages"),
            coverage=_coverage(covered),
        )
    ]


def plan_for(plan: dict, index: int) -> dict:
    """A plan that writes exactly module `index` of the approved curriculum.

    Derived, never stored: the approved plan is untouched. Every concept the
    module covers becomes one section, so the existing per-part pipeline can
    generate and verify it without knowing a curriculum exists.
    """
    found = [m for m in modules(plan) if m.index == index]
    if not found:
        raise ValueError(f"the approved plan has no module {index}")
    module = found[0]

    situation = dict(plan.get("interpret_situation") or {})
    by_concept = {c["concept"]: c for c in (plan.get("scope") or {}).get("covered", [])}
    covered = [by_concept[c] for c in module.concepts if c in by_concept]
    if not covered:
        raise ValueError(f"module {index} ({module.title}) covers no approved concept")

    # The module's own title and capability become the document's, because that
    # is what the user approved this document to be. Entry point stays the
    # curriculum's -- adjusting it per module is predecessor handling, and that
    # is deliberately not here.
    situation["subject"] = module.title
    if module.capability:
        situation["target_capability"] = module.capability

    return {
        "interpret_situation": situation,
        "scope": {"covered": covered, "cut": []},
        # `units` is the section shape (decision 10). One section per approved
        # concept -- the smallest mapping that needs no new decision.
        "partition": {
            "units": [
                {
                    "heading": c["concept"],
                    "covers": [c["concept"]],
                    "why_here": c.get("why", ""),
                }
                for c in covered
            ]
        },
        "traversal": {
            "sequence": [c["concept"] for c in covered],
            "why": module.why_here,
        },
        # The curriculum's exclusions belong to the curriculum, not to any one
        # module. Repeating them in every PDF would tell the reader the same
        # thing N times and imply each module owns the omission.
        "consequence": {"exclusions": []},
        "extent": {"pages": module.extent} if module.extent else {},
    }
