"""The system's side of the contract: does the artifact deliver the approved plan?

A real run produced one of six approved units, omitted fifteen of seventeen
concepts, wrote a PDF, and reported success in green. Nothing compared the
document to the commitment, so nothing could have said otherwise.

These tests pin the property that makes the plan gate mean anything: **the
generator cannot silently omit an approved unit, or a large part of one, and
still be reported as success.** Every one of them runs without a provider --
the check is code, so it cannot itself hallucinate a pass.
"""

from __future__ import annotations

import json

import pytest

from agent.fulfilment import (
    check_document,
    check_unit,
    covers,
    requirements,
    section_text,
)
from agent.generate import _from_plan
from agent.providers import Completion

PLAN = {
    "interpret_situation": {
        "subject": "Graph algorithms",
        "purpose": "Interview preparation",
        "entry_point": "Basic DSA",
        "target_capability": "Pick the right graph algorithm",
        "capacity": None,
        "stated": [],
        "inferred": [],
    },
    "scope": {
        "covered": [
            {"concept": "BFS Traversal", "depth": "work through", "why": "core", "anticipates": "none"},
            {"concept": "DFS Traversal", "depth": "work through", "why": "core", "anticipates": "none"},
            {"concept": "Union-Find", "depth": "explain", "why": "connectivity", "anticipates": "none"},
            {
                "concept": "Dijkstra's Algorithm",
                "depth": "explain",
                "why": "weighted",
                "anticipates": "cross-reference",
            },
        ],
        "cut": [],
    },
    "partition": {
        "units": [
            {"heading": "Traversals", "covers": ["BFS Traversal", "DFS Traversal"], "why_here": "one shape"},
            {"heading": "Connectivity", "covers": ["Union-Find"], "why_here": "standalone"},
            {"heading": "Weighted", "covers": ["Dijkstra's Algorithm"], "why_here": "weights"},
        ]
    },
    "traversal": {"sequence": ["Traversals", "Connectivity", "Weighted"], "why": "simple first"},
    "consequence": {
        "exclusions": [
            {"topic": "Network flow", "consequence": "Cannot do max-flow questions.", "when_to_learn": "Later."}
        ]
    },
    "extent": {"per_unit": {"Traversals": "~4 pages"}},
}


def _section(heading: str, texts: list[str], *, kinds: list[str] | None = None) -> dict:
    blocks: list[dict] = [{"kind": "prose", "text": t} for t in texts]
    for kind in kinds or []:
        if kind == "example":
            blocks.append(
                {"kind": "example", "diagnosis": "procedure-execution", "title": "Trace", "steps": ["a", "b"]}
            )
        elif kind == "table":
            blocks.append(
                {"kind": "table", "diagnosis": "cross-reference", "headers": ["a"], "rows": [["b"]]}
            )
    return {"heading": heading, "blocks": blocks}


class Scripted:
    """Replies in order. Records what each call was asked for."""

    name, model = "stub", "stub-1"

    def __init__(self, *replies: dict | str) -> None:
        self.replies = [r if isinstance(r, str) else json.dumps(r) for r in replies]
        self.seen: list[str] = []

    def complete(self, *, system, user, schema, max_tokens) -> Completion:
        self.seen.append(user)
        return Completion(
            text=self.replies.pop(0),
            input_tokens=5,
            output_tokens=9,
            model=self.model,
            provider=self.name,
        )


# --------------------------------------------------------------------------
# Work orders: the plan, split into per-unit briefs
# --------------------------------------------------------------------------


def test_requirements_split_the_plan_into_one_order_per_unit() -> None:
    orders = requirements(PLAN)
    assert [o["heading"] for o in orders] == ["Traversals", "Connectivity", "Weighted"]
    assert [c["concept"] for c in orders[0]["concepts"]] == ["BFS Traversal", "DFS Traversal"]
    assert orders[0]["extent"] == "~4 pages"


def test_orders_follow_the_approved_order_not_the_partition_order() -> None:
    plan = {**PLAN, "traversal": {"sequence": ["Weighted", "Traversals", "Connectivity"], "why": "x"}}
    assert [o["heading"] for o in requirements(plan)] == ["Weighted", "Traversals", "Connectivity"]


def test_a_concept_in_no_unit_still_gets_an_order() -> None:
    """The plan page surfaces these as "Also covered", so the user may have
    approved one. Dropping it here would lose it silently."""
    plan = {
        **PLAN,
        "partition": {"units": [{"heading": "Traversals", "covers": ["BFS Traversal"], "why_here": "x"}]},
        "traversal": {"sequence": ["Traversals"], "why": "x"},
    }
    orders = requirements(plan)
    assert orders[-1]["heading"] == "Also covered"
    assert {c["concept"] for c in orders[-1]["concepts"]} == {
        "DFS Traversal",
        "Union-Find",
        "Dijkstra's Algorithm",
    }


# --------------------------------------------------------------------------
# Coverage: catching omission
# --------------------------------------------------------------------------


def test_a_qualifier_in_the_concept_name_is_not_owed_by_the_document() -> None:
    """"Topological Sort (Kahn's BFS)" is a note to the planner. A section that
    teaches topological sort has covered it."""
    text = section_text(_section("Ordering", ["Topological sort orders a DAG."]))
    assert covers(text, "Topological Sort (Kahn's BFS)")


def test_coverage_is_not_fooled_by_a_different_topic() -> None:
    text = section_text(_section("Traversals", ["BFS explores level by level."]))
    assert covers(text, "BFS Traversal")
    assert not covers(text, "Dijkstra's Algorithm")


def test_a_unit_that_omits_a_concept_is_not_satisfied() -> None:
    order = requirements(PLAN)[0]
    report = check_unit(order, _section("Traversals", ["BFS explores level by level."], kinds=["example"]))
    assert report.concepts_covered == ("BFS Traversal",)
    assert report.concepts_missing == ("DFS Traversal",)
    assert not report.satisfied


def test_a_unit_never_produced_is_reported_as_such() -> None:
    report = check_unit(requirements(PLAN)[0], None)
    assert not report.generated
    assert report.concepts_missing == ("BFS Traversal", "DFS Traversal")
    assert not report.satisfied


# --------------------------------------------------------------------------
# Treatments
# --------------------------------------------------------------------------


def test_treatment_is_observed_and_never_required() -> None:
    """Which treatment a concept deserves depends on artifact type, purpose and
    subject together, and that has not had its design pass. Recording what the
    plan anticipated and what the model produced gives that pass evidence;
    enforcing a rule now would fix a taxonomy by accident.

    So a unit that produces none of the anticipated treatment is still
    satisfied -- as long as it covers its concepts.
    """
    order = requirements(PLAN)[2]
    bare = check_unit(order, _section("Weighted", ["Dijkstra's Algorithm is greedy."]))

    assert bare.treatments_anticipated == ("cross-reference",)
    assert bare.treatments_produced == ()
    assert bare.depths_required == ("explain",)
    assert bare.satisfied, "treatment must not decide completeness"
    assert not hasattr(bare, "treatments_missing")


def test_treatment_observations_do_not_reach_the_documents_problems() -> None:
    orders = requirements(PLAN)
    reports = [
        check_unit(orders[0], _section("Traversals", ["BFS Traversal.", "DFS Traversal."])),
        check_unit(orders[1], _section("Connectivity", ["Union-Find tracks disjoint sets."])),
        check_unit(orders[2], _section("Weighted", ["Dijkstra's Algorithm."])),
    ]
    document = {
        "sections": [_section("Traversals", []), _section("Connectivity", []), _section("Weighted", [])]
    }
    result = check_document(PLAN, document, reports)

    assert result.satisfied, result.problems
    assert not any("treatment" in p.lower() for p in result.problems)


def test_depth_is_recorded_but_not_enforced() -> None:
    """`work through` delivered as prose only used to be a problem. Depth-to-
    treatment is exactly the mapping the design pass owns, so it is now recorded
    and left alone."""
    order = requirements(PLAN)[0]
    report = check_unit(
        order, _section("Traversals", ["BFS Traversal and DFS Traversal both visit every node."])
    )
    assert report.depths_required == ("work through",)
    assert report.departures == 0
    assert report.satisfied


# --------------------------------------------------------------------------
# The final gate
# --------------------------------------------------------------------------


def test_a_document_missing_a_whole_unit_is_not_satisfied() -> None:
    """The exact failure from the real run, at document scale."""
    orders = requirements(PLAN)
    reports = [
        check_unit(orders[0], _section("Traversals", ["BFS Traversal.", "DFS Traversal."], kinds=["example"])),
        check_unit(orders[1], None),
        check_unit(orders[2], _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"])),
    ]
    document = {"sections": [_section("Traversals", []), _section("Weighted", [])]}
    result = check_document(PLAN, document, reports)

    assert not result.satisfied
    assert result.units_missing == ("Connectivity",)
    assert "Union-Find" in result.concepts_missing
    assert any("missing" in p for p in result.problems)


def test_a_complete_document_is_satisfied() -> None:
    orders = requirements(PLAN)
    reports = [
        check_unit(orders[0], _section("Traversals", ["BFS Traversal.", "DFS Traversal."], kinds=["example"])),
        check_unit(orders[1], _section("Connectivity", ["Union-Find tracks disjoint sets."])),
        check_unit(orders[2], _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"])),
    ]
    document = {
        "sections": [_section("Traversals", []), _section("Connectivity", []), _section("Weighted", [])]
    }
    result = check_document(PLAN, document, reports)
    assert result.satisfied, result.problems
    assert result.coverage == 1.0


def test_a_section_nobody_approved_is_reported_as_a_change() -> None:
    """Agreeing to X is not agreeing to X plus whatever else seemed good."""
    orders = requirements(PLAN)
    reports = [
        check_unit(orders[0], _section("Traversals", ["BFS Traversal.", "DFS Traversal."], kinds=["example"])),
        check_unit(orders[1], _section("Connectivity", ["Union-Find tracks disjoint sets."])),
        check_unit(orders[2], _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"])),
    ]
    document = {"sections": [_section("Network Flow", ["Edmonds-Karp."])]}
    result = check_document(PLAN, document, reports)
    assert result.changed == ("Network Flow",)
    assert not result.satisfied


# --------------------------------------------------------------------------
# End to end, no provider
# --------------------------------------------------------------------------


def test_each_unit_is_generated_from_its_own_brief_not_the_whole_plan() -> None:
    """Handing every call the entire plan is what let a model wander off and
    write a different part than the one asked for."""
    provider = Scripted(
        _section("Traversals", ["BFS Traversal.", "DFS Traversal."], kinds=["example"]),
        _section("Connectivity", ["Union-Find tracks disjoint sets."]),
        _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"]),
    )
    generated = _from_plan("graph cheat sheet", PLAN, provider=provider)

    assert generated.calls == 3
    assert len(generated.document.sections) == 3
    first = provider.seen[0]
    assert "BFS Traversal" in first and "DFS Traversal" in first
    assert "Union-Find" not in first, "unit 1 was told about another unit's concepts"
    assert generated.fulfilment is not None and generated.fulfilment.satisfied


def test_a_short_unit_is_asked_again_with_the_gap_named() -> None:
    provider = Scripted(
        _section("Traversals", ["BFS Traversal only."], kinds=["example"]),
        _section("Traversals", ["BFS Traversal.", "DFS Traversal."], kinds=["example"]),
        _section("Connectivity", ["Union-Find tracks disjoint sets."]),
        _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"]),
    )
    generated = _from_plan("graph cheat sheet", PLAN, provider=provider)

    assert generated.calls == 4
    assert "DFS Traversal" in provider.seen[1]
    assert "left these out" in provider.seen[1]
    assert generated.fulfilment.satisfied


def test_a_unit_that_stays_short_survives_into_the_report() -> None:
    """The property the whole module exists for: it must be possible for the
    system to say "this is not what you approved"."""
    provider = Scripted(
        _section("Traversals", ["BFS Traversal only."], kinds=["example"]),
        _section("Traversals", ["BFS Traversal still only."], kinds=["example"]),
        _section("Connectivity", ["Union-Find tracks disjoint sets."]),
        _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"]),
    )
    generated = _from_plan("graph cheat sheet", PLAN, provider=provider)

    assert not generated.fulfilment.satisfied
    assert "DFS Traversal" in generated.fulfilment.concepts_missing
    assert generated.fulfilment.coverage < 1.0


def test_one_failing_unit_does_not_cost_the_others() -> None:
    class Flaky(Scripted):
        def complete(self, *, system, user, schema, max_tokens):
            if "Connectivity" in user:
                raise RuntimeError("provider returned nothing")
            return super().complete(system=system, user=user, schema=schema, max_tokens=max_tokens)

    provider = Flaky(
        _section("Traversals", ["BFS Traversal.", "DFS Traversal."], kinds=["example"]),
        _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"]),
    )
    generated = _from_plan("graph cheat sheet", PLAN, provider=provider)

    assert len(generated.document.sections) == 2
    assert generated.fulfilment.units_missing == ("Connectivity",)
    assert not generated.fulfilment.satisfied


def test_front_matter_comes_from_the_approved_plan_not_the_model() -> None:
    """Title, entry point and target were shown to the user and agreed. Asking a
    model to restate them lets them drift from what was approved."""
    provider = Scripted(
        _section("Traversals", ["BFS Traversal.", "DFS Traversal."], kinds=["example"]),
        _section("Connectivity", ["Union-Find tracks disjoint sets."]),
        _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"]),
    )
    doc = _from_plan("graph cheat sheet", PLAN, provider=provider).document

    assert doc.title == "Graph algorithms"
    assert doc.assumed_entry == "Basic DSA"
    assert doc.target_capability == "Pick the right graph algorithm"
    assert [g.topic for g in doc.deliberate_omissions] == ["Network flow"]


def test_the_heading_is_the_plans_not_the_models() -> None:
    """A renamed part is a part the completeness check cannot find."""
    provider = Scripted(
        _section("Traversal Techniques!", ["BFS Traversal.", "DFS Traversal."], kinds=["example"]),
        _section("Connectivity", ["Union-Find tracks disjoint sets."]),
        _section("Weighted", ["Dijkstra's Algorithm."], kinds=["table"]),
    )
    doc = _from_plan("graph cheat sheet", PLAN, provider=provider).document
    assert [s.heading for s in doc.sections] == ["Traversals", "Connectivity", "Weighted"]


def test_a_plan_with_no_units_is_refused_rather_than_half_written() -> None:
    with pytest.raises(ValueError, match="nothing to write"):
        _from_plan("x", {"scope": {"covered": []}}, provider=Scripted())


# --------------------------------------------------------------------------
# Curriculum → modules
# --------------------------------------------------------------------------

CURRICULUM = {
    "interpret_situation": {
        "subject": "Agentic AI",
        "purpose": "Interview preparation",
        "entry_point": "Nothing",
        "target_capability": "Build and talk about agentic systems",
        "capacity": None,
        "stated": [],
        "inferred": [],
    },
    "scope": {
        "covered": [
            {"concept": "Chat Completions API", "depth": "work through", "why": "x", "anticipates": "none"},
            {"concept": "Retrieval basics", "depth": "explain", "why": "x", "anticipates": "none"},
            {"concept": "Chunking strategies", "depth": "explain", "why": "x", "anticipates": "none"},
        ],
        "cut": [],
    },
    "partition": {
        "modules": [
            {
                "title": "LLM API Foundations",
                "covers": ["Chat Completions API"],
                "why_here": "Everything else calls a model.",
                "capability": "Call a model from your own code and shape its output.",
            },
            {
                "title": "RAG Fundamentals",
                "covers": ["Retrieval basics", "Chunking strategies"],
                "why_here": "One pipeline.",
                "capability": "Build a retrieval pipeline over your own documents.",
            },
        ]
    },
    "traversal": {"sequence": ["LLM API Foundations", "RAG Fundamentals"], "why": "APIs first."},
    "consequence": {"exclusions": []},
    "extent": {"per_unit": {"LLM API Foundations": "~8 pages"}},
}


def test_work_orders_come_from_modules() -> None:
    orders = requirements(CURRICULUM)
    assert [o["heading"] for o in orders] == ["LLM API Foundations", "RAG Fundamentals"]
    assert [c["concept"] for c in orders[1]["concepts"]] == [
        "Retrieval basics",
        "Chunking strategies",
    ]


def test_a_legacy_plan_still_opens() -> None:
    """17 stored projects have `partition.units` — sections of one document,
    written before the curriculum layer. They must keep working, and they are
    not silently re-read as modules."""
    legacy = {
        **CURRICULUM,
        "partition": {
            "units": [
                {"heading": "One", "covers": ["Chat Completions API"], "why_here": "x"},
            ]
        },
        "traversal": {"sequence": ["One"], "why": "x"},
    }
    orders = requirements(legacy)
    assert [o["heading"] for o in orders] == ["One", "Also covered"]


def test_a_curriculum_refuses_to_be_written_as_one_document() -> None:
    """Several modules is several PDFs. One document with a thin section per
    module is not the artifact the plan promised, and producing it would be the
    generator committing the exact failure fulfilment.py exists to prevent."""
    with pytest.raises(ValueError, match="curriculum of 2 modules"):
        _from_plan("agentic ai notes", CURRICULUM, provider=Scripted())


def test_a_single_module_plan_generates_normally() -> None:
    """One module is a document, not a curriculum of one."""
    single = {
        **CURRICULUM,
        "scope": {"covered": CURRICULUM["scope"]["covered"][1:], "cut": []},
        "partition": {"modules": [CURRICULUM["partition"]["modules"][1]]},
        "traversal": {"sequence": ["RAG Fundamentals"], "why": "x"},
    }
    provider = Scripted(
        _section("RAG Fundamentals", ["Retrieval basics.", "Chunking strategies matter."])
    )
    generated = _from_plan("rag notes", single, provider=provider)
    assert [s.heading for s in generated.document.sections] == ["RAG Fundamentals"]
    assert generated.fulfilment.satisfied
