# System Design — Rev. 4

**5 Sep 2026 · downstream of `Architecture.md` (Rev. 2) and `Product-Semantics.md` (Rev. 3)**

Architecture Rev. 2 §15 refuses storage, schema, database, framework, prompt design, agent topology, queueing, concurrency and deployment — deliberately. This document picks up exactly that list and nothing above it.

> **Rev. 4.** Rev. 3 said an artifact both *is* a commitment and is pointed at by one. It cannot be both: **a commitment is an event, an artifact version is an object** (§5). Identity now rests on the produced bytes rather than a claimed function of two hashes. Retention duration is demoted from invariant to policy. Appendix D8 — *a user references a March document in September* — adds three invariants, one of which is a new product obligation: **supersession and retraction are not the same event.**
>
> **Rev. 3.** Appendix D7 asked whether the *delivered artifact* can be reconstructed six months later on an evolved system. It cannot, and should not be — retention replaces reproduction. Artifact versions became first-class (§5) and `derivation_environment` split in two (§4). One consequence runs upstream: Architecture §12 files bulk output as *"regenerable, lowest historical value,"* which is right for draft prose and **wrong for delivered bytes**.
>
> **Rev. 2** changed how this document makes claims, not what it believes. Rev. 1 labelled `FastAPI` and `SELECT … FOR UPDATE SKIP LOCKED` **LOCKED** while simultaneously saying schema was premature. Every claim is now sorted into three levels, and eight invariants arrived from Appendix D1–D6.

---

## 0. How to read this

### Three levels — the reading key

```
INVARIANT       must survive any implementation change.
                Forced by a locked claim upstream, or by a mechanism
                with no alternative.

CHOICE          the current preferred implementation. Real alternatives
                exist; this one is picked and reversible.

IMPLEMENTATION  free to change without review. Recorded for concreteness,
                not as commitment.
```

The failure this prevents: mistaking *"we found a sensible implementation"* for *"the architecture forces this implementation."* Architecture states the **properties required**; this document **chooses technology**. `durable job claiming with concurrent workers` is an invariant. `SKIP LOCKED` is implementation.

Statuses on individual claims remain **LOCKED / WORKING MODEL / OPEN** as in the sibling documents, and apply *within* a level.

**What this document does not contain.** No build sequencing, no phase plan, no code, no migrations.

---

## 1. A job is not a decision — INVARIANT

> The `job` record is an **execution unit**. The `decision` record is a **judgment**. Architecture §2 gives them different admission rules, and nothing guarantees they have the same shape.

One direction is forced:

> **Jointly resolved decisions must share an execution unit.** Neither is finalised without the other's value, so both must be produced inside one resolution — and a resolution is a runtime boundary.

**The converse is not forced.** Rev. 1 said sequential and parallel decisions map to separate jobs as if that were derived. It isn't. A job boundary is chosen for runtime reasons — retry granularity, cancellation, latency, atomicity, cost, observability, cache-prefix reuse. Two decisions that share no constraint may still share a unit because one model call with a shared cached prefix is cheaper than two.

```
INVARIANT       joint decisions share an execution unit
CHOICE          everything else — batch or separate per runtime need
```

**Why the invariant is load-bearing.** Architecture §7 requires invalidation keyed to decisions, never to units. Record only jobs and correcting the representation dirties the sectioning unconditionally, every correction invalidates its whole unit, and the cost model that justifies the architecture is wrong. This is also the exact defect in the previous system design: its `spec` blob merged span, coverage, outcomes, depth, sequencing and density into one versioned row, so correcting the sequencing re-versioned the coverage.

---

## 2. Four structures, four record kinds — INVARIANT

```
ARCHITECTURE §2                    THIS DOCUMENT

decision taxonomy      ──→   decision records
execution topology     ──→   job records
lifecycle              ──→   commitment records + two state axes
invalidation           ──→   dependency records
```

### Two kinds of dependency, and only one of them can be recorded late

```
DECLARED    structural, knowable from the pipeline definition
            representation → draft

RECORDED    dynamic, knowable ONLY to the resolution that produced both,
            at the moment it produced them
            "this representation choice actually drove that sectioning"
```

A declared edge can be reconstructed from the pipeline at any time. A **recorded** edge cannot — it exists nowhere but in the resolution that observed it. That is why decision records are not merely provenance in this system: they carry dependency structure that has no other source.

Rev. 1 collapsed these into one edge table and said all edges are "written at resolution time." That would make the edge store a dumping ground for facts already implied by the pipeline. Keep them distinct; only recorded edges must be persisted eagerly.

---

## 3. Stack

### Required properties — INVARIANT

| Property | Why |
|---|---|
| durable job claiming with concurrent workers | jobs run for minutes; crashes must not lose or duplicate work |
| a store that holds unschematised decision output | payloads change shape constantly (§4) |
| **a rendering engine with post-layout geometry** | see below |
| append-only testimony | Architecture §12 — testimony is never rewritten |
| content-addressed derivation results | §11 invariant 2 |

### Current choices — CHOICE

| Piece | Choice | Note |
|---|---|---|
| Backend API | Python · FastAPI | |
| Worker | in-process loop over a job table | §10 justifies the absence of a broker |
| Store | Postgres + JSONB | |
| Object store | local FS in dev, S3-compatible in prod | artifacts only |
| Engine | Playwright · Chromium · Jinja2 | one satisfier of the geometry invariant |
| Retrieval | `pgvector`, same Postgres | **conditional** — see below |
| Model | `claude-opus-5`, adaptive thinking, per-decision `effort` | §6 |
| Frontend | Next.js | **deferred** — first real job is the plan gate |

`SELECT … FOR UPDATE SKIP LOCKED` is **implementation**.

### The geometry requirement — INVARIANT; Chromium is the CHOICE

Two engine jobs are impossible without knowing where content landed **after** layout: drawing a connector between two elements, and detecting slot overflow. Both need post-layout measurement of arbitrary elements.

Semantics §8 and Architecture §13 license diagrams, flows, sequences and swimlanes — every one needs geometry. So the requirement is real.

**What it eliminates:** WeasyPrint and the whole class of non-browser HTML→PDF converters, none of which expose post-layout geometry to the caller. **What it does not eliminate:** WebKit or Gecko. Rev. 1 said "Chromium is forced"; the requirement is forced, Chromium is one satisfier.

**Corollary:** `validate` and `render` share one measurement pass.

### Retrieval is conditional — INVARIANT

It serves **source ingestion**, which Architecture §3 marks *conditional on the subject* — present for a statute or syllabus, absent for backend development, which has no authoritative source. Retrieval is a branch, not a spine. A project with no sources never touches it.

---

## 4. Conceptual records — WORKING MODEL

**These are the records the system requires, not a table list.** They are drawn relationally for concreteness; nothing here forecloses event storage, append-only history, or separate read projections. Every `output` payload is deliberately unschematised until three genuinely different subjects have run through it — Semantics §14 and Architecture §15 both warn against hardening content schema before the vocabulary settles.

```
project            id, user_id, title, derivation_environment, created_at

utterance          id, project_id, ord, role, text, created_at
                   -- TESTIMONY. Never derived, never rewritten, permanent.

decision           id, project_id, kind, status, freshness,
                   member_id NULL, job_id,
                   inputs_hash,                  -- content address
                   model, prompt_version, effort, params,
                   output, rejected, cost, created_at

                   kind ∈ intake_strategy | interpret_situation
                        | select_frame* | ingest_sources*
                        | derive_structure | relevance | traversal
                        | consequence | scope | partition
                        | section | representation | draft
                        | render_config | layout_feasibility     * conditional

dependency         from_decision_id, to_decision_id, kind
                   kind ∈ declared | recorded     -- §2

commitment         id, project_id, kind, member_id NULL,
                   snapshot,                     -- SELF-DESCRIBING
                   decision_ids [],              -- what exactly is committed
                   artifact_version_id NULL,     -- kind = delivery only
                   decision_environment,         -- §11 invariant 8
                   approved_by, approved_at, superseded_by NULL
                   kind ∈ plan | demo | draft | layout | promotion | delivery
                   -- FIVE of these six are preceded by a gate (§7).
                   -- `delivery` is a commitment without a gate: nothing is
                   -- checked at delivery, but reliance begins there.

member             id, project_id, ord, title, job,
                   requires [],                  -- declared predecessors
                   declared_exit, actual_exit NULL,
                   entry_premise, artifact_id NULL, is_demo, state

set_status         id, project_id, completeness, blocking_members []
                   -- §11 invariant 6

job                id, project_id, unit, member_id NULL, state,
                   claimed_inputs_hash,          -- §11 invariants 4, 5
                   attempts, last_error, started_at, finished_at
                   state ∈ queued | running | needs_input
                         | blocked | done | failed | abandoned

verification       id, project_id, layer, target_id, covered,
                   entry_premise_hash, findings, created_at
                   layer ∈ structural | model_judgment
                         | source_grounded | human

artifact_version   id, member_id, ord,
                   bytes_ref, bytes_hash, format,   -- IDENTITY
                   doc_model_hash,                  -- explanation: what
                   render_environment,              -- explanation: how
                   decision_ids [],                 -- REFERENCES, never copies
                   pagination,                      -- block_id → page. Artifact-owned.
                   stamp,                           -- §11 invariant 11
                   superseded_by NULL,
                   supersession_kind NULL,          -- revision | retraction
                   created_at
                   -- delivery is recorded as a commitment, not a column
```

**Two environments, not one.** Rev. 2 had a single `derivation_environment`. D7 showed it conflates two things that fail differently:

```
DECISION ENVIRONMENT   model · prompt version · taxonomy version
                       asset version · source versions
                       → re-derive the same doc_model

RENDER ENVIRONMENT     template version · engine version
                       browser version · font versions
                       → re-render the same bytes
```

A font update repaginates. A browser point release changes line breaking. Neither touches a single decision, and Rev. 2 could not express either.

Composition-asset records — versioned concepts, typed relations, promotion proposals — are deferred; see §12.

### Lifecycle status and freshness are two axes — INVARIANT

Rev. 1 had one four-value enum. It is a 2×2, and the two axes get queried independently.

```
                current            stale
candidate       candidate          dirty
committed       committed          superseded
```

The conflation shows in Rev. 1's own wording: it defined `dirty` as *"derived from something that changed, **never committed**"* — the status axis leaking into a freshness name. Both axes are queried alone: *everything stale* is the re-derivation plan; *everything committed* is the historical record.

**`superseded` remains load-bearing.** When a learner switches from *"build things"* to *"interview prep,"* the committed databases member is not wrong and may be reusable unchanged. Collapsing it into `dirty` rebuilds work nobody asked to rebuild.

### Five notes

**`utterance` is a record, not a column.** Architecture §12: testimony is the only state derived from nothing, and every downstream decision interprets it. When an interpretation is wrong you need the original words.

**`decision.rejected` is not debug output.** *"Why isn't X in here?"* is among the likeliest user questions and cannot be answered if exploration discards what it considered.

**`decision.inputs_hash` is a content address, not a cache key.** Its correctness requirements are in §11.

**`commitment.snapshot` must stand alone** — concept names, exclusions and their reasons as its own content. `decision_ids` are links for re-derivation, never the substance. The user approved a *meaning*, not a set of row ids.

**`verification.entry_premise_hash` exists because coverage is not a sufficient key.** Members 5–6 are verified against a reader who completed member 4; if member 4 fails, their passes were earned against a false premise even though their own content never changed.

---

## 5. Identity — INVARIANT

Architecture §9's levels, as keys.

| Level | Meaning | Materialised |
|---|---|---|
| `asset_version` | which subject × frame snapshot | P3 |
| `concept_id` | a node in that asset | project-local until P3 |
| `instance_id` | this concept, at this resolution, in this project | now |
| `placement_id` | member + section + role | now |
| `block_id` | the realised passage | now |

Relevance and scope key to **instances**; section and representation to **placements**; draft to **blocks**; verification to **placements plus entry premise**; invalidation to **decision records**.

**Invalidation stays decision-keyed.** An external change — a source going v3→v4, an asset v7→v12 — is not a decision and does invalidate. But it invalidates *by invalidating the decision that consumed it*. The trigger is external; the edge is decision-keyed. Architecture §7 survived a direct attack on this and it is not reopened here.

Split and merge break `concept_id` continuity by construction, which is why §12 requires reconciliation rather than an id-stability promise that cannot be kept.

### What an artifact is — INVARIANT

Rev. 2 modelled an artifact as a file pointer hanging off a member. D7 shows that is too thin.

> A **member** is plan-side identity: what it must teach, its declared exit, its entry premise. It is stable across the life of the project.
>
> An **artifact version** is one delivered realisation of that member. A member has many over time.

```
member  :  artifact version   ::   plan  :  output
```

**A new version exists when either environment moves**, because either changes what the user would receive. But a version is not a *function* of those two hashes — rendering is not deterministic even at a fixed environment: PDF timestamps, document ids and font-subset naming all vary run to run.

```
IDENTIFIED BY   bytes_hash          what was actually produced
EXPLAINED BY    doc_model_hash      why it says this
                render_environment  why it looks like this
```

The same split as reconstruction versus replay (§11 invariant 10), applied to identity. Immutable, never mutated in place — only superseded.

### What the artifact owns, and what it must not

The artifact **references** the decision set that produced it. It does **not** copy target, scope, structure or representation into itself. Those are decisions with one home, and duplicating them would give the same judgment two homes that can silently diverge — the `spec`-blob mistake of the previous system design, one level down.

But two things are genuinely artifact-owned and exist nowhere else:

- **the bytes** — see invariant 9; they cannot be reliably reproduced
- **pagination** — which block landed on which page

Pagination is not derivable from any decision. It is a joint product of the doc model and the render environment, and **users reference it**: *"see page 34."* A re-render that moves it is a visible break even when every decision is unchanged.

### A commitment is an event; an artifact version is an object — INVARIANT

Rev. 3 said both *"a delivered artifact is a commitment"* and *"the layout commitment produces an artifact version."* Those are different claims and it cannot be both.

> **An artifact version is an object.** A **commitment is an event that records reliance on one.**

The decisive test is that neither implies the other. An artifact version can exist with no commitment — a candidate render that fails layout validation. A commitment can exist with no artifact version — the plan commitment. Two kinds of thing.

```
layout gate passes
      ↓
layout commitment        the doc model fits this template in this environment
      ↓
artifact_version         the object: bytes, pagination, both environments
      ↓
delivery commitment      reliance begins; artifact_version_id points at it
```

**`delivery` is a commitment without a gate.** Five of the six commitment kinds are preceded by a check (§7); delivery is not — nothing is verified at the moment a file leaves. But reliance unquestionably begins there, and Architecture §5 admits commitments by reliance, not by checking. So: still five gates, now six commitment kinds.

### What is self-describing, precisely

Rev. 3 said *"the bytes are self-describing."* That is wrong — bytes alone do not explain why a document exists or what it was built from. The self-describing unit is:

```
artifact record  +  bytes  +  pinned decision references  +  both environments
```

The bytes are what was relied upon. The record is what makes the reliance explicable.

---

## 6. Agent — WORKING MODEL

The decisions, as functions with a **side-effect-free interface**.

```python
interpret_situation(utterances, prior)          -> Situation
select_frame(subject, situation, candidates)    -> Frame | None      # conditional
ingest_sources(sources)                         -> SourceStructure   # conditional
derive_structure(subject, frame, frontier)      -> CandidateGraph
relevance(graph, situation, authority)          -> Relevance
traversal(graph, relevance, situation)          -> Order
consequence(graph, relevance, situation)        -> ConsequenceMap
scope_and_partition(...)      -> (Scope, Partition), Constraints      # JOINT
section_and_representation(...) -> (Sections, Representations), Constraints  # JOINT
draft(placement, representation, context)       -> Blocks
render_config(situation, template)              -> RenderConfig
```

**Not "pure."** Rev. 1's word was wrong. These functions may retrieve, call tools, and read sources internally — `ingest_sources` must read files, and external syllabus validation may need retrieval. What is guaranteed is the **interface**: values in, values out, no writes to system state. That is what makes decisions testable in isolation and replayable from a recorded `inputs_hash`; it is not a prohibition on internal tool use.

**The agent imports no store.**

### Joint functions return their constraint report

Without that second return value there is nothing to write as a **recorded** dependency, and §2's fourth structure has no source. Re-deriving one member re-enters the function with the sibling **pinned**.

### Model configuration per decision — CHOICE

| Decision | Shape | Effort |
|---|---|---|
| `interpret_situation`, `relevance`, `scope_and_partition` | `messages.parse` + Pydantic | `high` |
| `section_and_representation` | `messages.parse` | `xhigh` — the hardest judgment in the system |
| `draft` | `messages.stream`, large `max_tokens` | `high` |
| `traversal`, `consequence`, `render_config` | `messages.parse` | `medium` |

Adaptive thinking throughout. `prompt_version` is recorded on every decision, because without it a recorded `inputs_hash` cannot be replayed.

### When workflow orchestration is needed — WORKING MODEL

Rev. 1 said *"more than roughly three distinct pipeline paths."* That number is arbitrary and would age badly — two branches can need orchestration; ten trivial ones need none.

> **Adopt workflow orchestration when execution semantics stop being manageable with ordinary application control flow.**

Symptoms, not counts: a successor chosen by inspecting the previous step's output · compensation on partial failure · long human waits inside a run · resumption across process restarts mid-graph · retries whose correct scope depends on where the failure occurred.

Typed functions with side-effect-free interfaces become graph nodes verbatim, so this is a one-way door in neither direction.

---

## 7. Verification — four reliability classes, not one umbrella

Rev. 1 filed *"every table cell is filled"* and *"a simulated reader can follow this"* under one word. They are different guarantees, and for law the difference is the whole point.

| Class | Guarantee | Mechanism |
|---|---|---|
| **structural** | deterministic, certain | code. Connectivity, entry/target bounds, table completeness, marked-gap completeness |
| **model judgment** | probabilistic, unbounded error | a simulated reader at the stated entry — can they FOLLOW it, can they ACT on it |
| **source-grounded** | as reliable as the source | claim checked against a cited authority; the only class that can support a legal or medical claim |
| **human** | authoritative, expensive | review; the escalation target for `CRITICAL` |

**Naming these separately is the point.** A model-judgment pass is not evidence that a statutory claim is correct. Source-grounded verification is, to the extent the source is.

### Allocation — WORKING MODEL

Consequence severity (Architecture §5, Semantics §10) is the **primary** input: Semantics §4 requires the final claim be *trustworthy enough for its use*, and omission consequence is precisely about use. It is not the only input. Others expected to matter: source authority, novelty, reversibility, model confidence, user-visible importance. Primary, layered, measured.

Scope by claim type — verify facts, answers, numbers, code, citations, required visuals; skip prose quality, tone, style. Across a forty-document set, unscoped verification tokens approach generation tokens.

### Severity — WORKING MODEL

```
INFO      show, no action
WARNING   allow, annotate
ERROR     attempt repair; block if repair fails
CRITICAL  block; requires a human decision
```

**`CRITICAL` is narrowly defined** — contradiction of a high-authority source, a demonstrably wrong answer, code that does not compile. Not "the model felt uneasy." And **`CRITICAL` is human-overridable**, because a probabilistic critical is still probabilistic and a false positive must never be unfixable.

### Five gates — INVARIANT

Architecture §5 admits a gate where a result becomes **externally relied upon**.

| Gate | Mechanism | Blocking |
|---|---|---|
| plan | user approval | yes |
| demo | user approval | yes |
| draft | correctness verification, severity-budgeted | by severity |
| layout | `engine.validate`, deterministic | always — repair loop |
| promotion | situation-free adjudicator | P3 |

**Not gated:** traversal, consequence, derived relevance, render configuration.

**Which page the demo shows:** the page of **highest treatment variance**, not the first — opening pages are orientation and use the fewest departures from prose, so they test the least. Computable from the `representation` records.

### The repair loop — IMPLEMENTATION

Repair receives only the failing blocks and their constraints, never the whole document, which stops the model "improving" text that already passed. The retry ceiling is a guess; see §13.

---

## 8. Execution and correction

### Generation is parallel; commitment is ordered — INVARIANT

> **The dependency graph constrains what B may assume, not when B may run.**

But only against a **contract**, which Rev. 1 left implicit:

```
PLANNED dependency     B runs against A's DECLARED EXIT
                       → concurrent generation is safe

COMMITTED dependency   B commits only after A commits
                       → ordering is real, and it is at commit time
```

`member.declared_exit` is fixed at partition time; `member.actual_exit` is recorded when A completes. **They can diverge**, and §11 invariant 7 says what happens then. `entry_premise` derives from the exits of the members this one *actually* depends on — not from every member with a lower index.

### Correction routing — INVARIANT

A correction is not a pipeline stage. It is a routing operation over the decision graph.

```
correction submitted
        ↓
resolve intent  →  classify to one of seven meanings  →  target decision(s)
        ↓
walk dependency closure  →  mark reached decisions stale
        ↓
return a RE-DERIVATION PLAN with an ESTIMATED cost
        ↓
user confirms  →  enqueue jobs
```

**Stale persists; it does not schedule a model call.** Corrections accumulate, regeneration costs money, the user may change their mind again, and some rebuilds need approval first.

**Cost is estimated, not predicted.** Recorded `cost` on prior decisions gives a defensible estimate; model latency and token usage vary, so it carries a range, not a number. Rev. 1's "predictable" was too strong.

### The seven meanings, as routing targets

| | Meaning | Target |
|---|---|---|
| 1 | not in the graph at all | `derive_structure` — promotable |
| 2 | present, rated not in play | `relevance` |
| 3 | in play, cut for capacity | `scope` — possibly correct, badly communicated |
| 4 | covered under an unrecognised name | aliases — promotable |
| 5 | too shallow to register | `scope` (depth allocation) |
| 6 | target is not what we inferred | `interpret_situation` |
| 7 | genuinely out of scope; the user is wrong | none — **defend the decision** |

Meaning 7 needs a real response path, not an error path. It has no semantic home yet (Architecture §14).

---

## 9. Contracts — INVARIANT

```
backend/     API · worker · store · routing
             NEVER imports the model SDK
             NEVER touches HTML or geometry
             holds no pedagogy

agent/       the decisions
             NEVER imports the store — values in, values out
             makes decisions testable and replayable

engine/      merge · measure · solve · annotate · paginate · validate · print
             NEVER imports the model SDK
             NEVER makes a network call
```

**Enforce all three with a CI import check** — implementation, but the boundaries are not. The engine's purity is what makes golden-image testing possible; the agent's is what makes decision replay possible.

### Engine pipeline — CHOICE

```
doc_model + template
      ↓  merge       blocks → HTML. Pure, no model.
      ↓  measure     browser loads it; post-layout geometry for every element
      ↓  solve       constraints → positions for labels and connectors
      ↓  annotate    inject SVG: arrows, circles, highlights
      ↓  paginate    honour keep-together / keep-with-next / breaks
      ↓  validate    measured vs declared → violations
      ↓  print       → PDF
```

```
engine.validate(doc_model, template_id) -> Violation[]
engine.render(doc_model, template_id)   -> bytes (PDF)
engine.preview(doc_model, template_id)  -> bytes (PNG, one page)
engine.feasible(plan, template_id)      -> Fits | Overflow(measured, limit)
```

### Candidate API surface — CHOICE

**Marked candidate deliberately.** These endpoints encode a workflow we have not settled: whether a project may hold several competing plans, whether approval is project-level or per-member, whether partial approval exists. Those are open (§13).

```
POST   /projects                        { text }
POST   /projects/:id/utterances         { text }
POST   /projects/:id/sources            multipart          [conditional]

GET    /projects/:id/intake
POST   /projects/:id/plan
GET    /projects/:id/plan                                  → plan, findings, extent
POST   /projects/:id/plan/approve       { decision_ids }   [GATE, idempotent]

GET    /members/:id
POST   /members/:id/demo
POST   /members/:id/demo/approve        { decision_ids }   [GATE, idempotent]
GET    /members/:id/artifact
POST   /members/:id/override            { finding_id, reason }

POST   /projects/:id/corrections        { text }           → re-derivation plan
POST   /projects/:id/corrections/:id/confirm

GET    /projects/:id/set-status                            → completeness, blockers
GET    /jobs/:id
GET    /decisions/:id                                      → record + dependencies
```

`GET /decisions/:id` is not a debug endpoint. It is how *"why isn't X in here?"* gets answered.

---

## 10. Capacity assumptions — WORKING MODEL

**The shape is the finding; the numbers are assumptions to be measured.** Rev. 1 presented both as fact.

> **This is not a high-QPS system. It is a bursty, expensive-per-request, long-running-job system.** ← the finding

Assumptions, for sizing only: ~1,000 weekly-active users · ~2 sets/month each at ~5 documents · ≈350 documents/day · ~0.004 req/s · exam season a 10–50× burst · 50–80k tokens per document plus verification · 2–5s of browser time per render.

What follows regardless of the exact numbers: read replicas and sharding are irrelevant; **cost per document is the metric, not QPS**; the real problems are queue backpressure during bursts, cost control, and job durability.

---

## 11. Production invariants

All eight arrived from Appendix D. None required a change to Architecture Rev. 2.

**1 · A commitment names the exact decision versions it commits.**
Re-committing an identical set is identity, not a second commitment. Idempotency for approvals falls out of this — no separate idempotency key is needed, and it holds across retries, clients and users. If the plan changed between two approvals the decision ids differ, and the second is genuinely a different commitment, which is correct.

**2 · A derivation's result is durable before its job is marked done, and `inputs_hash` covers everything that can change the output** — inputs, model, prompt version, effort, params. A worker that crashes after generating but before completing must find its own result on retry, or the most expensive work in the system is paid for twice.

**3 · Invalidation is idempotent.** Marking stale is set membership, not a counter, so duplicate corrections converge. A duplicate submission costs one classification call and reaches identical state.

**4 · A job re-checks input freshness when it is claimed, not only when it is enqueued.** Without this, a scope change during a 30-member build burns the entire queue. With it, queued work is dropped for free — the single largest cost saving available during cancellation.

**5 · A derivation may publish only if its input hash is still current for its target.** Compare-and-set on publish.
This is the one that **corrects Rev. 1**, which said cancellation does not matter for correctness. It does. Two jobs writing the same member — one stale, one fresh — do not collide in the content-addressed store, but they do collide on the member's current-output pointer, and last-writer-wins can leave the stale one in place.

**6 · Set completeness is a first-class status, distinct from member state.**
A member can be **complete by its own job's condition and still not deliverable**, because Architecture §10 requires the union to cover the target. When member 3 fails, members 1–2 remain downloadable, member 4 may have generated successfully against 3's declared exit and is still not shippable. Member state cannot express that; the set needs its own.

**7 · A predecessor's exit failure invalidates its successors' verification**, even when the successors' own content is unchanged — the same finding as Architecture B3, recurring at member level. Recording `actual_exit` alongside `declared_exit` is what makes the divergence detectable at all.
Divergence routes two ways: give the predecessor more capacity (**scope**) or lower its declared exit (**partition**). Lowering an exit forces a successor to cover more, which is legal but must be **surfaced, never silent**.

**8 · A commitment pins its whole derivation environment**, not just decision ids: model, prompt version, **taxonomy version**, asset version, source versions.
This absorbs source-version lineage and taxonomy evolution into one mechanism. When any of them moves under a commitment, the answer is the same as asset drift in Architecture B1 — a **reconciliation report**, never a silent re-derivation.

**9 · A delivered artifact can never be silently replaced or reconstructed in place.**
Re-deriving decisions reproduces the *doc model*. It does not reproduce the *bytes*: byte-identical re-render would require a pinned browser, pinned fonts and deterministic PDF metadata, and even then yields visual equivalence rather than a guarantee. So the delivered bytes are kept rather than regenerated on demand.

**Retention *duration* is policy, not invariant.** Indefinite is the sensible default, and legal or privacy obligations may later force deletion — an erasure request is a real case. The invariant survives deletion intact: a delivered version may be **removed**, disclosed as removed; it may never be **quietly swapped** for a different one under the same identity.

This **corrects Architecture §12 upstream.** Its bulk-output category — *"large, regenerable, lowest historical value"* — is right for draft prose and wrong for a delivered artifact, which is not regenerable and acquires its highest value at the moment it leaves the system. A delivered artifact version is a **commitment**, and inherits that category's rules.

The failure this prevents is ordinary and severe: **a user asks a question about a document they downloaded three months ago.** Without version retention we answer from the current one, which may no longer say what they are reading.

**10 · Reconstruction and replay are different guarantees, and need different environments.**
`decision_environment` answers *"why does it say this?"* — reproducible, because decisions are content-addressed and replayable. `render_environment` answers *"why does it look like this?"* — explicable but **not** reproducible, because template, engine, browser and font versions drift and are not all under our control.

Rev. 2's single `derivation_environment` could answer neither question about the render side. Both are now recorded on the artifact version, so the explanation survives even where the reproduction cannot.

**11 · A delivered artifact carries its own identity in its bytes.**
A visible or embedded version stamp. Without it, *"page 34 of my notes"* is ambiguous across every version we retained, and the system must guess which document the user is holding — which makes the entire retention apparatus unusable for the one job it was built for. Cheap to add, and load-bearing.

**12 · The version in hand is authoritative for questions about itself; the latest is authoritative for what we now believe.**
`superseded_by` orders versions. It does **not** make an older version wrong to answer about. Both facts are owed at once: *"the March version you have says X on page 34; that was corrected in April and the current version says Y."* Answering only from the latest tells the reader something they cannot see in the document in front of them.

This is what makes pagination artifact-owned (§5) pay: once the version is known, a page number resolves to specific blocks.

**13 · Supersession and retraction are different events, and retraction is an obligation.**
A revision that adds a section supersedes. A correction that fixes a **wrong claim** retracts — and Semantics §4 locks that a materially wrong document is not a document. Having shipped one, the obligation to say so follows; it does not expire because a newer version exists.

`supersession_kind ∈ revision | retraction` carries it, and the trigger is available: a correction that resolves a `CRITICAL` or `ERROR` correctness finding produces a retraction, anything else a revision.

Retraction is **per-claim, not per-chain**. If C retracts something introduced in B, a holder of A was never exposed and should not be told they were. That makes the **version diff** a requirement rather than a nicety — it is the only thing that says which blocks changed and how, and therefore the only thing that makes a retraction actionable.

### What backward compatibility gets for free

Appendix D6 found that **recorded dependencies make the decision graph per-project**. A project carries the graph it was actually built with, so adding a fifteenth decision does not retroactively rewrite the history of existing projects — their closures stay correct *for them*.

Had dependencies been inferred from a global pipeline definition, a taxonomy change would silently alter what every past correction should have invalidated. §2's recording claim was not chosen for this; it delivers it anyway.

---

## 12. Deferred

| Deferred | Until |
|---|---|
| Composition asset records, versioning, promotion, reconciliation | reuse across projects measurably pays |
| Situation-free adjudicator | there is an asset to promote into |
| Frontend | the pipeline runs headless |
| Auth, accounts, billing | there is something worth logging into |
| **Multi-tenancy: project isolation, source access control, shared-asset visibility, artifact permissions** | before any second user. Out of altitude here, not out of mind — a shared composition asset built from private sources is a real disclosure risk |
| Broker (Redis / Celery) | the job table measurably bottlenecks |
| Separate vector store | `pgvector` measurably bottlenecks |
| Workflow orchestration | the symptoms in §6 appear |
| Template catalogue | Semantics §2's open question closes |
| Streaming progress UI | polling stops being enough |

---

## 13. Open questions

```
—    which payloads harden first, and after how many genuinely
     different subjects?

—    retry ceiling in the repair loop. Three is a guess.

—    where retrieval enters — ingestion only, or draft as well?
     Significant cost implications.

—    verification budget: §7 sets the allocator; the right spend per
     set is unknown until measured.

—    source authority scoring. The previous design proposed four axes —
     scope · factual · terminology · assessment — with a real
     discriminator: a textbook outranks a syllabus on `factual` and
     loses to it on `scope`. A CANDIDATE ANSWER to the external-
     authority question open in Architecture §16, not a settled one.

—    draft granularity: per placement, per section, or per member?
     Smaller calls parallelise and cost less; larger calls hold tone.
     This is Architecture §16's "is Draft one decision or two."

—    plan cardinality: may a project hold several competing plans?
     May approval be partial? §9's API assumes not, and that is
     untested.

—    cancellation policy: abort in-flight, or drain? Invariant 4 makes
     the queue free to drop; the in-flight decision is cost-vs-
     complexity and needs real numbers.

—    cross-project learner history. A returning user's entry point is
     partly KNOWN to us — we generated what they studied. Semantics §1
     lists entry point as user-set and binding. That may be a gap in
     the semantics, not here. See D5.

—    edge-closure walking is the hottest path in the system and has no
     index strategy yet.

—    a frame that changes mid-flight. Untested.

—    artifact retention policy. Delivered versions are kept forever
     (invariant 9). Undelivered ones — a demo, a superseded candidate,
     a rejected layout — probably are not. Where is the line, and who
     decides?

—    pagination stability across a re-render is now known to be
     user-visible ("see page 34"). Whether we owe stability, or only
     disclosure that it moved, is unsettled.

—    HOW a retraction reaches the holder of an old version. Invariant
     13 establishes the obligation and the diff makes it actionable;
     the channel is undecided, and it is the only obligation in this
     document that may need to reach a user who is not currently in
     the product.

—    whether a delivered artifact's stamp should be human-visible on
     the page, embedded in metadata, or both. Metadata alone fails
     when a user prints the document.
```

*The version diff moved out of this list in Rev. 4 — invariant 13 makes it required, not optional.*

---

# Appendix D — production stress tests

Six cases, run against Rev. 1 before it was revised. **No case exposed a root architectural problem.** Findings are classified by level.

### D1 — Duplicate delivery

*Retried approval · retried correction · worker crash after generation, before completion.*

**Approval.** Two identical approvals write two commitments and enqueue two sets of member jobs — double spend. Memoisation does not help: a commitment is an event, not a derivation. But a commitment that names *which decision versions it commits* makes re-committing the same set identity, and that is stronger than an idempotency key because it holds across retries, clients and users. → **invariant 1**

**Correction.** Duplicate submission writes a duplicate utterance, which is correct if the user really said it twice. Downstream, both classify identically and mark the same set stale — and marking stale is set membership, not a counter. Damage bounded to one wasted classification. → **invariant 3**

**Crash after generation.** The expensive work succeeded; the job still reads `running`. A reaper requeues it, and it reruns — *unless* the result was durable before the job completed, in which case the rerun computes the same hash and returns the memo. The requirement is a **write ordering**, and it holds only if the hash covers everything that changes the output. → **invariant 2**; the reaper is *implementation*.

### D2 — Cancellation during a 30-member build

*12 running, 18 queued, user changes scope.*

Three separable concerns, and they classify differently.

**Queued work** — a job that re-checks freshness at claim time is dropped for free. This is the largest saving available and it is architectural, because checking only at enqueue burns the whole queue. → **invariant 4**

**In-flight work** — abort or drain is cost-vs-complexity. → **choice**

**Salvage** — a half-drafted member's blocks are still valid for placements the change did not touch. This needs no new machinery; it is invalidation at block granularity, which the identity model already supports. → **choice**

**And one correctness finding.** Rev. 1 said cancellation does not matter for correctness. Two jobs writing the same member — one stale, one fresh — do not collide in the content-addressed store, but they do collide on the member's current-output pointer. Last-writer-wins can leave the stale output in place. → **invariant 5**, and a correction to Rev. 1.

### D3 — Partial failure

*Members 1–2 pass, 3 fails, 4 waits.*

Members 1–2 are committed and complete by their own job's condition: **downloadable**. Member 4 may have generated successfully against 3's declared exit — structurally fine, entry premise unmet, **not deliverable as part of the set**.

That distinction — *member-complete* versus *set-deliverable* — has no home in Rev. 1. It is not new architecture: Architecture §10 already requires the union to cover the target. It was simply never materialised. → **invariant 6**

Retry-3-only and override-3 both already exist as mechanisms. What the interface offers is → **choice**.

### D4 — Declared exit versus actual exit

*Member 2 declares "can design a normalised schema"; its output stops at normalisation. Member 3 generated concurrently against that declared exit.*

The detection mechanism already exists — judgment verification of member 2 against its own target *is* the exit check, because a member's target and its exit are the same thing. What was missing is the **trigger** and the **routing**: an exit failure must invalidate successors' verification even though their content is untouched, and the repair routes either to scope (more capacity) or to partition (lower the exit).

Lowering an exit forces a successor to cover more. That is legal — it is a scope change on the successor — but it inverts Semantics §9's assumed-entry rule and must be surfaced. → **invariant 7**

### D5 — Return visit, six months later, different goal

*"Learn backend to build an app" → "prepare me for backend interviews."*

Trace what carries over: testimony differs, situation differs, and therefore relevance, traversal, consequence, scope and everything downstream differ. **Only `derive_structure` is shared** — which is exactly the seam Architecture §7 identified.

So *"same project or new?"* is really asking **what owns the structure derivation**. Without a shared asset it must be the project, which forces an awkward choice. With one, a project is just *(situation + commitments + artifacts)* and a new one is free and correct.

**The project-identity question is an artifact of the deferred asset, not a defect.** New project is right — and this broadens the asset's justification: it is not only a cost optimisation, it is what makes return visits coherent. → **choice**, with a P3 dependency.

One thing does not carry and probably should: **what the learner now knows.** Their entry point for the interview course is higher because we generated the first course. Semantics §1 lists entry point as user-set and binding, so nothing in the current model uses it. That may be a gap in the semantics. → **open**, D5 in §13.

### D6 — Taxonomy evolution as backward compatibility

*A fifteenth decision arrives — Architecture §16 predicts a document-level coherence pass specifically.*

**Existing projects are unaffected, by construction.** Adding a `kind` value is additive. And stored dependencies were **recorded from actual runs**, not inferred from a pipeline definition — so each project carries the graph it was built with, and an old project's closure remains correct *for that project*. A fifteenth decision it never had cannot appear in its history.

Had dependencies been inferred globally, a taxonomy change would silently alter what every past correction should have invalidated. §2's recording claim delivers backward compatibility it was not chosen for.

**Re-deriving an old project after the change** is the same shape as asset drift in Architecture B1: re-derive on the new taxonomy and the committed plan rests on a derivation the user never approved; pin the old one and the project never improves. Same answer — pin, and reconcile visibly.

That generalises. Model version, prompt version, taxonomy version, asset version and source versions are all *"the system changed under a commitment,"* and they want one mechanism rather than five. → **invariant 8**, which also absorbs source-version lineage.

### D7 — Reconstructing a delivered artifact six months later

*The system has evolved. A user asks about the PDF they downloaded in March.* Reconstruction is a stronger test than replay, and it breaks something replay does not.

**What determines how a delivered PDF looks?** Decisions, blocks and render configuration are all recorded — but the template CSS, the layout engine, the browser build and the **font metrics** are not, and every one of them changes pagination without touching a single decision. A font update alone repaginates a document.

So `derivation_environment` was incomplete, and incomplete in a structured way: it is **two** environments. Decisions re-derive a doc model; only the render environment turns a doc model into these bytes. → **invariant 10**

**And byte-level reproduction is not achievable anyway.** Pinning the browser and fonts and stripping PDF timestamps gets close to visual equivalence, never to a guarantee, and several of those versions are outside our control. The honest conclusion inverts the mechanism:

> For a delivered artifact, **retention replaces reproduction.** We can reconstruct the *explanation*; we cannot reconstruct the *artifact*. So we keep it.

Which reclassifies it. A delivered artifact is not bulk output — it is a **commitment**, by Architecture §5's own definition: a self-describing snapshot of something externally relied upon. → **invariant 9**, and a correction to Architecture §12.

**Is `artifact` under-modelled?** Yes, but not in the way the challenge proposed. Target, scope, structure and representation are **decisions**; making them fields of an artifact would give the same judgment two homes that can diverge — the `spec`-blob mistake one level down. The artifact *references* its decision set.

What it genuinely owns is narrower and was entirely missing: **the bytes**, and **pagination**. Pagination is a joint product of doc model and render environment, derivable from neither alone, and it is the one artifact-level fact users cite directly.

**Does delivery need a sixth gate?** No. A gate is a check before commit; delivery is not a check. Layout stays the gate, and delivery is the commitment that follows — which is also what makes retention mandatory rather than discretionary.

### D8 — A user references a March document in September

*March: version A delivered. April: a correction produces B, delivered. June: a font update produces C, undelivered. September: "on page 34 of my notes it says X, and that looks wrong."*

**Which document is "my notes"?** The system retained A, B and C and knows when A and B were delivered. It does **not** know which one the user is reading — and cannot, unless the file says so. Retention without self-identification is unusable for exactly the case it was built for. → **invariant 11**

**Page 34 of which version?** Once the version is known this resolves cleanly, because pagination is per-artifact-version. That is the payoff of D7's finding, arriving one test later.

**Is A still authoritative?** Both answers are needed at once. A is authoritative for *what the document in their hand says*; the latest is authoritative for *what we now believe*. Answering only from the latest describes a document the reader cannot see. → **invariant 12**

**And the sharpest finding: why was it corrected?** If April's change added a section, A is merely old. If it fixed a **wrong claim**, A is wrong — and Semantics §4 locks that a materially wrong document is not a document. Having shipped one, the obligation to say so does not expire because a newer version exists. **Supersession and retraction are different events**, and the trigger is already available: a correction resolving a `CRITICAL` or `ERROR` correctness finding retracts. → **invariant 13**

**Multi-revision.** Retraction is per-claim, not per-chain: if C retracts something B introduced, a holder of A was never exposed. So the retraction needs to know which blocks changed and how — which promotes the **version diff** from an open question to a requirement.

**Verdict:** no architectural defect. Three invariants, one new product obligation, and one open question the model cannot answer on its own — *how* a retraction reaches someone who is not currently in the product.
