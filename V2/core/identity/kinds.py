"""Per-kind envelope fields, as data. TD §5.3-§5.9a, summarised in §5.10.

**Why this module exists, since the Implementation Plan's file list does not name it.**
§15.2's acceptance bar is the *exclusion* half of the golden table -- *"mutate
`entry_point` -> structure UNCHANGED"*. That assertion is vacuous against a bare
`envelope(kind, member, inputs, env)`, because a field you never passed obviously cannot
move the hash. The only non-vacuous form is a **projection** from everything known about a
project down to the fields one kind reads, and then asserting the projection drops what
§5.3-§5.9a say it drops. This is that projection, and it is here rather than in the test
so that the production path and the golden table read one table (§5.11's whole point:
*"one table that every other section points at"*).

**Transcribed against Rev. 12**, which this module's construction produced: §5.6 lost
`partition_version_id` from `sections`, §5.1's kind domain gained `routing`, and §5.4-§5.7
gained `decode_params`. All three were a fact stated in one place and contradicted in
another; see the design's own revision note.

**Two places where this applies a blanket rule over an older field list**, both from the
design's own corrections rather than a judgment of mine:

  * `decode_params` is on every model-backed kind. §5.1a and §5.9a both say so
    (*"new in Rev. 7 and applies to every model-backed kind"*), while §5.4-§5.7's env
    blocks predate Rev. 7 and do not list it. §5.10 names the one kind with no model call:
    `document`, whose env is `builder_version` alone.
  * `memo`'s env is `model_id, prompt_version, decode_params`. §5.7 writes
    *"model_id, prompt_version, max_tokens"*, and §5.1a defines
    `decode_params = {temperature, top_p, max_tokens, seed?}` -- so listing both would
    hash `max_tokens` twice under two names.

What is deliberately NOT here: how `brief_inputs_hash`, `module_covers_hash`,
`transcript_hash`, `front_matter_hash` or `source_set` are *computed*. Those need
`core/types`, which is the next task. This module takes them as opaque values, which is
also the honest shape -- each is a hash, and the kind reads the hash, not the structure.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from core.identity import member as member_mod
from core.identity.canonical import Canonical
from core.identity.envelope import Envelope, EnvelopeKind, envelope


class MemberFrom(StrEnum):
    """Where the member comes from when building this kind."""

    ROOT = "root"
    """No member -- `member.root()`. The spec gives `""` and nothing is read from context."""

    CONTEXT = "context"
    """`context["member"]`, already built by `member.py`. Which constructor applies is the
    caller's knowledge (a module id for `sections`, a section id for `memo`, a level for
    `ordering`), and `envelope()` checks the shape against §5.11a regardless."""


@dataclass(frozen=True, slots=True)
class KindSpec:
    """One row of §5.10's summary table, in the form the code reads."""

    kind: EnvelopeKind
    inputs: tuple[str, ...]
    env: tuple[str, ...]
    member_from: MemberFrom


# `decode_params` on every model-backed kind -- §5.1a, §5.9a.
_MODEL_ENV = ("model_id", "prompt_version", "decode_params")
_MODEL_ENV_TAXONOMY = ("model_id", "prompt_version", "taxonomy_version", "decode_params")

SPECS: Mapping[str, KindSpec] = {
    # ---- version-addressed, project-scoped -------------------------------------------
    "situation": KindSpec(
        kind="situation",
        # NOT sources (a source is not testimony), NOT the capability declaration
        # (computed), NOT frame or tier -- they read FROM this, per §9.1's ordering.
        inputs=("transcript_hash",),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.ROOT,
    ),
    "job": KindSpec(
        kind="job",
        # NOT structure: the job does not depend on the subject's shape. CF-2 made this
        # its own Decision.
        inputs=("transcript_hash", "situation_version_id"),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.ROOT,
    ),
    # ---- content-addressed, shareable across projects (§5.2, §5.2a) ------------------
    "scope_tier": KindSpec(
        kind="scope_tier",
        # Readings, not version ids, so two projects phrased alike share the answer.
        inputs=("subject_key", "purpose_reading", "target_capability_reading", "source_set"),
        env=_MODEL_ENV,
        member_from=MemberFrom.ROOT,
    ),
    "frame": KindSpec(
        kind="frame",
        # NOT candidates -- no catalogue exists (§6.3a). Sources ARE in: §6.3's bug was
        # treating the subject alone as the key.
        inputs=("subject_key", "source_set", "frame_selecting_readings"),
        env=_MODEL_ENV,
        member_from=MemberFrom.ROOT,
    ),
    "structure": KindSpec(
        kind="structure",
        # No situation (§0.1). `source_set` carries extractor_version per source, because
        # structure consumes the EXTRACTED skeleton, not the raw bytes (§5.3b) -- without
        # it an extractor upgrade produces a better skeleton that is silently ignored.
        inputs=("subject_key", "frame", "source_set"),
        env=("model_id", "prompt_version", "taxonomy_version", "frontier", "decode_params"),
        member_from=MemberFrom.ROOT,
    ),
    # ---- version-addressed, downstream of the roots ----------------------------------
    "projection": KindSpec(
        kind="projection",
        # Where `entry_point` first enters, via `situation_version_id`. Granularity is
        # projected, which is why `structure` must not see it (§5.3, [LOCKED §8]).
        inputs=(
            "structure_version_id",
            "situation_version_id",
            "job_version_id",
            "scope_tier_version_id",
        ),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.ROOT,
    ),
    "scope": KindSpec(
        kind="scope",
        # NOT `density_constants`: Extent is COMPUTED from the scope (C1), so recalibrating
        # changes Extent without invalidating `scope` -- that saves a full re-plan per
        # calibration run (OQ-2).
        inputs=("projection_version_id", "situation_version_id", "job_version_id"),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.ROOT,
    ),
    "partition": KindSpec(
        kind="partition",
        inputs=("scope_version_id", "situation_version_id", "job_version_id"),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.ROOT,
    ),
    "sections": KindSpec(
        kind="sections",
        # NO `partition_version_id` -- §5.6, Rev. 12, which this implementation found.
        # Rev. 11 listed it as an input while the same section's rationale and §15.2's
        # golden case both required that a re-partition leaving a module's covers intact
        # REUSES that module's sections. A re-partition mints a new partition version by
        # definition, so including it invalidated every module on every partition change.
        #
        # A module's sections are identified by its id, its covers, and the situation and
        # job. **The partition that produced it is provenance, not identity** -- the same
        # distinction §5.8 draws between a Document's content and its construction key.
        # `ml-weekend` went 5 modules -> 3 in one correction; both survivors keep theirs.
        inputs=(
            "module_id",
            "module_covers_hash",
            "situation_version_id",
            "job_version_id",
        ),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.CONTEXT,
    ),
    "ordering": KindSpec(
        kind="ordering",
        # `bound_constraints_hash` is the channel §0 measured as missing: "section wise"
        # became a depth_register and the order was then explained as derived. With the
        # constraint in the envelope a stated ordering both binds and invalidates.
        inputs=(
            "member_producer_version_id",
            "member_identity_list_hash",
            "situation_version_id",
            "job_version_id",
            "bound_constraints_hash",
        ),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.CONTEXT,
    ),
    # ---- the two envelope kinds that are not decisions -------------------------------
    "memo": KindSpec(
        kind="memo",
        # `brief_inputs_hash` ONLY (§5.7a). Excluded and provably so: `commitment_id`
        # (T6 -- the measured project is 8 modules and 40 sections, and a
        # commitment-keyed memo would re-spend all 40 at ~65s for a one-module
        # correction), sibling sections (independence is the measured property),
        # `capacity` and `depth_register` (not rendered by the brief), `template`.
        inputs=("section_id", "brief_inputs_hash"),
        env=_MODEL_ENV,
        member_from=MemberFrom.CONTEXT,
    ),
    "document": KindSpec(
        kind="document",
        # `section_memo_keys` is ORDERED, not sorted -- two orderings of the same sections
        # are different documents. `commitment_id` absent per §0.3: including it would mint
        # a new Document on every re-approval and supersede every prior artifact for
        # nothing. The commitment lives in DocumentProvenance, many-to-one.
        inputs=("front_matter_hash", "section_memo_keys"),
        # The only kind with no model call (§5.10). `builder_version` is a content hash
        # over the builder's source, because a hand-bumped constant gets forgotten and
        # this one is invisible when wrong (§5.8).
        env=("builder_version",),
        member_from=MemberFrom.CONTEXT,
    ),
    # ---- the correction router (see envelope.py's note on §5.1 vs §5.9a) -------------
    "routing": KindSpec(
        kind="routing",
        # Keyed on the utterance AND the set it routed against, because the same sentence
        # against a different plan is a different routing problem. NOT the targets it
        # returns -- that is the output.
        inputs=("correction_utterance_id", "current_decision_set_hash"),
        env=_MODEL_ENV_TAXONOMY,
        member_from=MemberFrom.ROOT,
    ),
}


def build(kind: EnvelopeKind, context: Mapping[str, Canonical]) -> Envelope:
    """Build `kind`'s envelope by projecting `context` through §5.3-§5.9a's field list.

    `context` may carry anything -- the whole of what is known about a project. The
    projection is what makes the exclusion half of §15.2 meaningful: `entry_point` can sit
    in the context untouched and `structure`'s envelope will not move, because
    `SPECS["structure"]` does not read it.
    """
    spec = SPECS.get(kind)
    if spec is None:
        raise ValueError(f"{kind!r} has no field specification (§5.3-§5.9a)")

    if spec.member_from is MemberFrom.ROOT:
        member = member_mod.root()
    else:
        supplied = context.get("member")
        if not isinstance(supplied, str):
            raise ValueError(
                f"{kind!r} takes a member, so context must carry 'member' built by "
                f"core.identity.member (§5.11a); got {type(supplied).__name__}"
            )
        member = member_mod.Member(supplied)

    return envelope(
        kind,
        member,
        _project(spec.inputs, context, kind, "inputs"),
        _project(spec.env, context, kind, "env"),
    )


def _project(
    fields: tuple[str, ...],
    context: Mapping[str, Canonical],
    kind: str,
    part: str,
) -> dict[str, Canonical]:
    missing = [field for field in fields if field not in context]
    if missing:
        raise KeyError(
            f"{kind!r} {part} requires {sorted(missing)}, absent from the context. "
            f"A field this kind reads and the context lacks is a caller bug, not a "
            f"default -- defaulting it would make two different projects share an envelope."
        )
    return {field: context[field] for field in fields}
