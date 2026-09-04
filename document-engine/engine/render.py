"""HTML -> PDF via headless Chromium.

Deterministic within a pinned environment: the same Document Model, template,
theme and Playwright version produce the same page images. PDF *bytes* differ
between runs (timestamps, object ordering), which is why the determinism test
compares rasterised pages, not files.

Chromium does not implement CSS `@page` margin boxes, so the running header and
footer are supplied as Chromium header/footer templates instead. Those templates
render outside the page box, in the margins configured here.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from .merge import TEMPLATES, THEMES, merge
from .schema import Document

_TOKEN = re.compile(r"^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);", re.M)

# Fallbacks only. The page box belongs to the theme — see --s-page-* — so a
# theme can change margins without touching Python, and the ground layer's
# negative offsets always match what Chromium was told.
_MARGIN_FALLBACK = {"top": "17mm", "bottom": "15mm", "left": "18mm", "right": "18mm"}


def _theme_tokens(theme: str) -> dict[str, str]:
    """Read the theme's tokens so header/footer fragments can use them.

    Chromium header/footer templates render in an isolated context that does
    not inherit the page's stylesheet, so the few values they need are
    substituted in rather than referenced as var().
    """
    css = (THEMES / f"{theme}.css").read_text(encoding="utf-8")
    return {m.group(1): m.group(2).strip() for m in _TOKEN.finditer(css)}


def _margin(tokens: dict[str, str]) -> dict[str, str]:
    """The page box, from the theme.

    Left and right are zero on purpose: Chromium paints the page background
    only inside the margin box, so any horizontal margin would print white on
    a dark theme. The horizontal gutter lives in the stylesheet instead
    (`.doc` padding), which keeps the ground reaching both paper edges.
    Top and bottom remain, because Chromium draws the running header and
    footer inside them.
    """
    return {
        "top": tokens.get("--s-page-top", _MARGIN_FALLBACK["top"]),
        "bottom": tokens.get("--s-page-bottom", _MARGIN_FALLBACK["bottom"]),
        "left": "0mm",
        "right": "0mm",
    }


# Chromium renders header/footer templates a fixed distance past the box it is
# given and does not clip the overflow. Two failure modes pull in opposite
# directions: a box that stops short of the margin leaves an unpainted seam
# where it meets the content, and a box that reaches too far paints over the
# first element of every page.
#
# Measured, not guessed. With the header disabled the figure's two-line top bar
# is 53px at scale 2; anything less means content is being clipped. Sweeping the
# box height with a fixed -6mm shift, against a 17mm top margin:
#
#     box     | white px | bar
#     17.0mm  |        7 |  53     seam
#     17.5mm  |        2 |  53     seam
#     18.0mm  |        0 |  53  <- margin + 1mm
#     18.5mm  |        0 |  50     clipping starts
#     21.0mm  |        0 |  35     badly clipped
#
# So: shift the box back by the bleed, and oversize it by 1mm. The window is
# only ~0.5mm wide, which is why both constants are here rather than inlined.
#
# Note the seam was identical on both themes — it only *looked* absent on the
# light one because white (255,255,255) against a #F7F6FD ground is a distance
# of 19, and the test threshold was 30. The test now compares exactly.
_CHROME_BLEED_MM = 6.0
_CHROME_OVERLAP_MM = 1.0


def _chrome_box(margin: str) -> str:
    """Box height for a header/footer template: the margin plus the overlap."""
    return f"{float(margin.rstrip('m')) + _CHROME_OVERLAP_MM:g}mm"


def _chrome_fragment(
    path: Path, doc: Document, tokens: dict[str, str], box_h: str
) -> str:
    text = path.read_text(encoding="utf-8")
    subs = {
        "__BOX_H__": box_h,
        "__BLEED__": f"{_CHROME_BLEED_MM:g}mm",
        "__MUTED__": tokens.get("--c-muted", "#666"),
        "__PAGENUM__": tokens.get("--c-page-num", "#000"),
        "__GROUND__": tokens.get("--c-ground", "#fff"),
        "__MARGIN__": tokens.get("--s-page-x", _MARGIN_FALLBACK["left"]),
        "__RUNNING_TITLE__": doc.running_title or "",
        "__EYEBROW__": doc.eyebrow or "",
        "__FOOTER_TEXT__": doc.footer_text or "",
    }
    for key, value in subs.items():
        text = text.replace(key, value)
    return text


def render(
    doc: Document,
    template: str = "study-notes",
    theme: str = "indigo-light",
    out: Path | None = None,
) -> bytes:
    """Render a Document Model to PDF bytes, optionally writing them to `out`."""
    html = merge(doc, template=template, theme=theme)
    tokens = _theme_tokens(theme)
    margin = _margin(tokens)
    template_dir = TEMPLATES / template

    # Write the HTML inside the template directory so relative references —
    # layout.css, ../../themes/*.css, fonts/*.woff2 — resolve over file://
    # with no server and no network.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", dir=template_dir, delete=False, encoding="utf-8"
    ) as fh:
        fh.write(html)
        page_path = Path(fh.name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(page_path.as_uri(), wait_until="load")
            page.emulate_media(media="print")
            # Web fonts are font-display: block; wait for them so the first
            # layout is the final one.
            page.evaluate("document.fonts.ready")
            pdf = page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=False,
                margin=margin,
                display_header_footer=True,
                header_template=_chrome_fragment(
                    template_dir / "header.html", doc, tokens,
                    _chrome_box(margin["top"]),
                ),
                footer_template=_chrome_fragment(
                    template_dir / "footer.html", doc, tokens,
                    _chrome_box(margin["bottom"]),
                ),
            )
            browser.close()
    finally:
        page_path.unlink(missing_ok=True)

    if out is not None:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf)
    return pdf
