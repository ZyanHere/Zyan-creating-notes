"""What we record about one V1 run.

Every function here is a *reading*. Nothing repairs, nothing decides, nothing is
written back into V1. Where V1 itself computes something -- coherence, capability
support, feasibility, fulfilment -- we record V1's own answer rather than a
recomputation, because the baseline is what V1 says about itself.

Three readings are computed HERE and not by V1, because V1 does not compute them:

  unassigned          concepts approved and belonging to no module (and the
                      mirror: named by a module, absent from scope). This is the
                      defect found by code reading; the harness measures its rate
                      instead of V1 being changed to prevent it.
  duplicate_coverage  a concept claimed by two modules -- delivered twice.
  slug_collisions     two module titles that name the same PDF file on disk.

They are measured with V1's own `slugify`, so what is reported is what V1 would
actually do, not an approximation of it.
"""

from __future__ import annotations

import collections
import re
from typing import Any

_PARENTHETICAL_LIST = re.compile(r"\(([^)]*,[^)]*)\)")


def _get(mapping: Any, *path, default=None):
    cursor = mapping
    for key in path:
        if not isinstance(cursor, dict):
            return default
        cursor = cursor.get(key)
        if cursor is None:
            return default
    return cursor


# ---------------------------------------------------------------------------
# intake
# ---------------------------------------------------------------------------


def intake(view: dict) -> dict:
    """What the system asked, and the record of why it asked exactly that."""
    sufficiency = view.get("sufficiency") or {}
    axes = sufficiency.get("axes") or []
    questions = view.get("questions") or []
    return {
        "state": view.get("state"),
        "verdict": sufficiency.get("verdict"),
        "budget": sufficiency.get("budget"),
        "asking": sufficiency.get("asking") or [],
        "over_budget": sufficiency.get("over_budget") or [],
        "questions_written": len(questions),
        "questions": [
            {
                "axis": q.get("axis"),
                "question": q.get("question"),
                "options": [o.get("label") for o in (q.get("options") or [])],
                "default_label": q.get("default_label"),
            }
            for q in questions
        ],
        "axes": [
            {
                "axis": a.get("axis"),
                "value": a.get("value"),
                "strength": a.get("strength"),
                "material": a.get("material"),
                "asked": a.get("asked"),
                "verified_spans": len(a.get("verified") or []),
                "discarded_spans": len(a.get("unverified") or []),
                "reason": a.get("reason"),
            }
            for a in axes
        ],
        # Semantics §1: a stated constraint that came back as an inference is the
        # provenance failure V1's register records as solved. Worth watching.
        "weak_axes": [a["axis"] for a in axes if a.get("strength") in ("guessed", "unknown")],
        "guessed_but_material": [
            a["axis"]
            for a in axes
            if a.get("strength") in ("guessed", "unknown") and a.get("material")
        ],
    }


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------


def situation(decisions: dict) -> dict:
    read = decisions.get("interpret_situation") or {}
    stated = read.get("stated") or []
    return {
        "subject": read.get("subject"),
        "job": read.get("job"),
        "purpose": read.get("purpose"),
        "entry_point": read.get("entry_point"),
        "target_capability": read.get("target_capability"),
        "capacity": read.get("capacity"),
        "stated": [s if isinstance(s, str) else s.get("text") for s in stated],
        "stated_axes": [
            None if isinstance(s, str) else s.get("axis") for s in stated
        ],
        "inferred": read.get("inferred") or [],
    }


def landscape(decisions: dict) -> dict:
    """What exists, and what relevance kept.

    `parenthetical_lists` is the tell `derive_v1.md` names explicitly: a concept
    called "Major Frameworks (LangGraph, AutoGen, CrewAI)" is five concepts the
    partition can never separate, because there is nothing there to divide.
    Counted so we can say how often granularity actually collapses.
    """
    concepts = _get(decisions, "derive_structure", "concepts", default=[]) or []
    judgements = _get(decisions, "relevance", "judgements", default=[]) or []
    in_play = [j for j in judgements if j.get("in_play")]
    return {
        "concept_count": len(concepts),
        "concepts": [
            {
                "name": c.get("name"),
                "built_from": c.get("built_from") or [],
                "family": c.get("family") or "",
            }
            for c in concepts
        ],
        "families": sorted({c.get("family") or "" for c in concepts} - {""}),
        "edges": sum(len(c.get("built_from") or []) for c in concepts),
        "roots": [c.get("name") for c in concepts if not (c.get("built_from") or [])],
        "parenthetical_lists": [
            c.get("name") for c in concepts
            if c.get("name") and _PARENTHETICAL_LIST.search(c["name"])
        ],
        "judged": len(judgements),
        "in_play": len(in_play),
        "out_of_play": [j.get("concept") for j in judgements if not j.get("in_play")],
        "unjudged": sorted(
            {c.get("name") for c in concepts} - {j.get("concept") for j in judgements}
        ),
    }


def scope(decisions: dict) -> dict:
    covered = _get(decisions, "scope", "covered", default=[]) or []
    depths = collections.Counter((c.get("depth") or "").strip().lower() for c in covered)
    anticipates = collections.Counter(c.get("anticipates") or "none" for c in covered)
    return {
        "covered_count": len(covered),
        "covered": [
            {
                "concept": c.get("concept"),
                "depth": c.get("depth"),
                "anticipates": c.get("anticipates") or "none",
                "why": c.get("why"),
            }
            for c in covered
        ],
        "depths": dict(depths),
        # The planner's treatment judgment. V1 uses it for page-size arithmetic
        # and feasibility only -- it never reaches the generator -- so this is
        # the number to compare against `treatments_produced` at generation.
        "anticipates": dict(anticipates),
        "anticipates_any": sum(v for k, v in anticipates.items() if k != "none"),
        "cut": _get(decisions, "scope", "cut", default=[]) or [],
    }


def partition(decisions: dict, *, slugify) -> dict:
    """Modules, and the three consistency readings V1 does not take."""
    modules = _get(decisions, "partition", "modules", default=[]) or []
    units = _get(decisions, "partition", "units", default=[]) or []
    covered = [
        c.get("concept")
        for c in (_get(decisions, "scope", "covered", default=[]) or [])
        if c.get("concept")
    ]

    placed = [c for m in modules for c in (m.get("covers") or [])]
    placed_set = set(placed)
    owners = collections.Counter(placed)

    by_slug: dict[str, list[str]] = collections.defaultdict(list)
    for module in modules:
        if module.get("title"):
            by_slug[slugify(module["title"])].append(module["title"])

    return {
        "shape": "modules" if modules else ("units" if units else "none"),
        "module_count": len(modules),
        "legacy_unit_count": len(units),
        "modules": [
            {
                "title": m.get("title"),
                "covers": m.get("covers") or [],
                "concept_count": len(m.get("covers") or []),
                "capability": m.get("capability"),
                "why_here": m.get("why_here"),
            }
            for m in modules
        ],
        "concepts_per_module": [len(m.get("covers") or []) for m in modules],
        # --- readings V1 does not take -------------------------------------
        "orphans": [c for c in covered if c not in placed_set] if modules else [],
        "phantoms": sorted(placed_set - set(covered)) if modules else [],
        "duplicate_coverage": sorted(c for c, n in owners.items() if n > 1),
        "slug_collisions": [
            {"slug": slug, "titles": titles}
            for slug, titles in by_slug.items()
            if len(titles) > 1
        ],
    }


def promises(view: dict) -> dict:
    """V1's own two diagnostics about whether a module holds together.

    Recorded rather than recomputed: `capability_support` is the closest thing
    V1 has to a measurement of capability grounding, and it is computed on every
    plan read and then shown to nobody who acts on it.
    """
    support = view.get("capability_support") or []
    coherence = view.get("coherence") or []
    unbacked = sum(len(s.get("unbacked") or []) for s in support)
    clauses = sum(len(s.get("clauses") or []) for s in support)
    return {
        "capability_clauses": clauses,
        "capability_unbacked": unbacked,
        "capability_unbacked_share": round(unbacked / clauses, 3) if clauses else None,
        "capability_support": support,
        "coherence": coherence,
        "modules_with_no_internal_dependency": [
            c.get("module") for c in coherence if not c.get("internal")
        ],
        "external_dependency_total": sum(c.get("external") or 0 for c in coherence),
    }


def plan_view(view: dict, *, slugify) -> dict:
    """Everything observable about one planned project, before approval."""
    decisions = view.get("decisions") or {}
    return {
        "state": view.get("state"),
        "situation": situation(decisions),
        "landscape": landscape(decisions),
        "scope": scope(decisions),
        "partition": partition(decisions, slugify=slugify),
        "promises": promises(view),
        "extent": view.get("extent") or {},
        "feasibility": view.get("feasibility") or {},
        "decisions_present": sorted(decisions),
    }


# ---------------------------------------------------------------------------
# corrections
# ---------------------------------------------------------------------------


def correction(view: dict, said: str) -> dict:
    """One correction turn, as V1's own router reported it."""
    turn = view.get("last_turn") or {}
    return {
        "said": said,
        "reading": turn.get("reading"),
        "claimed": turn.get("claimed") or [],
        "actual": turn.get("actual") or [],
        # The router's contract, measured: decisions that changed without being
        # routed to. V1 reports this and writes them anyway.
        "unclaimed_drift": turn.get("unclaimed_drift") or [],
        "claimed_but_unchanged": turn.get("claimed_but_unchanged") or [],
        "out_of_scope": turn.get("out_of_scope"),
        "not_understood": turn.get("not_understood"),
        "landed": bool(turn.get("actual")),
    }


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------


def generation(module_title: str, index: int, result) -> dict:
    """What one module's generation produced, from V1's own GenerateResult."""
    fulfilment = result.fulfilment or {}
    report = result.representation
    units = fulfilment.get("units") or []
    return {
        "index": index,
        "module": module_title,
        "title": result.title,
        "pages": result.pages_estimate,
        "model_calls": result.calls,
        "repairs": result.repairs,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "provider": result.provider,
        "model": result.model,
        "prompt_version": result.prompt_version,
        "satisfied": fulfilment.get("satisfied"),
        "coverage": fulfilment.get("coverage"),
        "concepts_required": fulfilment.get("concepts_required") or [],
        "concepts_missing": fulfilment.get("concepts_missing") or [],
        "units_missing": fulfilment.get("units_missing") or [],
        "problems": fulfilment.get("problems") or [],
        # The comparison the treatment question turns on. V1 records both and
        # enforces neither -- and `anticipates` never reaches the generator, so
        # these are two independent judgments, not a plan and its execution.
        "treatments_anticipated": sorted(
            {t for u in units for t in (u.get("treatments_anticipated") or [])}
        ),
        "treatments_produced": sorted(
            {t for u in units for t in (u.get("treatments_produced") or [])}
        ),
        "words": sum(u.get("words") or 0 for u in units),
        "blocks": sum(u.get("blocks") or 0 for u in units),
        "departures": sum(u.get("departures") or 0 for u in units),
        "representation": {
            "pairs": [list(p) for p in report.pairs],
            "undiagnosed": report.undiagnosed,
            "unlisted": list(report.unlisted),
            "unrendered": list(report.unrendered),
            "stated_gaps": list(report.stated_gaps),
            "scale": report.scale,
            "clean": report.is_clean(),
        },
        "render_environment": dict(result.render_environment),
        "pdf": str(result.pdf_path),
    }
