"""Verification for step 2 — the model writes content, and nothing else.

Most of this runs without an API key: the contract lives in `validate_section`,
and a fake client exercises the retry loop. Only `test_live_*` needs a key, and
it is skipped without one.

    python -m pytest agent/tests -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import (
    FillError,
    build_prompt,
    fill,
    have_key,
    load_plan,
    validate_section,
)
from agent.fill import SYSTEM

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plans" / "module-01.json"


def plan():
    return load_plan(json.loads(PLAN.read_text(encoding="utf-8")))


def section_with_prose():
    """SECTION 2 — para, subheading, para, code, callout."""
    return plan().sections[5], 5


def good_payload():
    return {"blocks": [
        {"id": 0, "type": "para", "text": "Two APIs dominate for builders today."},
        {"id": 1, "type": "subheading", "text": "OpenAI: Chat Completions"},
        {"id": 2, "type": "para", "text": "The SDK wraps `POST /v1/chat/completions`."},
        {"id": 3, "type": "code", "text": "import os\nprint(os.getenv('K'))"},
        {"id": 4, "type": "callout", "text": "Low temperature is not a quality dial."},
    ]}


# ------------------------------------------------------------------ plan


def test_plan_validates():
    p = plan()
    assert p.title and len(p.sections) == 6


def test_plan_carries_no_prose():
    """A plan declares briefs and caps. Content is what fill() adds."""
    for section in plan().sections:
        for spec in section.blocks:
            assert not hasattr(spec, "text")


# ---------------------------------------------------------------- prompt


def test_prompt_states_every_constraint_it_checks():
    """Contract 8: what the verifier checks is also stated in the prompt.

    Relying on validation alone burns retries on failures that a sentence in
    the prompt would have prevented.
    """
    section, i = section_with_prose()
    prompt = build_prompt(plan(), section, i)
    assert "max_words=65" in prompt          # per-block caps
    assert "lang=python" in prompt
    assert "file=openai_basic.py" in prompt
    assert "max_lines=26" in prompt
    assert "label=CODE NOTE" in prompt
    assert "ids [0, 1, 2, 3, 4]" in prompt   # exact ids and order
    assert "Never write HTML" in SYSTEM
    assert "may not add a block" in SYSTEM


def test_prompt_omits_passthrough_blocks():
    """Figures are authored, not written. They must not appear as work items."""
    p = plan()
    section = p.sections[4]                   # SECTION 1 contains a figure
    prompt = build_prompt(p, section, 4)
    assert "type=figure" not in prompt
    assert "BLOCKS TO WRITE (3)" in prompt    # 2 paras + 1 callout, not the figure


# ------------------------------------------------------------ validation


def test_accepts_a_correct_response():
    section, i = section_with_prose()
    blocks, findings = validate_section(section, good_payload(), i)
    assert [b.type for b in blocks] == ["para", "subheading", "para", "code", "callout"]
    assert findings == []


def test_passthrough_blocks_are_restored_in_position():
    """The figure is not sent to the model, but must come back in its slot."""
    p = plan()
    section = p.sections[4]
    payload = {"blocks": [
        {"id": 0, "type": "para", "text": "One."},
        {"id": 1, "type": "para", "text": "Two."},
        {"id": 3, "type": "callout", "text": "Three."},
    ]}
    blocks, _ = validate_section(section, payload, 4)
    assert [b.type for b in blocks] == ["para", "para", "figure", "callout"]
    assert blocks[2].layers[0].width == 56    # untouched


@pytest.mark.parametrize("mutate,expect", [
    (lambda d: d["blocks"].append({"id": 5, "type": "para", "text": "extra"}),
     "expected exactly 5 blocks"),
    (lambda d: d["blocks"].pop(),
     "expected exactly 5 blocks"),
    (lambda d: d["blocks"][1].update(type="para"),
     "must be type 'subheading'"),
    (lambda d: d["blocks"][0].update(text="<b>markup</b>"),
     "contains HTML"),
    (lambda d: d["blocks"][3].pop("text"),
     "missing field"),
    (lambda d: d["blocks"][0].pop("id"),
     'needs an integer "id"'),
])
def test_rejects_structural_deviation(mutate, expect):
    """Structure is fixed by the plan. Anything else is a failure, not a note."""
    section, i = section_with_prose()
    payload = good_payload()
    mutate(payload)
    with pytest.raises(FillError) as e:
        validate_section(section, payload, i)
    assert expect in str(e.value)


def test_over_cap_is_a_finding_not_a_failure():
    """A 95-word paragraph against a 90-word cap is a note. Caps guide the
    writer; structure is what breaks a document."""
    section, i = section_with_prose()
    payload = good_payload()
    payload["blocks"][0]["text"] = "word " * 200
    blocks, findings = validate_section(section, payload, i)
    assert blocks
    assert any(f.kind == "cap" for f in findings)


def test_list_count_mismatch_is_a_finding():
    p = plan()
    section = p.sections[1]                   # LEARNING OBJECTIVES, count=6
    payload = {"blocks": [{"id": 0, "type": "list", "items": ["a", "b", "c"]}]}
    blocks, findings = validate_section(section, payload, 1)
    assert len(blocks[0].items) == 3
    assert any(f.kind == "count" for f in findings)


# ----------------------------------------------------------- retry loop


class FakeClient:
    """Replays scripted responses so the retry loop can be tested offline."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        self.model = "fake"

    def complete(self, system, user, temperature=0.2):
        self.calls += 1
        return self.replies.pop(0)


def one_section_plan():
    p = plan()
    p.sections = [p.sections[5]]
    return p


def test_retries_with_the_reason_attached():
    bad = json.dumps({"blocks": good_payload()["blocks"][:3]})   # too few
    good = json.dumps(good_payload())
    client = FakeClient([bad, good])
    result = fill(one_section_plan(), client)
    assert client.calls == 2
    assert result.attempts == 2
    assert len(result.document.sections[0].blocks) == 5


def test_gives_up_after_the_ceiling():
    bad = json.dumps({"blocks": []})
    client = FakeClient([bad, bad, bad])
    with pytest.raises(FillError) as e:
        fill(one_section_plan(), client)
    assert "after 3 attempts" in str(e.value)


def test_tolerates_fenced_and_chatty_responses():
    """Models wrap JSON in fences or commentary despite instructions."""
    wrapped = "Here you go:\n```json\n" + json.dumps(good_payload()) + "\n```\nHope that helps!"
    client = FakeClient([wrapped])
    result = fill(one_section_plan(), client)
    assert client.calls == 1
    assert result.document.sections[0].blocks[0].type == "para"


def test_filled_document_renders():
    """The whole point: a filled plan is a real Document the engine accepts."""
    from engine import merge

    client = FakeClient([json.dumps(good_payload())])
    result = fill(one_section_plan(), client)
    html = merge(result.document)
    assert "Two APIs dominate" in html
    assert "<code class=\"chip\">POST /v1/chat/completions</code>" in html


# ------------------------------------------------------------------ live


@pytest.mark.skipif(not have_key(), reason="OPENROUTER_API_KEY not set")
@pytest.mark.live
def test_live_three_runs_all_valid():
    """Step 2's success criterion: regenerate the same section three times and
    get three valid documents."""
    from agent import make_client

    client = make_client()
    p = one_section_plan()
    for run in range(3):
        result = fill(p, client)
        types = [b.type for b in result.document.sections[0].blocks]
        assert types == ["para", "subheading", "para", "code", "callout"], run
