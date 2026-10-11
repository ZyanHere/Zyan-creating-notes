"""`envelope()` -- the identity of a derived decision. TD §5.1.

    Envelope = first 16 bytes of SHA-256( canonical_json({
        "v":      1,
        "kind":   <DecisionKind | "memo" | "document">,
        "member": <member identity, or "" for a root decision>,
        "inputs": { ... },
        "env":    { ... }
    }) )

An envelope addresses **the output of a function**, and §5.1a states the limit of that
claim plainly enough to be worth repeating where someone will read it:

    it DOES guarantee      at most one committed result per key, and that a HIT returns
                           *a* result derived under exactly this declared environment
    it does NOT guarantee  byte-identical regeneration -- `temperature > 0` is
                           non-deterministic, and a provider may revise a model behind a
                           stable `model_id`

So pinning the environment makes an approval **auditable**, not **reproducible**. §E2's
*"a reused result is a valid result, not the result"* is that sentence made operational.

----

**One deviation from §5.1's literal text, and it is a reading of the design rather than a
change to it.** §5.1 gives the kind domain as `DecisionKind | "memo" | "document"`, which
does not admit `routing` -- yet four other places require a routing envelope to exist:
§5.9a specifies its inputs and env field by field, §5.10's summary table carries a
`routing` row with family `version`, §5.12a keys the `routing` claim domain on
*"§5.9a's routing envelope"*, and I18 gives `RoutingResult`'s identity as *"the routing
envelope (§5.9a)"*. §5.2 separately lumps `routing` with `render` and `source_extract` as
*"not envelope kinds at all"* -- which is right about those two (they are keyed on
`{document_id, render_env_hash}` and `{source_content_hash, extractor_version}`, neither
an envelope) and wrong about `routing`.

`routing` is therefore admitted here, and it is **not** a `DecisionKind`: its result row is
`RoutingResult`, not a `DecisionVersion`, so it gets no slot, no `version_number` and no
place in a `Commitment`. This is the same defect class §5.12 names -- *"the document said
this is the only envelope construction and then used one the construction does not
admit"* -- and §5.1's enumeration is the stale half, since §5.9a was added precisely
because *"five kinds never got the field-by-field treatment."*
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, NewType

from core.identity import member as member_mod
from core.identity.canonical import Canonical, digest_128

Envelope = NewType("Envelope", bytes)
"""16 bytes. A distinct type from `TaskKey` and `ClaimKey` so that handing one to the
other is a type error and not only a hash mismatch found at runtime."""

type DecisionKind = Literal[
    "situation",
    "job",
    "scope_tier",
    "frame",
    "structure",
    "projection",
    "scope",
    "partition",
    "sections",
    "ordering",
]
"""The kinds that produce a `DecisionVersion`: a slot, a `version_number`, dependency
edges, and a place in a `Commitment`."""

type EnvelopeKind = DecisionKind | Literal["memo", "document", "routing"]
"""Everything `envelope()` admits. `memo` and `document` are envelope kinds without being
decisions; `routing` is the deviation documented in this module's docstring."""

ENVELOPE_FORMAT_VERSION = 1
"""`v` in every payload. §5.1: makes a widening non-breaking."""

DECISION_KINDS: frozenset[str] = frozenset(
    {
        "situation",
        "job",
        "scope_tier",
        "frame",
        "structure",
        "projection",
        "scope",
        "partition",
        "sections",
        "ordering",
    }
)
"""The ten, as a runtime set. Needed separately from `MEMBER_SHAPE` because that table also
carries `memo`, `document` and `routing` -- kinds with envelopes that are **not** decisions.
`claim_key.decision()` must reject those three: their claim domains are `memo`, `document`
and `routing`, not `decision:memo`. `test_decision_kinds_matches_the_type` pins this set to
`DecisionKind`."""

SHARED_KINDS: frozenset[str] = frozenset({"scope_tier", "frame", "structure"})
"""§5.2a. A **static** set, because it is a design statement and not configuration: these
are the three decisions whose output is a property of the subject rather than of the
project. Adding a fourth needs §6's argument, not a config edit."""

MEMBER_SHAPE: Mapping[str, member_mod.MemberShape] = {
    # Root -- a project-level decision with no member (§5.11a).
    "situation": member_mod.MemberShape.ROOT,
    "job": member_mod.MemberShape.ROOT,
    "scope_tier": member_mod.MemberShape.ROOT,
    "frame": member_mod.MemberShape.ROOT,
    "structure": member_mod.MemberShape.ROOT,
    "projection": member_mod.MemberShape.ROOT,
    "scope": member_mod.MemberShape.ROOT,
    "partition": member_mod.MemberShape.ROOT,
    "routing": member_mod.MemberShape.ROOT,
    # A level, not an entity: "modules" | "sections:<module_id>".
    "ordering": member_mod.MemberShape.ORDERING,
    # A bare assigned id (S14).
    "sections": member_mod.MemberShape.MEMBER,  # module_id
    "memo": member_mod.MemberShape.MEMBER,  # section_id
    "document": member_mod.MemberShape.MEMBER,  # module_id
}
"""§5.11a's table, as the thing `envelope()` enforces. Every kind appears exactly once --
`test_every_envelope_kind_declares_a_member_shape` asserts the two stay in step, so a new
kind cannot be added without deciding its member."""


def is_shared(kind: EnvelopeKind) -> bool:
    """§5.2a. One predicate, and sharedness is a property of a kind, not a kind of its own.

    Rev. 4's `SHARED` pseudo-kind was withdrawn: there is one decision domain, and this
    selects the shared path in `PUBLISH` (§7.3a) and `step_shared` (§7.3b).
    """
    return kind in SHARED_KINDS


def envelope(
    kind: EnvelopeKind,
    member: member_mod.Member,
    inputs: Mapping[str, Canonical],
    env: Mapping[str, Canonical],
) -> Envelope:
    """The envelope for one derived decision.

    `member` is checked against §5.11a's shape for this kind, so a `memo` with a root
    member or a `structure` with a section id is rejected at construction rather than
    becoming a duplicate row behind a UNIQUE constraint that NULLs made permissive.
    """
    shape = MEMBER_SHAPE.get(kind)
    if shape is None:
        raise ValueError(f"{kind!r} is not an envelope kind (§5.1, and this module's note)")
    member_mod.check(member, shape)

    return Envelope(
        digest_128(
            {
                "v": ENVELOPE_FORMAT_VERSION,
                "kind": kind,
                "member": member,
                "inputs": inputs,
                "env": env,
            }
        )
    )


def all_envelope_kinds() -> tuple[str, ...]:
    """Every admissible kind -- read off `MEMBER_SHAPE`, which is already exhaustive.

    Not a second hand-written list, and not reflection over the type alias either: the
    table is the source, and `test_member_shape_table_matches_the_type` pins it to
    `EnvelopeKind` so neither can drift. Reflection belongs in the test, where being
    fragile is cheap and visible.
    """
    return tuple(MEMBER_SHAPE)
