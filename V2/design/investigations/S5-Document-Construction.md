# §5 — Document Construction / Assembly

A deep read of one section. **No design, no domain model, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**The section is thin in code and load-bearing in architecture.** `_assemble` is ~25
lines. The *document model* — the block vocabulary it assembles into — is the contract
between §4 and §6 and the thing the whole product's representation question turns on.

**And a finding that reframes an earlier conversation:** the semantic-representation /
realization split — *"the LLM says 'show this as a containment relationship', the engine
decides the geometry"* — **already exists in V1**, for relations. See §4 below.

---

## 1. What this section actually is

**Two responsibilities, and only one of them is `_assemble`:**

- **Assembly** — combine generated sections into one `Document`, taking front matter
  from the approved plan rather than from the model.
- **The document model** — the typed vocabulary a document may contain. Written by §4,
  read by §6, and the thing that decides what can be said at all.

**Starts** when sections exist. **Ends** at a `Document` ready to render.

---

## 2. What exists today

### Assembly

`[OBSERVED]` `agent/generate.py:_assemble(plan, situation, sections)` — and its whole
argument is in the docstring:

> *"The title, who it is for and what they will be able to do are the **plan's**
> answers, already shown to the user and agreed. Asking a model to restate them would
> let them drift from what was approved for no gain."*

So `title`, `subtitle`, `assumed_entry`, `target_capability` come from the situation, and
`deliberate_omissions` from `consequence.exclusions`. No model call. Both string fields
have defensive defaults (*"Not stated — this document assumes no particular
background."*).

### The Document

`[OBSERVED]` `agent/contracts.py:Document` — `title`, `subtitle`, `cover`,
`running_head_left/right`, `footer_text`, `assumed_entry`, `target_capability`,
`sections[]`, `deliberate_omissions[]` of `MarkedGap{topic, consequence, when_to_learn}`.

`assumed_entry` and `target_capability` are required, with field descriptions that state
why: *"Stated so the reader can tell whether it is for them"* and *"Concrete, not a
topic list."*

### The block vocabulary — 11 kinds, and one principle

`[OBSERVED]` `Prose` is the base: *"The default carrier. **Every other block is a
departure from this.**"*

Every non-prose block subclasses `Departure`, which carries:

```python
realizes: ClassVar[bool] = True     # does this block *draw* something?
diagnosis: str | None = None        # which prose failure it answers
```

`Callout` is the one exception — `realizes = False`, because *"it is text in a box: it
asserts no shape, order, containment or magnitude, so it cannot make a false spatial
claim."*

And the guard that compares the two `[OBSERVED]`:

> *"A diagnosed E may not be drawn … the model diagnoses that the reader needs to see the
> thing itself, then reaches for the nearest available block and draws boxes.
> `is-part-of` over [mucosa, submucosa, muscularis, serosa] renders, looks like a
> diagram, and is not what the reader needed. **Nothing caught it before, because
> `diagnosis` and `kind` were recorded side by side and never compared.**"*

The error message offers exactly two repairs and forbids a third: *"Do not delete the
diagnosis to make this pass."*

It is also explicit about what it cannot catch: *"a **misdiagnosis**. A model that labels
the same block `topology` draws exactly the same false figure and passes … This guard
catches self-contradiction only — which is the case worth catching first, because a model
that diagnosed correctly and drew anyway is the one we can still repair."*

### `diagnosis` is free text — deliberately

`[OBSERVED]` And the reason is worth quoting, because it is the strongest argument
*against* typing a vocabulary that I have found in this repo:

> *"Free text rather than an enum, deliberately. An enum of the seven failures in §13
> would make the one interesting reading impossible: **a model that needed a failure the
> taxonomy does not list.** The prompt names the seven and tells the model to write
> `unlisted: <name>` when none fits, so the gap arrives as data."*

So V1 types the vocabularies it considers closed and leaves open the one it is still
learning. That is a deliberate distinction, not an oversight.

### `RelationalStructure` — the semantic block

`[OBSERVED]` This is the finding worth the most.

```python
kind: Literal["relation"]
relation: Literal["is-subset-of","is-part-of","precedes","causes","associates-with"]
entities: list[Entity]      # "Order is meaning, not layout."
```

> *"Replaces `StackDiagram`, which was named after a **geometry**. That is the defect
> Representation Boundary Rev. 3 calls treating 'diagram' as the decision: a stack says
> *sits on top of*, so containment and sequence both came out as pyramids and one of them
> was false … **The model states the relation. It never names a geometry** — which
> geometry tells that relation's truth is Rev. 3 §2's honesty table, applied by the
> template."*

**That is exactly the architecture the blank-page discussion proposed as new work**:
educational decision → semantic representation specification → realization capability.
It exists, it is typed to five relations, and the realization is the template's.

---

## 3. Problems

### Measured

**A7 — and its exact shape is now clear.** `[MEASURED + OBSERVED]` 36 departures, **6
undiagnosed**, `clean: false`, document renders.

`diagnosis: str | None = Field(default=None, ...)` — **optional, defaulting to `None`.**
And the guard's condition is `if self.realizes and self.diagnosis is not None`. So a
departure with **no** diagnosis passes the validator entirely: the guard catches
self-*contradiction*, never *absence*. Six blocks exercised that default.

`[INFERENCE]` A7 is therefore one field's optionality, not a missing mechanism. The
mechanism is built and the door is open beside it.

### Observed

**The vocabulary is mixed: 1 semantic block and 10 presentational ones.**

| Semantic | Presentational | Structural |
|---|---|---|
| `RelationalStructure` | `Code`, `Table`, `BulletList`, `Chips`, `WorkedExample`, `CheckQuestion`, `Callout` | `Prose`, `Heading`, `Subhead` |

`[INFERENCE]` So the original objection — *"a Document model designed around a coding PDF
cannot be the universal representation"* — is **half-answered**. The diagram half was
fixed properly and named after the relation. The rest is still named after what it looks
like. Whether that matters depends on whether `Table` and `Code` are genuinely
domain-neutral in a way `StackDiagram` was not `[UNKNOWN]` — a table is arguably a
*presentation* of comparison, and comparison is a relation.

**`Heading` and `Subhead` are blocks inside a `Section` that already has a `heading`.**
`[OBSERVED]` Two levels of heading in the block stream plus one on the container. With no
section decision (Q8), the block-level headings are the only way to structure inside a
section — so they are doing the job a section decision would do, from inside the content.

**The semantic vocabulary exceeds the realization vocabulary.** `[OBSERVED]` Five
relations; `module-guide`, `night-lab` and `grimoire` have no realization for
`is-part-of`, `causes`, or `associates-with`. So a document can legally assert a relation
that **three of four templates cannot draw** — and `RenderResult.unrendered` exists
precisely because three `chips` blocks once vanished from a finished PDF.

**Q8 lands here too.** `[OBSERVED]` §4 established the cause (`plan_for`: *"Every concept
the module covers becomes one section"*). The *consequence* is here: `Section` has no
sub-structure, so a 6-section module over 7 concepts is inexpressible.

**`_assemble` lives in `agent/generate.py`.** `[OBSERVED]` Document identity is
plan-derived and assembled inside the generation module, which makes §5 not a stage so
much as a function §4 happens to call.

**`title = situation["subject"]`.** `[OBSERVED]` And on the module path
`plan_for` sets `situation["subject"] = module.title`. So the document title is the
module title, correctly — but by way of overwriting the subject field, which is the same
field §2's breadth appears to track.

### Strong inference

- **This is the one stage with no CC1 instance.** Everything `_assemble` computes is
  used. The guard it carries **actually raises**. It is the only place in V1 where a
  computed judgment blocks something.
- **And that guard is the model for the rest.** A1, A2, A6, A7 all want exactly this
  shape: compare two recorded things and refuse the contradiction.
- **The block union is the real coupling point in the product.** Adding a representation
  means touching the union, every template, and the generator prompt — three edits, which
  is the shape the `chips` bug came in.

### Unknown

- Are `Table`, `Code`, `WorkedExample` domain-neutral, or presentational in the way
  `StackDiagram` was? `[UNKNOWN]` — never tested on a non-technical subject end to end.
- Are five relations enough? `[UNKNOWN]` — `unlisted:` was **empty in the one run**, so
  no taxonomy gap has been observed yet. That is also the mechanism that would report
  one.
- Would a section level in `Section` change generation granularity for the better?
  `[UNKNOWN]`
- How often does a model diagnose correctly and draw anyway (what the guard catches) vs
  misdiagnose (what it cannot)? `[UNKNOWN]` — 0 guard trips observed.

---

## 4. The key architectural question

**Is the document model a vocabulary of things a document contains, or a vocabulary of
claims a document makes?**

V1 answers both, in one union, and the split runs exactly along the line where it
matters:

```
RelationalStructure   →  states a CLAIM  ("is-subset-of over [AI, ML, DL]")
                         template chooses the geometry
Code / Table / Chips  →  states a FORM   ("this is a table")
                         template chooses only the styling
```

`[INFERENCE]` The claim-shaped block is the one that was rewritten after a real defect —
containment and sequence both rendering as pyramids. The form-shaped blocks have not been
stress-tested against a domain where their form is wrong.

**The question to ask of each remaining block:** *could two different meanings produce
this same block and one of them be false?* That is the test `StackDiagram` failed. For
`Code` the answer is plainly no. For `Table` `[INFERENCE]` it is arguably yes — a
comparison table and a lookup table are different claims with the same form, and the
reference's five document jobs distinguish *retrieve* from *look up* on exactly that
basis.

**Second question, from A7:** the guard proves that comparing `diagnosis` against `kind`
catches real errors. `diagnosis` being optional means it is compared only when the model
volunteers it. **Making it required is the smallest change in the repository with a
measured defect behind it.**

---

## 5. Where this section starts and ends

**Current** `[OBSERVED]`: `_assemble` runs inside `_from_plan`, after the unit loop,
before `check_document`. The document model is in `agent/contracts.py`, imported by
`engine/` only through duck-typed mappings — `render_html` takes *"a document-shaped
mapping"* and *"does not import the agent's types: it renders whatever satisfies the
shape."*

**That boundary is good and should be kept** `[INFERENCE]` — it is what allows a template
fix without a regeneration, and what makes the renderer swappable.

**Boundaries worth questioning** `[INFERENCE]`:

- **Assembly belongs with §4 or is a stage — not both.** Its current position makes
  "document identity" a generation concern.
- **The block union may want splitting** into claims and forms, which would put the
  honesty machinery (`diagnosis`, `realizes`, the guard) on claims only, where it belongs.
- **`Section` is the missing level**, and it is a §2 decision before it is a §5 shape.

---

## 6. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| Departure with a `perceptual-referent` diagnosis and `realizes=True` | **raises**, with two named repairs | the guard working `[OBSERVED]` |
| Departure with **no** diagnosis | accepted, renders | **A7** |
| Departure misdiagnosed but self-consistent | accepted, renders | out of mechanical reach, and the code says so |
| A relation three templates cannot draw | accepted; `unrendered` reports after the fact | §5↔§6 mismatch |
| A block kind a template has no branch for | `unrendered` probe catches it | the `chips` bug, now detected |
| `unlisted: <name>` diagnosis | accepted as data — the taxonomy-gap signal | never observed `[MEASURED]` |
| No exclusions | `deliberate_omissions: []` | fine |
| Missing situation fields | defensive default strings | fine |

---

## 7. What makes this section valuable

`[OBSERVED]` Three things, and they are the best-argued code in V1:

1. **Front matter cannot drift from the plan.** Not asking the model is the mechanism.
2. **`diagnosis` + `kind` are compared, not just recorded.** The only place in V1 where
   a contradiction between two model judgments raises.
3. **The relation names the claim, never the geometry.** Which makes the honesty table a
   template concern and keeps two different meanings from producing one picture.

And the deliberate non-typing of `diagnosis` — so a taxonomy gap arrives as data rather
than being coerced into the nearest listed value — is a genuinely good argument, and a
caution against typing everything reflexively.

---

## 8. Constraints and cross-section effects

**On §2** — `anticipates` (planning's prose-failure judgment) and `diagnosis` (the
block's) are **the same vocabulary used at two stages**, and §4 showed the first never
reaches the writer. They should agree and are never compared.

**On §4** — the union is what generation may emit; the guard is the only contract
violation generation can trip. Q8's granularity follows from `Section` having no
sub-level.

**On §6** — the union is what templates must branch on, and the five relations are what
the honesty table must realize. **Three templates already fall short.** Any renderer
change starts here.

**On §7** — the Document JSON is persisted deliberately, so this model is a stored
schema: changing it is a migration concern, not just a code change.

---

## 9. Solution directions — compared, not chosen

**A. Make `diagnosis` required on `Departure`.** *Delivers:* A7 structurally — an
unlicensed departure becomes inexpressible. *Cost:* one field, plus a prompt line.
*Risk:* forces a diagnosis where the model has none, which may produce a *false*
diagnosis instead of an absent one — worse, because the guard then compares against
noise. `[INFERENCE]` A required field with an explicit `"unlisted:"` escape already has
precedent in this file.

**B. Split the union into claims and forms.** Honesty machinery on claims only.
*Delivers:* a principled place for future representations, and a test for each existing
block (*"could two meanings produce this and one be false?"*). *Cost:* a contracts
change plus every template.

**C. Compare `anticipates` against `diagnosis`.** The plan said which prose failure this
concept would hit; the block says which one it answered. *Delivers:* treatment becomes
plan-vs-execution instead of two opinions — the thing §4 identified as missing.
*Cost:* small, and it needs §4's option B (render `anticipates` into the brief) first.

**D. Give `Section` a sub-level.** *Delivers:* Q8. *Cost:* §2 needs a section decision
first; then §4's granularity and every template change.

**E. Move `_assemble` out of `generate.py`.** *Delivers:* clarity about what owns document
identity. *Cost:* trivial. *Value:* mostly organisational.

**F. Close the relation/realization gap.** Either give all four templates all five
relations, or make the union's relation set a function of the chosen template.
*Delivers:* removes the case where a legal document cannot be drawn. *Cost:* template
work, or a coupling between §5 and §6 that does not currently exist.

**G. Leave it.** *Argument:* it is the only stage with no CC1 instance and the only one
whose check actually blocks. *Argument against:* A7 is measured and one field wide.

**The shape:** A is the smallest change in the repo with a measured defect behind it. C is
the one that makes two existing vocabularies talk to each other. B and D are real
architecture and both depend on decisions elsewhere. F is a §6 question wearing a §5
hat.

---

## What remains genuinely open

1. **Required `diagnosis`, or a required-with-escape?** Forcing a value may trade absence
   for falsehood.
2. **Are the form-shaped blocks domain-neutral?** Untested outside technical subjects.
3. **Are five relations enough?** The `unlisted:` channel exists to tell us and has never
   fired.
4. **Should `anticipates` and `diagnosis` be one vocabulary or two?**
5. **Does `Table` fail the StackDiagram test?** A comparison table and a lookup table are
   different claims with one form.
6. **Where does the section level live** — §2's decision, §5's shape, or both?
