"""`claim_key()` -- the identity of a coordination lease. TD §5.12a.

    claim_key(domain, identity) = first 16 bytes of SHA-256( canonical_json({
        "v":        1,
        "domain":   ClaimDomain,      <-- the discriminator, as in task_key()
        "identity": { ... }
    }) )

**Why this exists at all.** Rev. 7 gave `render`, `source_extract` and `routing` claims and
no way to key them: `Claim.key` was documented as *"the envelope"*, `envelope()`'s kind
domain admitted none of the three, and §5.9 says an artifact *has no envelope*. So the
protocol said *"use a claim"* while the schema said *"claims are envelopes"* -- not
mechanically transcribable, which is this document's own bar.

**Not every reusable result is a derived decision.** A rendered artifact, an extracted
source and a routing judgment are all worth single-flighting, but none is a
`DecisionVersion`: none gets a slot, a `version_number`, dependency edges, or a place in a
`Commitment`. Widening `envelope()` would have claimed decision semantics for three things
that have none.

`CHOICE` (§5.12a) -- this wraps the envelope for the decision-shaped domains rather than
using the envelope directly as the claim key. *Cost:* one extra hash. *Benefit:*
`Claim.key` has **one** construction for all six domains instead of being *"an envelope,
except for three cases"* -- which is exactly the shape of the bug being fixed.

Six domains, and the result row each one coordinates:

    decision:<kind>   {envelope}                                 DecisionVersion / SharedDerivation
    memo              {envelope}                                 MemoIndex
    document          {construction_key}                         Document + DocumentConstruction
    render            {document_id, render_env_hash}             ArtifactIndex
    source_extract    {source_content_hash, extractor_version}   SourceExtraction
    routing           {envelope}                                 RoutingResult
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NewType

from core.identity.canonical import Canonical, digest_128
from core.identity.envelope import DECISION_KINDS, DecisionKind

ClaimKey = NewType("ClaimKey", bytes)

ClaimDomain = NewType("ClaimDomain", str)
"""A `NewType` over `str` rather than a fifteen-member `Literal`, because one of the six
domains is parameterised by kind. Construct them with `decision()` or the constants
below -- never by writing the string, which is what the constructor is for."""

DECISION_PREFIX = "decision:"

MEMO: ClaimDomain = ClaimDomain("memo")
DOCUMENT: ClaimDomain = ClaimDomain("document")
RENDER: ClaimDomain = ClaimDomain("render")
SOURCE_EXTRACT: ClaimDomain = ClaimDomain("source_extract")
ROUTING: ClaimDomain = ClaimDomain("routing")

CLAIM_KEY_FORMAT_VERSION = 1

CLAIM_IDENTITY: Mapping[str, tuple[str, ...]] = {
    # The envelope IS the identity for the three decision-shaped domains; `claim_key`
    # wraps it so that `Claim.key` has one construction (the CHOICE above).
    "decision": ("envelope",),
    "memo": ("envelope",),
    "routing": ("envelope",),
    # A construction key is an idempotency key ONTO a Document, not the Document's
    # identity -- §5.8. The Document itself is identified by content.
    "document": ("construction_key",),
    # No envelope: an artifact is not derived from a model call, it has content identity
    # (§5.9). A re-render under a new engine build is new work.
    "render": ("document_id", "render_env_hash"),
    # The identity that Rev. 8 had to fix in the Task key too, for the same reason: an
    # extractor upgrade must be new work.
    "source_extract": ("source_content_hash", "extractor_version"),
}
"""Keyed by domain *family*, so every `decision:<kind>` shares one row. §5.12a's table as
the thing `claim_key()` enforces."""

CLAIM_DOMAIN_FAMILIES: tuple[str, ...] = tuple(CLAIM_IDENTITY)
"""The six. `test_there_are_exactly_six_claim_domains` holds this to §5.12a's count, which
is a number the design states repeatedly and would otherwise drift silently."""


def decision(kind: DecisionKind) -> ClaimDomain:
    """`decision:<kind>` -- the domain for a derived decision of this kind."""
    if kind not in DECISION_KINDS:
        raise ValueError(
            f"{kind!r} is not a DecisionKind. `memo`, `document` and `routing` have "
            f"envelopes but are not decisions -- their claim domains are the bare names "
            f"MEMO, DOCUMENT and ROUTING (§5.12a)."
        )
    return ClaimDomain(DECISION_PREFIX + kind)


def family_of(domain: ClaimDomain) -> str:
    """The domain's family -- every `decision:<kind>` collapses to `decision`."""
    if domain.startswith(DECISION_PREFIX):
        return "decision"
    return domain


def claim_key(domain: ClaimDomain, identity: Mapping[str, Canonical]) -> ClaimKey:
    """The claim key for one coordinated result.

    `identity` must carry exactly the field set §5.12a declares for the domain's family.
    The envelope-shaped domains take `{"envelope": <lowercase hex>}` -- hex, because §5.1
    renders ids as hex and `canonical.dumps` refuses raw bytes rather than encoding them
    silently.
    """
    family = family_of(domain)
    expected = CLAIM_IDENTITY.get(family)
    if expected is None:
        raise ValueError(f"{domain!r} is not a ClaimDomain (§5.12a)")
    if family == "decision" and domain.removeprefix(DECISION_PREFIX) not in DECISION_KINDS:
        raise ValueError(f"{domain!r} names a kind that is not a DecisionKind (§5.1)")

    supplied = frozenset(identity)
    required = frozenset(expected)
    if supplied != required:
        missing = sorted(required - supplied)
        extra = sorted(supplied - required)
        raise ValueError(
            f"claim_key({domain!r}) identity must be exactly {sorted(required)} (§5.12a); "
            f"missing={missing} unexpected={extra}"
        )

    return ClaimKey(
        digest_128(
            {
                "v": CLAIM_KEY_FORMAT_VERSION,
                "domain": domain,
                "identity": identity,
            }
        )
    )
