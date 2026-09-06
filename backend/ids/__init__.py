"""Content addressing.

Build Spec §4. Every invariant that depends on content addressing depends on
this module being right, so the rules here are strict by design:

  * floats are rejected, never rounded  -- a float that serialises differently
    across platforms silently breaks memoisation, which silently doubles the
    most expensive spend in the system
  * strings and keys are NFC-normalised, and a normalisation collision between
    two keys is an error rather than a silent overwrite
  * mappings serialise with sorted keys and no whitespace
  * ``decision_ids_hash`` is order- and duplicate-independent: approving the
    same set in a different order is the same approval
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

__all__ = [
    "canonical",
    "content_hash",
    "decision_ids_hash",
    "Envelope",
    "CanonicalisationError",
]


class CanonicalisationError(TypeError):
    """A value cannot be canonicalised deterministically."""


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _freeze(obj: Any, path: str = "$") -> Any:
    # bool before int: bool is a subclass of int in Python.
    if obj is None or isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        raise CanonicalisationError(
            f"float at {path}: floats are rejected, not rounded. "
            "Use an int, or a string carrying the exact decimal text."
        )
    if isinstance(obj, str):
        return _nfc(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise CanonicalisationError(
                    f"non-string key {key!r} at {path}: object keys must be strings"
                )
            nkey = _nfc(key)
            if nkey in out:
                raise CanonicalisationError(
                    f"key collision at {path}: {key!r} normalises onto an existing key. "
                    "Silently dropping one would change the hash without changing intent."
                )
            out[nkey] = _freeze(value, f"{path}.{nkey}")
        return out
    if isinstance(obj, (list, tuple)):
        return [_freeze(item, f"{path}[{i}]") for i, item in enumerate(obj)]
    raise CanonicalisationError(
        f"unsupported type {type(obj).__name__} at {path}: "
        "canonicalisation accepts None, bool, int, str, UUID, mapping, list, tuple"
    )


def canonical(obj: Any) -> bytes:
    """Deterministic bytes for any accepted value."""
    return json.dumps(
        _freeze(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_hash(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def decision_ids_hash(ids: Iterable[UUID | str]) -> str:
    """Identity of a decision set. Order- and duplicate-independent (Build Spec §4)."""
    return content_hash(sorted({str(i) for i in ids}))


@dataclass(frozen=True, slots=True)
class Envelope:
    """The complete effective input to one decision (Build Spec §4).

    Every factor that can change a decision's output lives here. Anything a
    decision reads that is not in the envelope breaks invariant 2 -- the memo
    would return a result computed under conditions that no longer hold, which
    is worse than wasteful: it serves a stale judgment as a current one.

    Decision functions take this and nothing else. That is checked structurally
    (one-parameter AST walk), narrowed by an import denylist, and probed
    empirically by the determinism test. None of the three is a proof of
    isolation; together they are the discipline.
    """

    kind: str
    member_id: str | None
    inputs: tuple[tuple[str, str], ...]  # (decision_id, output_hash), sorted
    model: str
    prompt_version: str
    effort: str
    params: Mapping[str, Any]
    taxonomy_version: str
    asset_version: str | None
    source_versions: tuple[tuple[str, str], ...]  # (source_id, version), sorted
    system_instructions_hash: str
    tool_outputs: tuple[tuple[str, str], ...] = ()  # (tool, result_hash), sorted

    def __post_init__(self) -> None:
        for field, value in (
            ("inputs", self.inputs),
            ("source_versions", self.source_versions),
            ("tool_outputs", self.tool_outputs),
        ):
            if list(value) != sorted(value):
                raise CanonicalisationError(
                    f"Envelope.{field} must be sorted; unsorted pairs hash differently "
                    "for identical inputs."
                )

    def hash(self) -> str:
        return content_hash(asdict(self))


def envelope_from(
    *,
    kind: str,
    member_id: UUID | str | None,
    inputs: Sequence[tuple[UUID | str, str]],
    model: str,
    prompt_version: str,
    effort: str,
    params: Mapping[str, Any],
    taxonomy_version: str,
    asset_version: str | None = None,
    source_versions: Sequence[tuple[str, str]] = (),
    system_instructions_hash: str,
    tool_outputs: Sequence[tuple[str, str]] = (),
) -> Envelope:
    """Build an Envelope, sorting the pair sequences so callers need not."""
    return Envelope(
        kind=kind,
        member_id=str(member_id) if member_id is not None else None,
        inputs=tuple(sorted((str(a), b) for a, b in inputs)),
        model=model,
        prompt_version=prompt_version,
        effort=effort,
        params=dict(params),
        taxonomy_version=taxonomy_version,
        asset_version=asset_version,
        source_versions=tuple(sorted(source_versions)),
        system_instructions_hash=system_instructions_hash,
        tool_outputs=tuple(sorted(tool_outputs)),
    )
