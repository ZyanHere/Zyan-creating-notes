"""Engine: merge -> print, with no model call.

Fast regression on the template. Every block kind appears here, so a template
edit that breaks one of them fails in under a second rather than after a paid
generation.

The "every block kind" claim was false for four kinds and stayed false long
enough for `chips` to vanish from a shipped PDF. It is now enforced against the
contract rather than asserted in a docstring -- see
`test_the_fixture_covers_every_block_kind`.
"""

from __future__ import annotations

import pytest

import typing

from agent.contracts import (
    Block,
    BulletList,
    Callout,
    CheckQuestion,
    Chips,
    Code,
    Document,
    Heading,
    MarkedGap,
    Prose,
    Entity,
    RelationalStructure,
    Section,
    Subhead,
    Table,
    WorkedExample,
)
from engine.render import TEMPLATES, render_html, render_pdf


def _all_kinds() -> set[str]:
    """Every `kind` the contract admits, read off the union itself."""
    members = typing.get_args(typing.get_args(Block)[0])
    return {typing.get_args(m.model_fields["kind"].annotation)[0] for m in members}


def _template_ids() -> list[str]:
    return sorted(p.name.removesuffix(".html.j2") for p in TEMPLATES.glob("*.html.j2"))


@pytest.fixture()
def document() -> Document:
    return Document(
        title="Binary Search",
        subtitle="Finding things in sorted data without looking at all of it",
        assumed_entry="You can read a for-loop and know what an array is.",
        target_capability="Implement binary search correctly and say why it terminates.",
        sections=[
            Section(
                heading="The idea",
                blocks=[
                    Prose(text="First paragraph.\n\nSecond paragraph."),
                    BulletList(items=["alpha", "beta"]),
                    BulletList(ordered=True, items=["step one", "step two"]),
                    Table(
                        caption="What it costs",
                        headers=["Approach", "Comparisons"],
                        rows=[["Linear", "n"], ["Binary", "log n"]],
                    ),
                    Code(language="python", code="def f(x):\n    return x", caption="A function"),
                    WorkedExample(
                        title="Searching for 7",
                        steps=["lo=0, hi=6", "mid=3, a[3]=5 < 7", "lo=4"],
                    ),
                    CheckQuestion(
                        prompt="Why not (lo+hi)/2?",
                        answer="It overflows in fixed-width integers.",
                    ),
                    Callout(tone="warning", title="Careful", text="Off-by-one lives here."),
                    Subhead(label="LEARNING OBJECTIVES"),
                    Heading(text="Invariants"),
                    Chips(items=["sorted input", "halving", "termination"]),
                    RelationalStructure(
                        relation="is-subset-of",
                        caption="Where it sits",
                        entities=[
                            Entity(label="searching", note="all of it"),
                            Entity(label="binary search", note="this module"),
                        ],
                    ),
                ],
            )
        ],
        deliberate_omissions=[
            MarkedGap(
                topic="Interpolation search",
                consequence="You will assume binary search is always optimal.",
                when_to_learn="Before working with uniformly distributed keys at scale.",
            )
        ],
    )


def test_every_block_kind_renders(document: Document) -> None:
    html = render_html(document.model_dump())
    for marker in ("<table", "<pre", "class=\"example\"", "class=\"check\"",
                   "class=\"callout warning\"", "<ol>", "<ul>"):
        assert marker in html, f"missing {marker}"


def test_items_field_is_not_the_dict_method(document: Document) -> None:
    """`BulletList.items` collides with `dict.items` under Jinja's default
    attribute-first lookup. _MappingFirstEnvironment fixes the class of bug;
    this is the case that found it."""
    html = render_html(document.model_dump())
    assert "<li>alpha</li>" in html
    assert "built-in method" not in html


def test_prose_splits_on_blank_lines(document: Document) -> None:
    html = render_html(document.model_dump())
    assert "<p>First paragraph.</p>" in html
    assert "<p>Second paragraph.</p>" in html


def test_marked_gap_carries_all_three_parts(document: Document) -> None:
    """Semantics §12: the boundary, its consequence, and when to learn it.
    Two out of three is not a marked gap -- it is a missing topic."""
    html = render_html(document.model_dump())
    assert "Interpolation search" in html
    assert "always optimal" in html
    assert "uniformly distributed keys" in html


def test_orientation_block_states_entry_and_target(document: Document) -> None:
    html = render_html(document.model_dump())
    assert "for-loop" in html
    assert "why it terminates" in html


def test_html_escapes_content() -> None:
    doc = Document(
        title="X",
        assumed_entry="a",
        target_capability="b",
        sections=[Section(heading="H", blocks=[Prose(text="<script>alert(1)</script>")])],
    )
    html = render_html(doc.model_dump())
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.slow
def test_pdf_renders_and_reports_its_environment(document: Document) -> None:
    """Invariant 10 in embryo: the engine reports what it read, because the
    caller cannot see the resolved browser build."""
    result = render_pdf(document.model_dump())
    assert result.pdf.startswith(b"%PDF")
    assert len(result.pdf) > 10_000
    env = result.render_environment
    assert env["engine"] == "playwright-chromium"
    assert env["browser_version"]
    assert len(env["template_version"]) == 12


def test_the_fixture_covers_every_block_kind(document: Document) -> None:
    """The docstring used to promise this and nothing checked it.

    A kind absent from the fixture is a kind no template is regression-tested
    against, which is how four of them came to render as nothing at all.
    """
    present = {b.kind for s in document.sections for b in s.blocks}
    assert present == _all_kinds(), f"fixture is missing {_all_kinds() - present}"


@pytest.mark.parametrize("template_id", _template_ids())
def test_kinds_a_template_cannot_draw_are_reported(document: Document, template_id: str) -> None:
    """Representation Boundary Rev. 3's cheapest failure: the document asserts
    something and the paper does not say it.

    A template need not draw every kind -- study-notes legitimately has no
    stack. What it may not do is drop one in silence. Drawn XOR reported, for
    every kind in the contract, checked against the template source so a
    deleted branch cannot pass by also deleting its evidence.
    """
    # The else-marker now guards on `b.kind == "relation"` to name the relation
    # it could not draw, which would read as a branch. Scan the branches only.
    source = "\n".join(
        line
        for line in (TEMPLATES / f"{template_id}.html.j2").read_text(encoding="utf-8").splitlines()
        if 'class="unrendered"' not in line
    )
    html = render_html(document.model_dump(), template_id=template_id)

    for kind in _all_kinds():
        has_branch = f'b.kind == "{kind}"' in source
        reported = f'data-kind="{kind}"' in html
        assert has_branch != reported, (
            f"{template_id}: {kind!r} has a branch={has_branch} but "
            f"reported-as-unrendered={reported} -- one or the other, never both "
            f"or neither"
        )


@pytest.mark.parametrize("template_id", ["module-guide", "night-lab"])
def test_relation_selects_the_geometry_not_the_model(template_id: str) -> None:
    """The property this contract exists for.

    One payload -- same entities, same notes, same order -- rendered twice with
    only the *relation* changed. Containment must get nested regions and order
    must get the layered flow. If both come out the same, the block is named
    after a geometry again and `topology -> stack` is back.
    """
    entities = [Entity(label="A", note="outer"), Entity(label="B"), Entity(label="C")]

    def render(relation: str) -> str:
        doc = Document(
            title="T", assumed_entry="a", target_capability="b",
            sections=[Section(heading="H", blocks=[
                RelationalStructure(relation=relation, entities=entities)
            ])],
        )
        return render_html(doc.model_dump(), template_id=template_id)

    contains, ordered = render("is-subset-of"), render("precedes")
    assert 'data-realization="nested-regions"' in contains
    assert 'data-realization="layered-flow"' in ordered
    assert contains != ordered


@pytest.mark.parametrize("relation", ["is-part-of", "causes", "associates-with"])
def test_relations_with_no_realization_are_reported_not_approximated(relation: str) -> None:
    """Rev. 3 §10 stage 5: when nothing honest is available, report it.

    Substituting a geometry that answers a different claim is the failure this
    whole change exists to remove, so an unbuilt relation must reach the engine
    as an omission and never as the nearest available picture.
    """
    doc = Document(
        title="T", assumed_entry="a", target_capability="b",
        sections=[Section(heading="H", blocks=[
            RelationalStructure(relation=relation, entities=[Entity(label="A")])
        ])],
    )
    html = render_html(doc.model_dump(), template_id="night-lab")
    assert f'data-relation="{relation}"' in html
    assert "data-realization" not in html


@pytest.mark.parametrize("template_id", ["grimoire", "night-lab", "module-guide"])
def test_cardinality_selects_among_honest_realizations(template_id: str) -> None:
    """Rev. 3 §10 stage 2: the structural filter.

    Nested regions stay honest at any depth, so this is not a truth
    disqualification -- at nine levels the rings sit closer than a line of type
    and the labels collide. The next realization the honesty table permits for
    `is-subset-of` takes over. The relation is unchanged either way.
    """
    def render(n: int) -> str:
        doc = Document(
            title="T", assumed_entry="a", target_capability="b",
            sections=[Section(heading="H", blocks=[RelationalStructure(
                relation="is-subset-of",
                entities=[Entity(label=f"L{i}") for i in range(n)],
            )])],
        )
        return render_html(doc.model_dump(), template_id=template_id)

    assert 'data-realization="nested-regions"' in render(4)
    assert 'data-realization="indented-layers"' in render(9)
    # the claim never changes, only the geometry answering it
    assert 'data-relation="is-subset-of"' in render(9)
