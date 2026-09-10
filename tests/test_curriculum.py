"""Reading an approved curriculum one module at a time.

The user generates modules on demand, not as a batch. Each becomes its own PDF
through the existing per-part generation and fulfilment pipeline, and the
approved plan is the source of truth throughout: writing module 4 must not be
able to change what module 5 was approved to contain.
"""

from __future__ import annotations

import copy

import pytest

from agent.curriculum import modules, plan_for

CURRICULUM = {
    "interpret_situation": {
        "subject": "Agentic AI",
        "job": "orient",
        "purpose": "Interview preparation",
        "entry_point": "No prior knowledge",
        "target_capability": "Answer interview questions about agentic AI",
        "capacity": None,
        "stated": [],
        "inferred": [],
    },
    "scope": {
        "covered": [
            {"concept": "Tool Use", "depth": "work through", "why": "core", "anticipates": "none"},
            {"concept": "ReAct", "depth": "work through", "why": "canonical", "anticipates": "none"},
            {"concept": "LangGraph", "depth": "explain", "why": "industry standard", "anticipates": "none"},
            {"concept": "CrewAI", "depth": "explain", "why": "role-based", "anticipates": "none"},
        ],
        "cut": [],
    },
    "partition": {
        "modules": [
            {
                "title": "Core Agent Patterns",
                "covers": ["Tool Use", "ReAct"],
                "why_here": "How an agent thinks and acts.",
                "capability": "Explain the thought-action-observation loop and tool calling.",
            },
            {
                "title": "Frameworks",
                "covers": ["LangGraph", "CrewAI"],
                "why_here": "A comparison.",
                "capability": "Compare frameworks and justify a choice.",
            },
        ]
    },
    "traversal": {"sequence": ["Core Agent Patterns", "Frameworks"], "why": "patterns first"},
    "consequence": {
        "exclusions": [
            {"topic": "Network flow", "consequence": "x", "when_to_learn": "later"}
        ]
    },
    "extent": {"per_unit": {"Core Agent Patterns": "~6 pages", "Frameworks": "~4 pages"}},
}


def test_modules_come_back_in_the_approved_order() -> None:
    got = modules(CURRICULUM)
    assert [(m.index, m.title) for m in got] == [
        (1, "Core Agent Patterns"),
        (2, "Frameworks"),
    ]
    assert got[0].concepts == ("Tool Use", "ReAct")
    assert got[0].extent == "~6 pages"
    assert got[1].capability == "Compare frameworks and justify a choice."


def test_traversal_decides_the_order_not_the_partition_list() -> None:
    plan = {**CURRICULUM, "traversal": {"sequence": ["Frameworks", "Core Agent Patterns"], "why": "x"}}
    assert [m.title for m in modules(plan)] == ["Frameworks", "Core Agent Patterns"]


def test_a_plan_without_modules_is_one_module() -> None:
    """Plans written before the curriculum layer were always a single document.
    Returning one module means the client has one shape to render, not two."""
    legacy = {
        **CURRICULUM,
        "partition": {"units": [{"heading": "All of it", "covers": ["Tool Use"], "why_here": "x"}]},
        "traversal": {"sequence": ["All of it"], "why": "x"},
    }
    got = modules(legacy)
    assert len(got) == 1
    assert got[0].title == "Agentic AI"
    assert len(got[0].concepts) == 4, "the whole plan's scope, not one unit's"


def test_a_module_plan_carries_only_that_modules_concepts() -> None:
    scoped = plan_for(CURRICULUM, 2)
    assert [c["concept"] for c in scoped["scope"]["covered"]] == ["LangGraph", "CrewAI"]
    assert "Tool Use" not in str(scoped)


def test_each_concept_becomes_a_section() -> None:
    """Decision 10 is not a planned decision yet. One section per approved
    concept is the smallest mapping that needs no new rule, and it lets the
    existing per-part pipeline verify each section against its concept."""
    scoped = plan_for(CURRICULUM, 1)
    assert [u["heading"] for u in scoped["partition"]["units"]] == ["Tool Use", "ReAct"]
    assert scoped["traversal"]["sequence"] == ["Tool Use", "ReAct"]
    assert not scoped["partition"].get("modules"), "a module plan is not itself a curriculum"


def test_the_module_titles_the_document_and_its_capability_is_the_target() -> None:
    scoped = plan_for(CURRICULUM, 2)
    situation = scoped["interpret_situation"]
    assert situation["subject"] == "Frameworks"
    assert situation["target_capability"] == "Compare frameworks and justify a choice."
    assert situation["entry_point"] == "No prior knowledge", (
        "entry point stays the curriculum's — adjusting it per module is "
        "predecessor handling, which is deliberately not here"
    )


def test_curriculum_exclusions_do_not_repeat_in_every_module() -> None:
    """They belong to the curriculum. Repeating them in every PDF tells the
    reader the same thing N times and implies each module owns the omission."""
    assert plan_for(CURRICULUM, 1)["consequence"]["exclusions"] == []


def test_deriving_a_module_plan_never_mutates_the_approved_plan() -> None:
    """The approved curriculum is the source of truth. Writing module 1 must not
    be able to change what module 2 was approved to contain."""
    before = copy.deepcopy(CURRICULUM)
    plan_for(CURRICULUM, 1)
    plan_for(CURRICULUM, 2)
    assert CURRICULUM == before


def test_an_unknown_module_is_refused_rather_than_guessed() -> None:
    with pytest.raises(ValueError, match="no module 9"):
        plan_for(CURRICULUM, 9)


def test_a_module_covering_nothing_approved_is_refused() -> None:
    plan = copy.deepcopy(CURRICULUM)
    plan["partition"]["modules"][0]["covers"] = ["Something never approved"]
    with pytest.raises(ValueError, match="covers no approved concept"):
        plan_for(plan, 1)


def test_a_module_plan_generates_through_the_existing_pipeline() -> None:
    """The point of scoping to a plan shape: nothing in generation needs to know
    a curriculum exists."""
    import json

    from agent.generate import _from_plan
    from agent.providers import Completion

    class Scripted:
        name, model = "stub", "stub-1"

        def __init__(self, *replies):
            self.replies = list(replies)
            self.seen: list[str] = []

        def complete(self, *, system, user, schema, max_tokens):
            self.seen.append(user)
            return Completion(
                text=json.dumps(self.replies.pop(0)),
                input_tokens=1, output_tokens=1,
                model=self.model, provider=self.name,
            )

    scoped = plan_for(CURRICULUM, 2)
    provider = Scripted(
        {"heading": "LangGraph", "blocks": [{"kind": "prose", "text": "LangGraph is a graph runtime."}]},
        {"heading": "CrewAI", "blocks": [{"kind": "prose", "text": "CrewAI is role-based."}]},
    )
    generated = _from_plan("agentic ai notes", scoped, provider=provider)

    assert generated.document.title == "Frameworks"
    assert [s.heading for s in generated.document.sections] == ["LangGraph", "CrewAI"]
    assert generated.fulfilment.satisfied
    assert "CrewAI" not in provider.seen[0], "each section's brief carries only its own concept"


def test_a_module_carries_the_depth_each_concept_was_approved_at() -> None:
    """`partition` says which module a concept landed in; `scope` says how deep
    it goes. Joined here so a client can show what a module contains without
    re-deriving it from the plan -- the generation screen used to list the
    modules and then render the whole plan underneath, which is the same
    modules a second time, built from *current* decisions rather than from the
    approved snapshot."""
    module = modules(CURRICULUM)[1]

    assert module.title == "Frameworks"
    assert [(c.concept, c.depth) for c in module.coverage] == [
        (name, next(
            row["depth"]
            for row in CURRICULUM["scope"]["covered"]
            if row["concept"] == name
        ))
        for name in module.concepts
    ]
    assert all(c.why for c in module.coverage), "the reason travels with the depth"
    assert module.to_json()["coverage"][0]["concept"] == module.concepts[0]


def test_a_concept_missing_from_scope_is_absent_rather_than_guessed() -> None:
    """A module may name a concept the plan never scoped. It stays in
    `concepts` -- that is what was approved -- but it cannot claim a depth
    nobody chose."""
    import copy

    plan = copy.deepcopy(CURRICULUM)
    plan["partition"]["modules"][0]["covers"].append("Never scoped")

    module = modules(plan)[0]

    assert "Never scoped" in module.concepts
    assert "Never scoped" not in [c.concept for c in module.coverage]
    assert len(module.coverage) == len(module.concepts) - 1

