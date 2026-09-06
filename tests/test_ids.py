"""Build Spec §4 -- content addressing.

Step 1 of the build order. Everything later rests on these holding.
"""

from __future__ import annotations

import uuid

import pytest

from backend.ids import (
    CanonicalisationError,
    Envelope,
    canonical,
    content_hash,
    decision_ids_hash,
    envelope_from,
)

# --------------------------------------------------------------------------
# canonicalisation
# --------------------------------------------------------------------------


def test_key_order_does_not_change_bytes():
    assert canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1})


def test_nested_key_order_does_not_change_bytes():
    assert canonical({"x": {"b": 1, "a": 2}}) == canonical({"x": {"a": 2, "b": 1}})


def test_list_order_does_change_bytes():
    # Sequence order is meaningful; only mapping key order is not.
    assert canonical([1, 2]) != canonical([2, 1])


def test_no_whitespace():
    assert canonical({"a": [1, 2]}) == b'{"a":[1,2]}'


def test_non_ascii_is_not_escaped():
    assert canonical({"k": "café"}) == '{"k":"café"}'.encode()


# --------------------------------------------------------------------------
# floats are rejected, not rounded
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", [1.0, 0.1, -2.5, 1e300])
def test_float_rejected(value):
    with pytest.raises(CanonicalisationError, match="float"):
        canonical({"n": value})


def test_float_rejected_when_nested():
    with pytest.raises(CanonicalisationError, match=r"\$\.a\.b\[1\]"):
        canonical({"a": {"b": [1, 0.5]}})


def test_int_and_bool_accepted():
    assert canonical({"i": 3, "t": True, "f": False, "n": None}) == (
        b'{"f":false,"i":3,"n":null,"t":true}'
    )


# --------------------------------------------------------------------------
# unicode normalisation
# --------------------------------------------------------------------------


def test_nfc_normalises_equivalent_strings():
    composed = "café"  # U+00E9
    decomposed = "café"  # e + combining acute
    assert composed != decomposed
    assert canonical({"k": composed}) == canonical({"k": decomposed})


def test_normalisation_key_collision_is_an_error():
    # Both keys normalise to "café". Silently dropping one would change the
    # hash without changing intent.
    with pytest.raises(CanonicalisationError, match="collision"):
        canonical({"café": 1, "café": 2})


# --------------------------------------------------------------------------
# rejected types
# --------------------------------------------------------------------------


def test_unsupported_type_rejected():
    with pytest.raises(CanonicalisationError, match="unsupported type"):
        canonical({"d": object()})


def test_non_string_key_rejected():
    with pytest.raises(CanonicalisationError, match="non-string key"):
        canonical({1: "a"})


def test_uuid_accepted_as_string():
    u = uuid.UUID("11111111-2222-3333-4444-555555555555")
    assert canonical({"id": u}) == canonical({"id": str(u)})


# --------------------------------------------------------------------------
# decision_ids_hash -- invariant 1
# --------------------------------------------------------------------------


def test_decision_ids_hash_is_order_independent():
    a, b, c = (uuid.uuid4() for _ in range(3))
    assert decision_ids_hash([a, b, c]) == decision_ids_hash([c, a, b])


def test_decision_ids_hash_is_duplicate_independent():
    a, b = uuid.uuid4(), uuid.uuid4()
    assert decision_ids_hash([a, a, b]) == decision_ids_hash([a, b])


def test_decision_ids_hash_accepts_str_and_uuid_alike():
    a, b = uuid.uuid4(), uuid.uuid4()
    assert decision_ids_hash([a, b]) == decision_ids_hash([str(a), str(b)])


def test_different_sets_differ():
    a, b = uuid.uuid4(), uuid.uuid4()
    assert decision_ids_hash([a]) != decision_ids_hash([a, b])


# --------------------------------------------------------------------------
# Envelope -- invariant 2
# --------------------------------------------------------------------------


def _envelope(**overrides):
    base = dict(
        kind="relevance",
        member_id=None,
        inputs=[(uuid.UUID(int=1), "h1"), (uuid.UUID(int=2), "h2")],
        model="claude-opus-5",
        prompt_version="relevance@3",
        effort="high",
        params={"max_tokens": 16000},
        taxonomy_version="2026-09-05",
        asset_version=None,
        source_versions=[],
        system_instructions_hash="sys-abc",
    )
    base.update(overrides)
    return envelope_from(**base)


def test_envelope_hash_is_stable():
    assert _envelope().hash() == _envelope().hash()


def test_envelope_input_order_does_not_matter():
    forward = _envelope(inputs=[(uuid.UUID(int=1), "h1"), (uuid.UUID(int=2), "h2")])
    reverse = _envelope(inputs=[(uuid.UUID(int=2), "h2"), (uuid.UUID(int=1), "h1")])
    assert forward.hash() == reverse.hash()


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "claude-sonnet-5"),
        ("prompt_version", "relevance@4"),
        ("effort", "medium"),
        ("taxonomy_version", "2026-10-01"),
        ("asset_version", "v12"),
        ("system_instructions_hash", "sys-xyz"),
        ("params", {"max_tokens": 8000}),
    ],
)
def test_every_envelope_field_changes_the_hash(field, value):
    """The envelope rule: anything that can change the output is in the hash.

    If one of these stops mattering, the memo returns a result computed under
    conditions that no longer hold.
    """
    assert _envelope().hash() != _envelope(**{field: value}).hash()


def test_input_output_hash_changes_the_envelope_hash():
    # An upstream decision re-deriving to a different output must invalidate
    # the memo of everything downstream.
    before = _envelope(inputs=[(uuid.UUID(int=1), "h1")])
    after = _envelope(inputs=[(uuid.UUID(int=1), "h1-changed")])
    assert before.hash() != after.hash()


def test_source_version_bump_changes_the_hash():
    before = _envelope(source_versions=[("statute-1", "v3")])
    after = _envelope(source_versions=[("statute-1", "v4")])
    assert before.hash() != after.hash()


def test_tool_output_change_changes_the_hash():
    before = _envelope(tool_outputs=[("retrieval", "r1")])
    after = _envelope(tool_outputs=[("retrieval", "r2")])
    assert before.hash() != after.hash()


def test_envelope_is_frozen():
    env = _envelope()
    with pytest.raises((AttributeError, TypeError)):
        env.model = "something-else"  # type: ignore[misc]


def test_unsorted_pairs_rejected_on_direct_construction():
    with pytest.raises(CanonicalisationError, match="must be sorted"):
        Envelope(
            kind="relevance",
            member_id=None,
            inputs=(("b", "h2"), ("a", "h1")),
            model="claude-opus-5",
            prompt_version="p@1",
            effort="high",
            params={},
            taxonomy_version="t",
            asset_version=None,
            source_versions=(),
            system_instructions_hash="s",
        )


def test_member_scope_changes_the_hash():
    m = uuid.uuid4()
    assert _envelope(member_id=None).hash() != _envelope(member_id=m).hash()


def test_content_hash_is_sha256_hex():
    h = content_hash({"a": 1})
    assert len(h) == 64 and set(h) <= set("0123456789abcdef")
