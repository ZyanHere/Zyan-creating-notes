"""Identity -- the names of things, computed from the things themselves. TD §5.

Three constructions with disjoint domains (T1), and nothing else in the system may build
an identity:

    envelope(kind, member, inputs, env)     a derived DECISION        §5.1
    task_key(kind, inputs)                  a production EVENT        §5.12
    claim_key(domain, identity)             a coordination LEASE      §5.12a

They answer different questions and have different lifetimes. An envelope asks *"is this
the same thing to derive?"* and must be stable forever; a task key asks *"is this the same
request?"* and its row is collectable after 30 days; a claim key asks *"is someone already
doing this?"* and its lease expires. Collapsing any pair is the mistake §21 names, and each
payload carries a `"domain"` or `"kind"` discriminator so no two can ever collide --
`test_three_key_constructions_are_disjoint` holds that.

This package imports nothing but itself and the standard library, which is enforced by
`tests/test_boundaries.py` rather than by convention. That is what makes it the one module
testable in total isolation, and why it is the first thing built.

**One name collision, deliberate and worth knowing about.** Three functions share a name
with the module that defines them -- `envelope`, `task_key`, `claim_key` -- and the
re-exports below win, because the flat form is what every caller wants:

    from core.identity import envelope, task_key, claim_key    the FUNCTIONS
    from core.identity.claim_key import MEMO, RENDER, decision  the module's other names

So `from core.identity import claim_key` gives you the function, and reaching the module's
constants means naming them. `import core.identity.claim_key as x` also binds the
function, not the module, which is the surprising one -- Python resolves it by attribute
lookup on the package.
"""

from __future__ import annotations

from core.identity.canonical import (
    DIGEST_BYTES,
    Canonical,
    digest_128,
    digest_256,
    dumps,
    sort_canonically,
)
from core.identity.claim_key import (
    DOCUMENT,
    MEMO,
    RENDER,
    ROUTING,
    SOURCE_EXTRACT,
    ClaimDomain,
    ClaimKey,
    claim_key,
    decision,
)
from core.identity.content import (
    ContentHash,
    ContentKind,
    ContentRef,
    content_hash,
    content_ref,
)
from core.identity.envelope import (
    DECISION_KINDS,
    SHARED_KINDS,
    DecisionKind,
    Envelope,
    EnvelopeKind,
    envelope,
    is_shared,
)
from core.identity.fingerprint import RequestFingerprint, Role, request_fingerprint
from core.identity.kinds import SPECS, KindSpec, MemberFrom, build
from core.identity.member import Member, MemberShape
from core.identity.task_key import TaskKey, TaskKind, task_key

__all__ = [
    "DECISION_KINDS",
    "DIGEST_BYTES",
    "DOCUMENT",
    "MEMO",
    "RENDER",
    "ROUTING",
    "SHARED_KINDS",
    "SOURCE_EXTRACT",
    "SPECS",
    "Canonical",
    "ClaimDomain",
    "ClaimKey",
    "ContentHash",
    "ContentKind",
    "ContentRef",
    "DecisionKind",
    "Envelope",
    "EnvelopeKind",
    "KindSpec",
    "Member",
    "MemberFrom",
    "MemberShape",
    "RequestFingerprint",
    "Role",
    "TaskKey",
    "TaskKind",
    "build",
    "claim_key",
    "content_hash",
    "content_ref",
    "decision",
    "digest_128",
    "digest_256",
    "dumps",
    "envelope",
    "is_shared",
    "request_fingerprint",
    "sort_canonically",
    "task_key",
]
