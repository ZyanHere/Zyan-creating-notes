"""merge -> print.

The engine takes a document-shaped mapping and a template id. It does not
import the agent's types: it renders whatever satisfies the shape, which is
what keeps the two subsystems independent when the agent's contracts change
at M3.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape
from playwright.sync_api import sync_playwright

TEMPLATES = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE = "study-notes"


@dataclass(frozen=True, slots=True)
class RenderResult:
    """What the engine produces, and what it observed while producing it.

    `render_environment` is CAPTURED HERE rather than passed in: the caller
    cannot see the resolved browser build or the template version, and System
    Design Rev. 4 invariant 10 is unenforceable unless the engine reports what
    it actually read. It is recorded from M1 because it cannot be backfilled.
    """

    pdf: bytes
    html: str
    render_environment: Mapping[str, str] = field(default_factory=dict)
    realizations: tuple[tuple[str, str], ...] = ()
    """(relation, realization) for each relational block, in document order.

    The template's half of the decision. Rev. 3 §10: the model states the
    relation, the template picks the geometry -- so neither side alone says what
    the reader saw.
    """

    unrendered: tuple[str, ...] = ()
    """Block kinds the template had no branch for, and so did not draw.

    The document asserted something the paper does not say. Silent until Rev. 3
    -- it is how three `chips` blocks vanished from a finished PDF without
    anyone noticing, and it is the cheapest representation failure to detect.
    """

    scale: float = 1.0
    """What Chromium scaled the document to. 1.0 is untouched.

    Below 1.0 every page was shrunk, including a full-bleed cover that then
    stops reaching the paper edge. The cause is always horizontal overflow;
    `overflows` names it.
    """

    overflows: tuple[str, ...] = ()
    """Elements wider than the page.

    Chromium's response to horizontal overflow is to shrink-to-fit the WHOLE
    document, so a single stray element on the last page silently rescales
    every page before it -- including a full-bleed cover, which then stops
    reaching the paper edge. The failure is invisible in the PDF and looks like
    a margin bug anywhere except where it is.

    This is `layout_feasibility` (Architecture §3, decision 14) in its smallest
    useful form: measured in the browser, reported to the caller, not repaired
    here.
    """


class _MappingFirstEnvironment(Environment):
    """Resolve `x.field` against mapping keys before Python attributes.

    Jinja's default order gives `block.items` the `dict.items` *method* rather
    than the block's `items` field, silently. The same trap waits for any field
    called `keys`, `values`, `get`, `copy` or `update`. Renaming contract fields
    to dodge a templating quirk is the wrong direction, so the lookup order is
    fixed here instead -- once, for every field that will ever exist.
    """

    def getattr(self, obj: Any, attribute: str) -> Any:  # noqa: A003 - Jinja's name
        if isinstance(obj, Mapping):
            try:
                return obj[attribute]
            except KeyError:
                pass
        return super().getattr(obj, attribute)


_INLINE_CODE = re.compile(r"`([^`]+)`")
_INLINE_BOLD = re.compile(r"\*\*([^*]+)\*\*")

# "1.", "2)", "Step 3 -" at the head of a step. The model supplies these because
# it is thinking about the finished page; the template is already numbering the
# list, so the reader gets "1. 1. DATA IN". Numbering is presentation and the
# template owns it -- stripping here is the same layering rule the rest of the
# system runs on, applied to two characters.
_LEADING_ENUM = re.compile(r"^\s*(?:step\s*)?\(?\d{1,2}\)?\s*[.):\-–—]\s+", re.I)


def _inline(text: str) -> Markup:
    """A two-token markup subset for running text: `code` and **bold**.

    Escape first, then insert markup, so content can never inject HTML. Prose
    that needs more than this is prose that should have been a different block.
    """
    escaped = str(escape(text))
    escaped = _INLINE_CODE.sub(r"<code>\1</code>", escaped)
    escaped = _INLINE_BOLD.sub(r"<strong>\1</strong>", escaped)
    return Markup(escaped)


def _denumber(text: str) -> str:
    """Drop a leading step number so an ordered list does not number it twice."""
    return _LEADING_ENUM.sub("", str(text), count=1)


def _env() -> Environment:
    env = _MappingFirstEnvironment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,  # a missing field is a bug, not a blank
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["inline"] = _inline
    env.filters["denumber"] = _denumber
    return env


def _template_version(template_id: str) -> str:
    """Content hash of the template. A CSS edit repaginates; Rev. 4 §4 requires
    that to be visible in the render environment."""
    import hashlib

    source = (TEMPLATES / f"{template_id}.html.j2").read_bytes()
    return hashlib.sha256(source).hexdigest()[:12]


def render_html(
    doc: Mapping[str, Any] | Any,
    *,
    template_id: str = DEFAULT_TEMPLATE,
    colophon: str = "",
) -> str:
    """merge: document + template -> HTML. Pure, no browser, no model."""
    template = _env().get_template(f"{template_id}.html.j2")
    return template.render(doc=doc, colophon=colophon)


# Per-template print options. Chromium's own header/footer is the only way to
# repeat page furniture -- it has no @page margin boxes -- but it cannot skip
# the first page, so a template with a full-bleed cover has to turn it off.
_PAGE_OPTIONS: dict[str, dict[str, Any]] = {
    "study-notes": {"page_numbers": True},
    "module-guide": {"page_numbers": False},
    # Chromium's footer cannot skip page 1, and a page number stamped on a
    # full-bleed cover is the tell that a template borrowed someone else's
    # page furniture.
    "night-lab": {"page_numbers": False},
    "grimoire": {"page_numbers": False},
}

# Runs in print media, after fonts settle. Reports the right edge of anything
# sticking past the document width, described well enough to find in a template.
#
# The limit is the PAGE width, not the window's. Measuring against `clientWidth`
# alone compared content to Playwright's 1280px viewport, so nothing on an A4
# page could ever exceed it -- the probe reported clean while a nowrap marginal
# note ran off the paper and Chromium rescaled every page to compensate. An
# instrument that cannot see the failure it exists for is worse than none,
# because it gets quoted as evidence.
_A4_CSS_PX = 794  # 210mm at 96dpi

_OVERFLOW_PROBE = """
() => {
  const limit = Math.min(document.documentElement.clientWidth, 794);
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.right <= limit + 0.5) continue;
    const id = el.tagName.toLowerCase()
      + (el.className && typeof el.className === 'string'
          ? '.' + el.className.trim().split(/\\s+/).join('.') : '');
    const text = (el.textContent || '').trim().slice(0, 40);
    out.push(`${id} overflows by ${Math.round(r.right - limit)}px` +
             (text ? ` -- "${text}"` : ''));
    if (out.length >= 8) break;
  }
  return out;
}
"""


# The templates' `{% else %}` branch. A block kind a template cannot draw is a
# representation failure, not a rendering detail: the document said something and
# the paper does not say it.
_UNRENDERED_PROBE = """
() => Array.from(document.querySelectorAll('.unrendered'))
        .map(el => el.dataset.relation ? el.dataset.kind + ':' + el.dataset.relation
                                       : el.dataset.kind)
"""

# Which geometry each relational block actually got. The relation is the model's
# claim and the realization is the template's answer to it; reporting only one of
# them is how `topology -> stack` hid two different relations behind one picture.
_REALIZATION_PROBE = """
() => Array.from(document.querySelectorAll('[data-realization]'))
        .map(el => [el.dataset.relation || '', el.dataset.realization])
"""

# Chromium answers horizontal overflow by scaling the whole document down. That
# is the damage; the overflowing element is only the cause. Reported as a ratio
# so a caller can say "every page came out at 92%".
_SCALE_PROBE = """
() => {
  const d = document.documentElement;
  return d.scrollWidth > 0 ? Math.min(1, d.clientWidth / d.scrollWidth) : 1;
}
"""

_FOOTER = (
    '<div style="width:100%;font-size:8pt;color:#767d87;'
    'font-family:Segoe UI,Helvetica,sans-serif;text-align:center;">'
    '<span class="pageNumber"></span></div>'
)


class BrowserMissing(RuntimeError):
    """Playwright is installed but its Chromium build was never downloaded.

    Its own message for this is a 9-line ASCII box wrapped in a
    `BrowserType.launch:` prefix, which reads like a crash in our code and, at
    the end of a generation, arrives after the model has already been paid for.
    Named so callers can check *before* spending anything -- `browser_ready()`
    costs a filesystem stat.
    """


def browser_ready() -> str | None:
    """None when a browser can actually be launched, else the command to fix it.

    Launches and closes one, rather than stat-ing `chromium.executable_path`:
    headless `launch()` runs the *headless shell*, a separate download from full
    Chromium, so the obvious check passes on exactly the installation this is
    meant to catch -- `chromium-1234` present, `chromium_headless_shell-1234`
    missing, which is the shape the error actually arrives in.

    Costs about a second. That is the point of comparison: the call it guards
    takes minutes and is billed.

    A string rather than a bool because there is exactly one useful thing to say
    when it is missing, and every caller would otherwise reinvent it.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Exception:  # noqa: BLE001 - any failure here means "not usable"
        return "playwright install chromium"
    return None


def render_pdf(
    doc: Mapping[str, Any] | Any,
    *,
    template_id: str = DEFAULT_TEMPLATE,
    colophon: str | None = None,
) -> RenderResult:
    """merge -> print. One browser, one page.

    CSS owns the page geometry: `prefer_css_page_size` plus no margin argument
    means the template's own `@page` rules apply, including `@page :first` for a
    full-bleed cover. Passing margins here would silently override them.
    """
    stamp = colophon if colophon is not None else _default_colophon(template_id)
    html = render_html(doc, template_id=template_id, colophon=stamp)
    options = _PAGE_OPTIONS.get(template_id, {"page_numbers": True})

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # noqa: BLE001 - re-raised, narrowed below
            if "Executable doesn't exist" not in str(exc):
                raise
            raise BrowserMissing(
                "Chromium is not installed for Playwright, so nothing can be "
                "rendered. Install it once with:\n\n    playwright install chromium"
            ) from exc
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            # Web fonts load after `load`; printing before they settle silently
            # falls back and changes every line break on the page.
            page.evaluate("document.fonts.ready")
            page.emulate_media(media="print")
            # Measure at page width, not window width. Playwright's viewport is
            # 1280px, so a `width: 100%` element lays out at 1280 and appears to
            # overrun A4 by 486px while printing perfectly -- the mirror image of
            # the bug this probe was fixed for, and just as misleading. Both
            # readings are only meaningful once the viewport IS the page.
            page.set_viewport_size({"width": _A4_CSS_PX, "height": 1123})
            page.evaluate("document.fonts.ready")
            overflows = tuple(page.evaluate(_OVERFLOW_PROBE))
            unrendered = tuple(page.evaluate(_UNRENDERED_PROBE))
            realizations = tuple(
                (str(r[0]), str(r[1])) for r in page.evaluate(_REALIZATION_PROBE)
            )
            scale = float(page.evaluate(_SCALE_PROBE))
            page.set_viewport_size({"width": 1280, "height": 720})
            page.emulate_media(media=None)
            pdf = page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=options["page_numbers"],
                header_template="<div></div>",
                footer_template=_FOOTER if options["page_numbers"] else "<div></div>",
            )
            browser_version = browser.version
        finally:
            browser.close()

    return RenderResult(
        pdf=pdf,
        html=html,
        realizations=realizations,
        unrendered=unrendered,
        scale=scale,
        overflows=overflows,
        render_environment={
            "template_id": template_id,
            "template_version": _template_version(template_id),
            "engine": "playwright-chromium",
            "browser_version": browser_version,
        },
    )


def _default_colophon(template_id: str) -> str:
    today = _dt.date.today().isoformat()
    return f"Generated {today} · template {template_id}@{_template_version(template_id)}"
