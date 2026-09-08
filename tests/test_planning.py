"""The plan loop, without a model.

The milestone's claims are properties of the loop, not of the prompt: that a
correction changes only what it routed to, that upstream faults reach upstream
decisions, that presentation is deferred rather than absorbed, and that approval
is idempotent. Those are tested against a stub provider — real generations are
slow, paid, and cannot be made to produce the exact divergence a regression needs.
"""

from __future__ import annotations

import json

import pytest

from agent.plan import (
    ALL_DECISIONS,
    INTERACTION_DECISIONS,
    PLAN_DECISIONS,
    UPSTREAM_DECISIONS,
    Partition,
    Scope,
    derive_extent,
)
from agent.providers import Completion
from backend.planning import PlanService
from backend.store import FileStore, commit_hash


# --- fixtures ---------------------------------------------------------------

REQUEST = "i need to revise human evolution for NEET"


def _axis(axis, value="v", source="inferred", quote="NEET", material="no_effect"):
    """A reading whose span really resolves against REQUEST."""
    return {
        "axis": axis,
        "value": value,
        "source": source,
        "supported_by": [] if source == "unknown" else [{"utterance_ord": 0, "quote": quote}],
        "would_differ": "a different plan",
        "materiality": material,
    }


AXES_SUFFICIENT = [
    _axis("subject", "Human evolution", "stated", "human evolution"),
    _axis("purpose", "NEET", "inferred", "NEET"),
    _axis("entry_point", "Class 11 biology", "inferred", "revise"),
    _axis("target_capability", "Answer NEET questions", "inferred", "NEET"),
    _axis("capacity", None, "unknown"),
    _axis("depth_register", None, "unknown"),
    _axis("artifact_type", None, "unknown"),
    _axis("template", None, "unknown"),
]

SITUATION = {
    "subject": "Human evolution",
    "job": "rehearse",
    "entry_point": "Class 11 biology",
    "purpose": "NEET",
    "target_capability": "Sequence hominin forms and name their traits.",
    "capacity": None,
    "stated": ["NEET syllabus only"],
    "inferred": ["Assumed the written exam, not the practical."],
}

READING_SUFFICIENT = {
    "interpret_situation": SITUATION,
    "axes": AXES_SUFFICIENT,
    "proposed_questions": [],
}

QUESTION = {
    "axis": "target_capability",
    "question": "What do you want to be able to do afterwards?",
    "why_it_matters": "Recall and application need different depth.",
    "options": [
        {"label": "Answer MCQs", "implication": "Facts and discriminators, no derivations."},
        {"label": "Understand deeply", "implication": "Mechanisms worked through."},
    ],
    "default_label": "Answer MCQs",
}

READING_ASKING = {
    "interpret_situation": SITUATION,
    "axes": [
        a
        if a["axis"] != "target_capability"
        else _axis("target_capability", None, "unknown", material="changes_the_plan")
        for a in AXES_SUFFICIENT
    ],
    "proposed_questions": [QUESTION],
}

LANDSCAPE = {
    "derive_structure": {
        "concepts": [
            {"name": "Primate lineage", "built_from": []},
            {"name": "Australopithecus", "built_from": ["Primate lineage"]},
            {"name": "Homo erectus", "built_from": ["Australopithecus"]},
        ]
    },
    "relevance": {
        "judgements": [
            {"concept": "Primate lineage", "in_play": True, "why": "Places humans."},
            {"concept": "Australopithecus", "in_play": True, "why": "Named-fossil staple."},
            {"concept": "Homo erectus", "in_play": True, "why": "NEET staple."},
        ]
    },
}

PLAN = {
    "scope": {
        "covered": [
            {"concept": "Primate lineage", "depth": "explain", "why": "Anchors the rest.",
             "anticipates": "none"},
            {"concept": "Australopithecus", "depth": "explain", "why": "Transition genus.",
             "anticipates": "none"},
            {"concept": "Homo erectus", "depth": "work through", "why": "Most-asked.",
             "anticipates": "cross-reference"},
        ],
        "cut": [],
    },
    "consequence": {
        "exclusions": [
            {
                "topic": "Molecular clocks",
                "consequence": "You cannot check a date a question gives you.",
                "when_to_learn": "Only beyond NEET.",
            }
        ]
    },
    "partition": {
        "units": [
            {"heading": "Where humans sit", "covers": ["Primate lineage"], "why_here": "Entry."},
            {
                "heading": "The hominins",
                "covers": ["Australopithecus", "Homo erectus"],
                "why_here": "One sequence.",
            },
        ]
    },
    "traversal": {
        "sequence": ["Where humans sit", "The hominins"],
        "why": "Taxonomy first; every later form is placed against it.",
    },
}


class StubProvider:
    """Returns whatever the test scripted, in order."""

    name, model = "stub", "stub-1"

    def __init__(self, *payloads: dict) -> None:
        self.payloads = list(payloads)
        self.seen: list[str] = []

    def complete(self, *, system, user, schema, max_tokens) -> Completion:
        self.seen.append(user)
        return Completion(
            text=json.dumps(self.payloads.pop(0)),
            input_tokens=10,
            output_tokens=20,
            model=self.model,
            provider=self.name,
        )


def routing(targets, reading="ok", out_of_scope=None, **outputs) -> dict:
    payload = {"targets": targets, "reading": reading, "out_of_scope": out_of_scope}
    payload.update(outputs)
    return payload


@pytest.fixture()
def service(tmp_path) -> PlanService:
    """Nothing left to ask, so create() reads and plans in one go."""
    return PlanService(FileStore(tmp_path), provider=StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN))


def opened(service: PlanService):
    return service.create(REQUEST)


# --- the three classes of decision ------------------------------------------


def test_all_eight_decisions_are_recorded_as_rows() -> None:
    assert set(ALL_DECISIONS) == set(PLAN_DECISIONS) | set(UPSTREAM_DECISIONS) | set(
        INTERACTION_DECISIONS
    )
    assert len(ALL_DECISIONS) == 8


def test_a_proposal_writes_one_row_per_decision(service: PlanService) -> None:
    view = opened(service)
    rows = service.store.current_decisions(view.project_id)
    assert set(rows) == set(ALL_DECISIONS)
    # each is its own record, addressable on its own -- not fields of one plan
    assert len({r.id for r in rows.values()}) == 8


def test_upstream_decisions_are_recorded_even_though_they_have_no_plan_section(
    service: PlanService,
) -> None:
    """They are distinct decisions in Architecture §3, not scope's internals.
    Recording them is what lets 'you missed X' route somewhere it can be fixed."""
    view = opened(service)
    rows = service.store.current_decisions(view.project_id)
    assert "derive_structure" in rows
    assert "relevance" in rows
    # and they are not shown as plan sections
    assert set(view.to_json()["decisions"]) >= set(UPSTREAM_DECISIONS)


# --- routing ----------------------------------------------------------------


def test_a_missing_concept_routes_to_structure_not_scope(service: PlanService) -> None:
    """Scope can only cut or keep what it was handed. A concept that was never
    derived cannot be restored by any change to scope, so misrouting here is
    unfixable by any later correction."""
    view = opened(service)
    structure = {
        "concepts": LANDSCAPE["derive_structure"]["concepts"]
        + [{"name": "Homo habilis", "built_from": ["Australopithecus"]}]
    }
    service.provider = StubProvider(
        routing(["derive_structure"], reading="H. habilis was missing", derive_structure=structure)
    )
    after = service.correct(view.project_id, "you've completely missed Homo habilis")

    turn = after.to_json()["last_turn"]
    assert turn["claimed"] == ["derive_structure"]
    assert turn["actual"] == ["derive_structure"]
    assert "scope" in turn["unchanged"]


def test_a_correction_changes_only_what_it_routed_to(service: PlanService) -> None:
    view = opened(service)
    tighter = {"covered": PLAN["scope"]["covered"][:1], "cut": ["Homo erectus"]}
    service.provider = StubProvider(routing(["scope"], scope=tighter))
    after = service.correct(view.project_id, "much shorter please")

    rows = service.store.current_decisions(view.project_id)
    assert rows["scope"].output == tighter
    for kind in ("partition", "traversal", "consequence", "interpret_situation"):
        expected = {"interpret_situation": SITUATION, **LANDSCAPE, **PLAN}[kind]
        assert rows[kind].output == expected
    assert after.to_json()["last_turn"]["actual"] == ["scope"]


def test_routing_is_the_routers_judgement_not_a_fixed_mapping(service: PlanService) -> None:
    """A capacity change may move partition too. The loop asserts agreement
    between the declared set and the actual set — never a phrase-to-decision map."""
    view = opened(service)
    single_unit = {"units": [PLAN["partition"]["units"][0]]}
    service.provider = StubProvider(
        routing(
            ["scope", "partition", "traversal"],
            scope={"covered": PLAN["scope"]["covered"][:1], "cut": ["Homo erectus"]},
            partition=single_unit,
            traversal={"sequence": ["Where humans sit"], "why": "Only one unit left."},
        )
    )
    turn = service.correct(view.project_id, "i only have four days").to_json()["last_turn"]

    assert set(turn["claimed"]) == {"scope", "partition", "traversal"}
    assert set(turn["actual"]) == {"scope", "partition", "traversal"}
    assert turn["unclaimed_drift"] == []


def test_drift_beyond_the_routed_set_is_reported(service: PlanService) -> None:
    """Reported, never repaired. A claim nobody checks is a wish."""
    view = opened(service)
    service.provider = StubProvider(
        routing(
            ["scope"],
            scope={"covered": PLAN["scope"]["covered"][:1], "cut": []},
            traversal={"sequence": ["The hominins"], "why": "Rewritten unasked."},
        )
    )
    turn = service.correct(view.project_id, "shorter").to_json()["last_turn"]

    assert turn["claimed"] == ["scope"]
    assert set(turn["actual"]) == {"scope", "traversal"}
    assert turn["unclaimed_drift"] == ["traversal"]


def test_a_decision_routed_to_but_left_alone_is_reported(service: PlanService) -> None:
    view = opened(service)
    service.provider = StubProvider(routing(["scope"], scope=PLAN["scope"]))
    turn = service.correct(view.project_id, "trim it").to_json()["last_turn"]

    assert turn["actual"] == []
    assert turn["claimed_but_unchanged"] == ["scope"]


def test_presentation_is_deferred_not_absorbed(service: PlanService) -> None:
    """Presentation-Boundary §5: a correction answered in the wrong place is worse
    than one deferred, because the user believes it was handled."""
    view = opened(service)
    before = service.store.current_decisions(view.project_id)
    service.provider = StubProvider(
        routing([], reading="wants a dark theme", out_of_scope="Appearance — the demo stage.")
    )
    after = service.correct(view.project_id, "make it black with yellow accents")

    turn = after.to_json()["last_turn"]
    assert turn["claimed"] == [] and turn["actual"] == []
    assert turn["out_of_scope"]
    assert not turn["not_understood"]
    assert {k: d.output for k, d in service.store.current_decisions(view.project_id).items()} == {
        k: d.output for k, d in before.items()
    }


def test_a_correction_that_lands_nowhere_is_flagged_as_not_understood(
    service: PlanService,
) -> None:
    view = opened(service)
    service.provider = StubProvider(routing([], reading="unclear"))
    turn = service.correct(view.project_id, "hmm").to_json()["last_turn"]
    assert turn["not_understood"] is True


# --- extent, approval, commitment -------------------------------------------


def test_extent_is_derived_from_scope_not_written_by_the_model() -> None:
    """Architecture §14: reporting extent is an obligation, not a free field."""
    small = derive_extent(Scope(**PLAN["scope"]), Partition(**PLAN["partition"]))
    bigger = derive_extent(
        Scope(
            covered=PLAN["scope"]["covered"] + [
                {"concept": "X", "depth": "work through", "why": "y"}
            ],
            cut=[],
        ),
        Partition(**PLAN["partition"]),
    )
    assert small != bigger
    assert small["pages"].endswith("pages") or small["pages"] == "~1 page"
    # per-unit, because a contents page is where a reader judges size
    assert set(small["per_unit"]) == {u["heading"] for u in PLAN["partition"]["units"]}
    assert small["parts"] == 2


def test_extent_moves_when_scope_moves(service: PlanService) -> None:
    view = opened(service)
    before = view.extent
    service.provider = StubProvider(
        routing(["scope"], scope={"covered": PLAN["scope"]["covered"][:1], "cut": []})
    )
    assert service.correct(view.project_id, "shorter").extent != before


def test_approval_is_idempotent_by_decision_set(service: PlanService) -> None:
    view = opened(service)
    first = service.approve(view.project_id)
    second = service.approve(view.project_id)
    assert first.id == second.id
    assert len(service.store.commitments(view.project_id)) == 1
    assert first.decision_ids_hash == commit_hash(first.decision_ids)


def test_the_commitment_names_the_upstream_decisions_it_rests_on(
    service: PlanService,
) -> None:
    """The user approved a meaning that depends on structure and relevance. If one
    drifts later, the approval rested on a derivation they never saw."""
    view = opened(service)
    rows = service.store.current_decisions(view.project_id)
    commitment = service.approve(view.project_id)

    for kind in PLAN_DECISIONS + UPSTREAM_DECISIONS:
        assert rows[kind].id in commitment.decision_ids
    # the conversation's own decision is not part of what was approved
    assert rows["intake_strategy"].id not in commitment.decision_ids


def test_the_snapshot_stands_alone(service: PlanService) -> None:
    """System Design §4: readable with the decision table dropped."""
    view = opened(service)
    snapshot = service.approve(view.project_id).snapshot

    assert snapshot["scope"]["covered"][0]["concept"] == "Primate lineage"
    assert snapshot["consequence"]["exclusions"][0]["consequence"]
    assert snapshot["consequence"]["exclusions"][0]["when_to_learn"]
    assert snapshot["extent"]
    assert "id" not in json.dumps(snapshot)


def test_the_transcript_is_append_only_testimony(service: PlanService) -> None:
    view = opened(service)
    service.provider = StubProvider(routing([], reading="x", out_of_scope="later stage"))
    service.correct(view.project_id, "make it black")

    said = [u.text for u in service.store.utterances(view.project_id) if u.role == "user"]
    assert said == ["i need to revise human evolution for NEET", "make it black"]


def test_a_view_survives_a_restart(tmp_path) -> None:
    """No session state in the service: another instance over the same store
    reads the same plan, including the last turn."""
    store = FileStore(tmp_path)
    first = PlanService(store, provider=StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN))
    view = first.create(REQUEST)
    first.provider = StubProvider(routing([], reading="deferred", out_of_scope="demo stage"))
    first.correct(view.project_id, "make it black")

    second = PlanService(FileStore(tmp_path))
    reloaded = second.view(view.project_id).to_json()
    assert reloaded["last_turn"]["reading"] == "deferred"
    assert set(reloaded["decisions"]) == set(ALL_DECISIONS)


# --- the intake loop --------------------------------------------------------


def test_a_bare_request_asks_before_it_plans(tmp_path) -> None:
    """The defect this replaced: questions were computed after the plan, so a
    six-word request produced a full plan and asked nothing. Architecture §4
    puts the intake loop first and terminates it on sufficiency."""
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING))
    view = service.create(REQUEST)

    assert view.state == "asking"
    assert view.questions and view.questions[0]["options"]
    # nothing downstream has been decided yet
    rows = service.store.current_decisions(view.project_id)
    assert set(rows) == {"interpret_situation", "intake_strategy"}


def test_questions_are_objective_with_distinct_options(tmp_path) -> None:
    """Semantics §1: the learner cannot specify their entry point but can
    recognise it. Options are how recognition is offered."""
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING))
    question = service.create(REQUEST).questions[0]

    assert 2 <= len(question["options"]) <= 4
    labels = [o["label"] for o in question["options"]]
    assert len(set(labels)) == len(labels)
    assert question["default_label"] in labels
    # every option says what it does to the plan, and they differ
    implications = [o["implication"] for o in question["options"]]
    assert all(implications) and len(set(implications)) == len(implications)


def test_an_answer_is_testimony_and_the_situation_is_re_read(tmp_path) -> None:
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING))
    view = service.create(REQUEST)
    service.provider = StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN)
    after = service.answer(view.project_id, "Answer MCQs")

    assert after.state == "planned"
    said = [u.text for u in service.store.utterances(view.project_id) if u.role == "user"]
    assert said == [REQUEST, "Answer MCQs"]
    # re-read, not patched: interpret_situation has a second row
    kinds = [d.kind for d in service.store.decision_history(view.project_id)]
    assert kinds.count("interpret_situation") == 2


def test_a_question_never_blocks(tmp_path) -> None:
    """Semantics §3. The user can always proceed on the carried defaults."""
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING))
    view = service.create(REQUEST)
    assert view.state == "asking"

    service.provider = StubProvider(LANDSCAPE, PLAN)
    assert service.proceed(view.project_id).state == "planned"


def test_readiness_is_sufficiency_not_a_turn_count(tmp_path) -> None:
    """A model that keeps asking about an axis the user just answered must not
    keep the user in a form. The exit is *no progress*: if an answer
    strengthened nothing, asking again will not either."""
    service = PlanService(
        FileStore(tmp_path),
        provider=StubProvider(READING_ASKING, READING_ASKING, LANDSCAPE, PLAN),
    )
    view = service.create(REQUEST)
    assert view.state == "asking"

    # the second read is identical -- nothing strengthened -- so it plans
    after = service.answer(view.project_id, "Answer MCQs")
    assert after.state == "planned"


def test_a_productive_answer_keeps_the_loop_open(tmp_path) -> None:
    """Progress, not a count: an answer that strengthens one axis while another
    stays weak and material is allowed to produce a second question."""
    second_round = {
        "interpret_situation": SITUATION,
        "axes": [
            _axis("subject", "Human evolution", "stated", "human evolution"),
            _axis("target_capability", "Answer MCQs", "stated", "NEET"),
            _axis("entry_point", None, "unknown", material="changes_the_plan"),
        ]
        + [_axis(a) for a in ("purpose", "capacity", "depth_register", "artifact_type", "template")],
        "proposed_questions": [{**QUESTION, "axis": "entry_point"}],
    }
    service = PlanService(
        FileStore(tmp_path), provider=StubProvider(READING_ASKING, second_round)
    )
    view = service.create(REQUEST)
    after = service.answer(view.project_id, "Answer MCQs")

    assert after.state == "asking"
    assert after.sufficiency["asking"] == ["entry_point"]
    assert service.MAX_INTAKE_ROUNDS >= 4  # a crash barrier, not the policy


def test_capacity_is_not_asked_for_upfront(service: PlanService) -> None:
    """Semantics §1: the learner cannot state extent in advance; reporting the
    derived extent is what prompts them to state a capacity. It arrives as a
    correction, not as an intake question."""
    view = opened(service)
    assert view.decisions["interpret_situation"]["capacity"] is None
    assert view.extent["pages"] and view.extent["study_time"]


# --------------------------------------------------------------------------
# The empty-question dead end
# --------------------------------------------------------------------------


def test_a_wanted_question_the_model_never_wrote_does_not_strand_the_user(
    tmp_path,
) -> None:
    """The decider names axes worth asking about; the model authors the
    questions. Nothing makes those agree, and `_read` intersects them.

    A real request -- "i need a cheat sheet for graph dsa questions for my
    interview" -- produced verdict `ask` on `target_capability` with zero
    surviving questions, so the page said "I'd rather ask than guess" and then
    showed nothing at all: no questions, no plan, no control.

    A question that does not exist cannot be answered, so it cannot be a reason
    to wait.
    """
    axes = [dict(a) for a in AXES_SUFFICIENT]
    for axis in axes:
        if axis["axis"] == "target_capability":
            axis["source"] = "unknown"
            axis["supported_by"] = []
            axis["materiality"] = "changes_the_plan"

    reading = {
        "interpret_situation": SITUATION,
        "axes": axes,
        # The decider wants target_capability asked; the model wrote nothing.
        "proposed_questions": [],
    }
    service = PlanService(
        FileStore(tmp_path), provider=StubProvider(reading, LANDSCAPE, PLAN)
    )
    view = service.create(REQUEST)

    assert view.sufficiency["verdict"] == "ask", "the decider still wants to ask"
    assert view.sufficiency["asking"] == ["target_capability"]
    assert view.questions == [], "nothing survived the intersection"

    assert view.state != "asking", (
        "state 'asking' with no questions renders a page with no control on it"
    )
    assert view.decisions.get("scope"), "planning must proceed when nothing can be asked"
