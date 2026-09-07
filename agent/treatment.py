"""What treatments this build can actually realize, and what that costs.

Policy, like `sufficiency.py`: code owns what the engine can do, the model owns
what the content needs. Neither half is domain-specific — the vocabulary is
Architecture §13's prose-failure taxonomy, which is the same for anatomy, law
and distributed systems.

Two jobs, both upstream of the plan gate:

    EXTENT        content is not prose-equivalent. A concept whose meaning is
                  spatial costs more page than a definition at the same depth,
                  and an extent that ignores this under-reports the artifact.

    FEASIBILITY   a prose failure this build cannot answer must be REPORTED,
                  not silently served as prose. Architecture §13: "if we cannot
                  produce anatomical figures, the correct response is to report
                  the limitation, not to substitute a diagram that answers a
                  different failure." §14 makes reporting it an obligation.

What is NOT here: which diagram. Selecting a realization is decision 11, at the
demo gate, over Representation-Boundary Rev. 3's honesty table. This module only
says that prose will fail, and in which of the seven ways.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Architecture §13's left column, verbatim. Seven failures, no subjects.
ProseFailure = Literal[
    "none",
    "cross-reference",
    "topology",
    "parallel-state",
    "perceptual-referent",
    "abstraction-grounding",
    "procedure-execution",
    "false-comprehension",
]

FAILURES: tuple[ProseFailure, ...] = (
    "cross-reference",
    "topology",
    "parallel-state",
    "perceptual-referent",
    "abstraction-grounding",
    "procedure-execution",
    "false-comprehension",
)


@dataclass(frozen=True, slots=True)
class Capability:
    """What this build can do about one prose failure.

    `weight` multiplies a concept's page cost. Every value is a guess and none
    has been measured -- but a wrong multiplier is a wrong number, while
    assuming 1.0 everywhere is a wrong *model*: it asserts that content whose
    meaning is spatial costs the same as a definition, which is the claim this
    module exists to remove.
    """

    served: bool
    weight: float
    licenses: str
    note: str


CAPABILITY: dict[ProseFailure, Capability] = {
    "none": Capability(True, 1.0, "prose", "The default carrier."),
    "cross-reference": Capability(
        True, 1.3, "table / comparison matrix", "Tables are rendered by every template."
    ),
    "topology": Capability(
        True,
        1.6,
        "nested regions · layered flow",
        "Served for containment and order. Composition, causation and "
        "association have no realization built yet — Representation-Boundary §3.",
    ),
    "parallel-state": Capability(
        False,
        1.6,
        "sequence · swimlane · timeline",
        "No realization exists. Two actors evolving at once currently come out "
        "as prose, which is the substitution §13 forbids.",
    ),
    "perceptual-referent": Capability(
        False,
        2.2,
        "image",
        "The system cannot draw the thing itself. Representation-Boundary calls "
        "this family E and it is the only one that cannot preserve assertions: "
        "a generated figure adds content the document never asserted.",
    ),
    "abstraction-grounding": Capability(
        True, 1.5, "worked example · code", "Both are rendered."
    ),
    "procedure-execution": Capability(
        True, 1.5, "trace with state shown", "Rendered as a stepped example."
    ),
    "false-comprehension": Capability(
        True, 1.2, "counter-example · failing case · check question", "Rendered."
    ),
}


@dataclass(frozen=True, slots=True)
class Shortfall:
    """One prose failure this build cannot answer, and what it costs here."""

    failure: ProseFailure
    concepts: tuple[str, ...]
    licenses: str
    note: str

    def to_json(self) -> dict:
        return {
            "failure": self.failure,
            "concepts": list(self.concepts),
            "licenses": self.licenses,
            "note": self.note,
        }


def weight(failure: str) -> float:
    return CAPABILITY.get(failure, CAPABILITY["none"]).weight  # type: ignore[arg-type]


def shortfalls(covered) -> tuple[Shortfall, ...]:
    """Prose failures the content anticipates and this build cannot serve.

    Returned so the plan can say so before it is approved. Silently producing
    prose-only notes for content whose meaning is spatial is the failure this
    exists to prevent -- the reader cannot see what is missing, which is exactly
    the quiet omission Semantics §12 forbids.
    """
    by_failure: dict[str, list[str]] = {}
    for item in covered:
        failure = getattr(item, "anticipates", "none")
        capability = CAPABILITY.get(failure)
        if capability is not None and not capability.served:
            by_failure.setdefault(failure, []).append(item.concept)

    return tuple(
        Shortfall(
            failure=failure,  # type: ignore[arg-type]
            concepts=tuple(concepts),
            licenses=CAPABILITY[failure].licenses,  # type: ignore[index]
            note=CAPABILITY[failure].note,  # type: ignore[index]
        )
        for failure, concepts in sorted(by_failure.items())
    )
