# Notes Engine System Design

**Rev. 3 — 1 Sep 2026 — companion to `Foundation.md` (Rev. 4)**

> ## ⚠ PARTLY SUPERSEDED — 4 Sep 2026
>
> Read **`Product-Semantics.md` (Rev. 1)** first.
>
> **Dead here.** The nine agent operations — named against a vocabulary of eight block
> types and one figure archetype, and unlikely to survive Q2. The Document Model /
> Template split as described. The engine's internal pipeline, which assumes CSS
> figures.
>
> **Still alive.** The three verification layers and their severity grading. The job
> lifecycle. The reasons for rendering inside a real browser. The stack decisions.
>
> Kept as evidence, **not as design**. Rewriting waits on Q2 and Q4.

Dataflow, storage, and the contracts between backend, agent, and engine.

Web version: https://claude.ai/code/artifact/a4fe9a82-7402-43be-80bf-f41fdae09f78

---

## 1. Stack decisions

| Piece | Choice | Status |
|---|---|---|
| Frontend | Next.js 16 + React 19 + Tailwind 4 | Locked — already built |
| Backend API | Python · FastAPI | Locked |
| Queue | Postgres job table + worker loop | Locked |
| Database | Postgres + JSONB | Locked |
| Vector store | `pgvector`, same Postgres | Locked |
| Object store | Local FS in dev, S3-compatible in prod | Locked |
| Engine | Python · Jinja2 + Playwright | **Provisional** |
| Renderer | Headless Chromium | Locked — JS measurement is required |

### The engine is a Python package, not an npm library — PROVISIONAL

A JS engine npm-linked into a Python agent creates a language boundary for no benefit: every render becomes a subprocess or service hop, and types are duplicated on both sides. Templates are HTML/CSS either way, and Playwright has first-class Python bindings.

The worker imports the engine directly — `engine.render(doc, template)` — with no serialization in the hot path. It remains a separate repo with a hard API boundary and no LLM inside; only the install mechanism changes (`pip install -e ../document-engine`).

**Marked provisional** because the decision is cheap to reverse early. Note that the multi-client argument does not by itself favour another language: a Python library behind a thin HTTP wrapper on the backend serves the web app, a future template editor and third parties alike. **The boundary that matters is the API, not the language** — and that boundary is already hard.

---

## 2. Dataflow

```
FRONTEND   (1) topic in   (3) intake    (7) GATE 1       (11) GATE 2
                │  ▲         │  ▲       approve plan     approve look
BACKEND    (2) match      ───┘  │       (8) fan out      (15) store
             project             │            │                ▲
AGENT      (4) retrieve → (5) SPEC → (6) SPEC VERIFY
                                    (9) SET PLAN
                                    (10) DOC PLAN + FEASIBILITY + demo
                                    (12) fill
                                    (13) content verify (severity)
ENGINE                              (14) validate ⟲ repair → render

        steps 10–15 run once per document, in parallel across the set
```

**Two gates, both cheap, both before the expensive part.** Gate 1 approves the scope decision. Gate 2 approves a single generated demo page.

### Walkthrough

1. **Topic in.** Free text. No form.
2. **Match project.** `pgvector` similarity against existing Projects. Above threshold → attach; below → new; ambiguous → ask.
3. **Intake — adaptive.** Questions generated from *gaps*, never a fixed form:
   - Does this topic have documented scope? (`RAG` yes · `OS, 5th sem, my university` no) If no, the syllabus is required.
   - Purpose, success criterion, deadline, hours available, level
   - **Visual preference**, chosen from a gallery of real rendered pages — a preference, not yet a binding
4. **Retrieve.** Chunk and embed sources; pull what is relevant. Score claim-specific authority (Foundation §3.1).
5. **Spec.** Span, coverage, per-unit outcomes, depth, sequencing rule, visual density, obligations, instructions.
6. **Spec verification.** Coverage vs scope authority, weightage vs assessment authority, span coherence, budget realism. Findings with severity.
7. **GATE 1.** User confirms the assumed-known list and reviews scope, findings shown inline. Edits create a new Spec version.
8. **Fan out.** Create the Set, one Document row per planned document, one Job each.
9. **Set Plan.** Coverage allocation across documents, dependency graph, redundancy rules, ordering, completion criteria.
10. **Document Plan + feasibility + demo.** Sections, blocks, archetypes. Then: does the preferred template hold this content within budget? Fits → bind. Overflows → surface the trade-off. Then generate **one** representative page.
11. **GATE 2.** Feedback is classified (§5.4) and cascades only as far as it must.
12. **Fill.** Per section: slot JSON under declared caps.
13. **Content verification.** On the Document Model, with severity (§5.1). Scoped by policy, not run on everything.
14. **Validate → repair → render.** Deterministic; failures route back to fill for that slot only.
15. **Store.** Artifact to object storage; Document marked complete.

> **Documents in a set generate in parallel, not in sequence.**

Because the Set Plan declares every document's *exit* before anything is written, document B generates concurrently with document A even while depending on it. **The dependency graph constrains what B may assume, not when B may run.**

---

## 3. Data model

```
user          id, email, created_at

project       id, user_id, title, topic, topic_embedding,
              scope_authority, status, created_at, updated_at
              scope_authority ∈ documented | consensus | asserted

source        id, project_id, kind, filename, storage_ref,
              extracted_text, published_at, created_at,
              authority JSONB { scope, factual,
                                terminology, assessment }   -- 0..1 each
              kind ∈ syllabus | past_paper | slides | textbook
                   | user_notes | reference

source_chunk  id, source_id, ord, text, embedding vector(1536)

workstream    id, project_id, purpose, success_criterion,
              situation JSONB { deadline, hours_available,
                                level, role },
              template_preference, status, created_at

spec          id, workstream_id, version, parent_version_id,
              body JSONB, verification JSONB,
              approved_at, created_at
              -- immutable; an edit writes a new row

set_plan      id, spec_id, spec_version, version,
              body JSONB { purpose, total_budget,
                           coverage_allocation, dependency_graph,
                           redundancy_rules, ordering,
                           completion_criteria },
              approved_at, created_at
              -- immutable and versioned

document      id, set_plan_id, index, title,
              requires JSONB,          -- declared concept dependencies
              spec_slice JSONB, entry_floor JSONB, exit JSONB,
              template_id, template_version,   -- bound after feasibility
              doc_plan JSONB,          -- sections, blocks, archetypes
              doc_model JSONB,
              verification JSONB,      -- findings with severity
              artifact_ref, is_demo, status

job           id, target_id, target_kind, type, state,
              attempts, last_error, started_at, finished_at
              type  ∈ retrieve | spec | spec_verify | set_plan
                    | doc_plan | feasibility | demo | fill
                    | content_verify | render
              state ∈ queued | running | needs_input | blocked
                      | done | failed
```

### Design notes

- **`source.authority` is a JSONB of four scores, not one integer.** Rev. 2 stored a single tier, which contradicted the Foundation's own rule that conflicts resolve by claim type. A textbook outranks a syllabus on `factual` and loses to it on `scope`.
- **Spec and Set Plan are immutable and versioned.** An edit writes a new row pointing at its parent — undo, diffing, and a record of exactly what each document was generated against, with no operation log.
- **`document.requires`** holds declared concept dependencies. `entry_floor` is derived from the exits of the documents this one actually depends on — **not from every document with a lower index.**
- **`document.template_id` is set after the feasibility check**, not at intake. `workstream.template_preference` records what the user picked; the document records what was actually bound.
- **`doc_plan` lives on the document**, `set_plan` is its own table. Rev. 2 had one "Document Plan" doing both jobs at different scopes.
- **`is_demo`** — the Gate 2 page is a real Document produced by the real pipeline, flagged so it is never mistaken for deliverable output.
- **`job.state` gains `blocked`** — a `CRITICAL` verification finding stops a document and requires a human decision.
- **Document Model in JSONB** — it changes shape constantly during development. Schema is provisional (Foundation §11).

---

## 4. Backend

### API surface

```
POST   /projects                     { text }   → project (+match info)
GET    /projects/:id
POST   /projects/:id/sources         multipart  → source (+authority scores)
PATCH  /sources/:id                  { authority }

POST   /projects/:id/workstreams     { purpose, situation, template_preference }
GET    /workstreams/:id/intake                  → next questions (adaptive)

POST   /workstreams/:id/spec                    → job
GET    /specs/:id                               → spec + findings
PATCH  /specs/:id                    { edits }  → new spec version
POST   /specs/:id/approve                       → set-plan job      [GATE 1]

GET    /set-plans/:id
PATCH  /set-plans/:id                { edits }  → new version
POST   /set-plans/:id/demo                      → demo document job
POST   /set-plans/:id/approve                   → N document jobs   [GATE 2]
POST   /set-plans/:id/feedback       { text }   → classified change

GET    /documents/:id                           → status + findings
GET    /documents/:id/artifact                  → PDF
POST   /documents/:id/regenerate     { scope }  → job
POST   /documents/:id/override       { finding_id, reason }
                                                → clears a CRITICAL block

GET    /templates                               → gallery metadata
GET    /jobs/:id                                → state, progress
```

### Job lifecycle

```
queued ──→ running ──→ done
             │  │  │
             │  │  └─→ blocked        (CRITICAL finding — human decision)
             │  └────→ needs_input    (gates, floor confirmation, ambiguity)
             └───────→ failed         (retry ceiling hit)
```

A worker loop claims jobs with `SELECT … FOR UPDATE SKIP LOCKED`. Concurrency is a worker-count setting.

### What the backend does not do

- Never calls an LLM directly. All model calls live in the agent package.
- Never touches HTML, geometry, or PDFs. It stores an artifact reference.
- Holds no pedagogy logic. Scope belongs to the agent; layout to the engine.

---

## 5. Agent

Nine operations. Typed functions called by the worker — **separate responsibilities, not separate agents.**

```
intake_questions(workstream, sources)      → Question[]   adaptive, from gaps

retrieve(topic, sources)                   → Chunk[] with claim-specific
                                             authority scores

plan_spec(situation, chunks, memory)       → Spec

verify_spec(spec, chunks)                  → Finding[]    "right plan?"

plan_set(spec, budget)                     → SetPlan: allocation,
                                             dependency graph, redundancy rules

plan_document(spec_slice, template,        → Section[] with archetypes
              entry_floor)                   + page allocation

check_feasibility(doc_plan, template,      → Fits | Overflow(options)
                  budget)

fill(section, slots, caps, context)        → { slot_id: content }

verify_content(doc_model, spec, chunks,    → Finding[]    "right content?"
               policy)

repair(violations|findings, slots, caps)   → { slot_id: content }
                                             failing slots only
```

### 5.1 The three verification layers, with severity

| Layer | Asks | Mechanism | Blocking |
|---|---|---|---|
| `verify_spec` | Did we plan the right thing? | LLM + scope/assessment authority | By severity |
| `verify_content` | Did we generate the right thing? | LLM + retrieval, on Document Model | By severity |
| `engine.validate` | Is it structurally valid? | Deterministic code | Always — repair loop |

```
INFO      → show, no action
WARNING   → allow, annotate
ERROR     → attempt repair; block if repair fails
CRITICAL  → block; requires human decision
```

Two guards stop this becoming a deadlock machine:

- **`CRITICAL` is narrowly defined** — contradiction of a high-authority source, a demonstrably wrong answer, code that does not compile. Not "the model felt uneasy."
- **`CRITICAL` is human-overridable** via `POST /documents/:id/override`. A probabilistic critical is still probabilistic; a false positive must never be unfixable.

### 5.2 Verification scope is a policy

Content verification runs per document. Across forty documents, verification tokens approach generation tokens — potentially doubling the cost of a set. So verification targets claim types that are expensive when wrong:

```
verify:      facts · answers · numbers · code · citations · required visuals
skip:        prose quality · tone · style
```

The policy is passed into `verify_content` and recorded on the run.

### 5.3 The repair loop

```python
for attempt in range(MAX_ATTEMPTS):          # 3
    violations = engine.validate(doc, template)
    if not violations:
        break
    patch = agent.repair(violations, slots, caps)
    doc = apply(doc, patch)                  # failing slots only
else:
    mark failed, keep partial output for inspection
```

Repair receives only the failing slots and their constraints, never the whole document. Small, cheap, and it stops the model "improving" text that already passed.

### 5.4 Feedback classification

```
classify(feedback) → presentation | density | scope

presentation  → new template_id            → re-render demo
density       → spec.visual_density, depth → new Spec version → re-plan → new demo
scope         → spec.coverage              → new Spec version → full re-plan
```

Template infeasibility enters the same path, with the user choosing whether the template or the scope gives way.

**Always surface the consequence as a trade-off rather than absorbing it silently:**

> *Going diagram-heavy at 30 pages means dropping 3 topics. Or keep all topics and go to 45 pages — about 4 more hours of reading. Which?*

Computable only because the budget was declared at intake.

### 5.5 On agent frameworks

**Scale is not the trigger. Branching is.** At scale the pain is cost per document, provider rate limits, bursty load, job durability, caching and observability. A framework addresses none of those.

| Real need | Justifies a framework? |
|---|---|
| A 40-document set dies at document 30 and must resume | **No.** Per-document job rows do this more simply than a graph checkpointer. |
| Human-in-the-loop at both gates, plus `blocked` | **No.** Job states and endpoints. |
| Sections filled in parallel, then joined | **No.** `asyncio.gather`. |
| Tracing complex runs | **No.** Available without the orchestrator. |
| **Different document types need different pipeline stages** | **Yes.** The real one. |

A maths-heavy document may need symbolic verification, a law document a citation check, a code-heavy one an execution check. Once the next step depends on the *content* of the previous step rather than a fixed order, hand-rolled routing gets ugly.

**Tripwire:** more than ~3 distinct pipeline paths, or a stage whose successor is chosen by inspecting the previous stage's output.

**Not a one-way door** — nine pure typed functions become nine nodes verbatim.

---

## 6. Engine

### Public API

```
engine.validate(doc_model, template_id) → Violation[]
engine.render(doc_model, template_id)   → bytes (PDF)
engine.preview(doc_model, template_id)  → bytes (PNG, one page)
engine.feasible(doc_plan, template_id)  → Fits | Overflow(measured, limit)
engine.templates()                      → TemplateMeta[]
engine.schema()                         → JSON Schema for doc_model

Violation = { block_id, slot_id, kind, detail, measured, limit }
kind ∈ overflow | missing_required | undefined_term
     | count_mismatch | orphan_connector | underfull_page
```

`engine.feasible` is what backs the §5 feasibility check — the engine already measures, so template capacity is answerable without a full render.

### Internal pipeline

```
doc_model + template
      ↓  merge        Jinja2: slots → HTML, no LLM, pure
      ↓  layout       Chromium loads it; JS measures every element
      ↓  solve        constraints → positions for labels & connectors
      ↓  annotate     inject SVG: arrows, circles, highlights
      ↓  paginate     honor keep-together / keep-with-next / breaks
      ↓  validate     measured vs declared → violations
      ↓  print        page.pdf()
```

### Why measurement happens inside a real browser

Drawing a connector between two elements and detecting slot overflow both require `getBoundingClientRect` after layout. That is why the renderer is Chromium, and it means **validate and render share one browser pass** — measure, then either report violations or continue to print.

### Repo layout

```
document-engine/
    engine/
        schema.py        doc model + template schema, JSON Schema export
        merge.py         slots → HTML (Jinja2)
        measure.py       Playwright session, element metrics
        solve.py         constraints → geometry
        annotate.py      connectors, circles, highlights → SVG
        paginate.py      flow → pages
        validate.py      measured vs declared
        feasible.py      capacity check without full render
        render.py        orchestrates → PDF
    templates/
        study-notes/     flowing: heading, body, code, callout, Q&A
        concept-map/     composed, atomic, full-page
    assets/
        symbols/ concepts/ frames/ strokes/
    gallery/             every archetype, dummy content, live reload
    tests/
        fixtures/        hand-written doc models — tests, not content
        golden/          reference PNGs, pixel-diffed
```

No network calls, no API keys, no model imports anywhere under `engine/`. Enforce it in CI with an import check — that constraint is what makes golden-image testing possible.

**The Document Model schema is provisional** (Foundation §11). Do not harden the engine's internals around it until it has survived three genuinely different page types.

---

## 7. Deliberately deferred

| Deferred | Until |
|---|---|
| Auth, accounts, billing | There is something worth logging into. |
| Redis / Celery | The Postgres job table measurably bottlenecks. |
| Separate vector DB | `pgvector` measurably bottlenecks. |
| Agent framework | Branching complexity — see §5.5. |
| Composed visual pages | Flowing documents work end to end. |
| Full asset library | The first template needs more than placeholders. |
| Spec reuse across users | Single-user generation is proven. |
| Streaming progress UI | Polling the job endpoint stops being enough. |

### Open questions this design does not settle

1. **Section-level or document-level fill?** Section-level keeps calls small and parallel but risks tonal drift.
2. **Retry ceiling.** Three is a guess.
3. **Where retrieval enters.** Spec only, or fill as well? Significant cost implications.
4. **Project-match threshold.** The embedding cutoff needs real data.
5. **Demo page selection.** Which page best represents a 40-page document — the first, the densest, or a synthesised composite?
6. **Verification budget.** §5.2 sets a policy; the right spend per set is unknown until measured.
7. **Who scores source authority?** Model-assigned at upload, user-adjustable, or inferred from the source kind alone.

---

## Appendix — load profile

> This is not a high-QPS system. It is a **bursty, expensive-per-request, long-running-job** system.

Single-university figures:

- 5,000 students, ~20% weekly active → ~1,000 active
- ~2 sets/month each, ~5 documents per set → ~10,000 documents/month → **~350/day**
- ~0.004 requests/second. Sharding and read replicas are irrelevant.
- Exam season is a **10–50× burst**, and each job runs for minutes, not milliseconds.
- Per document: ~15k output tokens plus input — 50–80k total, **plus verification**, which can approach the same again if unscoped. **Cost per document is the metric**, not QPS.
- Rendering: 2–5s of Chromium per document. Trivial at 350/day; needs a browser pool at burst.

The real problems are **queue backpressure during bursts, cost control, and job durability** — not throughput scaling.

---

*Architecture and contracts precede implementation.*

*Next: Phase 1 — author one flowing template by hand, then run the thin vertical slice through it.*
