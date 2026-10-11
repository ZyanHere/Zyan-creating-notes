"""Content addressing for payloads in object storage. TD §4.3.

    ContentRef = "<bucket>/<kind>/<sha256-hex>"     CHOICE: hex, not base64url -- greppable

**Content-addressed, not key-addressed, and this follows from fencing** (§4.3, `DECIDED`).
If a payload were stored at a path derived from its envelope, two racing workers would
write to the **same path**, and a fenced-out worker could overwrite the committed
payload's bytes. Content addressing makes each write land at its own path; only the
committed claim references one; the loser's payload is an orphan.

That is also the ordering rule in T5 -- *"payloads are content-addressed in object storage
and written before the claim commit"* -- which is how the Postgres-to-object-storage
transaction gap is closed without a distributed transaction.
"""

from __future__ import annotations

import hashlib
from typing import Literal, NewType

ContentHash = NewType("ContentHash", bytes)
"""32 bytes -- `bytes32` in §4.2's schema, not truncated. These are not index keys, so
§5.1's 128-bit argument does not apply."""

ContentRef = NewType("ContentRef", str)

type ContentKind = Literal[
    "decision-payload",
    "memo-payload",
    "document",
    "artifact-pdf",
    "artifact-html",
    "source-payload",
    "source-extract",
    "export-zip",
]
"""§4.3's eight kinds. A closed set, because the path is the only thing distinguishing two
payloads of different kinds with identical bytes."""

CONTENT_KINDS: frozenset[str] = frozenset(
    {
        "decision-payload",
        "memo-payload",
        "document",
        "artifact-pdf",
        "artifact-html",
        "source-payload",
        "source-extract",
        "export-zip",
    }
)


def content_hash(data: bytes) -> ContentHash:
    """The payload's identity: `sha256` over the exact bytes that will be stored."""
    return ContentHash(hashlib.sha256(data).digest())


def content_ref(bucket: str, kind: ContentKind, digest: ContentHash) -> ContentRef:
    """`"<bucket>/<kind>/<sha256-hex>"` -- the path this payload is written to.

    Lowercase hex. The `CHOICE` in §4.3 is greppability: a path you can paste into a log
    search is worth more than the handful of characters base64url would save.
    """
    if kind not in CONTENT_KINDS:
        raise ValueError(f"{kind!r} is not a ContentKind (§4.3)")
    if not bucket or "/" in bucket:
        raise ValueError(f"bucket must be a non-empty single segment, got {bucket!r}")
    if len(digest) != hashlib.sha256().digest_size:
        raise ValueError(
            f"digest must be a full sha256 ({hashlib.sha256().digest_size} bytes), "
            f"got {len(digest)} -- a truncated hash in a write-once path is a collision "
            f"waiting to overwrite committed bytes"
        )
    return ContentRef(f"{bucket}/{kind}/{digest.hex()}")
