"""`request_fingerprint()` -- the mechanism §18.3 promised. TD §4.2, §18.3.

    request_fingerprint : bytes32    sha256(canonical_json({role, text}))

Rev. 4 defined the 200/409 rule in §18.3 and never added the column, so the rule was
unimplementable. With the fingerprint stored alongside `(project_id, request_id)`:

    matching fingerprint  -> return the existing turn        a retry, idempotent
    mismatch              -> 409 request_id_reused           a different payload reusing
                                                             a client-supplied id

The distinction is the whole point. A retry of the same utterance must not append a second
`Utterance` (S11 is append-only, so there is no undo), and a *different* utterance arriving
under a reused `request_id` must not silently overwrite the first one's meaning.

Full-width, not truncated: this is a comparison value, not an index key.
"""

from __future__ import annotations

from typing import Literal, NewType

from core.identity.canonical import digest_256

RequestFingerprint = NewType("RequestFingerprint", bytes)

type Role = Literal["user", "system"]
"""§4.2's `Utterance.role`. There is no `assistant` role: the system's own turns are
`system`, and model output lives in a payload, not in the transcript."""


def request_fingerprint(role: Role, text: str) -> RequestFingerprint:
    """The payload fingerprint for one intake request.

    Goes through the same canonical serialiser as every identity, so the NFC rule applies
    here too -- the same sentence typed with a composed and a decomposed accent is one
    request, not two, and will not produce a spurious 409.
    """
    if role not in ("user", "system"):
        raise ValueError(f"{role!r} is not an Utterance role (§4.2)")
    return RequestFingerprint(digest_256({"role": role, "text": text}))
