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


# ---------------------------------------------------------------------------
# The Project as the durable object: what survives a restart, and what comes
# out of it in one download.
#
# Both go through the HTTP surface, because both failures were surface
# failures: a reopened project reported a bare "done" for work it had fully
# described on disk, and there was no way to get a curriculum out except one
# PDF at a time.
# ---------------------------------------------------------------------------

CURRICULUM = {
    "interpret_situation": {"subject": "Human digestion", "purpose": "Class 11"},
    "scope": {
        "covered": [
            {"concept": "Alimentary canal", "depth": "explain", "why": "The spine of it."},
            {"concept": "Villi", "depth": "work through", "why": "Absorption."},
        ],
        "cut": [],
    },
    "partition": {
        "modules": [
            {
                "title": "The canal",
                "covers": ["Alimentary canal"],
                "why_here": "Orientation.",
                "capability": "Trace a meal.",
            },
            {
                "title": "Absorption",
                "covers": ["Villi"],
                "why_here": "One mechanism.",
                "capability": "Explain uptake.",
            },
        ]
    },
    "traversal": {"sequence": ["The canal", "Absorption"], "why": "Order."},
    "extent": {"per_unit": {"The canal": "~4 pages", "Absorption": "~3 pages"}},
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A live API over a temp store and a temp artifact directory.

    `JOBS` is left empty on purpose: an empty job table is exactly what a
    restarted server has, so every assertion below is about what the Project
    can reconstruct from disk alone.
    """
    from fastapi.testclient import TestClient

    from backend import api, service
    from backend.planning import PlanService
    from backend.store import Commitment, Decision, FileStore, commit_hash

    monkeypatch.setattr(service, "OUT", tmp_path / "out")
    plans = PlanService(FileStore(tmp_path / "projects"))
    monkeypatch.setattr(api, "_plans", plans)
    api.JOBS._jobs.clear()

    project = plans.store.create_project("local", title="notes on human digestion")
    plans.store.add_utterance(project.id, "user", "notes on human digestion")
    # The decision rows, not just the commitment: approval snapshots decisions
    # that already exist, and the displayed title is derived from them. A
    # fixture with a commitment and no decisions is a project that cannot
    # happen.
    for kind, output in CURRICULUM.items():
        plans.store.put_decision(
            Decision(
                id=f"d-{kind}",
                project_id=project.id,
                kind=kind,
                status="committed",
                freshness="current",
                inputs_hash="h",
                output=output,
            )
        )
    plans.store.add_commitment(
        Commitment(
            id="c1",
            project_id=project.id,
            kind="plan",
            snapshot=CURRICULUM,
            decision_ids=["d1"],
            decision_ids_hash=commit_hash(["d1"]),
            decision_environment={},
            approved_by=None,
        )
    )
    return TestClient(api.app), project.id, tmp_path / "out" / "artifacts" / project.id


def _write_module(artifacts, title, *, pages=3, satisfied=True):
    """A generated module, as `service.generate` leaves it on disk."""
    import json

    from backend.service import slugify

    artifacts.mkdir(parents=True, exist_ok=True)
    stem = slugify(title)
    (artifacts / f"{stem}.pdf").write_bytes(
        b"%PDF-1.4\n/Type /Pages\n" + b"/Type /Page\n" * pages
    )
    (artifacts / f"{stem}.report.json").write_text(
        json.dumps(
            {
                "title": title,
                "calls": 3,
                "stated_gaps": ["a diagram we could not draw"],
                "unrendered": [],
                "fulfilment": {
                    "satisfied": satisfied,
                    "coverage": 1.0,
                    "units_approved": ["x"],
                    "units_generated": ["x"],
                    "concepts_required": ["x"],
                    "concepts_covered": ["x"],
                    "problems": [],
                    "units": [],
                },
            }
        ),
        encoding="utf-8",
    )


def test_a_reopened_project_remembers_what_it_produced(client) -> None:
    """The restart case. `service.generate` has always written a report sidecar
    beside every PDF and nothing ever read it, so page count, cost and the
    fulfilment check lived only in the in-memory job and died with the process:
    reopening a project showed a bare "done" for work the system had fully
    described on disk."""
    api_client, project_id, artifacts = client
    _write_module(artifacts, "The canal", pages=7)

    modules = api_client.get(f"/projects/{project_id}/modules").json()["modules"]
    written, pending = modules[0], modules[1]

    assert written["state"] == "done"
    assert written["pages"] == 7
    assert written["calls"] == 3
    assert written["satisfied"] is True
    assert written["fulfilment"]["coverage"] == 1.0
    assert written["representation"]["stated_gaps"] == ["a diagram we could not draw"]
    # The module nobody has written stays plainly un-written.
    assert pending["state"] == "idle"
    assert "pages" not in pending


def test_a_module_without_its_sidecar_is_still_done(client) -> None:
    """The PDF is the record. An older or interrupted run may have no sidecar,
    and that must not demote finished work back to `idle`."""
    api_client, project_id, artifacts = client
    _write_module(artifacts, "The canal")
    (artifacts / "the-canal.report.json").unlink()

    modules = api_client.get(f"/projects/{project_id}/modules").json()["modules"]

    assert modules[0]["state"] == "done"
    assert modules[0]["pages"] == 3
    assert modules[0].get("fulfilment") is None


def test_the_index_counts_what_is_written(client) -> None:
    api_client, project_id, artifacts = client
    row = api_client.get("/projects").json()[0]
    assert (row["modules_done"], row["modules_total"]) == (0, 2)
    assert row["title"] == "Human digestion"
    assert row["query"] == "notes on human digestion"

    _write_module(artifacts, "The canal")
    row = api_client.get("/projects").json()[0]
    assert (row["modules_done"], row["modules_total"]) == (1, 2)


def test_export_carries_the_written_modules_in_curriculum_order(client) -> None:
    """A curriculum is several PDFs, and fetching 25 of them one at a time is
    not a download. The `NN-` prefix exists only inside the archive: on disk a
    module's PDF is named from its title with no ordering, so unzipping would
    otherwise present the curriculum alphabetically -- the one order the plan
    explicitly decided against."""
    import io
    import zipfile

    api_client, project_id, artifacts = client
    # Written out of order, to prove the archive follows the plan and not the
    # filesystem.
    _write_module(artifacts, "Absorption")
    _write_module(artifacts, "The canal")

    response = api_client.get(f"/projects/{project_id}/export.zip")

    assert response.status_code == 200
    assert response.headers["x-modules-written"] == "2"
    assert response.headers["x-modules-total"] == "2"
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert names == [
        "human-digestion/01-the-canal.pdf",
        "human-digestion/02-absorption.pdf",
        "human-digestion/plan.json",
    ]


def test_export_includes_only_what_exists(client) -> None:
    import io
    import zipfile

    api_client, project_id, artifacts = client
    _write_module(artifacts, "Absorption")

    response = api_client.get(f"/projects/{project_id}/export.zip")

    assert response.headers["x-modules-written"] == "1"
    assert response.headers["x-modules-total"] == "2"
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert "human-digestion/02-absorption.pdf" in names
    assert not any("the-canal" in n for n in names)


def test_export_refuses_an_empty_project(client) -> None:
    """An empty zip is a download that looks like it worked."""
    api_client, project_id, _ = client

    response = api_client.get(f"/projects/{project_id}/export.zip")

    assert response.status_code == 409
    assert "no module of this project has been written" in response.json()["detail"]

