"""The decider: how much must be known before planning starts.

No model. The whole point of splitting policy from judgment is that the policy
half is decidable in code, so these tests assert the three questions the record
has to answer: **why did we ask**, **why did we not ask**, and **what would
materially differ**.
"""

from __future__ import annotations

import pytest

from agent.sufficiency import (
    AXES,
    DEFAULT_BUDGET,
    POLICY,
    AxisReading,
    Span,
    decide,
    from_json,
    improved,
)

SAID = ["i need to revise human evolution for NEET"]


def reading(axis, *, value="v", source="inferred", spans=(), material="changes_the_plan",
            differs="a different plan") -> AxisReading:
    return AxisReading(
        axis=axis,
        value=value,
        source=source,
        supported_by=[Span(utterance_ord=o, quote=q) for o, q in spans],
        would_differ=differs,
        materiality=material,
    )


def subject_known(**over):
    return reading("subject", source="stated", spans=((0, "human evolution"),), **over)


# --- policy is code, and it is derived from locked claims -------------------


def test_only_the_subject_can_block() -> None:
    """Semantics §3: a question is an offer to correct early, never a blocker.
    The one exception is a prerequisite -- with no subject there is nothing to
    plan at all, which is not the same as an unanswered question."""
    blocking = [a for a in AXES if POLICY[a].blocking]
    assert blocking == ["subject"]
    assert POLICY["subject"].prerequisite


def test_capacity_and_the_biasing_axes_are_never_asked() -> None:
    """Capacity because §1's corollary makes the extent report what elicits it;
    depth register and template because they are biasing, not binding."""
    for axis in ("capacity", "depth_register", "template"):
        assert not POLICY[axis].askable
        assert POLICY[axis].because


def test_target_capability_is_askable_but_never_blocking() -> None:
    """Semantics §2 LOCKED: the target may not exist yet, and that is a
    legitimate state."""
    assert POLICY["target_capability"].askable
    assert not POLICY["target_capability"].blocking


def test_purpose_outranks_the_others_when_the_budget_binds() -> None:
    """Semantics §5 LOCKED: purpose is the arbiter."""
    askable = [a for a in AXES if POLICY[a].askable and a != "subject"]
    assert min(askable, key=lambda a: POLICY[a].priority) == "purpose"


# --- the prerequisite -------------------------------------------------------


def test_no_subject_is_a_prerequisite_not_a_weighed_axis() -> None:
    result = decide([reading("subject", value=None, source="unknown")], SAID)
    assert result.verdict == "needs_subject"
    assert result.asking == ("subject",)
    # nothing else competes for attention while there is nothing to plan
    assert result.over_budget == ()


def test_a_known_subject_lets_the_other_axes_be_weighed() -> None:
    result = decide([subject_known()], SAID)
    assert result.verdict != "needs_subject"


# --- provenance is verified, not taken on trust -----------------------------


def test_a_quote_that_is_not_in_the_transcript_is_discarded() -> None:
    """Free-text evidence cannot be checked; a span can. Support that does not
    resolve against stored testimony demotes the reading to a guess."""
    result = decide(
        [subject_known(), reading("purpose", source="inferred", spans=((0, "for my PhD viva"),))],
        SAID,
    )
    purpose = result.by_axis("purpose")
    assert purpose.strength == "guessed"
    assert purpose.unverified == ("for my PhD viva",)
    assert "discarded unverifiable support" in purpose.reason


def test_a_resolving_quote_makes_the_reading_inferred() -> None:
    result = decide(
        [subject_known(), reading("purpose", source="inferred", spans=((0, "NEET"),))],
        SAID,
    )
    purpose = result.by_axis("purpose")
    assert purpose.strength == "inferred"
    assert purpose.verified[0].quote == "NEET"
    assert purpose.reason == "inferred, supported by 'NEET'"
    assert not purpose.asked


def test_a_span_pointing_at_a_missing_utterance_does_not_resolve() -> None:
    result = decide(
        [subject_known(), reading("purpose", spans=((7, "NEET"),))],
        SAID,
    )
    assert result.by_axis("purpose").strength == "guessed"


def test_claiming_stated_without_support_is_still_a_guess() -> None:
    result = decide([subject_known(), reading("purpose", source="stated")], SAID)
    assert result.by_axis("purpose").strength == "guessed"


# --- why we asked, and why we did not ---------------------------------------


def test_weak_and_material_is_asked() -> None:
    result = decide(
        [subject_known(), reading("purpose", source="unknown", value=None)],
        SAID,
    )
    purpose = result.by_axis("purpose")
    assert result.verdict == "ask"
    assert purpose.asked
    assert purpose.reason == "weak (unknown) and a different answer would change the plan"
    assert purpose.would_differ


def test_weak_but_immaterial_is_not_asked_and_says_so() -> None:
    result = decide(
        [subject_known(), reading("purpose", source="unknown", value=None, material="no_effect")],
        SAID,
    )
    purpose = result.by_axis("purpose")
    assert not purpose.asked
    assert "would not change the plan materially" in purpose.reason
    assert result.verdict == "sufficient"


def test_a_non_askable_axis_carries_the_locked_claim_as_its_reason() -> None:
    result = decide(
        [subject_known(), reading("capacity", source="unknown", value=None)],
        SAID,
    )
    capacity = result.by_axis("capacity")
    assert not capacity.asked
    assert capacity.reason.startswith("never asked —")
    assert "Semantics §1" in capacity.reason


def test_every_axis_gets_a_verdict_and_a_reason() -> None:
    result = decide([subject_known()], SAID)
    assert {a.axis for a in result.axes} == set(AXES)
    assert all(a.reason for a in result.axes)


# --- the budget is a constraint, not a rule ---------------------------------


def test_the_budget_is_configurable_and_not_baked_in() -> None:
    weak = [
        subject_known(),
        reading("purpose", source="unknown", value=None),
        reading("entry_point", source="unknown", value=None),
        reading("target_capability", source="unknown", value=None),
    ]
    assert decide(weak, SAID, budget=1).asking == ("purpose",)
    assert decide(weak, SAID, budget=3).asking == (
        "purpose",
        "entry_point",
        "target_capability",
    )
    assert DEFAULT_BUDGET  # a default exists, but nothing depends on its value


def test_over_budget_axes_are_recorded_not_dropped() -> None:
    """They become visible assumptions in the plan rather than silent ones."""
    weak = [
        subject_known(),
        reading("purpose", source="unknown", value=None),
        reading("entry_point", source="unknown", value=None, differs="four extra concepts"),
    ]
    result = decide(weak, SAID, budget=1)

    assert result.asking == ("purpose",)
    assert result.over_budget == ("entry_point",)
    entry = result.by_axis("entry_point")
    assert not entry.asked
    assert "over the question budget" in entry.reason
    assert entry.would_differ == "four extra concepts"


def test_every_weak_material_axis_is_asked_when_the_budget_allows() -> None:
    weak = [
        subject_known(),
        reading("purpose", source="unknown", value=None),
        reading("entry_point", source="unknown", value=None),
    ]
    result = decide(weak, SAID, budget=10)
    assert set(result.asking) == {"purpose", "entry_point"}
    assert result.over_budget == ()


# --- the whole record is serialisable ---------------------------------------


def test_the_record_round_trips_for_storage() -> None:
    result = decide([subject_known(), reading("purpose", spans=((0, "NEET"),))], SAID)
    blob = result.to_json()
    assert blob["verdict"] in ("needs_subject", "ask", "sufficient")
    assert len(blob["axes"]) == len(AXES)
    assert all({"axis", "strength", "reason", "would_differ"} <= set(a) for a in blob["axes"])


@pytest.mark.parametrize("axis", AXES)
def test_every_axis_has_a_policy_with_a_citation(axis: str) -> None:
    assert POLICY[axis].because


# --- artifact type: askable, and usually inferred ---------------------------


def test_artifact_type_is_askable() -> None:
    """Semantics §1 makes it user-set and binding; §2 uses long-vs-short notes
    as its own example of two presets that produce different plans."""
    assert POLICY["artifact_type"].askable
    assert not POLICY["artifact_type"].blocking


def test_artifact_type_established_by_wording_is_not_asked() -> None:
    said = ["short revision notes on signals and systems for GATE"]
    result = decide(
        [
            reading("subject", source="stated", spans=((0, "signals and systems"),)),
            reading("purpose", source="stated", spans=((0, "GATE"),)),
            reading("artifact_type", value="short notes", source="stated",
                    spans=((0, "short revision notes"),)),
            reading("entry_point", source="unknown", value=None),
        ],
        said,
    )
    assert not result.by_axis("artifact_type").asked
    assert result.by_axis("artifact_type").strength == "stated"
    assert result.asking == ("entry_point",)


def test_a_request_that_settles_everything_asks_nothing() -> None:
    """The point of inferring first: fewest turns, not filled fields."""
    said = ["short revision notes on signals and systems for GATE, i've done the basics"]
    everything = [
        reading(a, source="stated", spans=((0, "GATE"),), material="no_effect")
        for a in ("subject", "purpose", "entry_point", "artifact_type", "target_capability")
    ]
    result = decide(everything, said)
    assert result.verdict == "sufficient"
    assert result.asking == ()


# --- readiness is sufficiency, not a turn count -----------------------------


def test_progress_is_measured_by_strength_not_by_turns() -> None:
    said = ["notes on signals and systems"]
    weak = decide(
        [subject_known(), reading("purpose", source="unknown", value=None)], said
    )
    assert improved(None, weak)          # the first read always counts as progress
    assert not improved(weak, weak)      # an answer that strengthened nothing did not

    stronger = decide(
        [subject_known(), reading("purpose", source="stated", spans=((0, "notes"),))], said
    )
    assert improved(weak, stronger)


def test_a_stored_record_rehydrates_for_the_next_turn() -> None:
    result = decide([subject_known(), reading("purpose", spans=((0, "human evolution"),))], SAID)
    again = from_json(result.to_json())
    assert again is not None
    assert [a.strength for a in again.axes] == [a.strength for a in result.axes]
    assert not improved(result, again)


def test_the_budget_ceiling_covers_every_askable_axis() -> None:
    """So a genuinely bare request resolves in ONE turn rather than several."""
    askable = [a for a in AXES if POLICY[a].askable and not POLICY[a].prerequisite]
    assert DEFAULT_BUDGET >= len(askable)


def test_a_span_covering_the_whole_request_supports_nothing() -> None:
    """Observed in the wild: for a seven-word request the model cited six of
    those words as support for purpose, entry point AND target. All three
    resolved, all three read as inferred, and nothing was asked. Evidence that
    backs every reading equally backs none of them."""
    said = ["i need notes on signal and system"]
    whole = "need notes on signal and system"
    result = decide(
        [
            reading("subject", source="stated", spans=((0, "signal and system"),)),
            reading("purpose", source="inferred", spans=((0, whole),)),
        ],
        said,
    )
    assert result.by_axis("purpose").strength == "guessed"
    assert result.by_axis("purpose").asked
    assert result.by_axis("subject").strength == "stated"


def test_a_short_answer_is_allowed_to_be_its_own_evidence() -> None:
    """The rule must not punish a two-word reply, where the whole utterance
    genuinely is the evidence for what it answers."""
    said = ["notes on signals", "GATE prep"]
    result = decide(
        [
            reading("subject", source="stated", spans=((0, "signals"),)),
            reading("purpose", source="stated", spans=((1, "GATE prep"),)),
        ],
        said,
    )
    assert result.by_axis("purpose").strength == "stated"


# --- treatment: content is not prose-equivalent ------------------------------


def test_the_capability_table_covers_every_prose_failure() -> None:
    from agent.treatment import CAPABILITY, FAILURES

    assert set(FAILURES) <= set(CAPABILITY)
    assert all(CAPABILITY[f].licenses and CAPABILITY[f].note for f in FAILURES)


def test_spatial_content_costs_more_than_prose_at_the_same_depth() -> None:
    """The claim being removed is that all content is prose-equivalent."""
    from agent.plan import Partition, Scope, derive_extent

    def scope(anticipates):
        return Scope(
            covered=[
                {"concept": f"C{i}", "depth": "explain", "why": "w", "anticipates": anticipates}
                for i in range(6)
            ],
            cut=[],
        )

    part = Partition(units=[{"heading": "U", "covers": [f"C{i}" for i in range(6)],
                             "why_here": "w"}])
    prose = derive_extent(scope("none"), part)
    spatial = derive_extent(scope("perceptual-referent"), part)
    assert spatial["pages"] != prose["pages"]


def test_an_unservable_treatment_is_reported_before_approval() -> None:
    """Architecture §13: report the limitation, never substitute prose for it."""
    from agent.plan import Scope, derive_feasibility

    result = derive_feasibility(
        Scope(
            covered=[
                {"concept": "Structure of the small intestine", "depth": "explain",
                 "why": "w", "anticipates": "perceptual-referent"},
                {"concept": "Enzyme comparison", "depth": "explain",
                 "why": "w", "anticipates": "cross-reference"},
            ],
            cut=[],
        )
    )
    assert not result["serves_everything"]
    gaps = result["shortfalls"]
    assert [g["failure"] for g in gaps] == ["perceptual-referent"]
    assert gaps[0]["concepts"] == ["Structure of the small intestine"]
    # the served one is not reported as a gap
    assert all(g["failure"] != "cross-reference" for g in gaps)


def test_content_prose_can_carry_reports_no_shortfall() -> None:
    from agent.plan import Scope, derive_feasibility

    result = derive_feasibility(
        Scope(covered=[{"concept": "A", "depth": "explain", "why": "w"}], cut=[])
    )
    assert result["serves_everything"]
    assert result["shortfalls"] == []


def test_anticipates_names_a_failure_never_a_diagram() -> None:
    """The plan schema stays domain-free and realization-free: selecting a
    figure is decision 11, at the demo gate."""
    from agent.treatment import FAILURES

    banned = ("diagram", "image", "figure", "chart", "venn", "anatom")
    assert all(not any(b in f for b in banned) for f in FAILURES)


# --------------------------------------------------------------------------
# Provenance: a span can exist and still not be evidence
# --------------------------------------------------------------------------

FROM_SCRATCH = "i need agentic ai notes for interview, from scratch"


def _reading(axis, value, source, quote, materiality="changes_the_plan"):
    return AxisReading(
        axis=axis,
        value=value,
        source=source,
        supported_by=[Span(utterance_ord=0, quote=quote)],
        would_differ="a different plan",
        materiality=materiality,
    )


def test_a_span_that_denies_the_reading_does_not_verify_it() -> None:
    """The real failure. `entry_point` read as "Beginner to agentic AI; assumes
    general ML/LLM literacy", citing the span "from scratch" in support.

    The quote is really in the request, so existence-checking passed and
    promoted the reading from `guessed` to `inferred` — out of reach of the
    question that would have caught it. Everything downstream then built on
    literacy the user said they did not have.
    """
    result = decide(
        [
            _reading("subject", "Agentic AI", "stated", "agentic ai"),
            _reading(
                "entry_point",
                "Beginner to agentic AI; assumes general ML/LLM literacy",
                "inferred",
                "from scratch",
            ),
        ],
        [FROM_SCRATCH],
    )
    entry = next(a for a in result.axes if a.axis == "entry_point")
    assert entry.verified == (), "a quote that denies the reading is not support"
    assert entry.unverified == ("from scratch",)
    assert entry.weak, "unsupported, so it must not sit at `inferred`"
    assert entry.material
    assert "entry_point" in result.asking, "weak and material — it must be asked"
    assert result.verdict == "ask"


def test_the_same_span_supports_a_reading_that_agrees_with_it() -> None:
    """The check must not fire on every mention of prior knowledge — only where
    the quote and the reading actually disagree."""
    result = decide(
        [
            _reading("subject", "Agentic AI", "stated", "agentic ai"),
            _reading("entry_point", "No prior exposure to agents or LLM APIs", "stated", "from scratch"),
        ],
        [FROM_SCRATCH],
    )
    entry = next(a for a in result.axes if a.axis == "entry_point")
    assert len(entry.verified) == 1
    assert entry.strength == "stated"
    assert "entry_point" not in result.asking


def test_a_negated_claim_of_prior_knowledge_is_not_a_contradiction() -> None:
    """"assumes no prior exposure" is the opposite claim from "assumes prior
    exposure" and differs by one word."""
    result = decide(
        [
            _reading("subject", "Agentic AI", "stated", "agentic ai"),
            _reading("entry_point", "Assumes no prior exposure to agents", "stated", "from scratch"),
        ],
        [FROM_SCRATCH],
    )
    entry = next(a for a in result.axes if a.axis == "entry_point")
    assert len(entry.verified) == 1, "negated prior-knowledge is agreement, not contradiction"


def test_an_unrelated_quote_is_untouched_by_the_check() -> None:
    """The check is one narrow family. A quote with no polarity claim in it must
    verify exactly as before."""
    result = decide(
        [
            _reading("subject", "Agentic AI", "stated", "agentic ai"),
            _reading("purpose", "Interview preparation", "inferred", "for interview"),
        ],
        [FROM_SCRATCH],
    )
    purpose = next(a for a in result.axes if a.axis == "purpose")
    assert len(purpose.verified) == 1
    assert purpose.strength == "inferred"


def test_a_stated_constraint_binds_the_axis_it_names() -> None:
    """Semantics §1: stated constraints bind. A statement *about* an axis that
    comes back as an *inference* on that axis was reinterpreted, not honoured —
    even when the words themselves carry no polarity to check."""
    readings = [
        _reading("subject", "Agentic AI", "stated", "agentic ai"),
        _reading("entry_point", "Comfortable with Python and ML basics", "inferred", "agentic ai"),
    ]
    free = decide(readings, [FROM_SCRATCH])
    assert not next(a for a in free.axes if a.axis == "entry_point").weak

    bound = decide(
        readings,
        [FROM_SCRATCH],
        stated=[{"text": "from scratch", "axis": "entry_point"}],
    )
    entry = next(a for a in bound.axes if a.axis == "entry_point")
    assert entry.weak, "a statement about this axis was read as an inference"
    assert "entry_point" in bound.asking


def test_legacy_stated_strings_bind_nothing() -> None:
    """Plans stored `stated` as bare strings with no attribution. They must keep
    behaving as they did rather than being retro-fitted with constraints the
    model never attributed."""
    readings = [
        _reading("subject", "Agentic AI", "stated", "agentic ai"),
        _reading("entry_point", "Comfortable with Python", "inferred", "agentic ai"),
    ]
    result = decide(readings, [FROM_SCRATCH], stated=["from scratch"])
    assert not next(a for a in result.axes if a.axis == "entry_point").weak


def test_a_short_request_whose_subject_is_quoted_minimally_verifies() -> None:
    """A real failure: for "i need notes on agentic AI" the model cited the whole
    six-word utterance as its span for subject. `_discriminating` discards a
    quote covering most of an utterance -- rightly, since such a quote supports
    every axis equally -- so subject fell to `guessed` and the gate demanded a
    subject the request plainly states.

    The guard stays. The citation was the fault: `agentic AI` is available as a
    two-word span, and the prompt now says to quote the shortest span that
    establishes the reading. Both halves are pinned here.
    """
    said = ["i need notes on agentic AI"]

    whole = decide([_reading("subject", "agentic AI", "stated", "i need notes on agentic AI")], said)
    lazy = next(a for a in whole.axes if a.axis == "subject")
    assert lazy.weak, "a whole-utterance quote must still be discarded"

    minimal = decide([_reading("subject", "agentic AI", "stated", "agentic AI")], said)
    tight = next(a for a in minimal.axes if a.axis == "subject")
    assert not tight.weak, "the minimal span must verify"
    assert tight.strength == "stated"
    assert minimal.verdict == "sufficient"


def test_the_prompt_tells_the_model_to_quote_minimally() -> None:
    """The guard cannot be loosened without reintroducing the failure it exists
    for, so the fix has to live in the instruction."""
    import pathlib

    prompt = pathlib.Path("agent/prompts/interpret_v1.md").read_text(encoding="utf-8")
    assert "SHORTEST SPAN" in prompt
    assert "DISCARDED" in prompt
