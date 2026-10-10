# §4 — Content Generation

A deep read of one section. **No design, no domain model, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**The stage that passed.** The one end-to-end run returned `satisfied: true`,
`coverage: 1.0`, `concepts_missing: []`, `units_missing: []`, `problems: []`,
`repairs: 0`. Everything below is about a stage that is **correct and slow**, plus
three defects the fulfilment check is structurally unable to see.

---

## 1. What generation actually is

**Responsibility.** Turn each approved work order into written content, and verify each
against the promise it was given.

**Starts** at an approved commitment (or a module-scoped narrowing of one).
**Ends** at a `Document` plus a fulfilment report.

**Its designed property, from the docstring** `[OBSERVED]` `agent/generate.py:115`:

> *"Per unit, not per document, for a reason beyond fitting in a context window: each
> call is answerable for a small, checkable promise. A model asked for one part either
> delivers it or visibly doesn't. **The system, not the model, is answerable for the
> artifact matching the plan.**"*

That is the change that took coverage from **2/17 to 17/17** on an unchanged model, and
it is the single most successful decision in V1.

---

## 2. What exists today

### The loop

`[OBSERVED]` `agent/generate.py:_from_plan`:

```
orders = requirements(plan)                    # one work order per module/unit
for order in orders:                           # SEQUENTIAL
    for attempt in range(2):
        user = _unit_brief(request, situation, order, missing=<from last report>)
        completion = provider.complete(system=unit_v1, user=…, schema=Section, max_tokens=32000)
        candidate  = _load_section(completion.text)      # repair on failure
        trial      = check_unit(order, candidate)
        keep the attempt with MORE concepts covered     # not the later one
        if trial.satisfied: break
document   = _assemble(plan, situation, sections)
fulfilment = check_document(plan, document, reports)
```

Three details worth naming `[OBSERVED]`:

- **A failing unit does not fail the run.** The exception is caught per unit, recorded
  as ungenerated, and *"the reason travels with it"* — because swallowing it produced a
  document reported only as *"doesn't match what was approved,"* which reads as model
  omission when the real cause was a spent rate limit. *"Same symptom, opposite fix."*
- **The better attempt wins, not the later one** — *"a retry that covers less than the
  first would otherwise make asking again actively harmful."*
- **The heading is the plan's, not the model's** — `candidate.heading = order["heading"]`.

### The work order

`[OBSERVED]` `fulfilment.requirements(plan)` reshapes the plan into one order per part:
`{heading, why_here, concepts[], extent}` — *"each order carries its own concepts,
depths and anticipated treatments, and nothing else."*

**And it has an orphan safety net:**

> *"A covered concept in no unit would silently vanish. The plan page surfaces these as
> 'Also covered', so the user may well have approved one."*

Covered concepts belonging to no module are appended as a synthetic `"Also covered"`
order. **This is a real mitigation, and §3 showed it is structurally disabled on the
path the product actually uses** — see below.

### The brief

`[OBSERVED]` `_unit_brief` — deliberately narrow: *"the other units are not this call's
business, and including them is what let a model wander off and write a different part
than the one asked for."* It renders the request, purpose, entry point, target
capability, stated constraints, the heading, `why_here`, the approved size, and each
concept with its depth and `why`.

### Verification

`[OBSERVED]` `check_unit(order, section)` → `UnitReport`, where
`satisfied = generated and not concepts_missing`. `check_document(plan, document,
reports)` → `Fulfilment` with `coverage`, `concepts_missing`, `units_missing`,
`problems`. Treatment is **observation only**: `treatments_anticipated`,
`treatments_produced`, `depths_required` — *"Neither makes a document unsatisfied."*

### Measured performance

`[MEASURED]` 5 calls · **323s** · 23,290 in / 8,959 out · 14 pages · 3,477 words ·
54 blocks · 36 departures · 0 repairs.

---

## 3. Problems

### Measured

**O1 — strictly sequential, and the units are provably independent.** `[OBSERVED +
MEASURED]` `_unit_brief(request, situation, order, missing)` reads the request, the
situation, and **its own order**. Nothing from a prior section. At ~65s per call,
parallel wall-clock is one call rather than five — **~4× latency at identical token
cost, sitting in a `for` loop.** No fulfilment check would ever surface this.

**A7 — departures escape without a licence.** `[MEASURED]` 36 departures, **6
undiagnosed**, `unlisted: 0`, `unrendered: 0`, `scale: 1.0`, `clean: false`. The check
runs, records, and does not block. The PDF renders.

**A4's other half.** `[MEASURED]` The brief tells the model *"Approved size for this
part: ~4 pages."* It produced **14**. So either the model disregards the figure or the
constant is so wrong that the required content cannot fit it. `[UNKNOWN]` which.

**`coverage: 1.0` verifies mention, not truth.** `[OBSERVED]` `covers()` is normalized
substring matching of a concept name against section text. A document can be
`satisfied: true` and factually wrong throughout. With §0 absent there is no mechanism
that could check otherwise.

### Observed

**`anticipates` never reaches the generator.** `[OBSERVED]` **Zero matches** for
`anticipates` in `agent/generate.py` and `agent/prompts/unit_v1.md`. The field is
present in the order (concepts are full `Covered` dicts) and `_unit_brief` does not
render it.

Consider what that field is for: *"Which failure of prose this concept's content is
expected to hit … This says only that prose alone will not carry it, and in which way."*
It drives `derive_extent` (via `weight()`) and `derive_feasibility` (via
`shortfalls()`) — **both planning-side** — and it does not drive the writing. A
judgment about how content must be written is consumed only by arithmetic and a report.

This is also why treatment comparison is meaningless as a check: the observer says so
directly — *"`anticipates` never reaches the generator, so these are two independent
judgments, not a plan and its execution."*

**`_unit_brief` puts raw Python dicts in the prompt.** `[OBSERVED — verified by
running it]`

```
- They explicitly asked for: {'text': 'section wise', 'axis': 'depth_register'}
- They explicitly asked for: {'text': 'from scratch', 'axis': 'entry_point'}
```

`stated` was a list of strings when the brief was written; the provenance work made it
a list of `StatedConstraint` objects and **the brief was not updated**. The model is
shown Python syntax and an internal axis name. `_brief` (the non-plan path) has the
same line.

`[INFERENCE]` A regression introduced by a good change, in a file with no test that
renders a brief.

**The orphan safety net cannot fire on the module path.** `[OBSERVED]` This is the code
path behind §3's finding.

`curriculum.plan_for(plan, index)` builds a narrowed plan whose scope is
`[by_concept[c] for c in module.concepts if c in by_concept]` — **this module's concepts
only**. Then `requirements()` runs on that narrowed plan, where `placed == by_concept`
by construction, so `orphans` is **always empty**.

So: `requirements()` has a mitigation for stranded concepts, and the module-at-a-time
flow — the product's actual flow — structurally disables it. The whole-plan path
(`generate_document(request)` with no plan) keeps it.

**`plan_for` silently drops phantoms.** `[OBSERVED]` The same
`if c in by_concept` filter. A module claiming a concept scope does not carry loses it
here, with no report — and `check_unit` then verifies against the *narrowed* order, so
the concept was never required. **A2 becomes invisible at generation time.**

**Q8's cause is stated in `plan_for`'s docstring.** `[OBSERVED]` *"**Every concept the
module covers becomes one section**, so the existing per-part pipeline can generate and
verify it without knowing a curriculum exists."* Sections are one-per-concept by
construction. The git-commits reference wants 6 named sections over 7 concepts; V1
produced 11 sections from 11 concepts. The section decision does not exist because
generation reuses the unit machinery.

**`situation["subject"] = module.title` on the module path.** `[OBSERVED]` So generation
sees the module title as the subject. Given §2's finding that landscape breadth tracks
subject richness, this is worth noting as a place where a title's phrasing reaches a
model call `[INFERENCE]` — though `plan_for` does not re-derive, so the effect here is
on prose, not structure.

**Predecessor handling is deliberately absent.** `[OBSERVED]` *"Entry point stays the
curriculum's — adjusting it per module is predecessor handling, and that is deliberately
not here."* So module 4 is written assuming the curriculum's entry point, not module 3's
exit. Intentional, and a real constraint on multi-module coherence.

### Strong inference

- **The two-attempt repair loop is well-shaped and cheap.** Keeping the better attempt
  and feeding back `concepts_missing` is the mechanism behind 17/17. It should survive
  any redesign.
- **Generation is the only stage with real feedback.** `check_unit` output feeds the
  retry. Nowhere else in V1 does a check change behaviour. **That is why this stage
  works.**
- **And it is the only stage that cannot see its own most important defects.** A7
  (licences), A4 (size), A2 (phantoms) and Q8 (sections) are all invisible to
  `check_unit`, because it checks the *narrowed order it was given*.

### Unknown

- Does concurrent unit generation change output quality or trip provider throttling?
  `[UNKNOWN]` (free tier is 20/min, so 5 parallel is within limits — but that is not
  production.)
- Does the model use the `extent` line at all? `[UNKNOWN]` — testable by varying it.
- Would rendering `anticipates` into the brief improve representation choice, or just
  produce more departures? `[UNKNOWN]`
- Is two attempts the right budget? `[UNKNOWN]` — 0 repairs observed in the one run.
- What does coverage look like across more cases? `[UNKNOWN]` — n=1.

---

## 4. The key architectural question

**What is generation answerable for?**

The docstring's answer is precise and, on the evidence, true: *"the system, not the
model, is answerable for the artifact matching the plan."* `check_unit` enforces exactly
that, per unit, and it works.

**The question the evidence raises is whether "matching the plan" is enough.** Three
things the plan asks for that generation neither receives nor is checked on:

| The plan says | Generation receives | Generation is checked on |
|---|---|---|
| this concept at depth `work through` | the depth string, in the brief | **nothing** — depth is recorded in `depths_required`, never enforced |
| prose alone will not carry this (`anticipates`) | **nothing** | nothing |
| ~4 pages for this part | the string | nothing |

`[INFERENCE]` So the contract generation actually honours is **coverage of named
concepts**, and the plan promises four things. Three of the four are unenforced —
which is CC1 again, and it is why `satisfied: true` carries less than it appears to.

**The deeper question:** `covers()` is substring matching. It answers *"does the concept
name appear."* A stronger check needs either a source (§0) or a judge — and **the
absence of both is why this stage looks flawless.** `[INFERENCE]` One measured run with
`coverage: 1.0` is evidence that the mechanism fires, not that the content is good.

---

## 5. Where generation starts and ends

**Current** `[OBSERVED]`: starts at a commitment (whole plan) or `plan_for(index)` (one
module); ends at `Document` + `Fulfilment`. `_assemble` is inside this stage, not after
it.

**Boundaries worth questioning** `[INFERENCE]`:

- **The unit/section conflation is a boundary problem, not a generation problem.** One
  model call per *concept-as-section* is the consequence of `plan_for` mapping concepts
  to sections. If §2 gained a section decision, generation's granularity would change
  with it.
- **`_assemble` may belong to §5.** It currently lives in `generate.py`, which makes
  document identity (title, audience, capability) a generation concern when it is
  entirely plan-derived.
- **Verification sits inside generation and also after it.** `check_unit` (in the loop)
  and `check_document` (after). The second one is the only whole-artifact check in V1,
  and it runs on a **narrowed** plan on the module path — so it cannot see the
  curriculum.

---

## 6. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| One unit's call fails | recorded ungenerated **with the reason**; run continues | well-made `[OBSERVED]` |
| All units fail | `ValueError: produced no usable part for any of the N approved units` | correct |
| Retry covers fewer concepts | first attempt kept | well-made |
| Model returns invalid JSON | `_parse_or_repair` gives it its own validation error once | the repair-prompt defect lived here and is now pinned by a test |
| Model uses a class name instead of a discriminator tag | `_canonical(kind)` maps four known cases | *"silently deciding for it is how a wrong document looks right"* |
| A phantom concept in the module | dropped by `plan_for`, never required, never reported | **A2 invisible** |
| An orphan concept | `"Also covered"` order — **only on the whole-plan path** | **disabled on the module path** |
| Departure with no licence | recorded, document renders | **A7** |
| Depth ignored by the writer | recorded in `depths_required`, never enforced | unchecked |
| Output exceeds approved extent by 3× | nothing | **A4** |

---

## 7. What makes this stage work, and worth preserving

`[OBSERVED]` Four properties, and they are the reason this is the one stage that passed:

1. **Small checkable promises.** One call, one part, one list of concepts it must name.
2. **A check that changes behaviour.** `concepts_missing` feeds the retry prompt. This is
   the only closed loop in V1.
3. **Failure that is attributable.** A rate-limited call and an omitting model produce
   *different* reports.
4. **Monotonic retries.** The better attempt wins, so asking again is never harmful.

**Preserve all four.** `[INFERENCE]` Any redesign that makes generation one large call,
or removes the per-unit check, re-opens the 2-of-17 defect.

---

## 8. Constraints and cross-section effects

**On §2** — generation is the **only** source of real density, and extent is what the
user approves against. They are unconnected, which is A4. Also: `anticipates` is
planning's statement about writing and generation never sees it.

**On §3** — the commitment snapshot is the brief. Every §3 weakness (phantoms, orphans)
arrives here and is *silently absorbed* by `plan_for`'s filter rather than reported.

**On §5** — `_assemble` lives here; the block union is the contract between the two.

**On §6** — the block kinds generation emits must have template branches, or they vanish
(the `chips` bug). And `A7`'s licences are the renderer's input.

**On §7** — four files per module, and the Document JSON is deliberately kept: *"a
template fix should not cost another generation."*

**On §8** — 323s per module and the longest job the runner handles; concurrency here
multiplies against renderer concurrency.

---

## 9. Solution directions — compared, not chosen

**A. Run units concurrently.** *Delivers:* ~4× latency, no token cost, and it does not
weaken the per-unit contract — each unit stays independently checkable. *Cost:* small.
*Risk:* provider throttling in production `[UNKNOWN]`; the sync codebase makes it a
structural change (CC4).

**B. Render `anticipates` into the brief.** *Delivers:* the plan's representation
judgment reaches the writer, and treatment comparison becomes plan-vs-execution instead
of two opinions. *Cost:* one line. *Effect:* `[UNKNOWN]`.

**C. Fix the stated-constraint rendering.** *Delivers:* removes Python dict reprs and an
internal axis name from the prompt. *Cost:* one line, plus a test that renders a brief.

**D. Make the licence a required field on the departing block types.** *Delivers:* A7
structurally — an unlicensed departure becomes inexpressible rather than detected.
*Cost:* a contracts change plus prompt update. *This is the cheap alternative to the
tool-based document-construction idea, and it targets the same defect.*

**E. Enforce depth and extent, or stop recording them.** Currently both are told to the
model and checked by nothing. *Delivers:* either a real contract or an honest one.
*Cost:* small for the second, unknown for the first.

**F. Report what `plan_for` drops.** A phantom silently disappearing is the one place A2
becomes invisible. *Delivers:* A2 detectable at generation time even if §3 does not
gate. *Cost:* near zero.

**G. Keep the orphan net on the module path.** Either carry stranded concepts into the
module-scoped plan or surface them per curriculum. *Delivers:* the mitigation
`requirements()` already implements. *Cost:* small. *Question:* which module should own a
stranded concept — the same question §3's patch refuses to answer.

**H. Add a grounding or judging check.** *Delivers:* the gap between "mentioned" and
"true." *Cost:* large, and it depends on §0.

**I. Move `_assemble` to §5 and give sections their own decision.** *Delivers:* Q8.
*Cost:* touches §2, §4, §5 and every template. *Sequencing:* cannot precede a §2 section
decision.

**The shape:** C, F and B are one-line changes with real value. A is the largest latency
win in the product. D is the cheap answer to A7 and to the document-operations question.
G and I depend on decisions in §3 and §2 respectively. H depends on §0. E is a choice
between two honest positions.

---

## What remains genuinely open

1. **Does parallelism degrade quality or trip limits?** The only thing standing between
   us and 4×.
2. **Does the model use `extent` at all?** Decides whether A4's fix is arithmetic or
   also behavioural.
3. **Would `anticipates` in the brief improve representation, or add noise?**
4. **Is coverage-of-named-concepts a sufficient contract**, given depth, treatment and
   extent are all unenforced?
5. **Who owns a stranded concept?** Blocks G, and §3's patch declines to answer.
6. **Is the one clean run representative?** n=1, and the prime suspect did not appear.
