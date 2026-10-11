"""`task_key()` -- the identity of a production event. TD §5.12.

    task_key(kind, inputs) = first 16 bytes of SHA-256( canonical_json({
        "v":      1,
        "domain": "task",          <-- a separate domain, not an envelope kind
        "kind":   TaskKind,
        "inputs": { ... }
    }) )

**Why this is not `envelope("task", ...)`**, which is what Rev. 4 wrote: `"task"` is not in
the envelope's kind domain, so the document declared one construction and then used one
the construction does not admit. The fix §5.12 chose is separation rather than widening,
and the reason is §4.1's tiers -- **a Task is process state; an envelope identifies a
reusable derived result.** They have different lifetimes: a Task row is collectable after
30 days (§10.6), an envelope must be stable forever.

Same serialiser, two domains. The `"domain"` field is what makes a task key and an
envelope over identical inputs **provably distinct**, so neither can be mistaken for the
other in a store or a log.

**The asymmetry worth knowing before you use this** (§8.1): a Task key asks *"is this the
same REQUEST?"* and a memo envelope asks *"is this the same CONTENT?"* -- which is why
`commitment_id` is in the `generate` task key and deliberately absent from the memo
envelope. The measured project has 8 modules and 40 sections; a commitment-keyed memo
would re-spend all 40 at ~65 s each for a correction touching one module.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, NewType

from core.identity.canonical import Canonical, digest_128

TaskKey = NewType("TaskKey", bytes)

type TaskKind = Literal[
    "source_extract",
    "plan",
    "correct",
    "generate",
    "render",
    "export",
]

TASK_DOMAIN = "task"
TASK_KEY_FORMAT_VERSION = 1

TASK_INPUTS: Mapping[str, tuple[str, ...]] = {
    # Rev. 8: NOT {source_id}. The claim identity is (content_hash, extractor_version), so
    # keying the Task on the source alone meant an extractor UPGRADE returned the old
    # succeeded Task and no extraction ever ran -- the claim said "new result" while the
    # Task said "same request".
    "source_extract": ("source_content_hash", "extractor_version"),
    # Rev. 3: ALL planning roots. The structure envelope already carries subject, frame,
    # sources AND the derivation environment -- and that last part is the hole. Bumping the
    # derive prompt moves the structure envelope and nothing else, so a plan key without it
    # read "already done" and never re-planned.
    "plan": ("structure_envelope", "situation_v", "job_v", "tier_v", "frame_v"),
    "correct": ("utterance_id",),
    # THE FIX (§8.1). A key of (project, generate, module_id) returns the old succeeded
    # Task instead of starting the new production event, and a module being generated again
    # under a new Commitment is a normal operation in the correction flow.
    "generate": ("commitment_id", "module_id"),
    "render": ("document_id", "render_env_hash"),
    # Rev. 6: the RESOLVED artifact set, not {commitment_id} -- the set can change while
    # the commitment does not (§9.9 (1)-(3)).
    "export": ("export_hash",),
}
"""§8.1's per-kind inputs, as the thing `task_key()` enforces rather than a comment. The
table is exhaustive and `test_task_inputs_table_matches_the_type` pins it to `TaskKind`."""


def task_key(kind: TaskKind, inputs: Mapping[str, Canonical]) -> TaskKey:
    """The idempotency key for one production event.

    `inputs` must carry exactly the field set §8.1 declares for this kind -- no more and
    no fewer. Enforcing it here is the point: an extra field makes a retry look like new
    work, and a missing one makes new work look like a retry. Both are CF-6's error class,
    *"an identity that does not capture what makes two things different."*
    """
    expected = TASK_INPUTS.get(kind)
    if expected is None:
        raise ValueError(f"{kind!r} is not a TaskKind (§5.12)")

    supplied = frozenset(inputs)
    required = frozenset(expected)
    if supplied != required:
        missing = sorted(required - supplied)
        extra = sorted(supplied - required)
        raise ValueError(
            f"task_key({kind!r}) inputs must be exactly {sorted(required)} (§8.1); "
            f"missing={missing} unexpected={extra}"
        )

    return TaskKey(
        digest_128(
            {
                "v": TASK_KEY_FORMAT_VERSION,
                "domain": TASK_DOMAIN,
                "kind": kind,
                "inputs": inputs,
            }
        )
    )


def all_task_kinds() -> tuple[str, ...]:
    return tuple(TASK_INPUTS)
