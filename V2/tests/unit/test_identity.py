"""§15.2's golden table -- *"this is what makes U1 safe"*.

    for kind in ALL_KINDS:
      for field in INCLUDED[kind]:  mutate -> assert envelope CHANGES
      for field in EXCLUDED[kind]:  mutate -> assert envelope UNCHANGED

**The exclusion half is the acceptance bar**, and it is generated rather than listed.
`INCLUDED` comes from `SPECS[kind]`, and `EXCLUDED` is *every other field in the context* --
so the suite asserts that `structure` ignores not merely `entry_point` and `project_id`
but every one of the ~30 facts a project has. A hand-written exclusion list would have to
be extended every time the context grows, which is the drift §5.11 exists to prevent.

§15.2's named cases are then written out separately on top. They are redundant against the
generated sweep and worth having anyway: the design names them, so a reader looking for
*"where is T6's 40-section saving tested"* should find a test with that name.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import get_args

import pytest

from core.identity import kinds, member
from core.identity.canonical import Canonical, dumps, sort_canonically

# Imported by name, not as a module: `core.identity` re-exports the FUNCTION `claim_key`,
# which shadows the module of the same name (see that package's docstring). Three of the
# seven modules have this property, and naming what you want is the fix.
from core.identity.claim_key import (
    CLAIM_DOMAIN_FAMILIES,
    MEMO,
    RENDER,
    ROUTING,
    ClaimDomain,
    claim_key,
    decision,
    family_of,
)
from core.identity.content import content_hash, content_ref
from core.identity.envelope import (
    DECISION_KINDS,
    MEMBER_SHAPE,
    SHARED_KINDS,
    DecisionKind,
    EnvelopeKind,
    all_envelope_kinds,
    envelope,
    is_shared,
)
from core.identity.fingerprint import request_fingerprint
from core.identity.task_key import TASK_INPUTS, TaskKind, task_key

MODULE_ID = "6f1c2d33-0000-4000-8000-000000000001"
SECTION_ID = "6f1c2d33-0000-4000-8000-000000000002"

# Typed up front rather than spread through the tests. Unpacking a value back out of the
# context (`[*ctx["source_set"], ...]`) loses its type, because a context value is the
# whole `Canonical` union -- so the shapes that get rebuilt live here instead.
STATUTE_SOURCE: Canonical = {"content_hash": "bb" * 32, "kind": "statute", "extractor_version": 1}
STATUTE_SOURCE_V2: Canonical = {
    "content_hash": "bb" * 32,
    "kind": "statute",
    "extractor_version": 2,
}
SYLLABUS_SOURCE: Canonical = {
    "content_hash": "0f" * 32,
    "kind": "syllabus",
    "extractor_version": 1,
}
FRAME_READINGS: Mapping[str, Canonical] = {
    "subject": "contract law",
    "purpose": "exam preparation",
}
MEMO_KEYS: list[Canonical] = ["0a" * 16, "0b" * 16]

# Everything knowable about a project: the fields some kind reads, AND the fields that
# exist and must never reach certain kinds. The second group is what gives the exclusion
# sweep its teeth, so each one is here because the design names it as excluded somewhere.
BASE_CONTEXT: Mapping[str, Canonical] = {
    # -- read by some kind ----------------------------------------------------------
    "transcript_hash": "aa" * 32,
    "situation_version_id": "1111",
    "job_version_id": "2222",
    "scope_tier_version_id": "3333",
    "structure_version_id": "4444",
    "projection_version_id": "5555",
    "scope_version_id": "6666",
    # Present, and read by NO kind -- that is the Rev. 12 contract. Having it here puts it
    # into the exclusion sweep for all 13 kinds, so the guard is not only the named
    # regression test below.
    "partition_version_id": "7000",
    "subject_key": "indian contract act 1872",
    "purpose_reading": "exam preparation",
    "target_capability_reading": "answer problem questions",
    "source_set": [STATUTE_SOURCE],
    "frame": {"axis": "statute", "value": "IN-ICA-1872"},
    "frame_selecting_readings": FRAME_READINGS,
    "module_id": MODULE_ID,
    "module_covers_hash": "cc" * 32,
    "member_producer_version_id": "7777",
    "member_identity_list_hash": "dd" * 32,
    "bound_constraints_hash": "ee" * 32,
    "section_id": SECTION_ID,
    "brief_inputs_hash": "ff" * 32,
    "front_matter_hash": "ab" * 32,
    "section_memo_keys": MEMO_KEYS,
    "builder_version": "ac" * 32,
    "correction_utterance_id": "8888",
    "current_decision_set_hash": "ad" * 32,
    # -- environment ----------------------------------------------------------------
    "model_id": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "prompt_version": "derive_v2",
    "taxonomy_version": "tax_v3",
    "frontier": 400,
    "decode_params": {"temperature": 0, "top_p": 1, "max_tokens": 4096},
    # -- present, and excluded from at least one kind -------------------------------
    "project_id": "9999",  # structure: sharing must survive (§5.3)
    "user_id": "aaaa",  # structure: same
    "entry_point": "no prior exposure",  # structure, frame: granularity is projected
    "capacity": "one weekend",  # memo: not rendered by the brief (§5.7a)
    "depth_register": "section wise",  # memo: same
    "commitment_id": "bbbb",  # memo (T6), document (§0.3)
    "template": "exam-notes",  # every kind: presentation (§12)
    "capability_declaration": "cd_v1",  # structure: computed, never derived (D5)
    "density_constants": {"words_per_concept": 120},  # scope: Extent is computed (C1)
    "candidates": ["IN", "UK"],  # frame: no catalogue exists (§6.3a)
    "sibling_section_hash": "ae" * 32,  # memo: independence is measured
}

MEMBER_FOR_KIND: Mapping[str, str] = {
    "sections": member.module(MODULE_ID),
    "document": member.module(MODULE_ID),
    "memo": member.section(SECTION_ID),
    "ordering": member.ordering_sections(MODULE_ID),
}


def context_for(kind: str) -> dict[str, Canonical]:
    ctx = dict(BASE_CONTEXT)
    ctx["member"] = MEMBER_FOR_KIND.get(kind, member.root())
    return ctx


def mutate(value: Canonical) -> Canonical:
    """A different value of the same shape. Enough to move a hash, nothing clever."""
    if value is None:
        return "now-present"
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return value + "-mutated"
    if isinstance(value, Mapping):
        return {**value, "mutated": 1}
    return [*value, "mutated"]


def mutated_context(kind: str, field: str) -> dict[str, Canonical]:
    ctx = context_for(kind)
    ctx[field] = mutate(ctx[field])
    return ctx


# ── the generated golden table ────────────────────────────────────────────────────────

ALL_KINDS = all_envelope_kinds()


def included_fields(kind: str) -> tuple[str, ...]:
    spec = kinds.SPECS[kind]
    return spec.inputs + spec.env


def excluded_fields(kind: str) -> tuple[str, ...]:
    read = set(included_fields(kind))
    return tuple(field for field in BASE_CONTEXT if field not in read)


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_every_included_field_changes_the_envelope(kind: EnvelopeKind) -> None:
    """The inclusion half. Easy, and it would be a glaring bug to fail."""
    baseline = kinds.build(kind, context_for(kind))
    for field in included_fields(kind):
        assert kinds.build(kind, mutated_context(kind, field)) != baseline, (
            f"{kind}: mutating {field!r} did not change the envelope, but §5.3-§5.9a "
            f"lists it as an input"
        )


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_no_excluded_field_changes_the_envelope(kind: EnvelopeKind) -> None:
    """**The acceptance bar.** Every project fact this kind does not read, swept.

    A failure here means an envelope is over-inclusive, and over-inclusion is the
    expensive direction: it re-derives work that was already correct. T6 measures one
    instance at 40 sections x ~65s.
    """
    baseline = kinds.build(kind, context_for(kind))
    for field in excluded_fields(kind):
        assert kinds.build(kind, mutated_context(kind, field)) == baseline, (
            f"{kind}: mutating {field!r} changed the envelope, but it is not in this "
            f"kind's input or env list (§5.3-§5.9a)"
        )


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_every_kind_reads_at_least_one_input(kind: EnvelopeKind) -> None:
    """A kind with no inputs would give every project one shared envelope."""
    assert included_fields(kind), f"{kind} has an empty field specification"


# ── §15.2's named cases, written out because the design names them ────────────────────


def test_structure_ignores_entry_point() -> None:
    """Granularity is projected `[LOCKED §8]`.

    §1's *"API foundations never in the graph"* is a granularity failure, and Projection
    owns it. A learner property cannot change the subject's shape.
    """
    base = kinds.build("structure", context_for("structure"))
    assert kinds.build("structure", mutated_context("structure", "entry_point")) == base


def test_structure_ignores_project_id_so_sharing_survives() -> None:
    """D11's sharing is the entire reason `structure` is content-addressed (§5.2).

    Two students at different universities, same subject, no sources: same envelope, one
    derivation, the second project pays nothing.
    """
    base = kinds.build("structure", context_for("structure"))
    assert kinds.build("structure", mutated_context("structure", "project_id")) == base
    assert kinds.build("structure", mutated_context("structure", "user_id")) == base


def test_structure_changes_when_a_source_is_added() -> None:
    ctx = context_for("structure")
    base = kinds.build("structure", ctx)
    with_source: list[Canonical] = [STATUTE_SOURCE, SYLLABUS_SOURCE]
    assert kinds.build("structure", {**ctx, "source_set": with_source}) != base


def test_structure_changes_when_the_extractor_is_upgraded() -> None:
    """§5.3b. Structure consumes the extracted skeleton, not the raw bytes.

    Without `extractor_version` in each source's contribution, an extractor upgrade
    produces a better skeleton that is then silently ignored.
    """
    ctx = context_for("structure")
    base = kinds.build("structure", ctx)
    upgraded: list[Canonical] = [STATUTE_SOURCE_V2]
    assert kinds.build("structure", {**ctx, "source_set": upgraded}) != base


def test_frame_changes_on_sources() -> None:
    """§6.3's bug: the subject alone is NOT the key."""
    base = kinds.build("frame", context_for("frame"))
    assert kinds.build("frame", mutated_context("frame", "source_set")) != base


def test_frame_changes_on_purpose() -> None:
    """Purpose can name a jurisdiction, which is what a frame selects."""
    ctx = context_for("frame")
    base = kinds.build("frame", ctx)
    readings: Canonical = {**FRAME_READINGS, "purpose": "UK bar exam"}
    assert kinds.build("frame", {**ctx, "frame_selecting_readings": readings}) != base


def test_frame_ignores_entry_point() -> None:
    """A learner property cannot make a relation true or false."""
    base = kinds.build("frame", context_for("frame"))
    assert kinds.build("frame", mutated_context("frame", "entry_point")) == base


def test_frame_ignores_candidates() -> None:
    """§6.3a -- no catalogue exists, so candidates cannot be an input."""
    base = kinds.build("frame", context_for("frame"))
    assert kinds.build("frame", mutated_context("frame", "candidates")) == base


def test_memo_ignores_commitment_id() -> None:
    """**T6, and the largest avoidable cost in the system.**

    The measured project has 8 modules and 40 sections. A correction touching module 5
    mints a new commitment; a commitment-keyed memo would re-spend all 40 sections at
    ~65s each. Section-content keying re-spends only what changed.
    """
    base = kinds.build("memo", context_for("memo"))
    assert kinds.build("memo", mutated_context("memo", "commitment_id")) == base


def test_memo_ignores_a_sibling_section() -> None:
    """Independence is the measured property: `_unit_brief` reads the request, the
    situation and its own order -- nothing from a prior section."""
    base = kinds.build("memo", context_for("memo"))
    assert kinds.build("memo", mutated_context("memo", "sibling_section_hash")) == base


def test_memo_ignores_capacity_and_depth_register() -> None:
    """§5.7a -- neither is rendered by the brief, so neither may invalidate written
    content."""
    base = kinds.build("memo", context_for("memo"))
    assert kinds.build("memo", mutated_context("memo", "capacity")) == base
    assert kinds.build("memo", mutated_context("memo", "depth_register")) == base


def test_memo_changes_on_the_brief() -> None:
    """The brief IS the input, so the envelope is the brief (§5.7a).

    §15.2's `mutate disclosed shortfalls -> CHANGES` lives inside `BriefInputs`, whose
    field list needs `core/types` and is the next task. What is assertable now is that the
    hash standing for the brief is load-bearing; `test_brief_hash_matches_renderer`
    arrives with the renderer, and until it does the envelope's honesty rests on one
    `BriefInputs` value having two consumers rather than on a test.
    """
    base = kinds.build("memo", context_for("memo"))
    assert kinds.build("memo", mutated_context("memo", "brief_inputs_hash")) != base


def test_document_changes_on_builder_version() -> None:
    """The Document Builder is a pure function whose output changes when its code does."""
    base = kinds.build("document", context_for("document"))
    assert kinds.build("document", mutated_context("document", "builder_version")) != base


def test_document_ignores_commitment_id() -> None:
    """§0.3 -- including it would mint a new Document on every re-approval and supersede
    every prior artifact for nothing, so `superseded(d)` would stop being meaningful."""
    base = kinds.build("document", context_for("document"))
    assert kinds.build("document", mutated_context("document", "commitment_id")) == base


def test_document_section_order_is_semantic() -> None:
    """§5.8 -- *"two orderings of the same sections are different documents."*"""
    ctx = context_for("document")
    base = kinds.build("document", ctx)
    reversed_keys: list[Canonical] = list(reversed(MEMO_KEYS))
    assert kinds.build("document", {**ctx, "section_memo_keys": reversed_keys}) != base


def test_sections_survive_a_repartition_that_leaves_this_module_intact() -> None:
    """§15.2's `sections` case. **Regression test for Rev. 12.**

    Rev. 11 listed `partition_version_id` as a `sections` input while §5.6's own rationale
    and §15.2's golden case both required the opposite. A re-partition mints a new
    `partition` DecisionVersion by definition, so with its id in the envelope every
    module's sections were invalidated on every partition change.

    Both directions are asserted here deliberately. The first half is the fix; the second
    half is what stops the fix from being *"ignore the partition entirely"*, which would
    make a module whose covers really did change reuse stale sections.

    `ml-weekend` went 5 modules -> 3 in one correction, so the saving is measured: both
    survivors keep their sections.
    """
    ctx = context_for("sections")
    base = kinds.build("sections", ctx)

    # (1) a re-partition this module survived unchanged -> same envelope, sections reused
    repartitioned = {**ctx, "partition_version_id": "a-brand-new-partition"}
    assert kinds.build("sections", repartitioned) == base

    # (2) the same re-partition, but THIS module's covers moved -> new envelope
    recovered = {**repartitioned, "module_covers_hash": "09" * 32}
    assert kinds.build("sections", recovered) != base


def test_sections_change_when_this_modules_covers_change() -> None:
    base = kinds.build("sections", context_for("sections"))
    assert kinds.build("sections", mutated_context("sections", "module_covers_hash")) != base


def test_no_kind_reads_the_partition_version() -> None:
    """Rev. 12, stated once over every kind rather than once for `sections`.

    The partition that produced a module is **provenance, not identity** -- the same
    distinction §5.8 draws between a Document's content and its construction key, and §0.3
    draws when it keeps `commitment_id` out of the document envelope.
    """
    for kind in ALL_KINDS:
        read = set(kinds.SPECS[kind].inputs) | set(kinds.SPECS[kind].env)
        assert "partition_version_id" not in read, (
            f"{kind} reads partition_version_id; §5.6 Rev. 12 removed it, and for "
            f"`sections` it re-derives every surviving module on every re-partition"
        )


def test_scope_ignores_density_constants() -> None:
    """C1 -- `Extent` is computed from the scope, not derived with it, so recalibrating
    the constants must not invalidate `scope`. That saves a full re-plan per calibration
    run (OQ-2)."""
    base = kinds.build("scope", context_for("scope"))
    assert kinds.build("scope", mutated_context("scope", "density_constants")) == base


def test_situation_ignores_sources() -> None:
    """§5.9a -- a source is not testimony."""
    base = kinds.build("situation", context_for("situation"))
    assert kinds.build("situation", mutated_context("situation", "source_set")) == base


def test_job_ignores_structure() -> None:
    """§5.9a -- the job does not depend on the subject's shape."""
    base = kinds.build("job", context_for("job"))
    assert kinds.build("job", mutated_context("job", "structure_version_id")) == base


def test_routing_is_keyed_on_the_utterance_and_the_set_it_routed_against() -> None:
    """The same sentence against a different plan is a different routing problem."""
    base = kinds.build("routing", context_for("routing"))
    assert kinds.build("routing", mutated_context("routing", "correction_utterance_id")) != base
    assert kinds.build("routing", mutated_context("routing", "current_decision_set_hash")) != base


# ── canonical JSON ────────────────────────────────────────────────────────────────────


def test_canonical_json_stable() -> None:
    """§15.2 -- same logical input in different key orders and Unicode normalisations
    produces one envelope."""
    composed = "Kafká"  # 'a' + combining acute
    precomposed = "Kafká"  # the single codepoint
    assert composed != precomposed

    one = dumps({"b": 1, "a": composed, "c": {"y": 2, "x": 3}})
    two = dumps({"c": {"x": 3, "y": 2}, "a": precomposed, "b": 1})
    assert one == two


def test_canonical_json_sorts_keys_by_code_point() -> None:
    assert dumps({"b": 1, "a": 2, "A": 3}) == b'{"A":3,"a":2,"b":1}'


def test_canonical_json_has_no_insignificant_whitespace() -> None:
    assert dumps({"a": [1, 2]}) == b'{"a":[1,2]}'


def test_canonical_json_preserves_array_order() -> None:
    """Order is semantic for `section_memo_keys`, so the serialiser must never sort."""
    assert dumps(["b", "a"]) == b'["b","a"]'


def test_canonical_json_rejects_floats() -> None:
    """§5.1 -- a float's textual form is not stable across languages."""
    with pytest.raises(TypeError, match="floats are excluded"):
        dumps({"temperature": 0.7})  # type: ignore[dict-item]


def test_canonical_json_rejects_bytes_and_says_to_hex_it() -> None:
    """Silently hex-encoding would make `b"\\xab"` and `"ab"` one identity.

    No `type: ignore` here, and that is the interesting part: `bytes` **type-checks** as
    `Canonical`, because `bytes` is a `Sequence[int]` and `int` is in the union. So the
    annotation does not exclude it and this runtime check is the only thing that does --
    load-bearing rather than defensive.
    """
    with pytest.raises(TypeError, match=r"\.hex\(\)"):
        dumps({"envelope": b"\xab\xcd"})


def test_canonical_json_rejects_a_normalisation_collision() -> None:
    """Two distinct keys normalising to one would make the payload depend on dict order."""
    with pytest.raises(ValueError, match="insertion order"):
        dumps({"Kafká": 1, "Kafká": 2})


def test_sort_canonically_is_deterministic_for_structured_items() -> None:
    """`source_set` is *"sorted"* (§5.3) and the items are objects, so "sorted" needs one
    definition rather than one per call site."""
    a: Canonical = {"content_hash": "bb", "kind": "statute"}
    b: Canonical = {"content_hash": "aa", "kind": "syllabus"}
    assert sort_canonically([a, b]) == sort_canonically([b, a])
    assert dumps(sort_canonically([a, b])) == dumps(sort_canonically([b, a]))


# ── the three constructions are disjoint ──────────────────────────────────────────────


def test_three_key_constructions_are_disjoint() -> None:
    """T1 -- the same inputs through all three produce three different keys.

    Each payload carries a `"domain"` or `"kind"` discriminator and a different key set,
    so no two canonical payloads can ever be byte-identical.
    """
    shared_inputs: Mapping[str, Canonical] = {"module_id": MODULE_ID}

    env = envelope("sections", member.module(MODULE_ID), shared_inputs, {})
    task = task_key("generate", {"commitment_id": "bbbb", "module_id": MODULE_ID})
    claim = claim_key(decision("sections"), {"envelope": env.hex()})

    assert len({bytes(env), bytes(task), bytes(claim)}) == 3


def test_a_task_key_and_an_envelope_over_identical_inputs_differ() -> None:
    """§5.12 -- *"the `domain` field makes a task key and an envelope over identical
    inputs provably distinct."*"""
    inputs: Mapping[str, Canonical] = {"module_id": MODULE_ID}
    env = envelope("sections", member.module(MODULE_ID), inputs, {})
    task = task_key("correct", {"utterance_id": MODULE_ID})
    assert bytes(env) != bytes(task)


def test_every_key_is_128_bits() -> None:
    env = kinds.build("situation", context_for("situation"))
    task = task_key("correct", {"utterance_id": "x"})
    claim = claim_key(RENDER, {"document_id": "d", "render_env_hash": "e"})
    assert len(env) == len(task) == len(claim) == 16


# ── member encoding, §5.11a ───────────────────────────────────────────────────────────


def test_root_member_is_the_empty_string_not_none() -> None:
    """Postgres forbids a nullable PK column AND treats NULLs as distinct in UNIQUE, so a
    nullable member would let `UNIQUE (project_id, kind, member, envelope)` admit two
    versions for one envelope -- disabling §11's guard silently."""
    assert member.root() == ""
    assert member.shape_of(member.root()) is member.MemberShape.ROOT


def test_a_member_kind_rejects_a_root_member() -> None:
    """`memo` with `member=""` is the bug that produces two versions for one envelope."""
    with pytest.raises(ValueError, match=r"§5\.11a"):
        envelope("memo", member.root(), {"section_id": SECTION_ID}, {})


def test_a_root_kind_rejects_a_member() -> None:
    with pytest.raises(ValueError, match=r"§5\.11a"):
        envelope("structure", member.module(MODULE_ID), {"subject_key": "x"}, {})


def test_ordering_members_are_levels_not_entities() -> None:
    assert member.ordering_modules() == "modules"
    assert member.ordering_sections(MODULE_ID) == f"sections:{MODULE_ID}"
    assert member.shape_of(member.ordering_modules()) is member.MemberShape.ORDERING
    assert member.shape_of(member.ordering_sections(MODULE_ID)) is member.MemberShape.ORDERING


def test_an_id_cannot_collide_with_a_level_literal() -> None:
    """`""` is safe only because no real member can equal it or a level literal."""
    with pytest.raises(ValueError, match="collides"):
        member.module("modules")
    with pytest.raises(ValueError, match="collides"):
        member.module("sections:x")


def test_an_empty_or_whitespace_id_is_refused() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        member.module("")
    with pytest.raises(ValueError, match="non-empty"):
        member.section(" leading")


def test_a_root_kind_ignores_a_member_sitting_in_the_context() -> None:
    """The projection reads what the spec says and nothing else, members included."""
    ctx = context_for("structure")
    base = kinds.build("structure", ctx)
    assert kinds.build("structure", {**ctx, "member": member.module(MODULE_ID)}) == base


def test_a_member_kind_changes_with_its_member() -> None:
    ctx = context_for("memo")
    base = kinds.build("memo", ctx)
    other = {**ctx, "member": member.section("6f1c2d33-0000-4000-8000-00000000ffff")}
    assert kinds.build("memo", other) != base


# ── the tables are the single source, and stay in step with the types ─────────────────


def test_member_shape_table_matches_the_type() -> None:
    """§5.11a's table must cover exactly `EnvelopeKind` -- a new kind cannot be added
    without deciding its member."""
    decision_alias, extras = get_args(EnvelopeKind.__value__)
    from_type = set(get_args(decision_alias.__value__)) | set(get_args(extras))
    assert set(MEMBER_SHAPE) == from_type


def test_decision_kinds_matches_the_type() -> None:
    assert set(DECISION_KINDS) == set(get_args(DecisionKind.__value__))


def test_kind_specs_cover_every_envelope_kind() -> None:
    """§5.3-§5.9a must specify every kind `envelope()` admits. §5.9a exists because five
    kinds had no field-by-field treatment and §15.2 had nothing to assert for them."""
    assert set(kinds.SPECS) == set(MEMBER_SHAPE)


def test_task_inputs_table_matches_the_type() -> None:
    assert set(TASK_INPUTS) == set(get_args(TaskKind.__value__))


def test_shared_kinds_are_decision_kinds() -> None:
    """§5.2a -- sharedness is a predicate over the decision domain."""
    assert SHARED_KINDS <= DECISION_KINDS
    assert set(SHARED_KINDS) == {"scope_tier", "frame", "structure"}
    assert is_shared("structure")
    assert not is_shared("memo")


def test_the_three_shared_kinds_are_exactly_the_content_addressed_ones() -> None:
    """§5.2: content-addressed means no project-local id in the inputs, which is what
    makes sharing possible rather than nominal."""
    project_local = {"project_id", "user_id"}
    for kind in SHARED_KINDS:
        read = set(kinds.SPECS[kind].inputs) | set(kinds.SPECS[kind].env)
        assert not (read & project_local), f"{kind} is shared but reads a project-local id"


def test_there_are_exactly_six_claim_domains() -> None:
    """§5.12a states six repeatedly; a seventh added without that argument is a bug."""
    assert len(CLAIM_DOMAIN_FAMILIES) == 6
    assert set(CLAIM_DOMAIN_FAMILIES) == {
        "decision",
        "memo",
        "document",
        "render",
        "source_extract",
        "routing",
    }


# ── task keys, §5.12 and §8.1 ─────────────────────────────────────────────────────────


def test_generate_task_key_includes_the_commitment() -> None:
    """§8.1's FIX. A key of (project, generate, module_id) would return the old succeeded
    Task instead of starting the new production event -- and generating a module again
    under a new Commitment is a normal operation in the correction flow."""
    first = task_key("generate", {"commitment_id": "c1", "module_id": MODULE_ID})
    second = task_key("generate", {"commitment_id": "c2", "module_id": MODULE_ID})
    assert first != second


def test_source_extract_task_key_moves_on_an_extractor_upgrade() -> None:
    """Rev. 8. Keying on the source alone meant an extractor upgrade returned the old
    succeeded Task and no extraction ever ran -- the claim said *"new result"* while the
    Task said *"same request."*"""
    v1 = task_key("source_extract", {"source_content_hash": "bb" * 32, "extractor_version": 1})
    v2 = task_key("source_extract", {"source_content_hash": "bb" * 32, "extractor_version": 2})
    assert v1 != v2


def test_plan_task_key_moves_when_the_derivation_environment_moves() -> None:
    """§8.1's actual hole: bumping the derive prompt moves the STRUCTURE envelope and no
    other, so a plan key without it read *"already done"* and never re-planned."""
    base = {
        "structure_envelope": "0a" * 16,
        "situation_v": "1",
        "job_v": "2",
        "tier_v": "3",
        "frame_v": "4",
    }
    assert task_key("plan", base) != task_key("plan", {**base, "structure_envelope": "0b" * 16})


def test_task_key_refuses_an_unexpected_input() -> None:
    """An extra field makes a retry look like new work; a missing one makes new work look
    like a retry. Both are CF-6's error class."""
    with pytest.raises(ValueError, match="unexpected"):
        task_key("correct", {"utterance_id": "u", "project_id": "p"})


def test_task_key_refuses_a_missing_input() -> None:
    with pytest.raises(ValueError, match="missing"):
        task_key("generate", {"module_id": MODULE_ID})


# ── claim keys, §5.12a ────────────────────────────────────────────────────────────────


def test_claim_domains_are_distinct_for_one_identity() -> None:
    """One envelope, two domains, two keys -- `Claim.key` has ONE construction for all
    six domains rather than being *"an envelope, except for three cases."*"""
    env = kinds.build("memo", context_for("memo"))
    as_memo = claim_key(MEMO, {"envelope": env.hex()})
    as_routing = claim_key(ROUTING, {"envelope": env.hex()})
    assert as_memo != as_routing


def test_decision_domain_refuses_a_kind_that_is_not_a_decision() -> None:
    """`memo`, `document` and `routing` have envelopes but are not decisions: their result
    rows are `MemoIndex`, `Document` and `RoutingResult`, so none gets a slot, a
    `version_number` or a place in a `Commitment`."""
    for kind in ("memo", "document", "routing"):
        with pytest.raises(ValueError, match="not a DecisionKind"):
            decision(kind)  # type: ignore[arg-type]


def test_every_decision_kind_has_a_claim_domain() -> None:
    for kind in sorted(DECISION_KINDS):
        domain = decision(kind)  # type: ignore[arg-type]
        assert family_of(domain) == "decision"
        assert len(claim_key(domain, {"envelope": "0a" * 16})) == 16


def test_render_claim_takes_no_envelope() -> None:
    """§5.9 -- an artifact is not derived from a model call, so it has no envelope. A
    re-render under a new engine build is new work."""
    with pytest.raises(ValueError, match="unexpected"):
        claim_key(RENDER, {"envelope": "0a" * 16})

    one = claim_key(RENDER, {"document_id": "d1", "render_env_hash": "e1"})
    two = claim_key(RENDER, {"document_id": "d1", "render_env_hash": "e2"})
    assert one != two


def test_claim_key_refuses_an_unknown_domain() -> None:
    with pytest.raises(ValueError, match="not a ClaimDomain"):
        claim_key(ClaimDomain("export"), {"export_hash": "x"})


def test_export_has_no_claim_domain() -> None:
    """T4's *"one deliberate exception"* -- export's output is canonicalised, so duplicate
    work is harmless (§9.9a) and §9.10 gives it no claim."""
    assert "export" not in CLAIM_DOMAIN_FAMILIES


# ── content addressing, §4.3 ──────────────────────────────────────────────────────────


def test_content_ref_is_greppable_hex() -> None:
    digest = content_hash(b"hello")
    ref = content_ref("mynotes", "memo-payload", digest)
    assert ref == f"mynotes/memo-payload/{digest.hex()}"


def test_content_ref_refuses_a_truncated_digest() -> None:
    """A truncated hash in a write-once path is a collision waiting to overwrite committed
    bytes -- which is the exact failure content addressing exists to prevent (§4.3)."""
    with pytest.raises(ValueError, match="full sha256"):
        content_ref("mynotes", "memo-payload", content_hash(b"x")[:16])  # type: ignore[arg-type]


def test_identical_bytes_land_at_the_same_path_and_different_bytes_do_not() -> None:
    assert content_hash(b"same") == content_hash(b"same")
    assert content_hash(b"same") != content_hash(b"other")


def test_content_ref_refuses_an_unknown_kind() -> None:
    with pytest.raises(ValueError, match="not a ContentKind"):
        content_ref("mynotes", "guesswork", content_hash(b"x"))  # type: ignore[arg-type]


# ── request fingerprint, §18.3 ────────────────────────────────────────────────────────


def test_request_fingerprint_distinguishes_a_retry_from_a_reused_id() -> None:
    """Matching fingerprint -> return the existing turn. Mismatch -> 409. Without the
    column the rule §18.3 defined was unimplementable."""
    retry = request_fingerprint("user", "explain consideration")
    assert retry == request_fingerprint("user", "explain consideration")
    assert retry != request_fingerprint("user", "explain offer and acceptance")
    assert retry != request_fingerprint("system", "explain consideration")


def test_request_fingerprint_normalises_unicode() -> None:
    """The same sentence typed with a composed and a decomposed accent is one request, so
    it must not produce a spurious 409."""
    assert request_fingerprint("user", "Kafká") == request_fingerprint("user", "Kafká")


def test_request_fingerprint_is_full_width() -> None:
    assert len(request_fingerprint("user", "x")) == 32
