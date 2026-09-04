# Notes Engine Foundation

**Rev. 4 — 1 Sep 2026 — supersedes `Product-Bible.md`**

> ## ⚠ PARTLY SUPERSEDED — 4 Sep 2026
>
> Read **`Product-Semantics.md` (Rev. 1)** first. It is the current source of truth
> for what the product is and what it decides.
>
> **Dead here.** The product thesis; the taxonomy that treats *template* as a visual
> skin; "eight block types" as the vocabulary; figures as a small archetype set. The
> eight contracts and the entity model were derived from the superseded thesis and
> have not been re-derived.
>
> **Still alive.** The three verification layers (now richer — see Product-Semantics
> §3). Claim-specific source authority. Span rather than floor. Determinism scoped to
> a pinned environment. Content/presentation separation, proven by the theme swap.
>
> Kept as evidence and for the parts listed above, **not as foundation**. This file
> will be rewritten once Q2 (what knowledge wants which representation) is answered.

A document generation system. The intelligence decides what you need; the engine renders it as a page worth keeping.

Web version: https://claude.ai/code/artifact/4614ce11-c4e9-463f-8d67-7d94f0f2659f
Companion: `System-Design.md` (Rev. 3)

## Status legend

- **LOCKED** — Decided. Build against it. Changing it changes the architecture.
- **PROVISIONAL** — Current best design, deliberately not frozen. Expected to change once tested.
- **OPEN** — Genuinely unresolved. Do not pretend otherwise.
- **DEAD** — Considered and rejected, with the reason. Do not resurrect without new evidence.

---

## 1. What the product is — LOCKED

This is **not an AI agent that makes PDFs**. It is a document generation system that happens to use AI for some of its steps.

> It takes a topic and a situation, decides what you actually need, and renders it as a designed document you would study from.

Two halves, both essential, neither sufficient alone:

- **The scope decision** — what gets covered, how deep, in what order, what gets cut. Invisible until it fails, but it is what separates useful material from generated filler.
- **The designed page** — layout, visual hierarchy, diagrams, density. Visible in two seconds, and the reason anyone shares a screenshot.

**The purpose decides what goes in. The budget decides how much fits.** Time is a constraint, never the driver. A researcher learning ML and a student preparing for GATE DS/AI, both with seven months, should receive almost nothing in common — §8.2.

The product is **not** an LMS, an AI tutor, a progress tracker, a course marketplace, or a chatbot. It does not track mastery. It does not teach. It produces documents.

---

## 2. The problem — LOCKED

> The same topic has many correct outputs. The system's job is to decide which one you need, then produce it at a quality no prompt can reach.

Operationally this is **triage inside a declared span, under a declared budget** — not coverage of a domain. You cannot completely cover Generative AI, and promising completeness in an unbounded field is dishonest.

### 2.1 The three failures, and their one cause

| Observed failure | What it actually is | Check |
|---|---|---|
| Canonical diagram never appears | No typed requirement that this concept carries a visual | Spec declares `visual: required` → verify present |
| "0 to 100" assumes prior knowledge | An undefined-symbol error — a term used before it is introduced | Spec declares a span → verify no term precedes its definition |
| 150 questions, always something missing | No declared spec to measure output against | Spec declares counts and categories → count them |

One root cause: **nothing in the pipeline ever declares an obligation, so nothing can be checked.** Each check above needs no domain knowledge, which makes it cheap. That is the entire useful residue of the "compiler for pedagogy" idea.

**But mechanical checking is necessary, not sufficient.** Counting 150 questions says nothing about whether they are good questions; confirming a diagram exists says nothing about whether it is the right architecture. See §7.

### 2.2 Span, not floor

```
span: [entry, exit]

SDE1 → SDE2/3     (20 → 60, not 0 → 100)
zero → basics     (0 → 15)
```

- **Entry too high** → undefined terms, reader is lost. The original 0→100 bug.
- **Entry too low** → six chapters on what a `div` is. The budget is silently spent re-teaching. Worse in practice, because nothing looks broken.

A span is two lists: **assumed known** and **target capability**. Role anchors are a first guess, never the answer.

**The floor must be confirmed, not guessed:** *"I'm assuming you already know these 14 things. Uncheck anything you don't."*

**The floor rises with the Project.** Material already generated is below the floor for the next Spec. This is the concrete purpose of Project memory.

### 2.3 The three span checks

1. Nothing **below** the floor gets taught
2. Nothing **above** the ceiling gets taught
3. Nothing **inside** gets skipped — no term used before it is introduced or declared known

Check 1 needs enforcement in the prompt as well as in validation — models default hard to explaining from scratch.

**Span and budget are independent.** Narrow span + long budget = go deep. Narrow span + short budget = essentials only.

---

## 3. Sources and authority — LOCKED

A real request rarely has one source of truth, and the sources will disagree. *"Notes for B.Tech 5th-semester Operating Systems"* may involve a university syllabus, the professor's slides, a textbook, previous-year papers, and the student's own notes. For this product's core users that is the normal case, not an edge case.

### 3.1 Authority is claim-specific, not a single rank

A source is not simply "more authoritative." It is authoritative **for a particular kind of claim**. A syllabus settles what is in scope and says nothing about how a theorem is derived; a textbook is the reverse; the professor's notes settle which notation this class uses.

So every Source carries four independent authority scores plus recency:

```
source.authority = {
    scope:        is this topic in or out?
    factual:      is this statement correct?
    terminology:  what is this called, in what notation?
    assessment:   what actually gets tested, and how heavily?
}
source.recency  = published_at
```

Typical profiles:

| Source | scope | factual | terminology | assessment |
|---|---|---|---|---|
| Official syllabus / exam blueprint | **high** | low | medium | low |
| Past papers, question banks | medium | medium | medium | **high** |
| Professor slides, course handouts | medium | medium | **high** | medium |
| Textbook, canonical reference | low | **high** | medium | low |
| Interview reports, community threads | low | low | low | medium |
| User's own notes | low | low | medium | low |
| Model's own knowledge | low | medium | low | low |

**A conflict is resolved by asking *which kind of claim is this?*, then consulting the source that scores highest on that dimension** — never by ranking documents wholesale. Ties break on recency.

The model's own knowledge is the fallback when no source covers a claim, and content sourced that way must be marked as such.

### 3.2 Scope authority tiers

Not every topic has documented scope. Three tiers, differing in confidence, not in whether the product applies:

- **Documented** — syllabus, exam blueprint, certification outline. Scope is given and verifiable.
- **Consensus** — SDE interviews, standard ML interviews. Scope is known by a community, recoverable from job posts and interview reports.
- **Asserted** — "roadmap to Senior SDE." The model's own judgment. Weakest tier, must be labelled, and the first thing a user should review.

**Intake derives from this.** Documented scope → do not ask for a syllabus. No documented scope → the syllabus is required and must be requested. Questions come from gaps, never from a fixed form.

### 3.3 Knowledge and Source layer

```
source chunks (retrievable)   ·  extracted terminology
syllabus → topic mappings     ·  canonical diagrams (vector, reusable)
verified content fragments    ·  prior approved Specs
```

**Accumulated from usage and uploads, not hand-curated per domain.** It grows because people use the product, not because someone is paid to build a graph. That is the whole difference from the idea rejected in §10.

---

## 4. Architecture — LOCKED (stages) · PROVISIONAL (schemas)

```
User situation
    ↓
Intent / context              adaptive intake · visual PREFERENCE chosen
    ↓
Retrieve sources + knowledge
    ↓
SPEC                          scope + outcomes
    ↓
SPEC VERIFICATION             "did we plan the right thing?"
    ↓
[ GATE 1 — user approves the plan ]
    ↓
SET PLAN                      allocation & dependencies across documents
    ↓
DOCUMENT PLAN                 sections, blocks, archetypes within one document
    ↓
TEMPLATE FEASIBILITY          does the preferred template hold this content?
    ↓                              fits → bind · overflows → surface trade-off
[ demo page → GATE 2 — user approves the look ]
    ↓
DOCUMENT MODEL                concrete, renderable, no geometry
    ↓
CONTENT VERIFICATION          "did we generate the right thing?"
    ↓
ENGINE VALIDATION             "is it structurally valid?"
    ↓
REPAIR / REGENERATE  ⟲
    ↓
RENDER
```

### 4.1 Template: preference early, binding late

Template and Spec constrain each other in both directions. A template limits how much fits on a page; the required content limits which templates are viable. That makes it a **feasibility problem, not an ordering problem.**

- The user picks a **visual preference** during intake, from a gallery of real rendered pages. Fast, and it captures density, formality and visual load in one choice.
- The Spec produces content requirements.
- **Feasibility check** after planning: does the preferred template hold this content within budget?
- Fits → bind. Overflows → **surface the trade-off**, never resolve it silently. This reuses the §8.3 cascade machinery.

Rev. 3 locked "template chosen before Spec." That was half right — the *preference* comes early, the *binding* cannot.

### 4.2 The objects

| Object | Answers | Persisted | Versioned | Editable |
|---|---|---|---|---|
| **Spec** | What should this material accomplish? | ✓ | ✓ immutable | ✓ |
| **Set Plan** | How is it allocated across documents, and what depends on what? | ✓ | ✓ | ✓ |
| **Document Plan** | How does one document divide into sections and blocks? | ✓ | ✓ | ✓ |
| **Template** | What visual language? | engine repo | ✓ | chosen |
| **Document Model** | The concrete renderable representation | ✓ | — | via repair |

Each passes the test: distinct responsibility, persisted, versioned, edited, consumed by another component. **Intent/context is not on this list** — it is fields on the Workstream with no independent lifecycle. Not every discovery earns a layer.

Rev. 3 had one "Document Plan" doing two jobs at different scopes. Splitting it into Set Plan and Document Plan is what gives set coordination a home — see §5.

### 4.3 What the Spec may contain

| Kind | Example | In the Spec? |
|---|---|---|
| **Outcome** | *"After this section the reader can explain self-attention and contrast it with recurrence."* | ✓ **per coverage unit**, not once per Spec |
| **Constraint** | `visual: required` · `150 questions, 12 categories` · `max 8 words` | ✓ machine-checkable |
| **Instruction** | *"Explain attention intuitively before introducing Q/K/V."* | ✓ generation guidance |
| **Content** | The actual paragraph the reader will read | ✗ never |

The Spec is not pure metadata. Stating outcomes **per coverage unit** is what makes content verification answerable: *does this section actually enable the stated capability?* A single set-level success criterion is too coarse to check against.

What the Spec must never carry is final reader-facing prose.

---

## 5. Set coordination — LOCKED

Coordination across many documents is one of the genuinely hard problems, and it needs an object. A Set is not a bag of PDFs.

### 5.1 The Set Plan

```
SET PLAN
├── purpose                  what this whole set is for
├── total budget             pages and reading hours across all documents
├── coverage allocation      which topics land in which document
├── dependency graph         document → concepts it requires
├── redundancy rules         what may repeat, what must not
├── ordering                 suggested reading order (not execution order)
└── completion criteria      when is this set done
```

### 5.2 Documents are not inherently sequential

A curriculum is a chain. An interview-prep set is not:

```
Workstream: Interview Prep
  PDF 1: 100 Questions
  PDF 2: System Design Cheatsheet
  PDF 3: Networking Revision
```

These are coordinated but independent — document 3 does not build on document 2. So dependency is **declared, not assumed by position**:

```
document.requires = [concept_x, concept_y]

entry_floor = span.assumed
            ∪ exits of the documents this one actually depends on
```

A curriculum's graph happens to be a chain; interview prep's is a set of independent nodes. **One mechanism, both shapes.**

### 5.3 Dependencies constrain content, not scheduling

Because the Set Plan declares every document's *exit* before anything is written, document B can generate **concurrently** with document A even while depending on it. The dependency graph decides what B may assume, not when B may run. A twelve-module set is twelve concurrent jobs.

---

## 6. The contracts — LOCKED

**1. The LLM never sees HTML.**
It emits content keyed to slot ids — `{ "callout-1": "..." }` — and nothing else. Hand a model markup to edit and it will rename a class, drop a wrapper, nudge a margin "to fit better," degrading the layout in ways you will not catch without diffing markup on every generation.

**2. A Template is a mold, not a foundation.**
Content is poured into it. It is not a starting point the model revises. The blast radius is exactly the content *by construction*, and regeneration is per-slot instead of per-page.

**3. No geometry in the Document Model — and a page number is geometry.**
The model carries constraints and relationships; the engine solves for position *and* pagination. Storing `x: 340` and storing `page: 3` are the same mistake. Rule of thumb: if a number would change when the text changes, it does not belong in the model.

**4. The engine reports; it does not repair.**
Overflow, missing visual, count mismatch, underfull page → violations returned. The agent rewrites the offending slot. The engine never edits content.

**5. Templates are archetypes, not documents.**
Block archetypes flow; page archetypes are composed and atomic. Five archetypes generate a forty-page set.

**6. Illustration is four systems plus a domain tier.**

| System | Examples | Mechanism |
|---|---|---|
| Symbols | lightbulb, warning, star | Lookup by name. ~80 covers most needs. |
| Concept illustrations | messy stack, missing piece, stairs up | Lookup by **concept** — `disorder`, `gradual-growth`, `bottleneck`. ~200 entries; concepts recur even when topics don't. |
| Connectors | arrows, braces, pointers | **Not assets.** Computed path + hand-drawn stroke renderer. Six kinds. |
| Frames | sticky note, torn strip, index card | A **decorator on a slot**: background + edge + attachment + rotation. |
| Domain figures | transformer architecture, animal cell | Per-domain vector art, held and *placed*, never improvised per run. |

The LLM emits a **concept tag** — `icon: "disorder"` — never a filename.

**7. You never generate what you don't ship.**
The Spec decides scope so generation only runs on what survives it. No intermediate "full theory" document converted into a cheat sheet.

**8. Every constraint the verifier checks is also stated in the prompt.**
Validation is the safety net, not the mechanism. A pipeline relying only on validation burns retries on failures it could have prevented.

---

## 7. The three verification layers — LOCKED

Three different failure classes. Three different mechanisms.

| Layer | Asks | Mechanism | Runs on |
|---|---|---|---|
| **Spec verification** | *Did we plan the right thing?* | LLM + sources. Coverage vs scope authority, weightage vs assessment authority, span coherence, budget realism. | Spec, before generation |
| **Content verification** | *Did we generate the right thing, per the plan?* | LLM + retrieval. Correctness, grounding, relevance, whether the diagram is the *right* diagram, whether outcomes are actually enabled. | Document Model, before render |
| **Engine validation** | *Is it structurally valid and renderable?* | Deterministic code. Overflow, counts, missing elements, orphan connectors, underfull pages, undefined terms. | Document Model, at render |

**Content verification confirms a document faithfully implements its plan. It cannot catch a plan that was wrong.** A Spec missing a major syllabus topic produces content that is correct, well-grounded, verified — and useless. Spec verification is only possible because §3 defines claim-specific authority.

**Engine validation stays deterministic** — it is the only layer testable with golden images and pixel diffs. Putting a model inside it would destroy that property.

Verification runs on the **Document Model, not the PDF**: you verify content, not a rendered artifact.

### 7.1 Severity, not advisory-only

Rev. 3 said semantic verification is advisory and never blocks. That does not survive contact with *"question 37 has a factually incorrect answer."*

| Severity | Meaning | Action |
|---|---|---|
| `INFO` | Observation worth surfacing | Show, do not act |
| `WARNING` | Possible weakness, no clear defect | Allow, annotate |
| `ERROR` | Defect against the Spec or a source | Attempt repair; block if repair fails |
| `CRITICAL` | Would mislead the reader | Block, require human decision |

Two guards keep this from becoming a deadlock machine:

- **`CRITICAL` is narrowly defined.** Contradiction of a high-authority source, a demonstrably wrong answer, code that does not compile. **Not** "the model felt uneasy." A loose definition produces a system that blocks on model anxiety.
- **`CRITICAL` is human-overridable.** A probabilistic critical is still probabilistic, and a false positive must never be an unfixable deadlock.

### 7.2 Verification scope is a policy, not "everything"

Content verification runs per document. Across a forty-document set, verification tokens approach generation tokens — it can double the cost of a set.

So **what gets verified is declared, not assumed.** Verify claim types that are expensive when wrong:

```
verify:      facts · answers · numbers · code · citations · required visuals
do not:      prose quality · tone · style
```

---

## 8. Entity model — LOCKED

```
PROJECT          topic workspace, persists over time
  ├── SOURCES        claim-specific authority (§3.1)
  ├── CONVERSATIONS  interfaces into project context
  └── WORKSTREAM     purpose + success criterion + situation
        │              (deadline, hours, level, role) + template preference
        └── SPEC         span, coverage, per-unit outcomes, depth,
              │            sequencing rule, visual density, obligations,
              │            instructions · immutable · versioned
              └── SET PLAN     allocation, dependency graph, redundancy rules
                    └── DOCUMENT
                          ├── requires[]        declared dependencies
                          ├── DOCUMENT PLAN     sections, blocks, archetypes
                          └── JOB               one execution

TEMPLATE         engine-repo asset; preferred at intake, bound after feasibility
```

**Changes from the Product Bible:** Content Plan → Spec (a scope decision, not an outline). Module deleted — grouping is a field. Workstream carries the **success criterion**. Spec carries the **sequencing rule** and **per-unit outcomes**. The **Set** is the unit of delivery, and the **Set Plan** is what makes it more than a folder.

### 8.1 Visual density is a Spec decision, not a constant

| Domain | Visual need |
|---|---|
| Agentic AI, backend, law | Almost none. Text, code, occasional flow diagram |
| Class 8 algebra | Worked examples, a few figures |
| Human digestive system | Diagram-dense — the diagram *is* the content |

Most documents are mostly flowing text. `visual: required` is a *declaration*, meaning most concepts declare nothing. The system must never force diagrams.

### 8.2 Why success criterion is the driver

Two users. Same topic area. Same seven months.

| | Researcher | GATE DS/AI |
|---|---|---|
| Success means | Can implement, fine-tune, read papers | Marks on a specific paper, negative marking |
| Sequencing | `prerequisite` | `weightage` |
| Depth | Implementation-level; code must run | Enough to solve exam-pattern questions |
| Coverage | Deep on one path, ignores the rest | The *entire published syllabus* |
| Content types | Notebooks, projects, papers | Formulas, solved numericals, PYQs |
| Verified by | Did you build the thing | Can you score under time pressure |

Roughly 30–40% topic overlap; close to **zero** treatment overlap.

Sequencing rules: `prerequisite` · `weightage` · `frequency-asked` · `problem-first` · `syllabus-order` · `motivation-first` (show the pain before the cure — *direct API calls → the mess → why LangChain exists*).

### 8.3 Feedback cascade

Approval feedback, and template infeasibility, can both invalidate decisions upstream. Classify by what is actually invalidated:

| Trigger | Invalidates | Cost |
|---|---|---|
| "Make it look different" | Template only | Re-render the demo |
| "More diagrams, longer" | Visual density + depth → **Spec** | New Spec version → re-plan → new demo |
| "You missed distributed caching" | Coverage → **Spec** | New Spec version → full re-plan |
| Template feasibility failure | Template **or** Spec — user chooses | Surface both options |

**Always surface the consequence as a trade-off:**

> *Going diagram-heavy at 30 pages means dropping 3 topics. Or keep all topics and go to 45 pages — about 4 more hours of reading. Which?*

Only computable because the budget was declared at intake.

---

## 9. Build order — LOCKED

> Prove the whole chain thin before making any part of it thick. The hand-work is authoring the template, not drawing a throwaway page.

**Phase 1 — The thin vertical slice.**
One topic → Spec → Set Plan → Document Plan → Template → Document Model → render → verify. Every stage present, every stage minimal.

It starts by **authoring one flowing template by hand** — `templates/study-notes/template.html`, with real slots and real capacity limits. That hand-authoring is where the Template schema is discovered, and its first render against a fixture is the target-drawing exercise. There is no separate throwaway page: the template is the hand-built artifact, and you keep it.

The goal of the phase is to find out whether the relationships between stages are right before hardening any of them.

**Phase 2 — Stress the Document Model.**
Long-form flowing notes, a Q&A document, one composed visual page. **Can one representation express all three elegantly?** Compare the block-flow model against the semantic-objects alternative (§11).

The composed page is where hand-work earns its keep: author it by hand first, and keep an **eyeball list** — everything you positioned by eye. Every item on that list is a solver feature. Until this phase resolves, the schema stays provisional.

**Phase 3 — Verification.**
All three layers, with severity. Spec verification first — it catches the most expensive class of error.

**Phase 4 — The asset library.** *(parallel, design not code)*
~80 symbols, ~200 concept illustrations, frame furniture, stroke renderer. A designer-month. Placeholders until then.

**Phase 5 — Sets and persistence.**
Set Plan, dependency graph, multi-document coordination, Project state, resume-later, parallel generation.

**Phase 6 — Scope reuse across users.**
Specs persist, get reused and corrected. *"Of 342 students who used this scope, the most common addition was deadlock recovery."* Built from usage, not curation.

**Note on existing code:** the dashboard frontend is Phase 5 UI, ahead of the engine. Keep it; stop growing it.

---

## 10. Dead ideas — DEAD

- ~~**Hand-curated per-domain Concept Node graphs**~~ — Curating concept graphs for law, medicine, signals and competitive exams re-derives what is latent in the models, goes stale, and generalizes only by paying curation cost per domain. **Not the same as having no knowledge layer** — see §3.3. Dead is the manually-built universal graph, not persisted sources, terminology, canonical diagrams, or reusable Specs.
- ~~**"Completeness" as the promise**~~ — Replaced by triage inside a declared span under a declared budget.
- ~~**Only works where a formal syllabus exists**~~ — An SDE interview has no syllabus but a real, socially-held scope. See §3.2.
- ~~**Entry floor as a single point**~~ — Documents are bounded at both ends. 20→60 and 0→15 are ordinary requests.
- ~~**`entry_floor` = union of all prior documents' exits**~~ — Assumes every set is a sequential curriculum. Interview prep is not. Dependencies are declared, not inferred from position. See §5.2.
- ~~**A single `authority_tier` per source**~~ — Authority is claim-specific. A textbook outranks a syllabus on facts and loses to it on scope. See §3.1.
- ~~**Semantic verification is advisory only**~~ — A factually wrong answer must be able to stop a document. Severity levels, with `CRITICAL` narrowly defined and human-overridable. See §7.1.
- ~~**Template bound before the Spec**~~ — The *preference* comes early; the *binding* requires a feasibility check against planned content. See §4.1.
- ~~**Page as the container in the data model**~~ — A page is where the ribbon gets cut, not a unit of meaning. Blocks flow; the engine paginates.
- ~~**"Models are bad at diagrams" as a core problem**~~ — A capability gap that has largely closed. What remains is a *declaration* problem.
- ~~**Markdown → PDF as the output path**~~ — Linear text cannot express spatial layout.
- ~~**Template is a function from Spec → Document Model**~~ — It is `f(Spec, Template)`, and the division happens in the Set Plan and Document Plan.
- ~~**Mechanical validation is sufficient**~~ — It checks structure, never meaning. See §7.
- ~~**LMS framing — Learning Journey, Goal, Curriculum, mastery tracking**~~ — Deadlines are an input to scope, not progress tracking.

---

## 11. Provisional and open

### PROVISIONAL — current best design, not frozen

- **The Document Model schema.** Currently `Document → Section → Block`. Whether one representation handles both spatial compositions (sketchnote pages) and flowing compositions (long-form notes) is **unproven**. The alternative worth testing against it: `Document → semantic objects + relationships + presentation constraints`, where blocks are one possible projection. Phase 2 decides. **Do not adopt the more abstract model pre-emptively** — replacing an untested concrete model with an untested abstract one buys indirection, not evidence.
- **Templates as the primary moat.** Visual craft is valuable and hard to copy, but most target content is text-heavy, which weakens the claim. A hypothesis, not a locked decision.
- **Template / Spec ordering.** §4.1 is the current answer — preference early, binding after feasibility. The loop may need more iterations in practice.
- **The Python engine.** Chosen because the agent is Python and Playwright has Python bindings. Reversible early. Note that the multi-client argument does not by itself favour another language: a Python library behind a thin HTTP wrapper serves the web app, a template editor and third parties alike. The boundary that matters is the API, not the language.
- **No agent framework.** The trigger is branching complexity, not scale — see `System-Design.md` §5.5 for the tripwire.

### OPEN

1. **Can one Document Model express both composed visual pages and long-form flowing notes?** The single most important unanswered question.
2. **Slot-capacity discipline.** Can models reliably write to a six-word cap?
3. **Archetype taxonomy.** How many block and page archetypes cover most needs?
4. **Minimum viable asset library.** The 80/200 figures are estimates, not measurements.
5. **Annotation.** Does output need margins and practice space, and should it export into a notes app?
6. **Sharing Specs across users.** Does it break anything about how a Project is imagined?
7. **Where retrieval enters the prompt chain** — Spec only, or fill as well? Significant cost implications.
8. **Verification cost ceiling.** §7.2 sets a policy; the right budget per set is unknown until measured.
9. **Which artifact types ship first.** Crash course, complete notes, interview prep, revision sheet, roadmap.

---

*Source of truth until a later approved revision.*

*Next action: Phase 1 — author one flowing template by hand, then run the thin vertical slice through it.*
