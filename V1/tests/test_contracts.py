"""The guard: a diagnosed `perceptual-referent` may not be drawn.

Representation Boundary Rev. 3 §10 stage 1 admits nothing for family E, so the
filter chain terminates at escalation by construction. That only bites if the
contract enforces it, and until now `diagnosis` and `kind` sat side by side in
the schema and were never compared -- so a model could diagnose "the reader must
see the thing itself" and then draw boxes, and the document would validate,
render, and look right.

These tests pin the comparison, both directions: the false figure is refused, and
everything that is not a false figure still passes.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from agent.contracts import (
    PERCEPTUAL_REFERENT,
    Document,
    Callout,
    Code,
    Entity,
    Prose,
    RelationalStructure,
    Table,
    WorkedExample,
    normalize_diagnosis,
)

GUT_WALL = [
    Entity(label="Mucosa"),
    Entity(label="Submucosa"),
    Entity(label="Muscularis"),
    Entity(label="Serosa"),
]


# --------------------------------------------------------------------------
# The failure the guard exists for
# --------------------------------------------------------------------------


def test_the_dangerous_case_is_refused() -> None:
    """Boxes and arrows for a heart. This is the whole point of the guard."""
    with pytest.raises(ValidationError) as caught:
        RelationalStructure(
            diagnosis="perceptual-referent",
            relation="is-part-of",
            entities=GUT_WALL,
        )
    assert "licenses no realization" in str(caught.value)


@pytest.mark.parametrize(
    "make",
    [
        pytest.param(
            lambda d: Table(diagnosis=d, headers=["Layer"], rows=[["Mucosa"]]),
            id="table",
        ),
        pytest.param(
            lambda d: Code(diagnosis=d, language="text", code="villus"), id="code"
        ),
        pytest.param(
            lambda d: WorkedExample(diagnosis=d, title="Villus", steps=["look"]),
            id="example",
        ),
        pytest.param(
            lambda d: RelationalStructure(
                diagnosis=d, relation="precedes", entities=GUT_WALL
            ),
            id="relation",
        ),
    ],
)
def test_no_block_may_realize_it(make) -> None:
    """Not just the relational block -- reaching for *any* available shape is the
    substitution §13 forbids."""
    with pytest.raises(ValidationError):
        make(PERCEPTUAL_REFERENT)


@pytest.mark.parametrize(
    "written",
    [
        "perceptual-referent",
        "Perceptual-Referent",
        "  perceptual-referent  ",
        "perceptual_referent",
        "perceptual referent",
        "unlisted: perceptual-referent",
        "unlisted: perceptual referent",
    ],
)
def test_spelling_does_not_get_you_past_it(written: str) -> None:
    """`diagnosis` is free text on purpose (a model needing a failure the taxonomy
    lacks is the reading that reopens the frozen baseline). Free text is not a
    licence to read it literally."""
    with pytest.raises(ValidationError):
        RelationalStructure(
            diagnosis=written, relation="is-part-of", entities=GUT_WALL
        )


# --------------------------------------------------------------------------
# The escape hatch, and everything the guard must not touch
# --------------------------------------------------------------------------


def test_a_callout_may_carry_it_because_it_draws_nothing() -> None:
    """Visual-Requirement-Routing §4. A callout asserts no shape, order,
    containment or magnitude, so it cannot make the false spatial claim. It is
    the one legal form: the brief, printed."""
    stated_gap = Callout(
        diagnosis="perceptual-referent",
        tone="warning",
        title="Figure not included",
        text=(
            "This needs a labelled cross-section of an intestinal villus showing "
            "the epithelium, the lacteal, the capillary network and the brush "
            "border, with the lacteal's position relative to the capillaries."
        ),
    )
    assert stated_gap.diagnosis == "perceptual-referent"
    assert Callout.realizes is False


def test_the_model_still_has_a_way_to_say_it() -> None:
    """A guard with no legal alternative converts one bad outcome into another:
    the model falls back to prose, which is the silent substitution the guard was
    built to stop. So assert it at the level that matters -- a whole document
    needing a figure this build cannot draw must still validate, and the
    diagnosis must survive into it rather than being deleted to get past the
    guard."""

    def document(block: dict) -> str:
        return json.dumps(
            {
                "title": "The Human Digestive System",
                "assumed_entry": "Class 11 biology, chapter read once.",
                "target_capability": "Trace a meal through the canal.",
                "sections": [
                    {
                        "heading": "Absorption",
                        "blocks": [
                            {"kind": "prose", "text": "Absorption happens at the villi."},
                            block,
                        ],
                    }
                ],
            }
        )

    drawn = {
        "kind": "relation",
        "diagnosis": "perceptual-referent",
        "relation": "is-part-of",
        "entities": [{"label": "Epithelium"}, {"label": "Lacteal"}],
    }
    stated = {
        "kind": "callout",
        "diagnosis": "perceptual-referent",
        "tone": "warning",
        "title": "Figure not included",
        "text": "This needs a labelled cross-section of a villus showing the "
        "epithelium, the lacteal and the capillary network.",
    }

    with pytest.raises(ValidationError):
        Document.model_validate_json(document(drawn))

    accepted = Document.model_validate_json(document(stated))
    gap = accepted.sections[0].blocks[1]
    assert gap.kind == "callout"
    assert gap.diagnosis == "perceptual-referent", (
        "the diagnosis must survive into the document -- it is what makes the "
        "gap countable in the representation report"
    )


@pytest.mark.parametrize(
    "diagnosis",
    [
        "topology",
        "cross-reference",
        "parallel-state",
        "abstraction-grounding",
        "procedure-execution",
        "false-comprehension",
        "unlisted: spatial-scale",
        None,
    ],
)
def test_every_other_diagnosis_still_draws(diagnosis) -> None:
    block = RelationalStructure(
        diagnosis=diagnosis, relation="is-part-of", entities=GUT_WALL
    )
    assert block.kind == "relation"


def test_prose_is_untouched() -> None:
    """Prose is not a Departure and carries no diagnosis. The guard must not have
    reached it."""
    assert Prose(text="The gut wall has four layers.").kind == "prose"
    assert not hasattr(Prose, "realizes")


def test_a_near_miss_is_not_swept_up() -> None:
    """`unlisted: perceptual-scale` is a different failure the taxonomy does not
    carry -- exactly the reading Rev. 3 is reopened by. Refusing it would destroy
    the signal."""
    block = Table(
        diagnosis="unlisted: perceptual-scale",
        headers=["Structure", "Size"],
        rows=[["Villus", "1 mm"]],
    )
    assert block.diagnosis == "unlisted: perceptual-scale"


# --------------------------------------------------------------------------
# Normalization, on its own
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Cross-Reference", "cross-reference"),
        ("cross_reference", "cross-reference"),
        ("  topology ", "topology"),
        ("unlisted: spatial scale", "spatial-scale"),
        ("unlisted:spatial-scale", "spatial-scale"),
        ("false  comprehension", "false-comprehension"),
    ],
)
def test_normalize_diagnosis(raw: str, expected: str) -> None:
    assert normalize_diagnosis(raw) == expected


# --------------------------------------------------------------------------
# Envelope repair: the tag the model reaches for vs the tag the schema wants
# --------------------------------------------------------------------------


def test_class_name_tags_are_repaired_not_spent_on_another_model_call() -> None:
    """A real run died on `kind: "checkquestion"`. The discriminator is
    `question`; `CheckQuestion` is the class name, which is what the model can
    see in the schema and what it reached for under load.

    The intent is unambiguous, so this is a serialization slip repaired like a
    markdown fence -- not a wrong educational decision, and not worth a second
    model call.
    """
    from agent.generate import _load

    payload = {
        "title": "Graph DSA",
        "assumed_entry": "Basic DSA.",
        "target_capability": "Pick the right algorithm.",
        "sections": [
            {
                "heading": "Representations",
                "blocks": [
                    {"kind": "prose", "text": "Adjacency list is the default."},
                    {
                        "kind": "checkquestion",
                        "prompt": "Which for sparse graphs?",
                        "answer": "Adjacency list.",
                    },
                    {"kind": "WorkedExample", "title": "BFS", "steps": ["queue = [s]"]},
                    {"kind": "bullet_list", "ordered": False, "items": ["V + E space"]},
                ],
            }
        ],
    }
    document, retagged = _load(json.dumps(payload))
    assert retagged == 3
    assert [b.kind for b in document.sections[0].blocks] == [
        "prose",
        "question",
        "example",
        "list",
    ]


def test_an_unknown_kind_is_not_guessed_at() -> None:
    """`paragraph` might have meant prose, or might have meant something we do
    not have. Deciding for the model is how a wrong document looks right --
    only class-name derivations are repaired."""
    from agent.generate import _retag

    block = {"kind": "paragraph", "text": "x"}
    assert _retag(block) == 0
    assert block["kind"] == "paragraph"


def test_the_repair_prompt_asks_for_the_whole_document() -> None:
    """The second failure in that run was worse than the first: the model replied
    with a single `{"kind": "prose", ...}` block, because the old prompt said
    "reply with the corrected JSON object only" beside an error naming
    `sections.0.blocks.3`. A recoverable slip became a total loss."""
    import inspect

    from agent.generate import _parse_or_repair

    source = inspect.getsource(_parse_or_repair)
    assert "COMPLETE document" in source
    assert "not a request to" in source
