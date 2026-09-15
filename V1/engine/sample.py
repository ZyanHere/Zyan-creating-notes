"""One document that exercises every block kind, as a plain mapping.

A dict rather than an `agent.contracts.Document` on purpose: the engine may not
import the agent (`tests/test_boundaries.py` enforces it), and `render_pdf`
already takes `doc.model_dump()`. The shape is the contract; this satisfies it
without the dependency.

Its job is coverage. A template that cannot draw a kind sends it to the
`{% else %}` branch, where it is invisible on paper and reported by the engine --
so rendering this and asserting `unrendered` is empty is how a template proves it
can draw the vocabulary. That check is what was missing when `study-notes`
silently dropped four kinds, `relation` among them: the default template could
not draw a diagram at all, and nothing said so.

Every relation appears, because each licenses a different geometry and a template
that handles one is not thereby handling the others.
"""

from __future__ import annotations

from typing import Any

BLOCK_KINDS: tuple[str, ...] = (
    "prose",
    "list",
    "code",
    "table",
    "example",
    "question",
    "callout",
    "subhead",
    "heading",
    "chips",
    "relation",
)

RELATIONS: tuple[str, ...] = (
    "is-subset-of",
    "is-part-of",
    "precedes",
    "causes",
    "associates-with",
)


def _relation_block(relation: str) -> dict[str, Any]:
    entities = {
        "is-subset-of": [
            {"label": "Artificial intelligence"},
            {"label": "Machine learning", "note": "Learns from data."},
            {"label": "Deep learning", "emphasis": True},
        ],
        "is-part-of": [
            {"label": "Alimentary canal"},
            {"label": "Small intestine"},
            {"label": "Mucosa", "note": "Innermost layer."},
        ],
        "precedes": [
            {"label": "Ingestion"},
            {"label": "Digestion", "emphasis": True},
            {"label": "Absorption"},
        ],
        "causes": [
            {"label": "Low pH in the stomach"},
            {"label": "Pepsinogen activates"},
            {"label": "Proteins break into peptides"},
        ],
        "associates-with": [
            {"label": "Amylase"},
            {"label": "Lipase"},
            {"label": "Trypsin", "note": "Pancreatic."},
        ],
    }[relation]
    return {
        "kind": "relation",
        "diagnosis": "topology",
        "relation": relation,
        "caption": f"Sample figure for {relation}.",
        # Every optional field spelled out. `model_dump()` emits defaults, so a
        # fixture that omits them is a shape the system never actually produces
        # -- and the templates render under StrictUndefined, where a missing key
        # is an error rather than a blank.
        "entities": [
            {"label": e["label"], "note": e.get("note"), "emphasis": e.get("emphasis", False)}
            for e in entities
        ],
    }


def sample_document() -> dict[str, Any]:
    """A fresh dict each call -- templates and tests must not share mutable state."""
    return {
        "title": "Every Block Kind",
        "subtitle": "A coverage fixture, not a real document.",
        "cover": None,
        "running_head_left": "Coverage fixture",
        "running_head_right": "Engine",
        "footer_text": None,
        "assumed_entry": "Nothing. This document teaches nothing.",
        "target_capability": "See whether a template can draw the whole vocabulary.",
        "sections": [
            {
                "heading": "Prose and structure",
                "eyebrow": "SECTION 1",
                "heading_tail": None,
                "blocks": [
                    {
                        "kind": "prose",
                        "text": "Prose is the default carrier. Every other block "
                        "here is a departure from it, licensed by a named failure "
                        "of prose.",
                    },
                    {"kind": "subhead", "diagnosis": "cross-reference", "label": "STRUCTURE"},
                    {"kind": "heading", "diagnosis": "cross-reference", "text": "A subheading"},
                    {
                        "kind": "chips",
                        "diagnosis": "cross-reference",
                        "items": ["one", "two", "three"],
                    },
                    {
                        "kind": "list",
                        "diagnosis": "cross-reference",
                        "ordered": False,
                        "items": ["An unordered item.", "Another one."],
                    },
                    {
                        "kind": "list",
                        "diagnosis": "procedure-execution",
                        "ordered": True,
                        "items": ["First step.", "Second step."],
                    },
                ],
            },
            {
                "heading": "Departures",
                "eyebrow": "SECTION 2",
                "heading_tail": None,
                "blocks": [
                    {
                        "kind": "table",
                        "diagnosis": "cross-reference",
                        "caption": "Two things along two dimensions.",
                        "headers": ["Dimension", "First", "Second"],
                        "rows": [["Speed", "Fast", "Slow"], ["Cost", "Low", "High"]],
                    },
                    {
                        "kind": "code",
                        "diagnosis": "abstraction-grounding",
                        "language": "python",
                        "code": "def area(r: float) -> float:\n    return 3.14159 * r * r",
                        "caption": "A short listing.",
                    },
                    {
                        "kind": "example",
                        "diagnosis": "procedure-execution",
                        "title": "Working it through",
                        "steps": ["lo = 0, hi = 6", "mid = 3", "Answer: 3.5 million rows"],
                    },
                    {
                        "kind": "question",
                        "diagnosis": "false-comprehension",
                        "prompt": "Does this template draw every kind?",
                        "answer": "Only if `unrendered` comes back empty.",
                    },
                    {
                        "kind": "callout",
                        "diagnosis": "cross-reference",
                        "tone": "note",
                        "label": "NOTE",
                        "title": "An ordinary callout",
                        "text": "Text in a box, asserting no geometry.",
                    },
                    {
                        "kind": "callout",
                        "diagnosis": "perceptual-referent",
                        "tone": "warning",
                        "label": "GAP",
                        "title": "Figure not included",
                        "text": "This is the one legal form of a diagnosed "
                        "perceptual-referent: the brief, printed, with nothing drawn.",
                    },
                ],
            },
            {
                "heading": "Relations",
                "eyebrow": "SECTION 3",
                "heading_tail": None,
                "blocks": [_relation_block(r) for r in RELATIONS],
            },
        ],
        "deliberate_omissions": [
            {
                "topic": "Everything else",
                "consequence": "This fixture teaches nothing and is not a document.",
                "when_to_learn": "Never; it exists to be rendered.",
            }
        ],
    }
