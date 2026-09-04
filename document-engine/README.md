# document-engine — SALVAGE

**This package does not import and does not run.** `engine/schema.py` was deleted,
and everything else imports from it.

That is deliberate. A working implementation of the wrong model is more dangerous
than a broken pile of reference files, because a working one invites extension.

Current source of truth: **`../Product-Semantics.md` (Rev. 2)**.
Recoverable in full from commit `07ebf72`, *"Snapshot before the vocabulary reset"*.

---

## What was deleted, and why

| Deleted | Reason (Product Semantics §) |
|---|---|
| `engine/schema.py` | §1 — the closed 8-block discriminated union. Not because a schema is wrong, because a **closed** one is. Representation is prose · comparison · example · question · code · diagram · table · sequence · exercise, and the set is not final. |
| `templates/study-notes/blocks/` | §8 — one partial per block type, including `figure_layer_stack.html`. Figures must be SVG generated from data, selected by the **relation** the content expresses. CSS cannot draw concentric sets and cannot draw a plot at all. |
| `templates/study-notes/layout.css` | §6 — 337 lines written for one job's grammar. Construct's *"a concept, developed"* is not look-up's *"an index reachable from a held question."* |
| `templates/study-notes/template.html` | The page shell assumes `Section → Block`. |
| `tests/fixtures/*.json` | Data in the dead vocabulary. |

## What was kept, and why

| Kept | Value |
|---|---|
| `engine/render.py` | **The measured Chromium constants.** Print bleed is 6mm; the header box must be `margin + 1mm`, a window about 0.5mm wide. Four rounds of being wrong, and the sweep table is in the comment. Vocabulary-neutral. |
| `engine/merge.py` | Jinja environment, autoescape on, `TemplateGap`. Mechanism, not content. |
| `engine/inline.py` | 43 lines: escape → substitute → trusted `Markup`. Two constructs only. Malformed input renders literally. |
| `tests/test_engine.py` | Cannot run. Kept for the header-seam methodology: **scan every row of every page and compare exactly.** Two earlier versions of that test passed while the defect was present — one sampled two rows, one used a tolerance of 30, and white against `#F7F6FD` is a distance of 19. |
| `tests/rasterise.py` | PDF → PNG. Determinism is compared by rasterised page, never by PDF bytes. |
| `themes/*.css` | The token discipline: every configurable visual value lives here, `layout.css` consumes tokens only. Proven by the theme swap. Some tokens (`--c-fig-1..5`, `--w-figure-col`) are archetype-specific and will not survive. |
| `header.html` · `footer.html` | Chromium `header_template` fragments — they pair with `render.py`'s constants. |
| `fonts/` | Poppins + JetBrains Mono, OFL, bundled for offline determinism. |

## What the semantics added that this engine never had

§9 locks: *when even the compression floor does not fit, the system must state that
the target does not fit the budget.*

This engine renders and stops. It reports nothing upstream. Knowing whether a
treatment fits requires **render → measure → feed back**, which makes the renderer
part of a loop rather than a terminus. That is a new requirement, and it argues for
rebuilding around measurement rather than bolting it on.

## Not yet designable

Product Semantics §14: *the archetype library cannot be sized until we know what
knowledge wants visual representation* — which is Q2, unanswered. The node
vocabulary is a function of the representation vocabulary. So the correct engine
cannot be specified today; only this one can be ruled out.
