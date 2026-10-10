# V1 Pipeline Problem Map

Every stage of V1, what it does, what is wrong with it, and what we still don't
know. Built to be consumed **one section at a time** when V2 design starts.

**No solutions are chosen here. No domain model. No architecture.**

---

## How these boundaries were derived

The proposed decomposition was the starting point. Two adjustments came out of the
code:

- **"Planning" is not one stage.** V1's own persisted decision kinds are
  `interpret_situation · intake_strategy · derive_structure · relevance · scope ·
  partition · traversal · consequence` — **eight** decisions across what the
  proposal treats as two stages. Planning is a sub-pipeline of five.
- **"Document construction" barely exists.** It is `_assemble()`, ~20 lines of pure
  function. Naming it a stage overstates it, which is itself worth recording.

One stage in the proposal has **no implementation at all** (§0).

**Evidence key** — `[OBSERVED]` in code · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning from code · `[UNKNOWN]` hypothesis needing measurement.

**Sources.** `V1/` at hash `807c8ec99a60`; `V2/runs/baseline-01` (10 records) and
`runs/generate-01` (1 end-to-end); `V1-Measured-Issues.md`; `Plan-Quality.md`;
`Runtime-Dependencies.md`; the Lexo-agent forensic study.

---

# §0 — Ingestion / external sources

### 1. What it does
Accept material the user brings — a syllabus, past papers, a textbook chapter,
lecture slides — and make it authoritative over terminology, ordering and coverage.

### 2. Current V1 implementation
**None.** `[OBSERVED]` A search of `backend/api.py` for `upload`, `UploadFile`,
`source`, `syllabus`, `ingest` returns **zero matches**. `select_frame` and
`ingest_sources` are specified in `Build-Spec.md` and return **zero matches
anywhere in the codebase** — not stubs, absent.

### 3. Problems
- **Q6 — external-authority structure unrepresented.** `[MEASURED, n=1 of 1
  opportunity]` The contract-act plan contains no section number anywhere:
  `Preliminary & Definitions`, not `ss. 1–2`.
- **Coverage is unverifiable in principle.** `[INFERENCE]` Everything V1 verifies is
  self-referential — the artifact against the plan, the plan against nothing. With no
  external list, a missing section is a judgment rather than a fact.
- **No retrieval of any kind.** `[OBSERVED]` The only `httpx` in the repo is the LLM
  client. So the correctness gate that `Product-Semantics` LOCKS is unenforced for
  every subject that has an authority.
- **Terminology risk did not materialise.** `[MEASURED]` P1 — V1 produced the Act's
  own words (`Free Consent — Coercion`, `Quasi-Contracts`, `Bailment — Pledge & Lien`)
  from model knowledge alone.

### 4. Evidence level
Absence: `[OBSERVED]`. Consequence for coverage: `[INFERENCE]`. Whether ingestion
would actually improve plans: `[UNKNOWN]` — never tested.

### 5. Constraints imposed
Because nothing is ingested, **every downstream stage treats the model's own
knowledge as the only source**. Scope, depth and ordering have no external referent,
so `traversal` cannot be checked and `relevance` cannot be audited.

### 6. Open questions
- Which subjects actually need it? (contract-act did; agentic-ai did not)
- What can a source bind — coverage only, or also terminology, ordering, assessment?
- Can the system detect that it *should* be reading a source and cannot?
- Is retrieval a stage, or a property of derive?

### 7. Solution directions
Authority-typed sources (scope / factual / terminology / assessment, per
`Foundation`); an explicit "authority absent" branch rather than silence; a
coverage-checkable external list; user upload; retrieval at derive time. **All
unexplored.**

---

# §1 — Intake

### 1. What it does
From the user's words, reconstruct the learning situation across 8 axes, decide
whether anything must be asked, write the questions, and decide when to stop.
Ends when `state == "ready"`.

### 2. Current V1 implementation
`[OBSERVED]` `backend/planning.py:_read()` → `agent.plan.interpret(transcript)` →
`sufficiency.decide(readings, utterances, stated=…)` → `agent.plan.ask(...)` only if
`sufficiency.asking` is non-empty. Policy is code
(`sufficiency.py:66–133`), judgment is the model's. `capacity`,
`depth_register`, `template` are `askable=False` by locked policy. Exit on
`sufficiency` or on no-progress (`improved()`), bounded by `MAX_INTAKE_ROUNDS`.
Split into `interpret`/`ask` to cut first-question latency from **102.6s → 17.7s**.

### 3. Problems
- **B8 — threshold calibration.** `[MEASURED]` Weak + askable + `material=False`
  occurs **0 times in 88 readings**; the filter has never suppressed a question. Yet
  it is not a rubber stamp — 88/88 `would_differ` populated, median 188 chars. A
  threshold difference, not a broken mechanism.
- **Q7 — over-asking.** `[MEASURED, n=1]` `git-commits` wrote 4 questions and flagged
  7 weak axes where the reference says 0–1. **The reference is contestable** on
  `entry_point`.
- **A8 — materiality enum collapsed to a boolean** before storage. `[OBSERVED]`
  `changes_details` and `no_effect` indistinguishable afterwards.
- **O7 — the whole transcript is re-interpreted every turn.** `[OBSERVED]`
  `interpret(transcript: str)`. Cost grows with conversation length; measured 1–2
  calls per answer.
- **Q1 partly originates here.** `job` is written by `interpret_situation`. See §2 —
  the defect is that nothing downstream depends on it.
- **A3 — STRUCK.** Not a defect; policy is correct.

### 4. Evidence level
Filter never firing: `[MEASURED]`. Concreteness of `would_differ`: `[MEASURED]`.
Whether the threshold is *wrong*: `[UNKNOWN]` — needs per-axis reference judgments on
more than one case. Whether re-interpretation costs anything measurable:
`[UNKNOWN]` — the model call may dominate.

### 5. Constraints imposed
Everything downstream inherits the situation and **cannot recover from a wrong
`entry_point`** — the agentic reference states this is not recoverable later: if the
landscape is built assuming API fluency, API foundations are never in the graph.
`capacity` being unasked means §2 must derive extent and §3 must negotiate it.

### 6. Open questions
- What magnitude of difference should count as `changes_the_plan`?
- Should a material *guess* be surfaced as a visible assumption, since policy
  forbids asking?
- Is re-interpretation per turn the right model, or should readings be incremental?

### 7. Solution directions
Use the middle enum value; persist the full enum; surface guessed-material axes as
assumptions; incremental re-reading; more references to calibrate against.

---

# §2 — Planning (derive → relevance → scope → partition → traversal)

### 1. What it does
Turn a situation into an approved-able curriculum: derive the concept landscape,
judge relevance, set scope and depth, partition into modules, order them, and state
consequences of cuts. **This is where the product's value lives.**

### 2. Current V1 implementation
`[OBSERVED]` Five decision kinds, model calls in `agent/plan.py`
(`derive_v1`, `plan_v3`, `plan_revise_v2`). Measured: **6 calls, 342s** for the plan
stage alone. Records carry `landscape` (concepts, typed edges, families, roots),
`scope` (covered, cut, depths, anticipates), `partition` (modules, concepts_per_module,
capability), `promises`, `extent`, `feasibility`.

### 3. Problems

**Structural**
- **A1 — approval passes an undeliverable plan.** `[MEASURED]` `serves_everything:
  False` in **6 of 8 plans**; 5 of those 6 reached approval and **all 5 were
  approved**. `perceptual-referent` ×5, `parallel-state` ×4 ("No realization
  exists"). Cross-cutting with §3 and §6.
- **A2 — phantoms.** `[MEASURED, 1 of 1 opportunity]` 42 concepts − 6 cut = 36 in
  scope; `concepts_per_module` sums to **40**. Approved.
- **A6 — unbacked capability clauses.** `[MEASURED]` 2 of 19 in the large plan, 0 in
  the seven smaller ones.
- **A4 — extent under-estimated ~3×.** `[MEASURED, n=1]` ~36 pages promised; module 1
  alone produced 14. Cross-cutting with §4 and §6.

**Quality**
- **Q1 — job misclassified.** `[MEASURED, n=3]` `construct` for all three; references
  say orient / retrieve-rehearse / construct. **2 of 3 wrong.** Root defect.
- **Q2 — over-scoping follows.** `[MEASURED, n=1]` 18 → 42 concepts; two modules for
  material the reference cuts.
- **Q3 — leftovers-bucket module.** `[MEASURED, n=1]` 9 concepts, 3 unrelated
  capability clauses — the exact shape the reference predicted.
- **Q4 — retrieval under-funded.** `[MEASURED, n=1]` 2 concepts where the reference
  wants 3 distinct ones.
- **Q5 — depth undifferentiated.** `[MEASURED, n=2]` 21/23 at `work through`, zero
  `mention`.
- **Q8 — sections unrepresentable.** `[OBSERVED]` No section decision exists;
  11 concepts → 11 sections. Architectural, not statistical.

**Reliability / performance**
- **A5 — `derive_v1` returns truncated JSON and loses the run.** `[MEASURED]` 2 of 10
  cases. The widest output in the pipeline.
- **B1 — high non-determinism.** `[MEASURED]` Same request: 29→42 concepts, 38→60
  edges, 1→5 roots, 5→8 modules, 0→6 cut.
- **O6 — no memoization.** `[OBSERVED]` `inputs_hash` is written into the decision row
  and **never read**. A re-derivation always costs a full call.
- **O8 — planning holds the HTTP request.** `[OBSERVED]` `def force_plan` is sync;
  measured 342s, and 11,537s in one case. `jobs.py` exists and only generation uses
  it. Cross-cutting with §8.
- **Root cause across A1/A2/A6/Q1/Q6/Q8** `[INFERENCE, high confidence]`: **V1 records
  judgments as free-form fields that nothing downstream depends on or checks.** `job`
  is a string nothing consumes; feasibility is computed and gates nothing;
  `capability_unbacked` is computed and gates nothing. Six findings, one disease.

### 4. Evidence level
All the Q-findings are `[MEASURED]` at n=1–3 and **must not be read as rates.** The
single-root inference is `[INFERENCE]`. That fixing the root improves *quality* as
well as consistency is `[UNKNOWN]`.

### 5. Constraints imposed
The plan is the contract every later stage is measured against — so **a wrong plan is
undetectable downstream** (§4 reported `coverage: 1.0` on a plan carrying 4
phantoms). Extent constrains §3's negotiation and §6's page budget. `partition`
determines the number of PDFs, which §7 currently equates with files.

### 6. Open questions
- Is B1 a defect or a property to manage? Determinism vs stable promises.
- Does making `job` consequential fix Q1, or is a judge needed?
- What bounds a derivation whose size scales with subject breadth (A5)?
- Should the five decisions stay five calls, or fewer/more?

### 7. Solution directions
Typed decisions with enforced relationships; deterministic `partition ⊆ scope ⊆
landscape`; extent computed from concepts × depth against measured density; job as a
typed decision with admissibility consequences; chunked or streamed derive;
memoization by input envelope; planning moved onto the job runner; operation-based
plan construction; a capability-decomposition representation; a section decision.
**None chosen.**

---

# §3 — Correction and approval

### 1. What it does
Let the user correct a plan in plain English, route the correction to the decision
that owns it, and commit an approved decision set.

### 2. Current V1 implementation
`[OBSERVED]` `plan_revise_v2` call; records carry `said`, `reading`, `claimed`,
`actual`, `unclaimed_drift`, `claimed_but_unchanged`, `out_of_scope`,
`not_understood`, `landed`. Approval is `approve()` → a `Commitment` with
`decision_ids` and a snapshot. Measured: correct 97s, **approve 0.04s**.

### 3. Problems
- **A1 — the gate gates nothing.** `[MEASURED]` Cross-cutting with §2/§6; the
  decision to *accept* belongs here.
- **B2 — `decision_count` is always exactly 7.** `[MEASURED]` Across every approval,
  for plans of 1 to 9 modules. Architecture §5 says commitment is per-member and
  ordered. Likely counting decision *kinds* — unverified.
- **Corrections work, and are the only self-repair in the system.** `[MEASURED]`
  `ml-weekend` went 5 modules → 3; `generate-01` went 7 phantoms → 4. **A correction
  answering a content complaint incidentally repaired a structural inconsistency.**
- **P4 — out-of-scope routing is correct.** `[MEASURED]` *"make it dark themed"* →
  `out_of_scope`, `landed: false`, `claimed: []`.
- **Lexo removed its approval gate.** `[OBSERVED, external]` W7 — `PlanApprovalTool`
  bound to no agent, capture functions never called, state fields vestigial. **The one
  pattern we most want to borrow is the one they abandoned**, with no recorded reason.

### 4. Evidence level
Gate ineffective: `[MEASURED]`. Corrections effective: `[MEASURED, n=2]`. Whether
approval is the right product primitive at all: `[UNKNOWN]` — Lexo's removal is
evidence about a different object (task execution, not deliverable scope).

### 5. Constraints imposed
Approval freezes a snapshot that §4 generates against. Because it accepts anything,
**§4 can be handed a self-contradictory contract** and will fulfil it faithfully.

### 6. Open questions
- What must be true before a plan is approvable?
- Should the user be shown feasibility shortfalls, or should they block?
- Is a commitment per-member (Architecture §5) or per-plan (what B2 suggests)?
- Why did Lexo remove theirs?

### 7. Solution directions
Admissibility preconditions on approval; surfacing shortfalls as part of the plan the
user reads; per-member commitment; correction as the primary repair channel rather
than a secondary one.

---

# §4 — Content generation

### 1. What it does
Turn each approved unit into written content — blocks with prose, lists, code,
tables, examples, questions, callouts, relations — and verify each against its
promise.

### 2. Current V1 implementation
`[OBSERVED]` `agent/generate.py:_from_plan`. `requirements(plan)` → one model call
per unit → `_load_section` → `check_unit` → keep the better of 2 attempts →
`_assemble` → `check_document`. Prompt `unit_v1`. Measured: **5 calls, 323s, 14
pages, 3,477 words, 54 blocks, 0 repairs, satisfied, coverage 1.0.**

### 3. Problems
- **It is correct.** `[MEASURED, n=1]` The only end-to-end run fulfilled its contract
  exactly — the defect we most suspected did not appear.
- **O1 — strictly sequential, and the units are independent.** `[OBSERVED]`
  `for order in orders:` around a blocking call. `_unit_brief` reads the request, the
  situation and **its own** order — nothing from prior sections. Measured ~65s per
  call; parallel wall-clock would be ~one call. **~4× latency sitting in a `for`
  loop, at identical token cost.**
- **A7 — departures escape without a licence.** `[MEASURED]` 36 departures, **6
  undiagnosed**, `clean: false`. The check exists and does not block.
- **Treatment is observation only.** `[OBSERVED]` `anticipates` never reaches the
  generator, so `treatments_anticipated` vs `treatments_produced` are two independent
  judgments, not plan-and-execution.
- **`coverage: 1.0` verifies mention, not truth.** `[OBSERVED]` `covers()` is
  normalized substring matching. A document can be `satisfied: true` and factually
  wrong throughout. Cross-cutting with §0 (no grounding).
- **A4's other half.** `[MEASURED]` 5 concepts → 14 pages is the density figure
  planning should have used.
- **Per-unit generation must survive any redesign.** `[INFERENCE]` Its docstring
  states the reason, and it is what took coverage 2/17 → 17/17.

### 4. Evidence level
Correctness: `[MEASURED, n=1]` — one run, prime suspect absent, not a clearance.
Sequentiality and independence: `[OBSERVED]`. That parallelism is safe:
`[INFERENCE]`, strong. That it does not degrade output or trip throttling:
`[UNKNOWN]`.

### 5. Constraints imposed
Generation defines real density, which is the only honest input to extent (§2).
Its output shape defines what §5 can assemble and §6 can draw.

### 6. Open questions
- Does concurrent unit generation change quality?
- Should a unit see its predecessors at all? (currently no — and the plan is the
  only coordination)
- Where should factual grounding enter, if anywhere?
- Is two attempts the right repair budget?

### 7. Solution directions
Concurrent units; licence as a required field on the block type rather than a
post-hoc check; feeding `anticipates` to the generator so treatment becomes a
contract; density feedback into extent; grounding hooks.

---

# §5 — Document construction / assembly

### 1. What it does
Combine generated sections into one `Document` — title, audience, capability,
exclusions — ready to render.

### 2. Current V1 implementation
`[OBSERVED]` `_assemble(plan, situation, sections)`, ~20 lines. Title, "who it is
for" and "what they will be able to do" are taken **from the plan, not the model** —
deliberately, so they cannot drift from what was approved.

### 3. Problems
- **The stage barely exists.** `[OBSERVED]` Naming it a pipeline stage overstates a
  pure function. Whether that is a *problem* is open — it may be correct minimalism.
- **Q8 lands here as well as §2.** `[OBSERVED]` Sections are one-per-concept by
  construction, so the section/module distinction has no home in either stage.
- **The document model is a typed block union of 11 kinds.** `[OBSERVED]` Whether that
  vocabulary is the right one is the open question the whole product turns on — the
  user's own earlier objection stands: *"a Document model designed around a coding
  PDF cannot be the universal representation."*
- **The Document JSON is persisted deliberately.** `[OBSERVED]` *"A template fix
  should not cost another generation."* A good decision; name it so it survives.

### 4. Evidence level
Thinness and field provenance: `[OBSERVED]`. Adequacy of the block vocabulary:
`[UNKNOWN]` — never tested against a non-technical domain end to end.

### 5. Constraints imposed
The block union is the contract between §4 and §6. **Adding a representation means
touching the union, every template, and the generator prompt** — three edits, which
is where the silent-drop bug lived.

### 6. Open questions
- Is the block union the right abstraction, or should representation be semantic
  (`containment`, `sequence`) with realization left to §6?
- Does assembly deserve to be a stage at all?
- Where do sections live?

### 7. Solution directions
Semantic representation with template-side realization; a generated template-coverage
check; keeping assembly as a pure function.

---

# §6 — Rendering / PDF

### 1. What it does
Document mapping + template id → HTML → PDF, plus report what it observed while
printing.

### 2. Current V1 implementation
`[OBSERVED]` `engine/render.py`, **`playwright.sync_api`**. `render_html` is pure
Jinja (`StrictUndefined`). `render_pdf` opens `sync_playwright()`, launches
**a fresh Chromium per call**, sets content with `wait_until="networkidle"`, awaits
`document.fonts.ready`, emulates print, resizes the viewport to A4 CSS pixels, runs
**four JS probes**, then prints. 4 templates, 2,480 lines.

### 3. Problems
- **O2 — a new browser process per PDF.** `[OBSERVED]` `Build-Spec.md` §8 specifies
  *"one long-lived browser per worker, recycled every 200 renders."* **The code does
  the opposite of its own spec.**
- **O4 — 3 of 4 probes don't need a browser.** `[OBSERVED]` `_UNRENDERED_PROBE` reads
  `.unrendered` elements **the template emitted**; `_REALIZATION_PROBE` reads
  `data-realization` attributes **the template wrote**. Both answerable by parsing the
  HTML string. Only `_OVERFLOW_PROBE` and `_SCALE_PROBE` need live layout.
- **A1's other half — the renderer already knows.** `[MEASURED]` `parallel-state:
  "No realization exists"` appears in 4 of 8 plans, computed *before* approval, and
  nothing blocks.
- **Three of four templates fetch webfonts at render time.** `[OBSERVED]` With
  `networkidle`, a host without egress waits out the timeout, then prints with
  fallbacks — **which changes pagination**, and pagination is artifact-owned truth.
- **Fonts are a property of the host.** `[OBSERVED]` A slim Linux image resolves none
  of `Source Serif 4 / Segoe UI / Cascadia Mono`.
- **The engine is not network-pure.** `[OBSERVED]` `tests/test_boundaries.py` forbids
  `engine/` from importing `httpx`/`requests`/`socket`, and Build-Spec §8 leans on
  that purity to justify golden-image testing — **but the browser it drives fetches
  fonts.** The test passes and the claim is false.
- **Caption/figure orphaning.** `[OBSERVED]` Chromium ignores `break-after: avoid` on
  a flex container. Known, unaddressed.
- **Full-bleed tint impossible past page 1.** `[OBSERVED]` Proven with three
  experiments; recorded as the first cost of choosing Chromium.
- **`is_truncated` fires at a hardcoded 15,500 output tokens** — a threshold whose
  Lexo analogue is a named bug. `[OBSERVED]` Cross-cutting with §4.
- **Why Chromium was chosen is narrower than it looks.** `[INFERENCE]` It is there
  **to measure**, because we cannot know space consumption without rendering. A
  renderer that computes layout as it flows knows before it draws — so the
  measurement requirement is partly a *consequence* of the engine choice.

### 4. Evidence level
Browser-per-render, probe provenance, font fetching: `[OBSERVED]`. Peak RSS, launch
share of wall time, whether a non-browser renderer can produce these templates: all
`[UNKNOWN]` — and all answerable **with zero model calls** against the saved
`generate-01` document JSON.

### 5. Constraints imposed
**This stage sets the deployment floor** (§8): ~700 MB install, a process per render,
and a memory profile nobody has measured. It also owns pagination, which makes extent
(§2) unverifiable until render time, and it silently defines which representations
are drawable — a fact §2 records and §3 ignores.

### 6. Open questions
- What is peak RSS for one render?
- How much of the 323s generate stage is browser launch?
- Can WeasyPrint produce these templates (`@page :first`, full-bleed, flex/grid)?
- **Do we need live layout measurement at all**, or is uninspectable pagination
  acceptable?
- Should the renderer be in-process, pooled, or a service?

### 7. Solution directions
Pooled/long-lived browser; HTML-parse the two template-authored probes; WeasyPrint;
Typst; ReportLab; a render service; inlined fonts; pinned font set in the image;
drop `networkidle` in favour of explicit font readiness. **Nothing chosen — and
Chromium is not assumed replaceable.**

---

# §7 — Delivery and storage

### 1. What it does
Persist projects, decisions, commitments and artifacts; serve a module's PDF; serve
the whole curriculum.

### 2. Current V1 implementation
`[OBSERVED]` `FileStore` — one JSON file per project holding all four tables, root
`out/projects`. Artifacts in `out/artifacts/{project_id}/`. Four files written per
module (`.pdf`, `.html`, `.json`, `.report.json`). `GET …/artifact.pdf` inline,
`?download=1` to force. `GET …/export.zip` builds separate files with an `NN-` prefix
**inside the archive only**, because on-disk names carry no ordering and would unzip
alphabetically — *"exactly the order the plan decided against."*

### 3. Problems
- **Postgres is declared and unused.** `[OBSERVED]` `psycopg[binary]` in
  `pyproject.toml`; `migrations/0001_init.sql` written and **unapplied**; `FileStore`
  is what runs.
- **No concurrency protection.** `[INFERENCE]` Read-modify-write of one JSON file per
  project, with `jobs.py` spawning threads. Two concurrent writes to one project can
  lose one.
- **`out/` is working-directory-relative.** `[OBSERVED]` `service.py:24` `OUT =
  Path("out")`, `store.py:117` `Path("out/projects")`. Running from elsewhere silently
  creates a second empty store.
- **Artifact filenames are title-derived slugs with no ordering.** `[OBSERVED]` The
  zip works around it; the filesystem does not.
- **No artifact versioning.** `[OBSERVED]` A regeneration overwrites. System Design
  Rev. 4 made `artifact_version` first-class and retention an invariant; neither
  exists.
- **File = module.** `[INFERENCE]` The references insist curriculum / artifact / file
  are three boundaries; V1 collapses the last two.
- **Ephemeral-disk hostility.** `[INFERENCE]` Cross-cutting with §8 — on a free PaaS
  instance all of this vanishes on restart.

### 4. Evidence level
Implementation: `[OBSERVED]`. Write-loss under concurrency: `[INFERENCE]`, untested.
Whether versioning matters before multi-user: `[UNKNOWN]`.

### 5. Constraints imposed
Storage shape decides what §8 can deploy onto. Single-JSON-per-project makes
per-decision querying impossible, so any invalidation or reuse mechanism (§2's
memoization) has nowhere to live.

### 6. Open questions
- What is the durable unit — project, decision, or artifact version?
- Does the file boundary belong to partition at all?
- What must be retained, and for how long?

### 7. Solution directions
Postgres with the written migration; a JSON-blob table as a smaller step; object
storage for artifacts; content-addressed artifact names; explicit versioning.

---

# §8 — Deployment and runtime

### 1. What it does
Run the backend, the renderer and the frontend somewhere a user can reach.

### 2. Current V1 implementation
`[OBSERVED]` `backend/app.py` → uvicorn, `timeout_keep_alive=900`. Sync endpoints, so
FastAPI threadpools them. `jobs.py` is threads + an in-process dict, explicitly *"not
a job queue — no persistence, no retries, no fan-out."* CORS hardcoded to
`localhost:3000`. No auth anywhere. No Dockerfile, no deploy config.

### 3. Problems
- **O3 — unbounded threads, each launching Chromium.** `[OBSERVED]` N concurrent
  generations = N browser processes.
- **512 MB is very likely fatal.** `[INFERENCE]` Browser-per-render **+** unbounded
  threads **+** 512 MB is the combination; **fix any one and it survives.** The blocker
  is the process model, not Chromium as such.
- **A restart loses running jobs.** `[OBSERVED]` Deliberate and documented — *"the
  failure mode is 'you have to press it again'."*
- **Ephemeral disk wipes everything** (§7). `[INFERENCE]`
- **Planning in the request path** (§2, O8). `[OBSERVED]`
- **No auth, one shared provider key.** `[OBSERVED]` A public URL drains the quota.
- **Chromium is undocumented-by-pip and absent by default.** `[OBSERVED]` Cost three
  rounds of diagnosis; `Runtime-Dependencies.md` exists because of it.
- **A shell check proves nothing about the server.** `[OBSERVED]` A sandbox with a
  redirected `%LOCALAPPDATA%` reported a complete install while the backend correctly
  reported it missing. `/health` is authoritative.
- **The free tier dominates measurement.** `[MEASURED]` 7 network failures + 2
  model-output failures across two baseline attempts; one case burned 11,537s.

### 4. Evidence level
All implementation facts `[OBSERVED]`. Memory ceiling `[UNKNOWN]` — the single most
important unmeasured number in the system.

### 5. Constraints imposed
Deployment shape constrains everything upstream: if a render must be pooled, §6
cannot be a pure function; if planning must survive a restart, §2 needs durable jobs;
if the instance is 512 MB, §6's engine choice is forced.

### 6. Open questions
- Peak RSS per render; concurrent ceiling.
- Is the renderer co-located or a separate service?
- What is the durable job substrate?
- Who is the deployment for — a portfolio link or real users? (changes auth, storage,
  and quota answers)

### 7. Solution directions
Playwright base image with pinned fonts; pooled browser; bounded worker concurrency;
durable jobs; Postgres; an access gate; renderer as a service; a paid provider for
measurement stability.

---

# Cross-cutting problems

Not assignable to one stage.

- **CC1 — Judgments recorded as inert fields.** `[INFERENCE, high confidence]` A1, A2,
  A6, A7, Q1, Q6, Q8 are one disease: something is computed, recorded, and depended on
  by nothing. Stages §1–§6.
- **CC2 — "A failure that looked like a success."** Approval accepting an
  undeliverable plan; `satisfied: true` beside 4 phantoms; the old 2-of-17 coverage
  bug; templates silently dropping blocks. **Lexo's §10.3 names six instances of
  exactly this class** and its I7 is the invariant we lack. Stages §3–§7.
- **CC3 — Verification is self-referential.** The artifact is checked against the
  plan; the plan against nothing. §0 + §2 + §4.
- **CC4 — Everything is synchronous.** Agent, engine and service are all sync. This is
  why parallelism (O1) is invisible as an option: the code shape forbids it. §2, §4,
  §6, §8.
- **CC5 — No reuse of any derivation.** `inputs_hash` written, never read. §2, §4, §7.
- **CC6 — Free-tier reliability contaminates every measurement.** §2, §4, §8.
- **CC7 — Latency, not tokens, is the cost.** `[INFERENCE]` 11 calls and ~89k tokens
  per module is cents; **857 seconds and a Chromium process are the real bill.** The
  50/day cap that dominates our thinking is a free-tier artifact, not a property of
  the architecture.

---

# Cross-section dependencies

Where changing one stage materially moves another.

| Change here | Forces reconsideration of |
|---|---|
| **§6 renderer engine** | §5 block vocabulary (what's drawable), §2 feasibility (what can be promised), §8 memory floor, the two template-authored probes, golden-image testing |
| **§6 live measurement dropped** | §2 extent must be computed, not observed; §3 loses the shortfall signal it already ignores |
| **§0 ingestion added** | §1 (a source is a stated constraint), §2 (read vs derived structure, traversal), §4 (grounding), §7 (source versions must persist) |
| **§2 typed plan decisions** | §3 approval gains preconditions; §4's brief changes shape; §7 needs per-decision storage, not one JSON blob |
| **§2 sections represented** | §4 stops being one-call-per-concept; §5 assembly gains real work; §6 templates gain a level |
| **§4 units parallelised** | §8 concurrency ceiling and provider rate limits; §6 if renders also parallelise |
| **§4 density measured** | §2 extent becomes computable; §3's negotiation becomes honest |
| **§7 Postgres** | §2 memoization becomes possible; §8 gains a dependency; concurrency protection arrives |
| **§8 pooled browser** | §6 can no longer be a pure function; process lifetime becomes a design concern |
| **§8 auth / multi-user** | §7 ownership and isolation; §0 private sources; §2 shared-asset promotion |
| **§3 approval preconditions** | §2 must produce a plan that can satisfy them; §6 must declare drawability before approval, not after |

**The two tightest couplings**, worth naming because they are easy to miss:

1. **§6 → §2.** The renderer decides what can be drawn. Planning promises
   representations. Today planning records the shortfall and approval ignores it. Any
   change to either side breaks the other's assumption.
2. **§4 → §2.** Generation is the only source of real density. Extent is the number
   the user approves against. **They are currently unconnected**, which is why A4 is
   off by ~3×.
