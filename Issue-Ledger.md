# Issue Ledger

Every problem, wrong assumption, and late discovery from building this product the
first time. It exists for one purpose: **the rebuild should pay for these once, not
twice.**

Scope: all four working sessions, from the first "what is this product" conversation
to the current curriculum → module → PDF flow. Compiled by extracting all 269 human
turns from the session transcripts, plus the design documents that were themselves
written as incident records (`Runtime-Dependencies.md`, `Plan-Fulfilment.md`,
`Visual-Requirement-Routing.md`).

**Status markers:** `[fixed]` · `[open]` · `[deferred]` · `[never-addressed]`

The last one matters most. `[never-addressed]` means it was identified and then the
build moved on — those are the ones that will bite the production version.

---

## 1. Product definition — alarms that changed the product, not the code

These arrived as *product* discoveries, each one invalidating work already done.

1. **The product was mis-framed as a quality problem.** `[fixed]`
   - Initial framing: "LLMs are bad instructional designers, build a better generator."
   - Actual problem: **there is no intermediate representation between "what should
     this contain" and "write the words."** Reframed as a compiler for pedagogy.
   - Cost: the entire first `Product-Bible.md` was discarded.

2. **"Completeness" was the wrong word; the real need is scope confidence.** `[fixed]`
   - The first thesis assumed an external authority (syllabus, exam blueprint).
   - Broke on "I have an SDE interview tomorrow" — no syllabus, still a real scope
     decision.

3. **Difficulty axis was wrong.** `[fixed]`
   - Assumed: cheatsheet vs textbook vs roadmap is the hard axis.
   - Actual: law vs medicine vs signal processing vs GATE syllabus — **domain
     modelling, not output modelling.**

4. **The artifact-type list was three different axes wearing one hat.** `[fixed]`
   - The original list mixed:
     - document kind (Q&A, long notes, revision sheet, cheatsheet)
     - depth (research-level)
     - visual treatment (diagram-heavy)
     - length (short, long)
   - Resolved to `Artifact: Long notes / Template: Diagram-heavy` — now LOCKED in
     `Product-Semantics.md` §2.

5. **Document "kinds" had to be discovered by mechanism, not named.** `[fixed]`
   - Naming produced 10+ plausible categories. Forcing candidates through
     *reader operation / unit / relation structure / completion condition* produced
     **five** real jobs.
   - **Q&A died** as a category — it decomposes into `retrieve known material` +
     content source + answer-withholding. The rule that killed it is worth keeping:
     *a category dies when its identity is fully explained by existing jobs plus
     independent axes.*

6. **Budget was treated as a user input for far too long.** `[fixed]`
   - Users do not know that Electrical Machines needs 100 pages. Asking them pushes
     an expert planning decision back onto the learner — the exact thing the product
     exists to prevent.
   - Split into **capacity** (user, optional, binding when stated) vs **extent**
     (system, derived, an *output* of planning).
   - Corollary that had to be stated separately: budget allocation is **never**
     `capacity ÷ members`. Now LOCKED in `Architecture.md` §11.

7. **"Shortest" as the definition of good was wrong.** `[fixed]`
   - Shortest optimises away examples, intuition, and the explanations of *why*.
   - Replaced with **minimum sufficient treatment**: sufficient + efficient +
     effective, with correctness as a gate rather than a trade-off.

8. **Sufficiency splits in two, and they fail independently.** `[fixed]`
   - `structural sufficiency` — the dependency chain is connected.
   - `practical sufficiency` — the learner can act without unacceptable omission
     consequences.
   - Found via the databases example: a document can be structurally complete and
     practically unsafe (transactions omitted).
   - Produced a fifth budget move: **mark the gap** — and the caution that warning
     about a missing concept is *not* teaching it.

9. **Omission consequence is not a node attribute.** `[open]`
   - `risk(transactions)` is meaningless; `risk(node | target, context)` is not.
     Transactions are low-consequence for a local notes app, extreme for banking.
   - Candidate dimensions — severity, visibility, reversibility — were never
     validated against more than one domain.

10. **"Silence is freedom" had to be made a rule, because the default was wrong.**
    `[fixed]` — unmentioned ≠ forbidden. Not asking for diagrams must not mean no
    diagrams. Now LOCKED, `Product-Semantics.md` §3.

---

## 2. Architecture — things locked too early, and what broke them

The recurring failure mode: **a plausible design was marked LOCKED before a
discriminating test existed.** Every item below was caught by review, not by the
build.

1. **The decision taxonomy was mistaken for the execution pipeline.** `[fixed]`
   - Rev. 1 drew one line: Situation → Composition → Projection → Scope → Partition →
     Structure → Treatment → Draft → Render.
   - **The Indian Contract Act test broke it.** Backend development is unusually
     mechanism-heavy and gave false confidence in a sequential pipeline. The law case
     exposed source ingestion vs structural derivation, frame selection,
     authority-provided relevance, parallel work, and jointly-resolved decisions.
   - Result: **four structures, four different admission rules** —
     - decision taxonomy (what can independently be wrong)
     - execution topology (what must resolve jointly)
     - lifecycle/commitment (where a result becomes relied upon)
     - invalidation (what goes stale)
   - `Architecture.md` Appendix C carries a standing warning against regressing to a
     linear stage list. **Keep that warning in the rebuild.**

2. **Execution coupling was conflated with dependency coupling.** `[fixed]`
   - Structure and Treatment resolve jointly — but changing treatment must not
     invalidate a structurally valid dependency order.
   - Sharing a job ≠ sharing invalidation.

3. **Arbitrary numeric thresholds were invented as architecture.** `[fixed]`
   - "One round, tiebreak fixed" for backward edges.
   - "More than roughly three branches → adopt an agent framework."
   - Both were guards invented before the behaviour was known. Replaced with
     *conditions*, not counts.

4. **Composition/Projection "fixpoint" was conceptually right and operationally
   empty.** `[fixed]` — no convergence definition, no stopping condition, no answer
   for whether the shared asset mutates inside the loop. Split into a versioned
   shared asset + project-local exploration that reads and never silently writes.

5. **"Situation" was doing three jobs.** `[fixed]` — user evidence, interpretation,
   and *intake strategy* ("what should we ask next?") are different kinds of
   decision. Conflating them made intake a black box. This one came back to bite in
   §5 below.

6. **Identity was too coarse.** `[fixed in design]` `[never-addressed in code]`
   - Using composition node IDs for everything breaks: `Transactions` appears in
     multiple artifacts, at different depths, in multiple representations.
   - Design settled on five levels: asset version → concept → project instance →
     placement → block.
   - **The current code has none of this.** It never got past M4.

7. **Verification was declared "not a stage."** `[fixed]` — it produces PASS / FAIL /
   INSUFFICIENT EVIDENCE / REQUIRES REVIEW, and gates the candidate → committed
   transition. That is a lifecycle stage by any definition.

8. **Candidate vs committed was missing from the main pipeline.** `[fixed in design]`
   `[never-addressed in code]` — approvals, corrections, regeneration, return visits
   and branching cannot be expressed with stages alone.

9. **`invalidate` kept being read as `regenerate`.** `[fixed]` — production needs the
   dirty state to *exist*: corrections accumulate, regeneration is expensive, the
   user may change their mind again.

10. **Lifecycle state and freshness were one enum.** `[fixed]` — became a 2×2
    (candidate/committed × current/stale). `committed + stale` = superseded;
    `candidate + stale` = dirty. A four-value enum could not express both axes.

11. **Stack choices were marked LOCKED when the architecture didn't force them.**
    `[fixed]` — FastAPI, Postgres, `SELECT FOR UPDATE SKIP LOCKED`, Chromium. The
    architecture forces *properties* (durable job claiming; post-layout geometry
    measurement); system design picks the technology. Three levels now separated:
    **architectural invariant / system-design choice / implementation detail.**

12. **`inputs_hash` under-specified the input envelope.** `[fixed]` — hashing the
    explicit function arguments is not enough. Tool outputs, retrieved source
    versions, system instructions, asset versions and taxonomy version all affect
    output. Without the complete envelope, invariant 2 is not actually enforced.

13. **Build-Spec schema defects, caught in review before any code ran.** `[fixed]`
    - `decision → member → artifact_version → member` circular table references; no
      stated migration order.
    - `UNIQUE (member_id, ord)` on `artifact_version` allowed only **one** artifact
      version per member — a direct contradiction of Rev. 4.
    - The delivery transition (layout passes → artifact_version → delivery commitment
      → `delivered_at`) had no transaction boundary of its own.
    - Conditional decisions implemented as "stubs that throw infeasibility" instead
      of explicit **applicability** branches.

---

## 3. Representation — the deepest and least-finished problem

This is the issue the product was founded on, and it is **still not solved**.

1. **The document model was a hidden visual taxonomy.** `[open]`
   - A `Document` model derived from one coding PDF cannot represent biology.
     `code block / terminal / API diagram / stack diagram` are not universal.
   - The user's words: *"That means the model isn't actually deciding representation.
     The document model itself has already assumed what a document can contain."*

2. **Adding concrete diagram types is a trap, and was explicitly forbidden.** `[open]`
   - `VennDiagram`, `BiologyDiagram`, `NeuralNetworkDiagram`, `ChemistryDiagram`,
     `MathDiagram` — this makes the vocabulary domain-specific and silently
     constrains the LLM to a hardcoded collection of subject artifacts.
   - Required separation, still only partly built:
     - educational decision — "this concept needs a visual"
     - **semantic representation specification** — "show this as a containment
       relationship"
     - **realization capability** — generate an image / render an equation / draw a
       relationship diagram / place labels

3. **Some visuals cannot be deterministically constructed at all.** `[fixed]`
   - Structurally drawable (containment, sequence, comparison) → HTML/SVG from a spec.
   - Perceptual (a labelled small intestine, a real anatomical illustration) → needs
     an actual image; no spec produces it.
   - Resolved with the **perceptual-referent** escape hatch in `agent/contracts.py`:
     family E admits no realization, and `Callout.realizes = False` because text in a
     box asserts no geometry. `Representation-Boundary` Rev. 3 is FROZEN.

4. **`served: bool` hid two different failures.** `[fixed]` — "the requirement was
   met" and "the requirement was dropped" were indistinguishable. The requirement is
   an element; the figure is a **binding**; the unbound state prints and is useful.

5. **The benchmark PDF quietly became the product's taste.** `[open]`
   - Every generated PDF came out with the same cover, same theme, same pyramid
     diagram, because the first template was reverse-engineered from one uploaded
     module.
   - The user caught it: *"everyone knows a Venn diagram would have been a great fit.
     then why is it here?"*

6. **Templates silently discarded block kinds.** `[fixed]`
   - The model emitted `chips`; `study-notes.html.j2` had no branch for `chips`,
     `subhead`, `heading` or `stack`, and **no `else`** — so they vanished without
     error.
   - Class of bug: an `if/elif` chain over a discriminated union with no exhaustive
     fallback.

7. **Three templates still cannot draw the relations they are given.**
   `[never-addressed]` — `module-guide`, `night-lab` and `grimoire` have no
   realization for `is-part-of`, `causes`, or `associates-with`.

---

## 4. Planning and curriculum

1. **Page count as a partition rule.** `[fixed]` — splitting because a PDF is long
   produces *one artifact rendered across two files*, not two artifacts. Three
   boundaries must stay separate: **curriculum / artifact / file.**
   - Standing instruction, restated several times: *"Don't use page count, concept
     count, dependency count, or tool names as automatic rules. Use them only as
     evidence."*

2. **Forcing every request through an artifact menu contradicts the thesis.**
   `[fixed]` — "I need an SVM cheatsheet" names the artifact; "I want to learn backend
   development" does not. Artifact type is an input **when explicitly requested**;
   otherwise artifact composition is part of the proposed plan.

3. **"Runaway extent is a partition signal" was too strong.** `[fixed]` — a large
   member may mean a wrongly merged partition, or may mean genuine scale. Reason to
   reconsider, not proof.

4. **Concept bundles were too coarse.** `[fixed]` — frameworks and benchmarks arrived
   pre-bundled; splitting granularity took 22 concepts to 31.

5. **Intake provenance was ignored by the planner.** `[fixed]` — a user saying "from
   scratch" did not produce a foundations module until provenance was threaded
   through. LLM Foundations then correctly became module 1.

6. **Breadth follows `subject` richness, not the structure prompt.** `[fixed]` —
   investigated as a prompt problem; it was not. `relevance` cuts only when the
   situation gives grounds, and **0 exclusions is often correct**.

7. **Depth-vs-capability mismatch.** `[deferred]` — Module 5 promises comparison over
   concepts that the plan marks at depth `mention`. Diagnosed, never fixed.

8. **Planning still runs synchronously inside the HTTP request.** `[open]`
   - `POST /projects/{id}/plan` holds a connection for minutes.
   - Every interruption — a reload, a timeout, a dropped connection — surfaces as
     "Failed to fetch", which reads as a network error for a working server that is
     still thinking.
   - `backend/jobs.py` already solves this for module generation. It was never
     applied to planning.

---

## 5. The agent ↔ user conversation

1. **Planning ran on every message.** `[fixed]` — "why is the backend calling so many
   APIs on one click?" `create()` ran interpret **and** derive **and** plan. First
   useful question took **102.6 s**.
   - Split into `interpret` (reads only) → `decide` → `ask` (only for named axes).
     **102.6 s → 17.7 s.** `create()` and `answer()` now never plan.
   - Made a standing product requirement: *"when I type 'I need notes on VLSI' I
     should get the first useful question quickly. I don't care if curriculum
     derivation takes minutes after the required information has been collected."*

2. **A fixed questionnaire was explicitly rejected.** `[fixed]` — no hardcoded
   purpose → background → goal sequence. Questions are asked only for axes whose
   answers would materially change the result.

3. **`needs_subject` routed to the correction router.** `[fixed]` — ran corrections
   over a plan that did not exist. 15–30 minute failures in which the user's answer
   was never read.

4. **Duplicate utterances accumulated.** `[fixed]` — a failed turn still persisted the
   answer; each retry appended it again. One project reached **four copies** of the
   same answer.

5. **A stated constraint could be silently demoted.** `[fixed]` — a constraint bound
   to an axis whose reading was not `stated` fell back to `guessed`.

6. **Span verification accepted spans that denied their own reading.** `[fixed]` —
   `_supports()` now rejects them, negation-aware.

7. **Intake had no exhaustion condition.** `[fixed]` — `_close_intake` writes
   `exhausted: True` and `closed_because`, so a stalled intake ends deliberately
   rather than looping.

---

## 6. Generation and contract enforcement

1. **The generator could omit most of an approved plan and report success.** `[fixed]`
   - This is the headline failure of the whole build. Coverage was **2 of 17 units**
     and the run reported OK.
   - Fixed by generating per unit, verifying per unit, assembling, then a final
     document-level completeness check. Same model, same prompt: **17 of 17.**
   - `agent/fulfilment.py` is now the system's side of the contract:
     `UnitReport.satisfied` = generated **and** no concepts missing.

2. **A repair prompt made the model return the wrong object — twice.** `[fixed]`
   - `"Fix exactly this and reply with the corrected JSON object only"` next to a
     dotted path made the model return the *inner* object.
   - Fixed in `agent/generate.py`, and **the identical twin in `agent/plan.py` was
     missed** until it broke a real request. Both are now pinned by one test.
   - Lesson: a prompt defect is a code defect and needs the same duplicate search.

3. **Treatment rules were deliberately kept out.** `[deferred]` — `treatments_anticipated`,
   `treatments_produced` and `depths_required` are **observation only**; none can make
   a document unsatisfied. Explicit instruction: no procedure-execution or
   treatment-specific rules yet.

4. **Curriculum regeneration on module generation.** `[fixed]` — the approved
   curriculum is the source of truth; `agent/curriculum.py` derives a module-scoped
   plan without mutating it.

5. **Artifacts were written into the FileStore's own root.** `[fixed]` —
   `out/projects/` held both project JSON and generated artifacts. Moved to
   `out/artifacts/{project_id}/`.

---

## 7. Rendering and the engine

1. **The white band — four rounds, and the user was right every time.** `[fixed]`
   - Round 1: I claimed the figure crop was a screenshot boundary. It was real
     clipping; bleed was 6 mm, not the 4 mm I guessed.
   - Round 2: claimed fixed. The band had **moved** — 6.6 mm between header and
     content. My test sampled only row 0 and the last row.
   - Round 3: *"if lightmode can be 0px, why not in darkmode"* — exposed that a colour
     tolerance of 30 cannot detect white against `#F7F6FD` (distance **19**). Both
     themes had been identical all along.
   - Round 4: swept to `box = margin + 1mm`. The correct window is **~0.5 mm wide**.
   - **The durable lesson, now a test comment:** loose thresholds are worse than no
     test. Scan every row of every page and compare exactly.

2. **`@page { margin: 0 }` overrode Playwright's margin** → content collided with the
   header. `[fixed]`

3. **Cascade collision:** `.para { margin: 0 }` beat `.block`'s `margin-bottom` on
   source order, collapsing paragraph gaps. `[fixed]` — `margin-top: 0` only.

4. **One overflowing element on page 3 shrank page 1 by 9%.** `[fixed]` — Chromium
   shrink-to-fits the whole document. This is `layout_feasibility` in embryo.

5. **Jinja `b.items` resolved to `dict.items`.** `[fixed]` — `_MappingFirstEnvironment`
   removes the entire class (`keys`, `values`, `get`, `update`).

6. **Full-bleed page tint is impossible past page 1.** `[open, documented]` — Chromium
   neither propagates html/body background into `@page` margins nor lets
   `position: fixed` escape the content box. Proven with three separate experiments.
   Recorded as the first observed cost of choosing Chromium.

7. **A figure caption can separate from its figure at a page boundary.**
   `[never-addressed]` — Chromium ignores `break-after: avoid` on a flex container.

8. **JetBrains Mono ligatures rendered `==` as one glyph.** `[fixed]`

9. **Type was ~18% too large** against the benchmark. `[fixed]` — matched by
   characters-per-line, not by trusting extracted point sizes.

10. **Unknown archetype leaked `jinja2.TemplateNotFound`.** `[fixed]` — `TemplateGap`
    raised after an explicit existence check.

---

## 8. Models, providers, and the free tier

1. **The free tier is the single largest source of lost time in this project.** `[open]`
   - OpenRouter free: **50 requests/day**, 20/min. Exhausted repeatedly; a full day's
     work has ended at `X-RateLimit-Remaining: 0`.
   - `ProviderRefused` 429s across several models in one sampling run — six runs, six
     refusals.

2. **An 8-minute 500 that was blamed on the wrong cause.** `[fixed]`
   - `POST /projects` → 500 after **518 s**.
   - Prime suspect was `OutputTruncated` against a 32000-token ask. Measured actual
     output: **interpret 2074 / derive 2882 / plan 2567.** The theory was wrong.
   - Real cause: **intermittent provider faults**, retries exhausted.
   - The user's instruction — *"Don't let it 'fix' based on the prime suspect"* — is
     what prevented a wrong fix from shipping.

3. **Provider errors escaped as HTTP 500 with a stack trace.** `[fixed]` —
   `NoProviderConfigured` → 503; `ProviderUnavailable` / `ProviderRefused` /
   `OutputTruncated` / `ValueError` → 502, with a sentence instead of a traceback.

4. **Small models fail span verification entirely.** `[open]` — `verified = 0`, every
   axis falls to `guessed`, the whole flow collapses to `needs_subject`. Measured
   across `gemma-4-26b`, `nex-n2.5-mini`, `lfm-2.5-2.6b`.

5. **Picked a model by its name.** `[fixed]` — `nemotron-3.5-lightning` is a reasoning
   model: **297.8 s and 881.1 s**, 11,438 output tokens, and it still failed.

6. **A model was withdrawn from the free tier mid-build.** `[fixed]` —
   `openai/gpt-oss-120b:free` 404'd between the fact-check and the first call.

7. **Free-tier output is wildly non-deterministic.** `[open]` — run 1: 4 pages, 5,113
   tokens, excellent. Run 2: a **stub** — 627 tokens, one section. Runs 3–4: 502s.

8. **Provider JSON-schema mode was deliberately rejected.** `[fixed]` — free models
   don't support strict schema output, and relying on it makes the pipeline
   provider-specific. Validate-and-retry instead.

---

## 9. Runtime dependencies and environment

Fully documented in `Runtime-Dependencies.md`; summarised because it cost three
rounds of diagnosis.

1. **Chromium is not installed by `pip install playwright`.** `[fixed]`
   - `pip` installs the *driver*; the browser is a separate ~700 MB download.
   - Every PDF render failed. Planning, intake and approval all worked — so it
     surfaced **only at the last step of a paid generation**.

2. **There are two browser builds, not one.** `[fixed]` — headless `launch()` runs
   `chromium_headless_shell`, not full Chromium. A check that stats only full
   Chromium reports success while rendering fails.

3. **A shell check proved nothing about the server.** `[fixed]`
   - The agent's sandbox had `%LOCALAPPDATA%` redirected into an app container. Every
     check it ran reported a complete install; the backend, outside that container
     against the same path string, correctly reported it missing.
   - **`/health` is authoritative, because the answering process is the one that
     renders.**

4. **Two prerequisites fail *silently*, which is worse.** `[open]`
   - **Fonts are a property of the render host.** Different metrics → different line
     breaks → different pagination — and pagination is artifact-owned truth.
   - **Three of four templates fetch webfonts at render time** from
     `fonts.googleapis.com`. On a host with no egress they stall to timeout and then
     render with fallbacks.

5. **The engine is not network-pure the way the boundary test implies.** `[open]` —
   `tests/test_boundaries.py` forbids `engine/` from importing `httpx`, `requests` or
   `socket`, and `Build-Spec.md` §8 leans on that purity to justify golden-image
   testing. The Python package makes no network call — **but the browser it drives
   does.**

6. **Uvicorn's 5-second keep-alive killed multi-minute turns.** `[fixed]` — closed the
   connection underneath a working request; the browser reported "Failed to fetch."
   Now `timeout_keep_alive=900`.

7. **`--reload` killed in-flight turns.** `[fixed]` — editing a file while the user's
   server was running ended their turn mid-call. Now off by default, with a warning
   when enabled.

8. **Port collisions produced an unreadable Windows socket error.** `[fixed]`

9. **`out/` is resolved relative to the working directory.** `[fixed]` — running from
   `backend/` would have created a second empty `out/` and come up with **none** of
   the 31 existing projects.

---

## 10. Frontend

1. **Duplicate React keys from LLM output.** `[fixed]` — `key={o.topic}` on
   `wontCover`; the model emitted the same topic string twice. Any list keyed on
   model-generated text has this bug.

2. **`Content-Disposition: attachment` broke the inline PDF preview.** `[fixed]` —
   inline by default, `?download=1` to force.

3. **Sessions were not projects.** `[fixed]` — leaving the page lost the work; there
   was no way back to the same curriculum; 25 modules could not be downloaded
   together. Converted to a durable Project as the primary object.

4. **The generation page re-showed the approved plan.** `[fixed]` — each module's plan
   now belongs to that module's card.

5. **UI looked like every other AI app.** `[fixed]` — rebuilt with an authored
   identity and *contextual* self-aware copy: different per screen, never the same
   joke twice, never humour on an actual error.

---

## 11. Multi-user and production — identified, never built

Everything here was raised in review and consciously postponed. **This is the section
the rebuild exists for.**

1. **Security and multi-tenancy.** `[never-addressed]`
   - A project belongs to a user. Shared assets may be global. Uploaded sources may
     be private. Generated artifacts may contain private information.
   - Needed: project isolation, source access control, shared-asset visibility,
     artifact permissions. **There is no auth in the current build at all.**

2. **Idempotency.** `[never-addressed]` — `inputs_hash` memoisation helps derivation;
   it does **not** solve command idempotency. Untested: duplicate user submission,
   API retry, worker retry, duplicate commit, duplicate approval, render retry,
   worker crash after generation but before commit.

3. **Cancellation.** `[never-addressed]` — a user changes scope while 40 expensive LLM
   calls are running. Correctness is unaffected; **cost, latency, capacity and UX are
   not.** No cancellation semantics exist.

4. **Partial project failure.** `[never-addressed]` — members 1–2 pass, 3 fails, 4
   waits. Can the user download 1 and 2? Retry only 3? Approve 3 manually? Abandon the
   set? The lifecycle model implies answers; the product semantics never stated them.

5. **Concurrent discovery and promotion.** `[never-addressed]` — two projects propose
   competing corrections to the same shared composition asset. Promotion requires a
   situation-free adjudicator. None exists.

6. **Source and version provenance.** `[never-addressed]` — a decision depends on
   source A v3, source B v8, composition asset v12, syllabus v2026, model X, prompt Y.
   Answering *"what exactly was this artifact based on?"* six months later needs a
   real lineage record.

7. **Version authority.** `[never-addressed]` — when a user says "my March document,"
   is that artifact history, the file they downloaded, or the authoritative answer?
   `delivered_at` and `superseded_by` exist in the schema; the **semantic rule does
   not**.

8. **Is `project` even the right top-level object?** `[never-addressed]` — a user
   returns six months later with a different goal on the same subject. Same project
   with reuse, or new project? This decision propagates into persistence and history.

9. **Contested or evolving subject structure.** `[never-addressed]` — backend
   development was an unusually stable test domain. Subjects whose structure depends
   on jurisdiction, school of thought, or year were never modelled. Composition is
   keyed by subject × frame in the design; nothing implements frames.

10. **Postgres is declared and unused.** `[open]` — `psycopg[binary]` is in
    `pyproject.toml`; `migrations/0001_init.sql` is written and **unapplied**;
    `FileStore` (one JSON file per project) is what actually runs. Concurrent writes
    from two requests to the same project are unprotected.

---

## 12. Process — how the build itself went wrong

Not code defects. These are the ways the *work* failed, and they repeated.

1. **Fixing on the prime suspect without confirming it.** `[fixed by instruction]`
   - The 518-second 500 blamed on truncation. Measured tokens disproved it.
   - The rule that saved it, now worth institutionalising: **name the exception from
     a traceback or a reproduction. Nothing below that step is worth doing.**

2. **Invalid reproductions treated as evidence.** `[fixed]` — ran
   `agent.plan.interpret` without importing `backend.config`, got
   `NoProviderConfigured` in 0 s, and nearly reported it as the cause. The real run
   took 58 s and succeeded.

3. **Reading the wrong field and nearly asserting a false mechanism.** `[fixed]` —
   probed `a.get('materiality')` on an `AxisVerdict` that has `material`. Got `None`
   and almost built a conclusion on it.

4. **Weak and tautological tests that passed while the defect was present.** `[fixed]`
   - `assert any(not cls.realizes ...)` — always true.
   - Two versions of the white-band test passed with a 6.6 mm band on screen.
   - **A test that cannot fail is worse than no test, because it ends the search.**

5. **Fixing one site of a duplicated defect.** `[fixed]` — the repair prompt existed in
   `agent/generate.py` and `agent/plan.py`. Only one was fixed; the other broke a real
   request later.

6. **Editing files while the user's server was running.** `[fixed]` — killed their
   in-flight turn.

7. **Heredoc escape mangling corrupted source files repeatedly.** `[fixed]` — `\n\n`
   inside a Bash heredoc became literal newlines and produced
   `SyntaxError: unterminated f-string literal` in `backend/api.py` **twice**. Use the
   editing tools, not shell heredocs, for source.

8. **Analysis noise mistaken for findings.** `[fixed]` — comma-splitting reported
   `"maturity"` and `"shared memory)"` as unbacked capability clauses; `LLMs` failed
   to match `LLM Fundamentals` for want of a plural fold.

9. **Building infrastructure before the product.** `[fixed]` — the original Build Spec
   opened with database, schema and job infrastructure. Rejected in favour of
   product-first milestones: *"build something real first, reach a usable milestone,
   then deepen it."*

10. **Every significant architectural correction came from review, not from the
    build.** External review caught the Template→Spec collapse, the missing Document
    Plan layer, source authority, sequential-document assumptions, the severity/
    blocking policy, artifact-version cardinality, and the premature LOCKs.
    **The rebuild should assume this is structural, and schedule the review.**

---

## 13. What the rebuild should carry forward

Not issues — the things that were *earned* and should not be re-derived.

- The four structures and their four separate admission rules.
- Decision ≠ job. Execution coupling ≠ dependency coupling.
- Status × freshness as a 2×2.
- Invalidation produces dirty state; it does not regenerate.
- Commitments are self-describing snapshots, not pointers.
- Reconstruction ≠ replay. Retention replaces reproduction for delivered bytes.
- Capacity (user, optional) vs extent (derived). Never `capacity ÷ members`.
- Correctness is a gate; purpose is the arbiter; silence is freedom.
- Structural vs practical sufficiency, and `mark the gap` as a real budget move.
- The representation boundary: assertion preservation, the honesty table, and a
  family that admits no realization.
- Per-unit generation with a document-level completeness check — the single change
  that took coverage from 2/17 to 17/17 on an unchanged model.
- Exact comparison in visual tests. Every row, every page, no tolerance.
- Diagnostics are evidence, never automatic rules.
