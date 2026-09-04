"""Document Model + Template + Theme -> HTML.

Pure: no network, no clock, no model. Same inputs give the same string.

Jinja2 autoescape is on. `inline()` is the only trusted boundary — see
engine/inline.py.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .inline import inline
from .schema import Document

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
THEMES = ROOT / "themes"

# Block type -> partial. A block type that is not in this map is a template
# gap, not a content error: fail loudly rather than silently dropping content.
BLOCK_TEMPLATE = {
    "para": "para.html",
    "subheading": "subheading.html",
    "code": "code.html",
    "callout": "callout.html",
    "list": "list.html",
    "badge": "badge.html",
    "figure": "figure_layer_stack.html",
    "cheatsheet": "cheatsheet.html",
}


class TemplateGap(RuntimeError):
    """A block type the template has no partial for."""


def _env(template_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(("html",)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["inline"] = inline
    return env


def _block_template(block, template_dir: Path) -> str:
    kind = block.type
    if kind == "figure":
        # Archetypes are separate partials; a generator selects one that
        # exists and can never invent one.
        name = f"figure_{block.archetype.replace('-', '_')}.html"
    else:
        name = BLOCK_TEMPLATE.get(kind)
    if not name:
        raise TemplateGap(f"no partial for block type {kind!r}")
    # Check on this side of Jinja so a missing partial reports as a template
    # gap rather than a TemplateNotFound from inside the render.
    if not (template_dir / "blocks" / name).is_file():
        raise TemplateGap(
            f"block type {kind!r} maps to blocks/{name}, "
            f"which does not exist in {template_dir.name}"
        )
    return f"blocks/{name}"


def merge(doc: Document, template: str = "study-notes", theme: str = "indigo-light") -> str:
    """Render the Document Model to a complete HTML string."""
    template_dir = TEMPLATES / template
    if not (template_dir / "template.html").is_file():
        raise FileNotFoundError(f"no template {template!r} in {TEMPLATES}")

    theme_path = THEMES / f"{theme}.css"
    if not theme_path.is_file():
        raise FileNotFoundError(f"no theme {theme!r} in {THEMES}")

    env = _env(template_dir)
    return env.get_template("template.html").render(
        doc=doc,
        # Themes live outside the template directory so one theme can serve
        # several templates. Relative path keeps the document loadable from
        # file:// with no server.
        theme_href=f"../../themes/{theme}.css",
        block_template=lambda b: _block_template(b, template_dir),
    )
