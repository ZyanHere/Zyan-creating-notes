"""Verification for the step-1 engine.

Run:  python -m pytest tests -q          (from document-engine/)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from engine import TemplateGap, load, merge, render
from engine.inline import inline
from tests.rasterise import rasterise

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
OUT = ROOT / "out" / "test"


def fixture(name: str):
    return load(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


# ----------------------------------------------------------------- inline


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("plain", "plain"),
        ("a `code` b", 'a <code class="chip">code</code> b'),
        ("a **bold** b", "a <strong>bold</strong> b"),
        # Malformed input renders literally — no repair, no partial markup.
        ("unclosed **bold", "unclosed **bold"),
        ("unclosed `code", "unclosed `code"),
        ("empty `` and ****", "empty `` and ****"),
        ("single *star*", "single *star*"),
        # Escaping happens before substitution, so nothing in the source can
        # reach the output as markup.
        ("<script>x</script>", "&lt;script&gt;x&lt;/script&gt;"),
        ("a & b", "a &amp; b"),
    ],
)
def test_inline(raw, expected):
    assert str(inline(raw)) == expected


def test_inline_never_emits_unescaped_source_markup():
    out = str(inline("<b>not bold</b> and `<i>x</i>`"))
    assert "<b>" not in out
    assert "<i>" not in out
    assert out.count("<code") == 1


# ----------------------------------------------------------------- schema


def test_fixtures_validate():
    for name in ("module-01.json", "stress.json"):
        assert fixture(name).sections


def test_unknown_block_type_is_rejected():
    with pytest.raises(ValidationError):
        load({"title": "t", "sections": [{"blocks": [{"type": "nope"}]}]})


def test_missing_required_field_is_rejected():
    with pytest.raises(ValidationError):
        load({"title": "t", "sections": [{"blocks": [{"type": "code", "lang": "py"}]}]})


def test_extra_field_is_rejected():
    """Silently ignoring an unknown key would hide a generator's mistakes."""
    with pytest.raises(ValidationError):
        load({"title": "t", "sections": [], "colour": "#fff"})


def test_layer_width_is_bounded():
    with pytest.raises(ValidationError):
        load({"title": "t", "sections": [{"blocks": [{
            "type": "figure", "archetype": "layer-stack", "caption": "c",
            "layers": [{"text": "x", "width": 400, "tone": "l1"}]}]}]})


def test_schema_export_is_usable():
    from engine import json_schema

    s = json_schema()
    assert s["title"] == "Document"
    assert "sections" in s["properties"]


# ------------------------------------------------------------------ merge


def test_merge_is_pure():
    doc = fixture("module-01.json")
    assert merge(doc) == merge(doc)


def test_merge_escapes_content():
    doc = load({"title": "t", "sections": [
        {"blocks": [{"type": "para", "text": "<script>alert(1)</script>"}]}]})
    html = merge(doc)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_unknown_archetype_is_a_template_gap():
    """A block the template cannot draw must fail loudly, not vanish."""
    doc = fixture("module-01.json")
    fig = next(b for s in doc.sections for b in s.blocks if b.type == "figure")
    object.__setattr__(fig, "archetype", "sunburst")
    with pytest.raises(TemplateGap):
        merge(doc)


# ----------------------------------------------------------------- render


@pytest.mark.slow
def test_render_is_deterministic_by_page():
    """Same input, same pinned environment, same pages.

    Compared as rasterised pages, not bytes: a PDF carries creation timestamps
    and object ordering that differ between identical renders.
    """
    doc = fixture("module-01.json")
    a, b = OUT / "det-a.pdf", OUT / "det-b.pdf"
    render(doc, out=a)
    render(doc, out=b)

    pa = rasterise(a, OUT / "det-a", scale=1.0)
    pb = rasterise(b, OUT / "det-b", scale=1.0)
    assert len(pa) == len(pb)
    for x, y in zip(pa, pb):
        assert x.read_bytes() == y.read_bytes(), f"page differs: {x.name}"


@pytest.mark.slow
def test_theme_swap_changes_pixels_but_not_content():
    """Content and presentation are separable.

    One Document Model, two themes. The model is untouched; the pages differ.
    """
    doc = fixture("module-01.json")
    before = doc.model_dump_json()

    light = render(doc, theme="indigo-light", out=OUT / "theme-light.pdf")
    amber = render(doc, theme="slate-amber", out=OUT / "theme-amber.pdf")

    assert doc.model_dump_json() == before, "rendering mutated the model"

    pl = rasterise(OUT / "theme-light.pdf", OUT / "theme-light", scale=1.0)
    pa = rasterise(OUT / "theme-amber.pdf", OUT / "theme-amber", scale=1.0)
    assert len(pl) == len(pa), "a theme changed pagination, not just appearance"
    assert any(x.read_bytes() != y.read_bytes() for x, y in zip(pl, pa))
    assert light != amber


@pytest.mark.slow
def test_header_neither_clips_content_nor_leaves_a_seam():
    """Chromium overflows the box it gives a header/footer template and does not
    clip it, so the box must be shifted back by the bleed and oversized by
    `_CHROME_OVERLAP_MM` — too little leaves an unpainted seam, too much paints
    over the first element of every page. The window is about 0.5mm wide.

    Two earlier versions of this test passed while the defect was present:

    * one sampled only the first and last row, and passed while a 6.6mm band
      sat between the header and the content;
    * one compared colours with a tolerance of 30, and reported the light theme
      as clean — white against a #F7F6FD ground is a distance of only 19.

    Hence: scan every row, and compare **exactly**. The gutter is sampled rather
    than the page centre, because the centre passes through real content.
    """
    import pypdfium2 as pdfium

    OUT.mkdir(parents=True, exist_ok=True)
    cases = [
        ("indigo-light", (0xC5, 0x6B, 0xB8), (247, 246, 253)),
        ("slate-amber", (0xE5, 0x76, 0x3A), (20, 23, 28)),
    ]
    for theme, bar_rgb, ground in cases:
        pdf = OUT / f"seam-{theme}.pdf"
        render(fixture("module-01.json"), theme=theme, out=pdf)
        doc = pdfium.PdfDocument(pdf)

        # 1. Content is not clipped: the figure's two-line top bar measures 53px
        #    at scale 2 when rendered with the header disabled.
        img = doc[1].render(scale=2).to_pil().convert("RGB")
        px = img.load()
        mid = range(img.width // 2 - 40, img.width // 2 + 40)
        rows = [
            y for y in range(img.height)
            if any(sum(abs(px[x, y][i] - bar_rgb[i]) for i in range(3)) < 30 for x in mid)
        ]
        assert rows, f"{theme}: figure bar not found"
        height = max(rows) - min(rows) + 1
        assert height == 53, (
            f"{theme}: top bar {height}px, expected 53 — the header is clipping content"
        )

        # 2. Every pixel of every gutter is exactly the ground colour. The
        #    gutter is 18mm wide (~102px at scale 2), so no content reaches it.
        for i in range(len(doc)):
            page = doc[i].render(scale=2).to_pil().convert("RGB")
            q = page.load()
            w = page.width
            for x in (2, 20, 60, 90, w - 90, w - 60, w - 20, w - 3):
                bad = [y for y in range(page.height) if q[x, y] != ground]
                assert not bad, (
                    f"{theme} page {i + 1}, x={x}: {len(bad)}px not the ground colour "
                    f"(first at row {bad[0]}, {q[x, bad[0]]}) — a seam has opened up"
                )


@pytest.mark.slow
def test_stress_fixture_renders():
    render(fixture("stress.json"), out=OUT / "stress.pdf")


def test_no_raw_visual_values_in_layout():
    """layout.css must consume tokens, never write design values.

    A hardcoded colour or size here would be invisible to a theme swap and
    would quietly break content/presentation separation.
    """
    css = (ROOT / "templates" / "study-notes" / "layout.css").read_text(encoding="utf-8")
    body = css.split("/* ------------------------------------------------------------- fonts */")[-1]
    offenders = []
    for i, line in enumerate(body.splitlines(), 1):
        stripped = line.split("/*")[0]
        if "#" in stripped and "url(" not in stripped:
            offenders.append((i, line.strip()))
        for unit in ("px", "pt", "em"):
            # 0 and 100% are structural; var() values are fine.
            import re

            for m in re.finditer(rf"(?<![-\w]){unit}\b", stripped):
                seg = stripped[max(0, m.start() - 12): m.end()]
                if "var(" in seg or "0.88em" in seg or "0.12em" in seg:
                    continue
                if re.search(rf"\d+(\.\d+)?{unit}", seg):
                    offenders.append((i, line.strip()))
                    break
    assert not offenders, "raw visual values in layout.css:\n" + "\n".join(
        f"  line {i}: {t}" for i, t in offenders
    )


def test_themes_define_the_same_tokens():
    """Every theme must define the full token set, or pages break silently."""
    import re

    themes = sorted((ROOT / "themes").glob("*.css"))
    sets = {}
    for t in themes:
        sets[t.stem] = set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", t.read_text(encoding="utf-8"), re.M))
    base = sets["indigo-light"]
    for name, tokens in sets.items():
        assert tokens == base, f"{name} token set differs: {base ^ tokens}"
