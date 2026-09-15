# Design Library — DEFERRED

> **Deferred 2026-09-08. Not scheduled; do not start it opportunistically.**
>
> **Build trigger:** the complete flow works end to end once — an approved plan reaching
> `agent/generate.py` and coming out as a PDF. Today those are two disconnected halves
> (`backend/planning.py` stops at `approve()`; `backend/service.py:generate()` still takes a
> raw request string), and building a design system across a seam that does not yet carry a
> plan would mean designing against a guess.
>
> **Ready to execute as written.** The implementation and verification sections below are
> build instructions, not sketches. Two things to re-check first, because they will have
> moved: the `.j2` measurements in §"The design specification", and whether
> `agent/contracts.py` still has no styling field.
>
> **What is already done** and must not be re-litigated: `Presentation-Boundary.md` §2 and
> rules 1 and 3 are corrected — template is user-selected, per Semantics §1 and §2 LOCKED.
> The contradiction that remains is in `agent/sufficiency.py`, which still carries
> `template: AxisPolicy(askable=False, …)` citing the withdrawn rule.

## Context

Two corrections led here.

**First**, `Presentation-Boundary.md` said templates were internal and users never select
them. That contradicted **Semantics §1** (Template — *user* — biasing) and **§2 LOCKED**,
which shows the selection literally: *Artifact: Long notes / Template: Diagram-heavy*. The
document is corrected; `agent/sufficiency.py` still carries the withdrawn rule.

**Second**, the previous version of this plan treated the four `.j2` files *as* the design
library. That is wrong. A design is a **structured specification** — layout, typography,
colour, spacing, hierarchy, page structure, component styling — and the PDF is what the user
looks at when choosing it. Today those two are fused: each `.j2` hardcodes its own palette in
`:root`, with no shared vocabulary (`study-notes` uses `--ink/--soft/--accent`; `night-lab`
uses `--ground/--panel/--yellow`). Consequences:

- Nothing can *describe* a design except the file itself.
- **Render configuration has nowhere to attach.** Presentation-Boundary rule 2 makes
  "black with yellow accents" an ungated per-project change needing no model call; with a
  hardcoded `:root` there is no knob. This is why `night-lab` exists at all — it is
  `study-notes`' job in another palette, and it cost 683 lines because the palette was not
  a parameter.

```
Design Library
    ↓
exemplar PDF                    ← what the user sees and picks
    ↓
design specification            ← what the renderer uses
    ├── page structure   ├── typography   ├── colour
    ├── spacing          ├── hierarchy    └── component styling
    ↓
        + content from the LLM (semantic only)
    ↓
      renderer
    ↓
    final PDF
```

**On extraction.** For designs we author there is nothing to reverse-engineer: we author the
spec and render the exemplar *from* it, so the spec is upstream of the PDF and can never
drift from it. Extracting a spec out of a PDF is only needed for a design we did **not**
author — a user uploading something they like. That is a separate feature; §"Not built"
names it as a branch this design leaves open.

**Already true, and preserved:** the LLM never invents styling. `agent/contracts.py` has no
font, colour or geometry field — `Callout.tone` is `note|warning` (semantic),
`Cover` carries text. The separation is real in the contract already; what changes is where
the design lives.

---

## The design specification

A versioned data object, one per design. Not Jinja, not CSS — data the renderer reads.

```
DesignSpec
  id · name · blurb · version · artifact_types[]

  page        size, margins, columns, cover: none | plain | full-bleed,
              furniture: page numbers, running heads, colophon placement
  type        families (display / body / mono), scale, weights, leading, tracking
  colour      ground, surface, ink, muted, rule, accent, warn, gap   ← ONE vocabulary
  space       unit, block rhythm, section gap, density: airy | standard | compact
  hierarchy   per heading level: rule, eyebrow, numbering, caps
  components  per block kind, a named variant —
                table    grid | zebra | minimal
                callout  left-rule | boxed | tinted
                code     framed | plain
                relation nested | layered | indented
```

Two constraints on that last group:

- **Variants are required, not optional.** Measured across the four existing designs:
  `study-notes` has no cover, `module-guide` has five `@page` contexts, `grimoire` uses six
  font stacks. A tokens-only spec would collapse all four toward one look.
- **`components.relation` stays bounded by the honesty table.** Representation-Boundary
  Rev. 3 §10 stage 3 gives the template a *ranking* among geometries the relation permits,
  never a free choice. A spec naming `nested` for `precedes` must be rejected, not drawn.
  Rev. 3 §8's layering is preserved exactly: a DesignSpec is a template expressed as data.

---

## Where the rendering goes

One renderer consuming `(document, design)`, replacing four bespoke templates:

- **`engine/design/`** (new). One spec file per design — `study-notes.toml`,
  `module-guide.toml`, `night-lab.toml`, `grimoire.toml` — plus `schema.py` defining
  `DesignSpec` and loading them.
- **`engine/render.py`**. `render_html(doc, design)` where `design` is a resolved
  `DesignSpec`; CSS custom properties are generated from `colour`/`type`/`space`, and
  `page`/`hierarchy`/`components` select variants. `template_id` becomes `design_id`
  throughout; `_template_version()` becomes a hash of the resolved spec, so a token edit is
  as visible in the render environment as a CSS edit was.
- **`engine/templates/`**. Collapses to one `document.html.j2` plus component partials —
  one partial per block kind, each honouring its variant field. All eleven kinds, once,
  which also removes today's coverage bug where `study-notes` silently drops `chips`,
  `heading` and `subhead` into the `{% else %}` branch.

**Migration is the risk, and it is handled one design at a time.** Converting bespoke CSS to
tokens plus variants will not be pixel-identical. Each design is converted, rendered against
`engine/sample.py`, and compared to the current output before its `.j2` is deleted. When a
design needs something the spec cannot express, that is evidence of a missing spec field —
recorded and added, never special-cased back into a bespoke file.

---

## The exemplar PDF

What the user actually picks from. Rendered from the spec plus one fixed sample document, so
it cannot drift from what they will receive.

- **`engine/sample.py`** (new). One document **as a dict, not a `Document`** — the engine
  may not import `agent` (`tests/test_boundaries.py` enforces it; `render_pdf` already takes
  `doc.model_dump()`). Exercises all eleven block kinds, so one fixture serves the exemplar
  and the coverage test.
- **`engine/render.py`**. `exemplar(design_id) -> bytes` (PNG of page one for the picker,
  PDF for "see the whole thing"), cached on the spec hash.

---

## The controls

Unchanged from the approved plan, with `template` now meaning `design`.

**Two control axes, not two questions.** The intake loop is model-proposes → policy-filters
(`backend/planning.py:295`). That is right for situation axes, wrong here: the option set is
system-owned data, and a permanent control means "Do you want long notes?" is a question the
system should never spend a turn on. The control *replaces* the question.

**A strip above the intake questions**, not a new state or gate:

| State | What the user sees |
|---|---|
| questions outstanding | strip **above** the questions — one screen, one turn |
| sufficient, nothing asked | strip alone with **Plan it** |
| planned | strip gone; design becomes a correction — a re-render, no model call |

**Artifact above design**, and the artifact narrows the set (Semantics §2: per-artifact-type
sets). Five presets from Semantics §7 — Detailed notes, Short notes, Revision sheet, Q&A,
Cheat sheet — all one `Document` shape differing by job, density and design.

**Optional throughout.** Semantics §1 marks it *biasing*; §3 *silence is freedom* is LOCKED.
Touch nothing and planning proceeds on an inferred artifact and a default design. Nothing
blocks. A request describing a *look* ("black with yellow") is **not** a design selection —
it stays render configuration, which now has tokens to attach to.

### Files

- **`agent/sufficiency.py`** — `control: bool` on `AxisPolicy`, true for `artifact_type` and
  `template`; `decide()` excludes control axes from `asking` while still reading them.
  Rewrite both `because` strings to cite Semantics rather than the withdrawn rule.
- **`agent/prompts/interpret_v1.md`** — read both axes, propose options for neither.
- **`backend/store.py`** — `select_presentation` into `PLAN_DECISIONS`, committed at
  approval (Presentation-Boundary rule 9).
- **`backend/planning.py`** — a `_NO_CALL` sentinel so `_write` (line 325) can record a
  system decision with no model call; `set_presentation(project_id, artifact_type,
  design_id)`; `view()` exposes the selection and the available designs.
- **`backend/api.py`** — `GET /designs?artifact_type=…`, `GET /designs/{id}/exemplar.png`,
  `POST /projects/{id}/presentation`.
- **`frontend/lib/api.ts`**, **`frontend/components/plan/ControlStrip.tsx`** (new),
  **`frontend/app/projects/[id]/page.tsx`**, **`frontend/lib/compose.ts`** — artifact chips,
  exemplar cards, and a defaulted design named in the plan's assumptions so a default is
  visible rather than silent.
- **`Presentation-Boundary.md`**, **`Plan-Gate-Milestone.md`** — record the control-axis rule
  and the ninth decision record.

---

## Deliberately not built

- **Spec extraction from a foreign PDF.** The branch that makes "upload a design you like"
  possible. Everything above is unchanged by it: it produces a `DesignSpec` by a different
  route and hands it to the same renderer.
- **Render-configuration UI.** Tokens now make it *possible*; it stays natural-language,
  Presentation-Boundary rules 3 and 5.
- **A graphical-bias multiplier on extent.** Stacking a second unmeasured multiplier on
  `treatment.py`'s already-guessed weights compounds error with nothing behind it.
- **Flashcards.** Different page geometry, not a design variation.
- **Closing the seam** between the approved plan and `agent/generate.py`. Separate and
  larger; this records the selection so it is there when that happens.

---

## Verification

1. `python -m pytest -q` — 170 pass today; new tests must not reduce that.
2. **Fidelity, per design**: render `engine/sample.py` through the converted spec and the
   original `.j2` and compare. This is the gate for deleting each `.j2`, and it is done one
   design at a time rather than as a batch.
3. **Coverage**: `rendered.unrendered` is empty for all four designs. Fails today on
   `study-notes`; the partial-per-block-kind renderer is what fixes it.
4. **Honesty table**: a spec naming a geometry the relation does not permit is rejected at
   load, not drawn. Rev. 3 §10 stage 1 in code.
5. **Policy**: neither control axis appears in `sufficiency.asking` for any transcript; a
   request naming an artifact still reads `stated`; one describing a colour does not set a
   design.
6. **No extra turn**: a transcript producing questions renders questions and the strip on one
   screen; answering both is one `answer()` call.
7. **End to end**, backend and frontend running: *"notes on the human digestive system for my
   class 11 biology exam"* → strip shows inferred artifact and four exemplars → pick Short
   notes, confirm scope and extent change → pick a non-default design, confirm
   `select_presentation` is written and appears in the commitment → repeat touching nothing
   and confirm `source: "default"`.
8. **Exemplars**: identical bytes across two runs; editing a spec changes its hash and
   invalidates the cache.
