"""The seam: an approved plan reaching the generator, and a client watching it.

Before this, `approve()` wrote a commitment nothing downstream read and
`/generate` took a raw string that had never been through a gate -- two working
halves that did not meet. These tests pin the join, and they pin it without a
model: the brief is built by pure code from a snapshot, and the job runner is a
thread with a status.
"""

from __future__ import annotations

import time

import pytest

from agent.generate import _brief
from backend.jobs import Jobs
from engine.render import render_html
from engine.sample import BLOCK_KINDS, RELATIONS, sample_document

SNAPSHOT = {
    "interpret_situation": {
        "subject": "The human digestive system",
        "purpose": "Class 11 biology exam",
        "entry_point": "Has read the chapter once",
        "target_capability": "Trace a meal through the canal",
        "capacity": None,
        "stated": ["include diagrams where they help"],
        "inferred": [],
    },
    "scope": {
        "covered": [
            {"concept": "Alimentary canal", "depth": "explain", "why": "The spine of it."},
            {"concept": "Villi", "depth": "work through", "why": "Absorption happens here."},
            {"concept": "Bile", "depth": "mention", "why": "Context for fat digestion."},
        ],
        "cut": ["Comparative anatomy"],
    },
    "partition": {
        "units": [
            {"heading": "The canal", "covers": ["Alimentary canal"], "why_here": "Orientation."},
            {"heading": "Absorption", "covers": ["Villi", "Bile"], "why_here": "One mechanism."},
        ]
    },
    "traversal": {"sequence": ["Absorption", "The canal"], "why": "Mechanism first."},
    "consequence": {
        "exclusions": [
            {
                "topic": "Comparative anatomy",
                "consequence": "Cannot answer cross-species questions.",
                "when_to_learn": "If the syllabus adds it.",
            }
        ]
    },
    "extent": {"pages": "~12 pages", "study_time": "about 3 hours"},
}


# --------------------------------------------------------------------------
# The brief: what the approved plan becomes
# --------------------------------------------------------------------------


def test_brief_carries_every_covered_concept_with_its_depth() -> None:
    """A concept dropped between approval and writing is a broken promise the
    reader cannot see. It has to reach the model to be written."""
    brief = _brief("notes on digestion", SNAPSHOT)
    for concept, depth in (
        ("Alimentary canal", "explain"),
        ("Villi", "work through"),
        ("Bile", "mention"),
    ):
        assert concept in brief
        assert f"{concept} — treat at depth: {depth}" in brief


def test_brief_follows_the_approved_order_not_the_partition_order() -> None:
    """`traversal` is its own approved decision. Rebuilding order from
    `partition` alone would silently discard it."""
    brief = _brief("notes on digestion", SNAPSHOT)
    assert brief.index("### Absorption") < brief.index("### The canal")


def test_brief_states_exclusions_as_forbidden_and_as_marked_gaps() -> None:
    brief = _brief("notes on digestion", SNAPSHOT)
    assert "do not cover" in brief.lower()
    assert "Comparative anatomy" in brief
    assert "Cannot answer cross-species questions." in brief
    assert "deliberate_omissions" in brief


def test_brief_carries_the_situation_and_what_they_asked_for() -> None:
    brief = _brief("notes on digestion", SNAPSHOT)
    assert "Has read the chapter once" in brief
    assert "include diagrams where they help" in brief
    assert "~12 pages" in brief


def test_brief_survives_a_thin_snapshot() -> None:
    """A plan can be approved with decisions missing; the brief must degrade
    rather than raise, because raising here loses an approved plan."""
    assert _brief("notes on x", {}).startswith("The learner asked for: notes on x")


def test_a_concept_in_no_unit_still_reaches_the_document() -> None:
    """`compose.ts` surfaces orphaned concepts on the plan page, so the user may
    have approved one. It must not vanish on the way to the writer."""
    snapshot = {
        **SNAPSHOT,
        "partition": {"units": [{"heading": "The canal", "covers": ["Alimentary canal"], "why_here": "x"}]},
        "traversal": {"sequence": ["The canal"], "why": "x"},
    }
    brief = _brief("notes", snapshot)
    assert "Villi" in brief and "Bile" in brief


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------


def _settle(jobs: Jobs, key: str, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = jobs.get(key)
        if job is not None and job.state != "running":
            return job
        time.sleep(0.01)
    raise AssertionError(f"job {key} never settled")


def test_a_job_carries_its_result() -> None:
    jobs = Jobs()
    jobs.start("p1", lambda: "a pdf")
    assert _settle(jobs, "p1").result == "a pdf"


def test_a_failing_job_reports_rather_than_disappears() -> None:
    """The free provider returns empty bodies. A generation that dies must say
    so, or the client polls forever against a job that will never finish."""
    jobs = Jobs()
    jobs.start("p2", lambda: (_ for _ in ()).throw(ValueError("produced invalid output twice")))
    job = _settle(jobs, "p2")
    assert job.state == "failed"
    assert "invalid output twice" in (job.error or "")
    assert job.detail and "ValueError" in job.detail


def test_starting_a_running_job_twice_does_not_run_it_twice() -> None:
    """A double-click must not spend two model calls."""
    calls: list[int] = []
    jobs = Jobs()

    def slow() -> str:
        calls.append(1)
        time.sleep(0.2)
        return "done"

    jobs.start("p3", slow)
    jobs.start("p3", slow)
    _settle(jobs, "p3")
    assert calls == [1]


def test_a_finished_job_can_be_forgotten_and_run_again() -> None:
    jobs = Jobs()
    jobs.start("p4", lambda: 1)
    _settle(jobs, "p4")
    jobs.forget("p4")
    assert jobs.get("p4") is None


# --------------------------------------------------------------------------
# Coverage: the template must draw what the document says
# --------------------------------------------------------------------------


def test_sample_document_exercises_every_block_kind() -> None:
    """The fixture is only evidence if it actually contains the vocabulary."""
    doc = sample_document()
    present = {b["kind"] for s in doc["sections"] for b in s["blocks"]}
    assert present == set(BLOCK_KINDS)

    relations = {
        b["relation"] for s in doc["sections"] for b in s["blocks"] if b["kind"] == "relation"
    }
    assert relations == set(RELATIONS)


def test_sample_document_matches_the_real_contract() -> None:
    """A fixture that drifts from `Document` tests a shape the system never
    produces. Templates render under StrictUndefined, where that is a crash."""
    from agent.contracts import Document

    Document.model_validate(sample_document())


@pytest.mark.parametrize("template_id", ["study-notes"])
def test_the_default_template_draws_the_whole_vocabulary(template_id: str) -> None:
    """`study-notes` silently dropped four kinds, `relation` among them -- the
    default template could not draw a diagram at all. Rendering the fixture is
    what catches that; nothing else did.

    Only the default is pinned here. The other three templates cannot draw
    `is-part-of`, `causes` or `associates-with`, and hand-fixing three bespoke
    templates is the duplicated work Design-Library.md exists to remove.
    """
    html = render_html(sample_document(), template_id=template_id)
    assert 'class="unrendered"' not in html


def test_each_relation_gets_its_own_geometry_in_the_default_template() -> None:
    """Rev. 3 §2: honesty is a property of (relation, geometry). Two relations
    sharing one geometry is how a stack drew containment and sequence alike and
    one of them was false. `causes` and `precedes` especially: sharing there
    collapses order into causation.
    """
    html = render_html(sample_document(), template_id="study-notes")
    realizations = {}
    for relation in RELATIONS:
        marker = f'data-relation="{relation}"\n              data-realization="'
        flat = html.replace("\n", " ").replace("  ", " ")
        needle = f'data-relation="{relation}" data-realization="'
        assert needle in flat, f"{relation} was not drawn"
        realizations[relation] = flat.split(needle, 1)[1].split('"', 1)[0]

    assert realizations["precedes"] != realizations["causes"]
    assert len(set(realizations.values())) >= 4, realizations
