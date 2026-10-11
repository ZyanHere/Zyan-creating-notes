"""`member` encoding -- the single home §5.11a says this must have.

    member : text NOT NULL       '' is the root sentinel; never null, in the column OR
                                 the envelope

**Why never null**, restated here because it is the reason and not a style note (§5.1):
Postgres forbids a nullable primary-key column, *and* treats `NULL`s as **distinct** in a
`UNIQUE` constraint. With `member = NULL`, `UNIQUE (project_id, kind, member, envelope)`
would admit two versions for one envelope -- silently disabling §11's independent guard
behind claim loss. The safety net would report as armed while being off.

`""` is safe because no real member can collide with it: a root member is empty, a level
member is a known literal or `literal:<id>`, and a member member is a bare id.

Three shapes, not five. §5.11a distinguishes `sections` (a module id), `memo` (a section
id) and `document` (a module id) -- but all three are bare ids and indistinguishable as
strings, so classification cannot tell them apart and does not pretend to. What it *can*
check is the distinction that carries the correctness weight: root vs level vs member.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NewType

Member = NewType("Member", str)

ROOT: Member = Member("")
"""The root sentinel. §5.1 `CHOICE` -- `""` over `'-'` or `'∅'`: it sorts first, it is
obviously not an id, and it needs no explanation in a query."""

_ORDERING_MODULES = "modules"
_ORDERING_SECTIONS_PREFIX = "sections:"


class MemberShape(StrEnum):
    """What a kind's member must look like. The enforceable half of §5.11a's table."""

    ROOT = "root"
    """`""` -- a project-level decision with no member."""

    ORDERING = "ordering"
    """`"modules"` or `"sections:<module_id>"` -- a level, not an entity."""

    MEMBER = "member"
    """A bare id: a module id or a section id."""


def root() -> Member:
    """`situation`, `job`, `scope_tier`, `frame`, `structure`, `projection`, `scope`,
    `partition`, `routing`."""
    return ROOT


def module(module_id: str) -> Member:
    """`sections` and `document` -- member is the module's assigned id (S14)."""
    return Member(_require_id(module_id, "module_id"))


def section(section_id: str) -> Member:
    """`memo` -- member is the section's assigned id (S14)."""
    return Member(_require_id(section_id, "section_id"))


def ordering_modules() -> Member:
    """`ordering` at module level -- one per project."""
    return Member(_ORDERING_MODULES)


def ordering_sections(module_id: str) -> Member:
    """`ordering` at section level -- one per module."""
    return Member(_ORDERING_SECTIONS_PREFIX + _require_id(module_id, "module_id"))


def shape_of(member: Member) -> MemberShape:
    """Classify a member by its encoding alone."""
    if member == ROOT:
        return MemberShape.ROOT
    if member == _ORDERING_MODULES or member.startswith(_ORDERING_SECTIONS_PREFIX):
        return MemberShape.ORDERING
    return MemberShape.MEMBER


def check(member: Member, expected: MemberShape) -> Member:
    """Raise unless `member` has the shape its kind requires.

    Called by `envelope()` on every construction, which is what turns §5.11a's table from
    documentation into a thing that cannot be violated. A `memo` envelope with
    `member=""` is the bug this catches, and it is the shape of bug that produces two
    versions for one envelope.
    """
    actual = shape_of(member)
    if actual is not expected:
        raise ValueError(
            f"member {member!r} has shape {actual.value}, but this kind requires "
            f"{expected.value} (§5.11a)"
        )
    if expected is MemberShape.ORDERING and member != _ORDERING_MODULES:
        _require_id(member.removeprefix(_ORDERING_SECTIONS_PREFIX), "module_id")
    return member


def _require_id(value: str, field: str) -> str:
    """Non-empty and whitespace-free. Deliberately not a uuid parse.

    §5.11a says these are uuids and S14 says they are assigned at partition time, but
    parsing here would make every test and fixture mint real uuids to exercise an
    encoding rule. What must be impossible is an id that collides with the root sentinel
    or with a level literal, and that is what emptiness and the prefix check cover.
    """
    if not value or value.strip() != value or any(c.isspace() for c in value):
        raise ValueError(f"{field} must be a non-empty id without whitespace, got {value!r}")
    if value == _ORDERING_MODULES or value.startswith(_ORDERING_SECTIONS_PREFIX):
        raise ValueError(f"{field} {value!r} collides with an ordering level literal")
    return value
