# document-engine

Document Model + Template + Theme → PDF.

No LLM. No network at render time. No clock. The engine reports; it never edits
content. This is step 1 of Phase 1 in `../Phase-1-Build-Plan.md`.

```bash
pip install -e .
python -m playwright install chromium

python -m engine render tests/fixtures/module-01.json                    # → out/module-01.pdf
python -m engine render tests/fixtures/module-01.json --theme slate-amber
python -m engine render tests/fixtures/module-01.json --html             # skip the browser
python -m engine schema                                                  # JSON Schema for the model
```

## Layers

```
doc_model (JSON)  →  merge.py   →  HTML   →  render.py  →  PDF
                     Jinja2                  Chromium
        ↑                ↑                       ↑
    schema.py      templates/            themes/*.css
```

- **`engine/schema.py`** — the Document Model. Content only: no coordinates, no
  page numbers, no colours, no font sizes. If a value would change when the
  text changes, it does not belong here.
- **`engine/inline.py`** — two inline constructs, `` `code` `` and `**bold**`.
  Escape, substitute, return trusted `Markup`. Malformed input renders
  literally: no repair, no partial tags.
- **`engine/merge.py`** — Jinja2, autoescape on. One partial per block type.
  A block type with no partial raises `TemplateGap` rather than vanishing.
- **`engine/render.py`** — headless Chromium. Reads the page box from the
  theme, substitutes theme colours into the running header/footer.

## The theme contract

`themes/*.css` holds **every configurable visual value** — colour, type, space,
shape, and the page box. `templates/*/layout.css` holds structure and consumes
tokens; a raw colour or size in it is a bug, and `test_no_raw_visual_values_in_layout`
fails on one.

That is what makes a theme swap free: same Document Model, same template, same
block partials, different `--tokens`. `test_theme_swap_changes_pixels_but_not_content`
proves the model is not mutated and the pagination does not move.

## Determinism

Scoped to a pinned environment: **playwright 1.62.0 / Chromium 151.0.7922.34**
(recorded in `engine.CHROMIUM_VERSION`). Bumping it invalidates golden images
and must be deliberate.

Determinism is tested **by rasterised page, not by PDF bytes** — a PDF carries
creation timestamps and object ordering that differ between identical renders.

```bash
python -m pytest tests -q              # all
python -m pytest tests -q -m "not slow"  # skip the browser
```

## Fixtures

- **`module-01.json`** — pages 2–3 of the benchmark, transcribed as data.
- **`stress.json`** — what the benchmark does *not* contain: a wrapping
  two-tone heading, a section with no label, a section with no heading,
  malformed inline syntax, a 30-item list, a callout at a page boundary, a
  code block taller than one page, 3- and 9-layer figures, a cheat sheet.

The stress fixture exists to stop the template being shaped around one
document. It has already caught three bugs the benchmark would not have:
a cascade collision that collapsed paragraph spacing, a running header
painting over the first element, and `overflow: hidden` truncating a code
block that spans pages.

### A note on how these were verified

Two versions of the header test passed while the defect was still there — one
sampled only the first and last pixel row, the other compared colours with a
tolerance of 30 while white against the `#F7F6FD` ground differs by only 19.
Visual checks are not enough and loose thresholds are worse than none: the
current test scans every row of every page and compares **exactly**.

## Known limitations

- **A figure caption can separate from its figure at a page boundary.**
  Chromium's print engine does not honour `break-after: avoid` on a flex
  container. The rules are in place and will start working if that changes;
  meanwhile it is the kind of orphan the Phase 2 `validate` module is meant
  to catch and report.
- **The header/footer box is sized by two measured constants.** Chromium
  overflows the box it gives a header/footer template by a fixed 6mm and does
  not clip it. Too small a box leaves an unpainted seam where it meets the
  content; too large a one paints over the first element of every page. The box
  is therefore shifted back by `_CHROME_BLEED_MM` and oversized by
  `_CHROME_OVERLAP_MM`, and the working window is only ~0.5mm wide. The sweep
  is recorded above those constants in `render.py`.
- **Page margins are left/right zero by design.** Chromium paints the page
  background only inside the margin box, so a dark theme would print white
  side margins. The horizontal gutter lives in `.doc` padding instead.

### On the renderer choice

Every limitation above is Chromium-specific. WeasyPrint — which produced the
benchmark — implements CSS `@page` margin boxes natively and has none of them:
running headers, footers and page numbers are ordinary CSS, and the page
background covers the whole sheet.

Chromium was chosen because Phase 2's annotation layer needs `getBoundingClientRect`
after layout, which WeasyPrint cannot provide, and because it installs cleanly on
Windows while WeasyPrint needs the GTK runtime. That trade is worth re-examining
if composed visual pages turn out to need less measurement than expected, or if
these page-edge artefacts start to matter.

## Not in this step

No `validate`, `solve`, `annotate` or `paginate` modules — Chromium's print
engine handles pagination for flowing documents. No LLM, no database, no Set
Plan, no verification layers, no UI. Figures beyond `layer-stack`.
