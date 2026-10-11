"""Canonical JSON and the 128-bit digest. TD §5.1.

Every identity in this system is `sha256(canonical_json(payload))[:16]`, and this module
is the only place either half is implemented. Three constructions share one serialiser
deliberately (§5.12: *"one serialiser, two domains"*) -- if they each had their own, the
disjointness argument in §5.12a would rest on three implementations agreeing.

The rules, from §5.1, each with the reason it exists:

    UTF-8                       the digest is over bytes, so the encoding is part of the spec
    keys sorted by code point   dict order is not semantic and Python's is insertion order
    no insignificant whitespace `separators=(",", ":")`
    strings NFC-normalised      the same text typed two ways must be one identity
    integers only, no floats    a float's textual form is not stable across languages
    arrays ordered or sorted    per kind -- see the note on ordering below

**Arrays are left exactly as given.** This module will not sort them, because for some
kinds order *is* the identity: §5.8's `section_memo_keys` is *"ORDERED, not sorted --
section order is semantic here, and two orderings of the same sections are different
documents."* Where the kind's spec says sorted (`source_set`, `member_identity_list_hash`)
the caller sorts, and `sort_canonically` below is how, so that "sorted" means one thing
across call sites rather than whatever each site's key function happened to be.

**`bytes` is rejected rather than hex-encoded for you.** §5.1 says version ids appear as
lowercase hex, and silently encoding would make `b"\\xab"` and `"ab"` the same identity --
a collision across types, in the one module whose job is to not have collisions. The error
says to call `.hex()`.

Note that `bytes` **satisfies** the `Canonical` annotation -- `bytes` is a `Sequence[int]`
and `int` is in the union, and there is no way to say "a sequence but not that one" in the
type system. So the runtime check below is the only thing keeping bytes out, which is why
it is a check and not an assertion.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import cast

type Canonical = str | int | Sequence[Canonical] | Mapping[str, Canonical] | None
"""What a canonical payload may contain. `float` is absent on purpose, so passing one is a
type error before it is a runtime error."""

DIGEST_BYTES = 16
"""128 bits. §5.1 `CHOICE`: collision probability is negligible at any plausible corpus
size and the key is half the width in every index. `v: 1` in each payload makes widening
to 256 a non-breaking change."""


def dumps(value: Canonical) -> bytes:
    """`value` as canonical JSON bytes. The only serialiser any identity may use."""
    normalised = _normalise(value, "$")
    text = json.dumps(
        normalised,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8")


def digest_128(payload: Mapping[str, Canonical]) -> bytes:
    """`sha256(canonical_json(payload))[:16]` -- the construction every identity shares."""
    return hashlib.sha256(dumps(payload)).digest()[:DIGEST_BYTES]


def digest_256(value: Canonical) -> bytes:
    """Full-width digest, for the hashes that are not keys.

    `brief_inputs_hash`, `content_hash`, `request_fingerprint` and friends are `bytes32`
    in §4.2's schema. They are not index keys, so the §5.1 truncation argument does not
    apply to them and the extra 16 bytes cost nothing.
    """
    return hashlib.sha256(dumps(value)).digest()


def sort_canonically(items: Iterable[Canonical]) -> list[Canonical]:
    """Deterministic order for a set-like array, by each item's own canonical bytes.

    `source_set` is *"sorted list of {content_hash, kind, extractor_version}"* (§5.3) and
    `member_identity_list_hash` is *"ORDERED is not semantic here -- sorted"* (§5.6). Both
    need an order over structured items, and "by canonical bytes" is the one order that
    needs no per-kind key function and cannot disagree with the serialiser.
    """
    return sorted(items, key=dumps)


def _normalise(value: object, path: str) -> Canonical:
    """Recursively NFC-normalise strings and reject anything not canonically expressible.

    Takes `object`, not `Canonical`, on purpose. `dumps` is typed, so a caller writing
    Python gets a type error before a runtime one -- but identities also get built from
    values that crossed an untyped boundary (a JSON body, a jsonb column), where `Any`
    defeats the annotation and only the isinstance checks are left. Typing this parameter
    `Canonical` would make those checks provably redundant to the type checker and
    actually redundant to nobody.

    `path` is carried only so the error names the offending field. A rejection here is
    always a programming error, and an error that says `$.inputs.source_set[0].weight`
    costs nothing to produce and saves the search.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)

    if isinstance(value, bytes | bytearray | memoryview):
        raise TypeError(
            f"{path}: raw bytes are not canonically expressible. §5.1 renders ids as "
            f"lowercase hex -- pass `.hex()`."
        )
    if isinstance(value, float):
        raise TypeError(
            f"{path}: floats are excluded by §5.1 -- a float's textual form is not stable "
            f"across languages. Use an integer, or a string if it is really a label."
        )

    if isinstance(value, Mapping):
        return _normalise_mapping(cast("Mapping[object, object]", value), path)
    if isinstance(value, Sequence):
        items = cast("Sequence[object]", value)
        return [_normalise(item, f"{path}[{i}]") for i, item in enumerate(items)]

    raise TypeError(f"{path}: {type(value).__name__} is not canonically expressible")


def _normalise_mapping(value: Mapping[object, object], path: str) -> dict[str, Canonical]:
    out: dict[str, Canonical] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{path}: key {key!r} is not a string")
        normalised_key = unicodedata.normalize("NFC", key)
        if normalised_key in out:
            # Two distinct keys that NFC-normalise to one. Silently dropping either would
            # make the payload depend on dict order, which is exactly what this module
            # exists to remove.
            raise ValueError(
                f"{path}: keys {key!r} and an earlier key both normalise to "
                f"{normalised_key!r}; the payload would depend on insertion order"
            )
        out[normalised_key] = _normalise(item, f"{path}.{normalised_key}")
    return out
