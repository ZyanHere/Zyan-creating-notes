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
    "stated": [{"text": "NEET syllabus only", "axis": None}],
    "inferred": ["Assumed the written exam, not the practical."],
}

READING_SUFFICIENT = {
    "interpret_situation": SITUATION,
    "axes": AXES_SUFFICIENT,
}

def intake(*questions) -> dict:
    """What `ask()` returns: the wording for axes the decider already chose."""
    return {"questions": list(questions)}


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
        "modules": [
            {
                "title": "Where humans sit",
                "covers": ["Primate lineage"],
                "why_here": "Entry.",
                "capability": "Place humans on the primate tree.",
            },
            {
                "title": "The hominins",
                "covers": ["Australopithecus", "Homo erectus"],
                "why_here": "One sequence.",
                "capability": "Order the hominin forms and say what changed at each.",
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
    """A project with a plan on it.

    Two steps now, because they are two different things: the conversational
    turn reads the request, and planning is asked for. `create()` never plans.
    """
    view = service.create(REQUEST)
    return service.proceed(view.project_id)


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
    single_unit = {"modules": [PLAN["partition"]["modules"][0]]}
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
    assert set(small["per_unit"]) == {m["title"] for m in PLAN["partition"]["modules"]}
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
    first.proceed(view.project_id)
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
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING, intake(QUESTION)))
    view = service.create(REQUEST)

    assert view.state == "asking"
    assert view.questions and view.questions[0]["options"]
    # nothing downstream has been decided yet
    rows = service.store.current_decisions(view.project_id)
    assert set(rows) == {"interpret_situation", "intake_strategy"}


def test_questions_are_objective_with_distinct_options(tmp_path) -> None:
    """Semantics §1: the learner cannot specify their entry point but can
    recognise it. Options are how recognition is offered."""
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING, intake(QUESTION)))
    question = service.create(REQUEST).questions[0]

    assert 2 <= len(question["options"]) <= 4
    labels = [o["label"] for o in question["options"]]
    assert len(set(labels)) == len(labels)
    assert question["default_label"] in labels
    # every option says what it does to the plan, and they differ
    implications = [o["implication"] for o in question["options"]]
    assert all(implications) and len(set(implications)) == len(implications)


def test_an_answer_is_testimony_and_the_situation_is_re_read(tmp_path) -> None:
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING, intake(QUESTION)))
    view = service.create(REQUEST)
    service.provider = StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN)
    after = service.answer(view.project_id, "Answer MCQs")

    assert after.state == "ready", "answering ends the conversation, not the wait"
    said = [u.text for u in service.store.utterances(view.project_id) if u.role == "user"]
    assert said == [REQUEST, "Answer MCQs"]
    # re-read, not patched: interpret_situation has a second row
    kinds = [d.kind for d in service.store.decision_history(view.project_id)]
    assert kinds.count("interpret_situation") == 2


def test_a_question_never_blocks(tmp_path) -> None:
    """Semantics §3. The user can always proceed on the carried defaults."""
    service = PlanService(FileStore(tmp_path), provider=StubProvider(READING_ASKING, intake(QUESTION)))
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
        provider=StubProvider(READING_ASKING, intake(QUESTION), READING_ASKING, intake(QUESTION), LANDSCAPE, PLAN),
    )
    view = service.create(REQUEST)
    assert view.state == "asking"

    # the second read is identical -- nothing strengthened -- so the
    # conversation closes. Planning is a separate, explicit step.
    after = service.answer(view.project_id, "Answer MCQs")
    assert after.state == "ready"
    assert after.decisions["intake_strategy"]["exhausted"]
    assert "strengthened nothing" in after.decisions["intake_strategy"]["closed_because"]


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
    }
    service = PlanService(
        FileStore(tmp_path),
        provider=StubProvider(
            READING_ASKING,
            intake(QUESTION),
            second_round,
            intake({**QUESTION, "axis": "entry_point"}),
        ),
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

    reading = {"interpret_situation": SITUATION, "axes": axes}
    service = PlanService(
        FileStore(tmp_path),
        # The decider wants target_capability asked; `ask()` comes back empty.
        provider=StubProvider(reading, intake(), LANDSCAPE, PLAN),
    )
    view = service.create(REQUEST)

    assert view.sufficiency["verdict"] == "ask", "the decider still wants to ask"
    assert view.sufficiency["asking"] == ["target_capability"]
    assert view.questions == [], "nothing survived the intersection"

    assert view.state == "ready", (
        "state 'asking' with no questions renders a page with no control on it"
    )
    assert not view.decisions.get("scope"), "planning waits to be asked for"
    assert service.proceed(view.project_id).decisions.get("scope")


def test_both_repair_prompts_ask_for_the_whole_object() -> None:
    """A model handed an error naming `interpret_situation` returned a bare
    Situation where a `Reading` was required — twice — and took the request
    down with it. The old wording invited exactly that:

        "Fix exactly this and reply with the corrected JSON object only"

    beside a dotted path. This was fixed in `agent/generate.py` first and the
    twin in `agent/plan.py` was missed, so both are pinned here together.
    """
    import inspect

    from agent.generate import _parse_or_repair
    from agent.plan import _call

    for fn in (_call, _parse_or_repair):
        source = inspect.getsource(fn)
        assert "COMPLETE" in source, f"{fn.__name__} must demand the whole object"
        assert "not a request" in source, (
            f"{fn.__name__} must say the dotted paths are a location, not a request"
        )


def test_the_repair_names_the_required_top_level_keys() -> None:
    """Read off the schema rather than written out, so it stays true for every
    call that uses `_call` — Reading, Landscape, PlanBody, Routing."""
    from agent.plan import Reading

    required = Reading.model_json_schema().get("required", [])
    assert "interpret_situation" in required and "axes" in required


def test_a_pre_plan_utterance_is_testimony_not_a_correction() -> None:
    """`needs_subject` is *before* a plan exists, so the reply is an answer.

    Routing it to `correct()` ran the correction router over decisions that do
    not exist — a long call that could not succeed, and the user's answer was
    never read. Observed live: three retries, 15-30 minutes each, no progress.
    """
    import inspect

    from backend import api

    source = inspect.getsource(api.add_utterance)
    assert '"asking", "needs_subject", "ready"' in source, (
        "every pre-plan state must route to answer(), not correct()"
    )


def test_an_identical_answer_repeated_is_a_retry_not_new_testimony(tmp_path) -> None:
    """A turn that dies after the utterance is written leaves it persisted, so
    pressing the button again appends it twice. One real project reached four
    copies of the same answer."""
    store = FileStore(tmp_path)
    service = PlanService(store, provider=StubProvider(READING_ASKING, intake(QUESTION)))
    view = service.create(REQUEST)

    answer = "Why you want it: NEET"
    service.provider = StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN)
    service.answer(view.project_id, answer)

    said = [u.text for u in store.utterances(view.project_id) if u.role == "user"]
    before = len(said)

    # The same answer again, as a retry would send it.
    service.provider = StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN)
    service.answer(view.project_id, answer)
    said = [u.text for u in store.utterances(view.project_id) if u.role == "user"]

    assert len(said) == before, f"the retry duplicated the answer: {said}"
    assert said.count(answer) == 1


def test_a_conversational_turn_is_exactly_one_model_call(tmp_path) -> None:
    """The turn the user waits on, and the whole requirement.

    Two things used to ride along on it. `interpret` authored questions for
    every weak axis it could see -- discarded whenever the verdict was
    `sufficient`, which is the common case -- and `create()` then ran `_plan()`
    inline, so a request that stated its own purpose and entry point paid for
    curriculum derivation before the user saw anything back.

    Neither happens now. One call: read the request.
    """
    provider = StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN)
    service = PlanService(FileStore(tmp_path), provider=provider)
    view = service.create(REQUEST)

    assert len(provider.seen) == 1, f"expected interpret only, got {len(provider.seen)}"
    assert view.state == "ready", "enough is known; the user has not asked for a plan"
    assert view.questions == []
    assert "scope" not in view.decisions, "nothing was derived or planned"


def test_planning_happens_only_when_the_user_asks_for_it(tmp_path) -> None:
    provider = StubProvider(READING_SUFFICIENT, LANDSCAPE, PLAN)
    service = PlanService(FileStore(tmp_path), provider=provider)
    view = service.create(REQUEST)
    assert view.state == "ready"

    planned = service.proceed(view.project_id)
    assert planned.state == "planned"
    assert planned.decisions.get("scope")
    # interpret, then derive and plan -- the expensive pair, and only on request.
    assert len(provider.seen) == 3


def test_questions_are_written_only_for_the_axes_the_decider_named(tmp_path) -> None:
    """`ask()` writes the wording. It does not choose the subject of the
    conversation, and it is never handed axes nobody asked about — which is what
    keeps this from becoming a fixed questionnaire."""
    provider = StubProvider(READING_ASKING, intake(QUESTION))
    service = PlanService(FileStore(tmp_path), provider=provider)
    view = service.create(REQUEST)

    assert view.state == "asking"
    asked = view.sufficiency["asking"]
    assert asked, "the decider chose at least one axis"

    ask_prompt = provider.seen[-1]
    for axis in asked:
        assert axis in ask_prompt, f"{axis} was chosen but not sent to ask()"
    assert "and no others" in ask_prompt


def test_the_same_topic_is_excluded_once(tmp_path) -> None:
    """A model that names the same exclusion twice has stated one exclusion.

    Observed: two `Multi-modal agents (vision, audio, code)` entries in one plan.
    Nothing downstream reads a repeat as anything but a repeat -- the plan lists
    it twice, the brief hands the writer the same exclusion twice, and the
    reader is told the same thing twice. It also collided in the UI, where
    `topic` is the list's React key.
    """
    from agent.plan import Consequence

    consequence = Consequence.model_validate(
        {
            "exclusions": [
                {"topic": "Multi-modal agents", "consequence": "a", "when_to_learn": "x"},
                {"topic": "Fine-tuning", "consequence": "b", "when_to_learn": "y"},
                # Same topic, second phrasing -- and a case/space variant, which
                # is how it actually turns up.
                {"topic": " multi-modal agents ", "consequence": "c", "when_to_learn": "z"},
            ]
        }
    )

    topics = [e.topic for e in consequence.exclusions]
    assert topics == ["Multi-modal agents", "Fine-tuning"]
    # First occurrence wins: the plan's ordering is the model's priority
    # ordering, and rewriting it here would be a second, unasked-for decision.
    assert consequence.exclusions[0].consequence == "a"


# --- the project index ------------------------------------------------------
#
# A Project is the durable object; the index is the only way back to one. These
# pin the two facts a row needs to be usable -- what it is, and how far it got.


def test_a_summary_names_the_subject_not_the_raw_query(service) -> None:
    """The stored title is the first 80 characters of what the user typed, so an
    index built on it showed four rows all reading `i need notes in agentic ai`.
    The displayed title is derived from the plan's own subject instead, and the
    query is carried separately because it is what the user recognises."""
    view = service.create(REQUEST)
    summary = service.summary(view.project_id)

    assert summary.title == "Human evolution"
    assert summary.query == REQUEST
    # Deriving rather than renaming: the stored row is untouched, so there are
    # never two titles to keep in sync.
    assert service.store.get_project(view.project_id).title == REQUEST


def test_a_summary_falls_back_to_the_query_before_anything_is_read(tmp_path) -> None:
    """A project whose opening read never landed has no subject to show. It is
    reported as `unread` rather than `ready`, because "ready to plan" over a
    project with no decisions is the index claiming work exists when none does
    -- which is what 9 of the 35 projects on the author's machine actually are,
    left behind by provider outages."""
    store = FileStore(tmp_path)
    project = store.create_project("local", title=REQUEST)
    store.add_utterance(project.id, "user", REQUEST)

    summary = PlanService(store).summary(project.id)

    assert summary.title == REQUEST
    assert summary.query == REQUEST
    assert summary.state == "unread"


def test_summary_and_view_never_disagree_about_state(service) -> None:
    """Two readers of the same rows. A project that says `ready` in the index and
    `asking` when opened is the app forgetting what it asked you, so both go
    through `lifecycle_state`."""
    view = service.create(REQUEST)
    assert service.summary(view.project_id).state == view.state

    service.proceed(view.project_id)
    after = service.view(view.project_id)
    assert service.summary(view.project_id).state == after.state == "planned"


def test_summaries_skips_a_project_it_cannot_read(service, tmp_path) -> None:
    """One corrupt file must not cost the user every other project."""
    good = service.create(REQUEST).project_id
    (tmp_path / "not-a-project.json").write_text("{ broken", encoding="utf-8")

    ids = [s.id for s in service.summaries()]

    assert ids == [good]


def test_approval_shows_on_the_summary(service) -> None:
    view = service.create(REQUEST)
    service.proceed(view.project_id)
    assert service.summary(view.project_id).approved is False

    service.approve(view.project_id)
    assert service.summary(view.project_id).approved is True

