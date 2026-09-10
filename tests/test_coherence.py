"""Dependency structure laid over modules — evidence, never a rule.

The analysis exists because it was legible where prose was not: one module in
the agentic-AI plan had 12 concepts and a single internal dependency, and the
per-concept links showed it was three things wearing one title.

These tests pin what it reports and, just as importantly, that it reports rather
than judges. A threshold here would decide the granularity question that has not
been answered — and would decide it wrongly for a comparison module and for a
capstone, both of which are zero by construction.
"""

from __future__ import annotations

from agent.coherence import analyse

STRUCTURE = {
    "concepts": [
        {"name": "Core loop", "built_from": []},
        {"name": "Tool use", "built_from": ["Core loop"]},
        {"name": "ReAct", "built_from": ["Core loop", "Tool use"]},
        {"name": "LangGraph", "built_from": ["Core loop"]},
        {"name": "CrewAI", "built_from": ["Core loop"]},
        {"name": "Cost optimisation", "built_from": ["Core loop"]},
    ]
}

PARTITION = {
    "modules": [
        {
            "title": "Foundations",
            "covers": ["Core loop", "Tool use", "ReAct"],
            "why_here": "One chain.",
            "capability": "Explain and build a single agent loop.",
        },
        {
            "title": "Frameworks",
            "covers": ["LangGraph", "CrewAI"],
            "why_here": "A comparison.",
            "capability": "Pick a framework and justify it against alternatives.",
        },
        {
            "title": "Production",
            "covers": ["Cost optimisation"],
            "why_here": "Running it.",
            "capability": "Run an agent within a cost budget.",
        },
    ]
}


def _by_module(reports):
    return {r.module: r for r in reports}


def test_a_chain_reports_internal_dependencies() -> None:
    r = _by_module(analyse(STRUCTURE, PARTITION))["Foundations"]
    assert (r.internal, r.external) == (3, 0)
    assert r.ratio == 1.0


def test_a_comparison_module_is_zero_by_construction_and_that_is_not_a_fault() -> None:
    """Frameworks that do not build on each other are what makes them
    comparable. Nothing in this module may treat that as a defect."""
    r = _by_module(analyse(STRUCTURE, PARTITION))["Frameworks"]
    assert (r.internal, r.external) == (0, 2)
    assert r.ratio == 0.0
    assert dict(r.depends_on_modules) == {"Foundations": 2}


def test_external_links_name_the_concept_and_where_it_lives() -> None:
    """The per-link detail is what showed that six "failure modes" each depended
    on exactly the concept they were the failure of."""
    r = _by_module(analyse(STRUCTURE, PARTITION))["Production"]
    external = [l for l in r.links if l.external]
    assert [(l.concept, l.depends_on, l.lives_in) for l in external] == [
        ("Cost optimisation", "Core loop", "Foundations")
    ]


def test_a_dependency_outside_the_plan_is_not_a_boundary_crossing() -> None:
    """A concept built from something no module covers was cut upstream. That is
    a scope fact, not a partition one."""
    structure = {"concepts": [{"name": "Core loop", "built_from": ["Transformers"]}]}
    partition = {
        "modules": [
            {"title": "Foundations", "covers": ["Core loop"], "why_here": "x", "capability": "y"}
        ]
    }
    r = analyse(structure, partition)[0]
    assert (r.internal, r.external) == (0, 0)
    assert r.ratio is None


def test_it_reports_no_verdict() -> None:
    """Evidence, not a rule. If a `satisfied`, `ok`, `coherent` or threshold ever
    appears here, a granularity decision has been made by accident."""
    r = _by_module(analyse(STRUCTURE, PARTITION))["Frameworks"]
    for forbidden in ("satisfied", "ok", "coherent", "problems", "threshold", "verdict"):
        assert not hasattr(r, forbidden), f"{forbidden} would make this a rule"
    assert set(r.to_json()) == {
        "module", "concepts", "internal", "external", "ratio",
        "depends_on_modules", "links",
    }


def test_absent_or_legacy_inputs_yield_no_evidence_rather_than_an_error() -> None:
    assert analyse(None, PARTITION) == []
    assert analyse(STRUCTURE, None) == []
    assert analyse(STRUCTURE, {"units": [{"heading": "x", "covers": [], "why_here": "y"}]}) == []


# --------------------------------------------------------------------------
# Is the capability backed by the concepts in scope?
# --------------------------------------------------------------------------

from agent.coherence import capability_support


def _module(title, covers, capability):
    return {"modules": [{"title": title, "covers": covers, "why_here": "x", "capability": capability}]}


def test_the_rag_case_reports_its_unbacked_claims() -> None:
    """The real one. Three claims over a scope of one concept, in a graph that
    contained no other retrieval concept at all — the reader is promised
    distinctions and techniques the module cannot deliver."""
    partition = _module(
        "Agentic RAG & Retrieval",
        ["RAG for Agents (Agentic RAG)"],
        "Explain how agentic RAG differs from passive RAG; design iterative "
        "retrieval loops with query reformulation; compare tool-augmented "
        "retrieval strategies.",
    )
    r = capability_support(partition)[0]
    assert len(r.clauses) == 3
    assert len(r.unbacked) == 2
    assert all("retrieval" in c for c in r.unbacked)
    assert r.backed[0][1] == ("RAG for Agents (Agentic RAG)",)


def test_a_capability_its_concepts_do_support_is_not_flagged() -> None:
    partition = _module(
        "LLM Foundations",
        ["LLM Fundamentals", "Tool Use & Function Calling"],
        "Explain how LLMs enable agency; design function-calling schemas.",
    )
    assert capability_support(partition)[0].unbacked == ()


def test_capability_verbs_do_not_count_as_support() -> None:
    """Every capability is full of "design", "compare", "explain". A word that
    matches every concept equally is evidence for none of them — the same
    failure `_discriminating` guards against in sufficiency.py."""
    partition = _module(
        "Frameworks", ["Design Patterns"], "Design and compare and explain things."
    )
    r = capability_support(partition)[0]
    assert r.unbacked == ("Design and compare and explain things.",)


def test_commas_inside_a_list_are_not_claim_boundaries() -> None:
    """Splitting on commas turned "maturity" and "shared memory)" into clauses
    and reported them unbacked — noise dressed as a finding."""
    partition = _module(
        "Frameworks",
        ["Major Frameworks (LangGraph, AutoGen, CrewAI)"],
        "Compare LangGraph, AutoGen, and CrewAI on state, multi-agent support, and maturity.",
    )
    r = capability_support(partition)[0]
    assert len(r.clauses) == 1
    assert r.unbacked == ()


def test_it_reports_no_verdict_either() -> None:
    r = capability_support(_module("M", ["C"], "Explain C."))[0]
    for forbidden in ("satisfied", "ok", "problems", "threshold", "verdict", "score"):
        assert not hasattr(r, forbidden), f"{forbidden} would make this a rule"
    assert set(r.to_json()) == {"module", "clauses", "backed", "unbacked"}


def test_a_module_with_no_capability_yields_nothing_rather_than_a_complaint() -> None:
    r = capability_support(_module("M", ["C"], ""))[0]
    assert r.clauses == () and r.unbacked == ()
    assert capability_support({"units": []}) == []
    assert capability_support(None) == []
