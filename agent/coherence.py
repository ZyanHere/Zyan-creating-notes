"""How the concept graph falls across the modules a plan derived.

**Diagnostic evidence. Nothing here decides anything.**

`derive_structure` records which concepts are built from which. `partition`
divides them into modules. Laying one over the other says where each module's
dependencies actually live -- inside it, or somewhere else -- and that turned out
to be legible where prose was not:

    Foundations & Single-Agent Patterns    7 internal, 0 external
    Failure Modes, Guardrails & Hardening  1 internal, 13 external

The second was one module by name and three by structure: six failure modes each
depending on exactly the concept it is the failure *of*, two guardrails, and four
production concerns that were the only thing in it cohering with each other.

**Why this is not a rule.** Low internal dependency is not a defect on its own. A
comparison module -- five frameworks, none built on another -- has zero by
construction, and that is what makes the comparison possible. A capstone depends
on everything and is depended on by nothing. Both are legitimate shapes, and a
threshold could not tell them from a bag of leftovers. What separates them is the
module's *capability*, which is a judgement, not a count.

So this reports, and a human reads it against the capability. Encoding a
dependency-count rule would decide the granularity question that has not been
answered yet -- and would decide it wrongly for the two shapes above.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConceptLink:
    """One dependency, and whether it crosses a module boundary."""

    concept: str
    depends_on: str
    lives_in: str | None
    """The module holding the dependency. None when it is out of scope entirely."""

    @property
    def external(self) -> bool:
        return self.lives_in is not None and self.lives_in != self.home

    home: str = ""

    def to_json(self) -> dict:
        return {
            "concept": self.concept,
            "depends_on": self.depends_on,
            "lives_in": self.lives_in,
            "external": self.external,
        }


@dataclass(frozen=True, slots=True)
class ModuleCoherence:
    """Where one module's dependencies live. Counts, not conclusions."""

    module: str
    concepts: int
    internal: int
    external: int
    depends_on_modules: tuple[tuple[str, int], ...]
    links: tuple[ConceptLink, ...]

    @property
    def ratio(self) -> float | None:
        """Internal share of the module's in-scope dependencies.

        Reported because it is the compact form of the counts, NOT because a
        value is good or bad. See the module docstring: 0.0 is correct for a
        comparison module and for a capstone.
        """
        total = self.internal + self.external
        return self.internal / total if total else None

    def to_json(self) -> dict:
        return {
            "module": self.module,
            "concepts": self.concepts,
            "internal": self.internal,
            "external": self.external,
            "ratio": None if self.ratio is None else round(self.ratio, 3),
            "depends_on_modules": [
                {"module": m, "count": n} for m, n in self.depends_on_modules
            ],
            "links": [l.to_json() for l in self.links if l.external],
        }


def analyse(structure: dict | None, partition: dict | None) -> list[ModuleCoherence]:
    """Lay `derive_structure`'s dependencies over `partition`'s modules.

    Returns an empty list rather than raising when either decision is absent or
    legacy-shaped: this is evidence, and evidence that cannot be gathered is
    simply absent.
    """
    if not structure or not partition:
        return []

    built: dict[str, list[str]] = {
        c["name"]: list(c.get("built_from") or [])
        for c in (structure.get("concepts") or [])
        if c.get("name")
    }
    modules = partition.get("modules") or []
    if not modules:
        return []

    home: dict[str, str] = {
        concept: m["title"] for m in modules for concept in (m.get("covers") or [])
    }

    out: list[ModuleCoherence] = []
    for module in modules:
        title = module["title"]
        covers = module.get("covers") or []
        links: list[ConceptLink] = []
        counts: dict[str, int] = {}
        internal = external = 0

        for concept in covers:
            for dependency in built.get(concept, []):
                lives_in = home.get(dependency)
                link = ConceptLink(
                    concept=concept,
                    depends_on=dependency,
                    lives_in=lives_in,
                    home=title,
                )
                links.append(link)
                if lives_in is None:
                    continue  # out of scope entirely; not a boundary crossing
                if lives_in == title:
                    internal += 1
                else:
                    external += 1
                    counts[lives_in] = counts.get(lives_in, 0) + 1

        out.append(
            ModuleCoherence(
                module=title,
                concepts=len(covers),
                internal=internal,
                external=external,
                depends_on_modules=tuple(
                    sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
                ),
                links=tuple(links),
            )
        )
    return out


def to_json(reports: list[ModuleCoherence]) -> list[dict]:
    return [r.to_json() for r in reports]


# ---------------------------------------------------------------------------
# Is a module's capability backed by the concepts in its scope?
# ---------------------------------------------------------------------------
#
# A module promised: "Explain how agentic RAG differs from passive RAG; design
# iterative retrieval loops with query reformulation; compare tool-augmented
# retrieval strategies." Its scope held one concept -- `RAG for Agents (Agentic
# RAG)` -- and the whole graph contained no other retrieval concept at all.
# Three claims, one concept: a cheque the scope cannot cash, and the reader is
# the one who finds out.
#
# WHAT THIS DETECTS: a clause of the capability sharing no substantive word with
# any concept the module actually covers.
#
# WHAT IT DOES NOT: whether a clause that *does* overlap promises more than the
# concept delivers, and whether the module's concepts belong together at all.
# The five-unrelated-things module traced perfectly and was still wrong. This is
# one narrow reading, and it is evidence -- nothing decides on it.

_NOT_SUBSTANTIVE = frozenset(
    """a an and are as at be by can could for from how in into is it its of on or
    the to via with within their them they this that these those what when where
    which who why will would you your able about across after also any both each
    either given if into more most much no not only other over per so some such
    than then there through under up upon use used using very well while whose
    design designs designing build builds building explain explains explaining
    compare compares comparing describe describes discuss discusses articulate
    articulates specify specifies identify identifies distinguish distinguishes
    contrast contrasts analyze analyse choose chooses decide decides recall
    recognise recognize state states justify justifies write writes architect
    architects""".split()
)

# Semicolons only. Splitting on commas cut inside enumerations -- "maturity"
# and "shared memory)" became "clauses" and were reported unbacked, which is
# noise dressed as a finding. A semicolon in a capability genuinely separates
# independent claims; a comma usually does not, and being conservative here
# costs a missed signal rather than a false one.
_CLAUSE_SPLIT = re.compile(r";")


def _terms(text: str) -> set[str]:
    """Substantive words, with the verbs of capability-writing removed.

    The verbs are dropped deliberately: every capability is full of them and
    they match every concept equally, which is the failure `_discriminating`
    guards against in `sufficiency.py` -- evidence that fits everything is
    evidence for nothing.
    """
    words = [w for w in re.split(r"[^a-z0-9]+", text.casefold()) if len(w) > 2]
    terms: set[str] = set()
    for word in words:
        if word in _NOT_SUBSTANTIVE:
            continue
        terms.add(word)
        # "LLMs" must meet "LLM Fundamentals". A trailing-s fold is the whole of
        # the stemming here -- anything more would start guessing at meaning,
        # and this only has to make an obvious match obvious.
        if word.endswith("s") and len(word) > 3:
            terms.add(word[:-1])
    return terms


@dataclass(frozen=True, slots=True)
class CapabilitySupport:
    """What the capability claims, against what the module actually covers."""

    module: str
    clauses: tuple[str, ...]
    backed: tuple[tuple[str, tuple[str, ...]], ...]
    """(clause, the module's concepts it shares substantive words with)."""

    unbacked: tuple[str, ...]
    """Clauses sharing nothing with any concept in this module's scope."""

    def to_json(self) -> dict:
        return {
            "module": self.module,
            "clauses": list(self.clauses),
            "backed": [
                {"clause": clause, "concepts": list(concepts)}
                for clause, concepts in self.backed
            ],
            "unbacked": list(self.unbacked),
        }


def capability_support(partition: dict | None) -> list[CapabilitySupport]:
    """Read each module's capability against the concepts it covers."""
    modules = (partition or {}).get("modules") or []
    out: list[CapabilitySupport] = []

    for module in modules:
        capability = (module.get("capability") or "").strip()
        covers = module.get("covers") or []
        concept_terms = {c: _terms(c) for c in covers}

        clauses = [c.strip() for c in _CLAUSE_SPLIT.split(capability) if c and c.strip()]
        backed: list[tuple[str, tuple[str, ...]]] = []
        unbacked: list[str] = []

        for clause in clauses:
            terms = _terms(clause)
            touched = tuple(c for c, ct in concept_terms.items() if terms & ct)
            if touched:
                backed.append((clause, touched))
            else:
                unbacked.append(clause)

        out.append(
            CapabilitySupport(
                module=module.get("title", ""),
                clauses=tuple(clauses),
                backed=tuple(backed),
                unbacked=tuple(unbacked),
            )
        )
    return out


def support_to_json(reports: list[CapabilitySupport]) -> list[dict]:
    return [r.to_json() for r in reports]
