# §6 — Rendering / PDF

A deep read of one section. **No design, no decision. Chromium is not assumed
replaceable.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**This section sets the deployment floor** and contains the single most important
unmeasured number in the product: peak memory of one render.

---

## 1. What rendering actually is

**Responsibility.** Document mapping + template id → HTML → PDF, **and** report what it
observed while printing.

**Starts** at a `Document` (as a plain mapping — the engine does not import the agent's
types). **Ends** at bytes plus a `RenderResult`.

**Two jobs, and the second is the one that shaped the choice of engine** `[OBSERVED]`:
the renderer is also the only component that can say what actually reached the paper.

---

## 2. What exists today

### The split

`[OBSERVED]` `engine/render.py`, 391 lines.

- **`render_html(doc, template_id, colophon)`** — *"merge: document + template → HTML.
  Pure, no browser, no model."* Jinja2 with `StrictUndefined`.
- **`render_pdf(...)`** — *"merge → print. One browser, one page."*

The engine's independence is deliberate: *"It does not import the agent's types: it
renders whatever satisfies the shape, which is what keeps the two subsystems independent
when the agent's contracts change at M3."*

### The print sequence

`[OBSERVED]` Inside `with sync_playwright() as p:` — **a fresh `p.chromium.launch()` per
call**:

```
set_content(html, wait_until="networkidle")
evaluate("document.fonts.ready")        # web fonts load after `load`
emulate_media("print")
set_viewport_size({width: _A4_CSS_PX, height: 1123})
evaluate("document.fonts.ready")
evaluate(_OVERFLOW_PROBE) · (_UNRENDERED_PROBE) · (_REALIZATION_PROBE) · (_SCALE_PROBE)
pdf(prefer_css_page_size=True)          # NO margin argument
```

Two comments carry hard-won reasons:

- **No margin argument.** *"CSS owns the page geometry … Passing margins here would
  silently override them"* — including `@page :first` for a full-bleed cover.
- **Viewport must be the page.** *"Playwright's viewport is 1280px, so a `width: 100%`
  element lays out at 1280 and appears to overrun A4 by 486px while printing perfectly —
  the mirror image of the bug this probe was fixed for, and just as misleading."*

### The four probes

`[OBSERVED]`

| Probe | Reads | Needs layout? |
|---|---|---|
| `_OVERFLOW_PROBE` | `getBoundingClientRect()` vs a 794px limit | **yes** |
| `_SCALE_PROBE` | what Chromium shrank the document to | **yes** |
| `_UNRENDERED_PROBE` | `.unrendered` elements **the template emitted** | no |
| `_REALIZATION_PROBE` | `data-realization` attributes **the template wrote** | no |

### Environment capture and the browser check

`[OBSERVED]` `render_environment` is *captured in the engine, not passed in* — *"the
caller cannot see the resolved browser build or the template version, and System Design
Rev. 4 invariant 10 is unenforceable unless the engine reports what it actually read."*

`browser_status()` / `browser_missing()` carry the sandbox lesson: the check must stat
**both** builds, because *"Headless `launch()` runs the headless shell, a separate
download."* And `browser_missing()` is deliberately narrow — *"it must never be the reason
a healthy run does not happen."*

### The honesty table, in a template

`[OBSERVED]` `study-notes.html.j2`:

```
is-subset-of / is-part-of  →  indented-layers
precedes                   →  numbered-steps
causes                     →  labelled-arrows
associates-with            →  undirected-cluster
else                       →  <div class="unrendered" …>
```

With the rule stated in CSS comments: *"One geometry per relation, each permitted for
that relation by Representation Boundary Rev. 3 §2's honesty table. The template chooses
among honest options; **it never picks a geometry the relation forbids.** `causes` is
deliberately NOT the `precedes` geometry: sharing it is the table's named dishonesty,
because it collapses order into causation."*

**All four templates have the `{% else %}` → `unrendered` branch.** The `chips`-class
silent-drop bug is fixed everywhere.

---

## 3. Problems

### The §5↔§6 mismatch, now quantified — and worse than previously stated

`[OBSERVED]`

| Template | relation branches | distinct geometries |
|---|---|---|
| `study-notes` (default) | 4 → all 5 relations | **4** |
| `module-guide` | 2 (`is-subset-of`, `precedes`) | **1** — `layered-flow` |
| `night-lab` | 2 | **1** — `layered-flow` |
| `grimoire` | 2 | **1** — `layered-flow` |

Two separate defects, not one:

1. **Three relations are invisible in three templates.** `is-part-of`, `causes`,
   `associates-with` → `unrendered`. Already known.
2. **Two relations are *conflated* in those same three templates.** `is-subset-of` and
   `precedes` both render as `layered-flow`. **This is the exact failure the rewrite
   existed to remove** — study-notes' own comment names geometry-sharing as *"the table's
   named dishonesty."* There, the named case is order-read-as-causation; here it is
   **containment read as order**: `AI contains ML` and `input precedes hidden` draw
   identically.

`[INFERENCE]` So `StackDiagram`'s defect was fixed in the default template and survives
in the other three. Nothing detects it, because `unrendered` reports *absence* and there
is no check for *two relations sharing one geometry*.

### A latent misattribution bug in the report

`[OBSERVED]` `backend/service.py:_representation_report`:

```python
drawn = list(rendered.realizations)
...
if block.kind == "relation":
    realization = drawn.pop(0)[1] if drawn else "(none)"
```

`realizations` contains one entry per relation block **the template actually drew**;
`unrendered` blocks contribute none. So with three relation blocks where the second is
unrendered, block 2 pops **block 3's** realization and block 3 gets `"(none)"`.

**Not a gap — a misattribution.** The report would claim block 2 was drawn with block 3's
geometry. And the condition that triggers it — a relation a template cannot draw — is the
normal case in three of four templates.

### Performance and deployment

**O2 — a fresh Chromium process per PDF.** `[OBSERVED]` `Build-Spec.md` §8 specifies
*"one long-lived browser per worker, recycled every 200 renders."* The code launches one
per call. **The implementation contradicts its own spec.**

**O3 — unbounded threads, each launching a browser.** `[OBSERVED]` `jobs.py` spawns a
daemon thread per generation; each calls `render_pdf`.

**`sync_playwright` in an async service.** `[OBSERVED]` Endpoints are `def`, so FastAPI
threadpools them and the event loop is safe — but it also means the renderer cannot be
awaited, and CC4 (everything synchronous) is partly anchored here.

**Three of four templates fetch webfonts at render time.** `[OBSERVED]` With
`wait_until="networkidle"`, a host without egress waits out the timeout, then prints with
fallback fonts — **which changes pagination**, and pagination is artifact-owned truth.

**Fonts are a property of the host.** `[OBSERVED]` `study-notes` asks for
`Source Serif 4 / Segoe UI / Cascadia Mono`. A slim Linux image resolves none.

**The engine is not network-pure, and a test asserts it is.** `[OBSERVED]`
`tests/test_boundaries.py` forbids `engine/` from importing `httpx`/`requests`/`socket`,
and Build-Spec §8 leans on that purity to justify golden-image testing. The Python package
makes no network call; **the browser it drives does.** The test passes and the claim is
false.

**Known Chromium limits, both documented** `[OBSERVED]`:
- A figure caption can separate from its figure at a page boundary — Chromium ignores
  `break-after: avoid` on a flex container.
- Full-bleed page tint is impossible past page 1 — *"Chromium neither propagates html/body
  background into `@page` margins nor lets `position: fixed` escape the content box"*,
  proven with three experiments and recorded as *"the first observed cost of choosing
  Chromium."*

**A1's other half lives here.** `[MEASURED]` `parallel-state: "No realization exists"`
appears in 4 of 8 plans — computed before approval, ignored by the gate.

### Strong inference

- **Chromium is here to measure, not to print.** The overflow and scale probes exist
  because we cannot know space consumption without rendering, and because Chromium
  answers overflow by silently shrinking every page. A renderer that computes layout as it
  flows knows before it draws — **so the measurement requirement is partly a consequence
  of the engine choice, not an independent requirement.**
- **The deployment blocker is the process model, not Chromium.** Browser-per-render **+**
  unbounded threads **+** 512 MB is the combination. Fix any one and it survives.
- **Two of the four probes are the template reporting back what it already decided.**
  That is a boundary confusion: the template knows at merge time which branch it took and
  which kinds it could not draw. Asking a browser is a round trip to learn something
  authored two steps earlier.

### Unknown — and this is the section's defining gap

- **Peak RSS of one render.** `[UNKNOWN]` Decides whether 512 MB is viable, whether
  pooling matters, and whether the renderer question is urgent.
- **Browser-launch share of the 323s generate stage.** `[UNKNOWN]` Could be 2s or 25s.
- **Concurrent ceiling.** `[UNKNOWN]`
- **Can WeasyPrint produce these templates?** `[UNKNOWN]` — `@page :first`, full-bleed
  covers, and whatever flex/grid the four templates use.
- **Do we need live layout measurement at all**, or is uninspectable pagination
  acceptable? `[UNKNOWN]` and it is a product question, not a technical one.

**All of the first four are answerable with zero model calls** against the saved
`generate-01` document JSON.

---

## 4. The key architectural question

**What must the renderer be able to tell us, and what merely happens to be easy to ask a
browser?**

Sorting the four probes by that test `[INFERENCE]`:

| | Question | Answerable without a browser? |
|---|---|---|
| `unrendered` | *"which block kinds did the template not draw?"* | **yes** — the template emitted the marker; parse the HTML |
| `realizations` | *"which geometry did each relation get?"* | **yes** — same |
| `overflow` | *"does anything exceed the page width?"* | **no** — needs layout |
| `scale` | *"was the whole document shrunk?"* | **no** — and it is Chromium-specific behaviour |

So the honest requirement is **one**: *can something overflow, and did it*. And `scale` is
not a general requirement at all — it is the consequence of Chromium's particular
shrink-to-fit response. A renderer that refuses to shrink would make the scale probe
meaningless rather than unimplementable.

`[INFERENCE]` That reframes the engine question. It is not *"can we replace Chromium and
keep four measurements."* It is *"is overflow detection worth a browser?"* — and the
answer depends on whether overflow is a defect we must catch before delivery or a
cosmetic risk we accept.

**Second question, from the template survey:** the honesty table is enforced by
*convention in four separate templates*, and three of them violate it. Rev. 3 §2 is a
document; nothing in code says `is-subset-of` and `precedes` may not share a geometry.
**That is a check `render_html` could make at merge time**, without a browser, from the
template's own `data-realization` attributes.

---

## 5. Where this section starts and ends

**Current** `[OBSERVED]`: starts at a document mapping, ends at bytes + observations.
`_representation_report` (in `backend/service.py`) turns those observations into the
report — so **interpretation lives in the backend, measurement in the engine**, which is
the right way round.

**Boundaries worth questioning** `[INFERENCE]`:

- **`render_html` and `render_pdf` are already separable** and only one needs a browser.
  The two template-authored probes belong to the first.
- **Is the engine a library or a service?** In-process means the browser's lifetime is the
  request's. A service means a warm browser and a bounded pool — which is Build-Spec §8's
  own answer, unimplemented.
- **Template identity is a §6 concern with §5 consequences.** `render_environment`
  captures `template_version` as a hash, which is right — but the *relation coverage* of a
  template is not part of any contract.

---

## 6. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| Chromium absent | `BrowserMissing`, refused **before** the model call | well-made — the check is in `service.generate` precisely so a spent generation is not discarded `[OBSERVED]` |
| Chromium present but broken | render attempted; the narrow check *"must never be the reason a healthy run does not happen"* | deliberate |
| Headless shell missing, full Chromium present | detected — both builds stat'd | the lesson is in the code |
| Block kind with no branch | `unrendered` reports it | fixed in all four templates |
| Relation with no branch | `unrendered` reports it, **and subsequent realizations misattribute** | latent bug |
| Two relations sharing a geometry | **nothing** | honesty violation, 3 of 4 templates |
| Horizontal overflow | whole document shrunk; `scale < 1.0` reported | *"Below 1.0 every page was shrunk, including a full-bleed cover that then stops reaching the paper edge."* |
| No egress, webfont template | waits out `networkidle`, prints with fallbacks | silent pagination change |
| Concurrent renders | N Chromium processes | `[UNKNOWN]` ceiling |

---

## 7. What makes this section valuable

`[OBSERVED]` Four things worth preserving whatever the engine becomes:

1. **The engine does not know the agent's types.** A duck-typed mapping is what lets a
   template fix happen without a regeneration.
2. **It reports what it read, not what it was told.** `render_environment` captured in the
   engine is the only reason invariant 10 is enforceable.
3. **It reports what it could *not* draw.** `unrendered` exists because three `chips`
   blocks once vanished from a finished PDF.
4. **The browser check is narrow on purpose**, and placed before the expensive call.

**And one thing that is genuinely excellent:** the relation→geometry mapping is
*documented against a rule* and the rule is cited in the template that follows it. The
problem is that three templates do not.

---

## 8. Constraints and cross-section effects

**On §2** — `anticipates` is the only channel by which planning learns what can be drawn,
and `shortfalls()` is computed from a capability table that describes *this* renderer.
**Change the engine and that table changes**, which changes feasibility, which changes
extent (`weight()`).

**On §5** — the block union is what templates must branch on, and the five relations are
what the honesty table must realize. Adding a representation is three edits.

**On §4** — a licence (`diagnosis`) is generation's output and the renderer's input. A7's
6 undiagnosed blocks render fine, which is why nothing stopped them.

**On §7** — `.pdf`, `.html` and `.json` all persisted; the HTML is an intermediate that is
kept. `render_environment` belongs to artifact identity.

**On §8** — **this stage is the deployment floor.** ~700 MB install, a process per render,
an unmeasured memory profile, and a font dependency that changes output rather than
failing.

---

## 9. Solution directions — compared, not chosen

**A. Measure first.** Peak RSS, launch share, concurrent ceiling, all against the saved
document JSON. *Delivers:* the four unknowns that gate every other option here.
*Cost:* **zero model calls.** Nothing below can be chosen without it.

**B. Pool the browser.** One long-lived instance per worker, recycled — Build-Spec §8's
own answer. *Delivers:* launch cost and most of the memory problem. *Cost:* the engine
stops being a pure function; process lifetime becomes a design concern.

**C. Move the two template-authored probes to merge time.** Parse the HTML string for
`.unrendered` and `data-realization`. *Delivers:* two of four measurements without a
browser, **and fixes the misattribution bug** by pairing in source order rather than DOM
order. *Cost:* small.

**D. Check the honesty table in code.** At merge time, assert no two relations share a
geometry within one template. *Delivers:* the conflation defect in 3 templates, and it
needs no browser. *Cost:* small.

**E. Drop `networkidle`; inline or self-host fonts.** *Delivers:* removes a silent
pagination change and a 30s stall on egress-less hosts. Also makes the boundary test's
purity claim true. *Cost:* small; font licensing needs checking.

**F. Try WeasyPrint on the saved document.** *Delivers:* whether a non-browser path exists
at all. *Loses:* the two layout probes. *Cost:* zero model calls.

**G. Typst or ReportLab.** *Delivers:* small, fast, deterministic layout — and knowing
space consumption *before* drawing, which is the requirement behind the probes.
*Cost:* the templates are rewritten, and 2,480 lines of Jinja/CSS encode the block
vocabulary. *Sequencing:* not before §5 settles.

**H. Renderer as a service.** *Delivers:* warm browser, bounded concurrency, independent
scaling, and it removes Chromium from the backend image. *Cost:* an extra deployment unit
and a network hop.

**I. Accept uninspectable pagination.** Drop overflow/scale, keep whatever engine is
cheapest. *Delivers:* the largest simplification available. *Costs:* a real capability —
and `scale < 1.0` silently ruins full-bleed covers, which is the failure that would go
unseen.

**The shape:** **A is a precondition, not an option.** C, D and E are small, browser-free,
and each fixes a measured or observed defect. B is Build-Spec's own answer to the
deployment problem. F is the cheapest test of the biggest question. G and H are real
architecture. I is a product decision disguised as a technical one.

---

## What remains genuinely open

1. **Peak RSS of one render.** The number the whole deployment story waits on.
2. **Is overflow detection worth a browser?** The honest form of the Chromium question.
3. **Can WeasyPrint render these four templates?** Decides whether a cheap path exists.
4. **Should relation coverage be part of a template's contract?** Three templates draw
   two relations identically and nothing notices.
5. **In-process, pooled, or service?** Changes what §6 is allowed to be.
6. **Who owns the capability table** that says what this build can draw — it describes the
   renderer and lives in `agent/treatment.py`.
