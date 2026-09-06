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
    for axis in ("capacity", "depth_register", "artifact_type", "template"):
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
