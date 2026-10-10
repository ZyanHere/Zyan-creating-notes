# MyNotes V2 — System Architecture

**Rev. 5 — fourth correction pass. FROZEN component set; see §K for what is and is not
frozen.** Derived from the nine section
investigations (`S0`–`S8`), the cross-section dependency map (`V1-Pipeline-Map.md`), the
measured defect ledger (`V1-Measured-Issues.md`) and the frozen domain model
(`Domain-Model.md` Rev. 4.1).

**Not in this document:** APIs, database tables, prompts, code, UI, implementation.
Technology is named where it constrains the shape; nothing here is a schema.

**Evidence key** — `[OBSERVED]` in V1 code/spec · `[MEASURED]` in the 11 records or a bench
run · `[INFERENCE]` reasoning · `[UNKNOWN]` unmeasured.

---

## Rev. 5 — what changed and why

Three findings. **All three accepted, none stale, nothing to revert** — the first pass where
that is true, and the reason §K now declares a freeze.

| | Finding | Status |
|---|---|---|
| **#1** | D17 has leases but no **fencing**. A lease expiring does not prove the old worker stopped, so a slow worker can return after a successor committed and perform a late state transition | **Accepted, and it closes a hole I had not seen.** Uniqueness prevents two rows; it does not prevent a *late overwrite of one row*. Fixed with a **claim epoch** plus **write-once** commits — and write-once is what makes Document identity-by-envelope sound at all (see #3) |
| **#2** | G6's table says Artifact Store loss leaves *"plans, documents"* working, while the prose says *"plan view and artifact delivery survive every failure except the Decision Store"* | **Accepted.** Direct contradiction, in two places. Same error class as Rev. 2's *"NO Task dependency"*: an over-broad survival claim stated once and not checked against its own table |
| **#3** | Document construction identity omits the **builder version**, unlike section envelopes (model + prompt) and the render environment (renderer build + template hash) | **Accepted.** It is an inconsistency not to apply a rule I applied in the two analogous places. Cost is ~0: Document construction is a pure `dom` function with no model call, so an extra build is free |

### Why #1 and #3 are the same problem seen twice

Both are about **what pins a result's inputs**. Without write-once commits, an envelope does not
determine its content — so a Document keyed by *"the exact set of section envelopes"* would not
be keyed to the content it was built from. Fencing makes envelope → content immutable, and that
is what makes the Document key meaningful. Adding the builder version then pins the last input
that was floating.

---

## Rev. 4 — what changed and why

A third review raised 14 findings. **Ten accepted, three stale, one a correct finding aimed at
the wrong line.** One of the ten makes me revert part of Rev. 3: I over-corrected C6.

### Three quote Rev. 2, not Rev. 3

| | Claim | Fact `[verified by grep]` |
|---|---|---|
| **#1** | D5 still says *"the declaration's version enters the derivation environment, so a renderer upgrade makes every committed plan's feasibility statement stale"* | **Not in Rev. 3.** D5's only mention of that sentence is the correction naming it: *"Rev. 2 said … which its own definitions forbid"* |
| **#2** | J2 says *"Decided here (D1–D16)"*, so D17 is referenced but undeclared; and D17 covers decisions, not the memo | **Both wrong.** J2 reads **D1–D18**. D17's guarantee block reads *"at most ONE DecisionVersion per (decision, envelope)"* **and** *"at most ONE Content Memo entry per section envelope"* |
| **#9** | *"Task admission cap bounds queue depth"* is conceptually wrong | **Already corrected in Rev. 3.** G5 lists **in-flight Task cap · backlog bound · per-user quota** as separate rows, with the explicit note that Rev. 2's version *"was false"* |

### But #1 found a real residual, one section away

D5 and E4 are consistent. **D15 was not.** One sentence survived the Rev. 3 edit:

> *"…and its feasibility statement differs, which E4 surfaces as staleness against the new
> declaration version."*

That is the contradiction, in the third of the three places it lived, and I missed it while
fixing the other two. A correct finding pointed at the wrong line still finds the bug — fixed
in D15.

### Rev. 3 over-corrected C6, and #14 is how it shows

Rev. 2 said every approved shortfall becomes a `Reference`. Rev. 3 split that into `Reference`
for `perceptual-referent` and *"report the gap as a marked omission"* for `parallel-state`. The
review asks the obvious question: **what block is a "marked omission"?** The vocabulary is
`Prose | StructuralClaim | Presentation | Reference`, and `MarkedGap` is *front matter* for cut
concepts, not a block — and a `parallel-state` concept is **covered**, not cut.

Working it through: `Reference` *"names something it cannot show"*, which is exactly what
reporting an undrawable swimlane is. So **both cases carry a `Reference`.** Rev. 3 conflated
two different questions:

```
which BLOCK carries it?      Reference, in both cases
is the gap PERMANENT?        yes for family E (cannot preserve assertions)
                             no for parallel-state (licensed, merely unbuilt)
```

The disposition belongs in the plan's disclosure and the capability roadmap — **not** in the
document. So Rev. 2 was right about the block, Rev. 3's review was right about the reason, and
Rev. 4 states both without inventing a block.

### The other nine, all applied

**#3** memo reservations need a durable coordination primitive; object storage alone does not
provide one (D10, D17) · **#4** template identity is a **content hash**, which V1 already
computes — `_template_version` with the docstring *"A CSS edit repaginates; Rev. 4 §4 requires
that to be visible in the render environment"* `[OBSERVED]` (D15) · **#5** P2 scoped: Integrity
is the only refusal over a **plan**; renderer availability is an **execution precondition**
(P2, C5) · **#6** the app baseline was a *bench script*, so I measured the real one — **65.4 MB
peak** with FastAPI, pydantic, agent, engine, uvicorn and httpx loaded, not 50 MB; the 512 MB
conclusion survives and T1 is now labelled a candidate (G2, H) · **#7** capacity expressed as a
formula with the measured project as one instance (G1, G3) · **#8** **429 / Retry-After split
from terminal 4xx** (F2) · **#10** domain functions return, orchestrators persist (B, D) ·
**#11** template selection given an owner (D, D15) · **#12** Document construction identity
defined (C5, D17) · **#13** execution is **at-least-once**, stated plainly (D17).

---

## Rev. 3 — what changed and why

A second review raised 14 findings. **Eleven are accepted in substance, one is a labelling
fix, two are stale, and one is largely already addressed.** Two of the proposed *resolutions*
are replaced with better-sourced ones, both settled by reading `agent/treatment.py`.

### Two findings quote Rev. 1, not Rev. 2

| | Claim | Fact |
|---|---|---|
| **#4** | T1 still says *"Postgres (or blob table)"*, contradicting D10 | **Not in Rev. 2.** That phrasing was Rev. 1's and was removed *because* D10 forbids it. Rev. 2's T1 reads `Postgres + object storage`, and D10 states plainly that the Document, Artifact and Memo stores want object storage while the Decision Store wants Postgres `[verified by grep]` |
| **#9** | D6 still labels the latency win `[MEASURED]` | **Not in Rev. 2.** D6 reads *"**The speedup is `[INFERENCE]`, not `[MEASURED]`** — Rev. 1 mislabelled it"*, and no `[MEASURED]` appears on any latency claim `[verified by grep]` |

### One is largely already addressed — #7

D11 already separates the keys and states that cross-project reuse is sound *"only when the
reuse key matches"*, and the reuse key includes **source versions**. The review's example —
Contract Law with the Indian Act vs UK legislation — is therefore handled: different sources,
different key, no sharing.

What is fair is the **wording**: calling `(subject, frame)` a *"domain key"* implies a
shareability that the reuse key denies. There is only **one** key. Fixed in D11.

### The one remaining architectural bug — #1, and it is worse than stated

The lease stops two workers running the same *Task*. It does not stop two **different** Tasks
whose steps share an envelope: two projects on the same subject both deriving
`SubjectStructure` (exactly the case D11's sharing exists for), or a lease expiring while the
original worker is still alive.

And the damage is not only a duplicate paid call. **Two versions under one envelope make
`stale(projection)` fire spuriously**, because a recorded dependency now has a newer version —
so a duplicate derivation would mark the entire downstream plan stale. That is a correctness
bug. Fixed by making `(decision, envelope)` **unique** and the `MISS → deriving` transition an
**atomic reservation** (D17).

### Two resolutions replaced, both settled by `agent/treatment.py`

**#5 — the Capability Declaration was too narrow, and V1 already has the missing half.** Rev. 2
described only Representation-Boundary §2's relation → geometry table, which cannot answer
*"can you serve `parallel-state`?"*. `agent/treatment.py` is the other table, and its docstring
states the division Rev. 2 collapsed:

> *"What is NOT here: which diagram. Selecting a realization is decision 11, at the demo gate,
> over Representation-Boundary Rev. 3's honesty table. **This module only says that prose will
> fail, and in which of the seven ways.**"*

Two tables, and the bridge is already a field — `Capability.licenses`. See D5 and D18.

**#6 — *"every approved shortfall becomes a `Reference`"* was wrong, and the proposed
per-need fallback table is under-determined.** The same file decides it: exactly **two of
seven** failures are unserved, **for different reasons**, and the difference sets the response.

| unserved because | `treatment.py`'s own note | response |
|---|---|---|
| **impossible in principle** — `perceptual-referent`, family E | *"the only one that cannot preserve assertions: a generated figure adds content the document never asserted"* | `Reference` — X1, and the only legal form |
| **licensed but unbuilt** — `parallel-state`, licenses *"sequence · swimlane · timeline"* | *"Two actors evolving at once currently come out as prose, which is the substitution §13 forbids"* | **report the gap**; the repair is to build the licensed realization |

And §13's rule, quoted in that docstring, is the governing one: *"if we cannot produce
anatomical figures, the correct response is to **report the limitation**, not to substitute a
diagram that answers a different failure."* See C6.

### The other nine, all applied

`Feasibility` is computed, so the Capability Declaration is neither a dependency nor in any
envelope — which removes #2's contradiction rather than choosing a horn (D5, E4) · Read API
wording and the failure claim scoped per read (B, G6) · slot formula labelled an initial
sizing model (G3, H) · in-flight cap separated from backlog bound and per-user quota (G5) ·
Task Store loss made conditional on D17 (B, G6) · what is synchronous in the Source Registry
stated (C1) · *"better attempt"* defined from V1's actual rule (C5) · recovery costs expressed
as sums rather than constants (F4, G6) — **the same error class corrected in G1 and then
reintroduced**.

---

## Rev. 2 — what changed and why

A review of Rev. 1 raised 23 findings. **All 23 are accepted in substance.** Two of the
proposed *resolutions* are wrong and are replaced with better-sourced ones, and one finding
understates the error it identifies. Three findings were reduced by measurement rather than
argument.

### The three that were settled by evidence, not opinion

| | Rev. 1 claimed | Now |
|---|---|---|
| **8-render extrapolation** | *"2 GB → ~8 renders"*, untested past 3 | **Measured through 8.** Memory is linear-to-slightly-sublinear: 254 · 244 · 233 · 237 MB per render at concurrency 1 · 3 · 6 · 8. 8 renders = 1,897 MB + 50 MB app. The extrapolation was right — **and the measurement found a constraint Rev. 1 missed entirely: CPU.** See G3 |
| **Per-module cost** | *"11 calls / 670 s per module"* | **Wrong, and worse than the review said.** `generate-01`'s project had **8 modules** (`concepts_per_module = [5,3,4,5,7,4,9,3]`) and planning was **6 calls once for all eight** `[MEASURED]`. Rev. 1 counted planning per module, so it over-stated a project's cost ~1.8×. The review's own corrected formula repeats the error — it attaches planning to a module too. See G1 |
| **"No two relations may share one geometry"** | my invented rule | **Wrong, and so is the proposed replacement.** `Representation-Boundary.md` §2's honesty table shows two relations sharing a geometry *legitimately* — `is-subset-of` and `is-part-of` are both nesting with **different reading conventions** — and states the rule directly: *"honesty is a property of the (relation, geometry, reading convention) **triple**, not of the geometry alone."* The review's *"same form + different labels is fine"* is also wrong, because the table's whole basis is that geometry asserts independently of labels. See D8 |

### The one architectural bug

**Generation was not resumable.** Rev. 1 said *"the decision store is the checkpoint"* while
also putting section results in the Task Store and calling that store *"disposable · loss
costs 0."* A generated section is not a `DecisionVersion`, so those three statements could
not all hold. Fixed with a **durable Content Memo store** (D14) — which is the same argument
V1 already made one level up when it retained the Document JSON.

### Ordered list of corrections

**Must-fix, all applied:** durable section results (D14) · dependency invalidation and the
`stale` / `reusable` split (E4) · Integrity reports *decisions implicated*, not *the*
decision (E5) · separate LLM and render concurrency caps (D16) · capability is per-template
and the template is pinned before Feasibility (D15) · `ScopeTier` envelope corrected (C1) ·
`SubjectStructure` identity function stated (D11) · one benchmark definition (G2) · 512 MB →
**1** render (H) · 8-render capacity measured (G3) · section-count-dependent capacity (G1) ·
approved-shortfall fallback is a `Reference` (C5).

**Should-fix, all applied:** honesty check is table-driven (D8) · Task Store loss ≠ zero cost
(B) · artifacts via signed URL above a threshold (C8) · `Authority` producer named (D) ·
attempt deadline vs Task budget (F1) · structure+projection joint only on derivation (C3) ·
the 4× generation win relabelled `[INFERENCE]` (D6) · logical kind separated from deployment
(B, D).

### On the review's largest conceptual point

It is right, and precisely so. P5's envelope was credited with five jobs. Scoring them:

| Claimed | Verdict |
|---|---|
| memoization | ✅ works as stated |
| Task idempotency | ✅ works as stated |
| restart of **decision** work | ✅ works as stated |
| staleness | ⚠️ **conflated two relations.** Reuse must key on dependencies **and** environment; approval-blocking staleness must key on **dependencies only**, or a prompt-version bump would invalidate an approved plan that is not wrong. Split in E4 |
| generation checkpointing | ❌ **does not work.** Needs a separate durable store (D14) |

Three of five stand unchanged; one needed splitting; one was false. That is the overreach,
and it is now named where it occurs rather than in the principle.

---

## 0. Two domain questions, and one contradiction already fixed

### OR-1 and OQ-3 do not block architecture

Rev. 4 of the domain model listed both as *required before architecture*. Having derived the
architecture, **that was too strong**, for specific reasons.

**OR-1** (may a concept belong to more than one `Section`?). The arithmetic that forced `⊎`
at the module level does not exist one level down: `derive_extent` sums pages **per module**
over its concepts `[OBSERVED]`, so a concept in two modules double-counts. Extent is never
computed per section, so section overlap breaks no arithmetic. Architecture consumes
**totality** only, which is what lets generation fan out per section and still guarantee the
module's coverage. The rule that must not assume exclusivity is stated in D6.

**OQ-3** (source as axis or stated reference). Both mechanisms are already expressible:
`Constraint.Target` admits `source`, and `Source` is an authoritative entity carrying
claim-specific `Authority`. A supplied syllabus and *"prepare me for GATE 2026"* both route
through the same two capabilities — **source resolution** and **constraint binding**. What is
open is intake's question vocabulary, a product decision.

### The contradiction found while deriving Rev. 1, now carried into the model

Rev. 4 had `superseded(a) ⟺ another Artifact exists for the same Module, created later`,
beside *"the same Document under a different template is a different artifact."* Both cannot
hold — a second template would supersede the first, when the two are alternatives. Now
(`Domain-Model.md` Rev. 4.1, CF-8):

```
superseded(d)  ⟺  a later Document exists for the same Module
superseded(a)  ⟺  a later Artifact exists for the same (Document, template)
```

Keyed `(Document, template)` and deliberately **not** the full render environment: a
re-render after an engine or font upgrade **does** supersede; a different template does not.

### `Job` is taken

The domain model uses **`Job`** for the five document jobs. This document uses **`Task`** for
a durable unit of background work.

---

# A. Architecture principles

Eight, each derived from measured or observed evidence.

### P1 — A judgment is real only if something depends on it

The pattern that appears seven times across §1–§7: *V1 records judgments as free-form fields
that nothing downstream depends on or checks.* `job` · `feasibility` · `partition.covers` ·
`capability_unbacked` · `diagnosis` · `inputs_hash` · `freshness` `[OBSERVED ×7]`.

**Consequence:** every component names what consumes its output. Applied to the invariants
themselves in E5: **an invariant a type can make inexpressible should not be a runtime
check** — seven of the fourteen are enforced by construction.

### P2 — Refuse on arithmetic, disclose on capability, ask a human for judgment

The domain model's three acts (§1), and H1/H2/H5. `approve()` has **no `raise` and no `if`
except idempotency** `[OBSERVED]`; `serves_everything: False` in 6 of 8 plans, 5 reached
approval, **all 5 approved** `[MEASURED]`.

**Consequence, scoped in Rev. 4:** **Integrity is the only component that may refuse a
*plan*.** That is distinct from an **execution precondition** — renderer unavailability refuses
a *generation Task* before it spends a model call (C5), and a `Task` budget refuses further
attempts (F1). Rev. 3 said *"exactly one component may cause an automatic refusal"*, which the
review correctly called false: those two also refuse.

```
refuses a PLAN            Integrity, and only Integrity — deterministic, H5
refuses EXECUTION         renderer unavailable · Task budget exhausted · backlog full
                          none of these is a judgment about the plan's content
```

The distinction matters because H2 must keep holding: a **representation shortfall** is
disclosed and never refused, while a **missing renderer** stops work that would otherwise be
paid for and discarded.

### P3 — Small, independently checkable promises

*"Each call is answerable for a small, checkable promise … **the system, not the model, is
answerable for the artifact matching the plan**"* — the change that took coverage from
**2/17 to 17/17** on an unchanged model `[OBSERVED]`.

**Consequence:** the unit of generation is a `Section` with its own concept list, its own
check, and — once D14 makes it durable — its own checkpoint.

### P4 — Identity is assigned; never positional, never derived from mutable content

S14. V1 keys generation by `_job_key(project_id, index)` and addresses a PDF by
`slugify(title)` `[OBSERVED]`; `ml-weekend` went 5 modules → 3 in one correction
`[MEASURED]`, so both are live hazards.

### P5 — Every derivation is addressed by its inputs, and this solves *three* things

`inputs_hash` is written into the decision row and **never read** `[OBSERVED]`; `commit_hash`
already proves the mechanism works `[OBSERVED]`.

**It gives** memoization, Task idempotency, and restart of decision work — one mechanism
instead of three. **It does not give** generation checkpointing (content is not a decision →
D14) and it does not by itself give staleness, which needs two distinct relations (E4).
Rev. 1 claimed all five; the correction is the substance of Rev. 2.

### P6 — No long work in a request; long work is durable, bounded and resumable

Three constraints from §8 that are one requirement wearing three hats: Chromium wants
bounded concurrency, a 323s generation wants to survive a restart, a 342s plan turn wants out
of the request path `[OBSERVED + MEASURED]`. One case burned **11,537s** `[MEASURED]`.

### P7 — Infrastructure declares capability; the domain reads it

The capability table lives in `agent/treatment.py` `[OBSERVED]` — the wrong side of the line.
**And capability is per-template**, which Rev. 1 missed: study-notes realizes 4 geometries
over all 5 relations; the other three realize **1** geometry over 2 relations `[OBSERVED]`.

### P8 — A conditional capability is never silently skipped

`Build-Spec.md` §1, locked. §0's finding: *"unknown whether an authority exists"* is **the
actual V1 state for all 10 cases** `[OBSERVED]`, so *"no source exists"* and *"we never
asked"* are indistinguishable.

---

# B. Logical components

Five planes, chosen where **failure domains and durability requirements differ** — not where
code would naturally divide. Every box carries its **kind**, because *"component"* invites a
service and §H is the only place deployment boundaries are decided. **T1 runs all of this in
one process.**

Kinds: **`dom`** domain logic (pure, no I/O) · **`orch`** orchestration ·
**`infra`** infrastructure adapter behind a port · **`store`** · **`decl`** versioned data.

**A `dom` component never writes.** Rev. 3's table said `Document Builder dom → writes
Document`, which contradicts the definition. The boundary, stated once and applying to every
`dom` row below:

```
dom    takes values, returns values.  Document Builder RETURNS a Document;
       Integrity RETURNS violations; Extent and Feasibility RETURN numbers and shortfalls;
       Sufficiency RETURNS a verdict; Template Policy RETURNS a template id.
orch   persists what dom returned, in the order F4 requires, and owns the transaction.
```

This is worth being strict about now: the next layer is technical design, and a `dom` function
that can reach a store is one that will be given a store.

```
┌─ CONVERSATION PLANE ─────────────── synchronous · product SLA ≤ 30 s ───────────┐
│  Conversation API  orch   appends Utterances, starts Tasks, owns nothing         │
│  Intake            orch + dom   situation · job · sufficiency policy (pure)      │
│  Read API          orch   plan view · Task status · artifact access              │
│                           NO model call · NO dependency on Task EXECUTION, on a   │
│                           live worker, or on the Model Gateway.  (Task STATUS     │
│                           does read the Task Store — Rev. 2's "NO Task            │
│                           dependency" was wrong wording, not a wrong design.)     │
└──────────┬───────────────────────┬─────────────────────────────────┬────────────┘
           │                       │                                 │
┌─ DECISION PLANE ─────────────────▼─────────────────────────────────┼────────────┐
│  Source Registry    orch+infra   tier · source kind · structure    │            │
│  Subject Knowledge  orch         SubjectStructure, envelope-keyed   │            │
│  Planner            orch         projection·scope·partition·        │            │
│                                  sections·ordering                  │            │
│  Extent · Feasibility  dom       computed, never authored           │            │
│         └────────────┬───────────────────────────┘                  │            │
│                      ▼                                              │            │
│        ┌──────────────────────┐      ┌─────────────────────┐       │            │
│        │  INTEGRITY    dom    │◄─────┤  Commitment   orch  │       │            │
│        │  pure function of a  │      │  one per approval   │       │            │
│        │  decision set.       │      │  exact versions,    │       │            │
│        │  No model. No state. │      │  keyed by member.   │       │            │
│        │  Reports DECISIONS   │      │  Refuses on stale   │       │            │
│        │  IMPLICATED, never   │      │  or on violation    │       │            │
│        │  the repair.         │      └─────────────────────┘       │            │
│        └──────────┬───────────┘                                     │            │
└───────────────────┼──────────────────────────────────────────────────┼───────────┘
                    │ reads the per-template Capability Declaration    │
┌─ PRODUCTION PLANE ▼────────────────────── asynchronous · bounded ────┼───────────┐
│  Generator        orch   fan-out per Section · 2 attempts · better wins          │
│  Document Builder dom    whole-or-nothing · front matter from the plan ·         │
│                          block validation (S6, X1, approved-shortfall rule)      │
│  Renderer         infra  merge + table-driven honesty check, then print          │
└──────────┬────────────────┬──────────────────┬──────────────────────┬───────────┘
           │                │                  │                      │
┌─ PERSISTENCE PLANE ▼──────▼──────────────────▼──────────────────────▼───────────┐
│                                                                                 │
│ Decision Store    Content Memo     Document Store   Artifact Store   Task Store │
│ utterances        section results  immutable        immutable        leases     │
│ sources           immutable        re-render input  content-addr.    attempts   │
│ versions          envelope-keyed   object-shaped    object storage   progress   │
│ commitments       DERIVED          DERIVED          AUTHORITATIVE    PROCESS    │
│ AUTHORITATIVE     (D14, new)       as delivered bytes                           │
│ ─────────────────────────────────────────────────────────────────────────────── │
│ loss: FATAL       loss: ~65 s      loss: 323 s      loss: ~3.4 s     loss: in-  │
│                   per section      per module       per document     flight     │
│                                                                      progress   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─ CAPABILITY PLANE ──────────────────────────────────────────────── decl ─────────┐
│  Model Gateway  infra   attempt deadline · Task budget · typed failures · jitter │
│                                                                                  │
│  Capability Declaration, PER (renderer build × template)   decl   TWO TABLES     │
│    ① NEED COVERAGE     ProseFailure → {served, weight, licenses}                 │
│         the seven of Architecture §13 · read by FEASIBILITY and EXTENT            │
│    ② HONEST REALIZATION relation → permitted (geometry, reading convention)       │
│         Representation-Boundary §2 · read by the MERGE-TIME CHECK                 │
│    bridge: `licenses` names ①'s realization family, which ② then constrains       │
│    pinned in the Commitment for REPRODUCIBILITY · never a dependency · never a    │
│    prompt                                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

  Work Coordinator  orch — leases Tasks; enforces THREE independent caps
  (Task admission · model-call concurrency per provider · render slots)
  plus the DB pool. Holds no domain state.
```

**Task Store loss is not free, and Rev. 1 said it was.** With D14 in place it costs
**in-flight progress and leases**, and **with D17 in place** it costs no model calls, because
a completed step is durable in the Decision Store or the Content Memo before the Task record
is allowed to matter. The honest statement: *recoverable without corrupting domain truth, and
without re-spending completed work — the second half conditional on D17's reservation
semantics.* Rev. 2 asserted the second half unconditionally, which the duplicate-derivation
race made false.

**Why the Read API depends on so little:** a provider outage must not make a delivered PDF
unreadable. §8 measured **7 network failures across two baseline attempts** `[MEASURED]`; the
provider is the least reliable thing in the system and delivery is what a user is least
willing to lose. The claim is **scoped per read** (G6): none of the three reads depends on the
Model Gateway, the Work Coordinator or a live worker. Each still needs its own store — plan view
the Decision Store, artifact delivery also the Artifact Store, Task status also the Task Store —
and an Artifact Store loss is recoverable by re-render from the Document.

**Why Integrity is its own component:** it runs at three moments — after planning, after
**every correction**, and at approval — and §3 identified corrections as *the mechanism that
creates orphans* `[OBSERVED]`. A check inside the planner runs once, in the wrong place.

---

# C. End-to-end flows

## C1 — Intake (synchronous)

```
append Utterance                                   authoritative · durable · no model
   │
   ├─ subject strong? ──► Source Registry: ScopeTier
   │      envelope = (subject, purpose, target_capability, supplied source versions)
   │      NOT (subject) alone — see below
   ▼
Intake: derive Situation + Job
   │   envelope = (transcript, model, prompt versions, taxonomy version)
   ▼
Sufficiency  dom · deterministic policy over the readings
   │   askable ∧ weak ∧ material, priority order, budget 4
   │   ScopeTier = documented → do not request a syllabus  ◄── Foundation §3.2, LOCKED
   ├─ asking non-empty → Ask (1 call) → questions in the response
   └─ else             → state = ready
```

**`ScopeTier` is keyed by subject × situation, and Rev. 1 keyed it by subject alone.** That
contradicted the frozen model directly — *"a property of subject × situation"* — and it is
exactly the false-reuse hazard U1 names. The evidence is in §0's own corpus: *"Operating
Systems for B.Tech 5th semester"* is **documented**; the same subject for general curiosity
is **asserted**. Purpose changes the tier, so purpose is in the key. Cross-project reuse
survives only when the whole key matches, which is much rarer — and correct.

**What the Source Registry does *synchronously* is exactly one thing: classify.** The
synchronous path determines the **tier** and the source's **kind** — one model call over the
subject, the purpose and whatever source metadata already exists. It does **not** fetch, crawl,
search, download or extract. Anything that touches the network or a file is a **Task**, which
is why D13 calls tier determination *the architectural floor, not ingestion*.

This matters for OQ-3's second mechanism. *"Here is my syllabus"* supplies a `Source` whose
bytes arrive by upload, and extraction is a Task. *"Prepare me for GATE 2026"* names a source
the system must **resolve**, and resolution is a Task too — so the intake turn that receives
it records a `Constraint` naming an unresolved `Source` and returns; it does not block on
resolution. **No external I/O ever sits inside a conversational turn.**

**The 30-second bound is a product SLA, not a measured fact.** Rev. 1 treated it as
measured. The measurement is *one* figure — first useful question **17.7s** after the split
that made `create()` and `answer()` never plan `[MEASURED]` — and §1 also records **1–2 calls
per answer** `[OBSERVED]`, so a two-call turn plausibly exceeds 30s. No p95 exists
`[UNKNOWN]`. The mitigation is unchanged and is what makes the SLA safe to hold: a breached
deadline fails the turn **retriably**, and a retry costs one call, because the `Utterance` is
already appended.

## C2 — Correction (Task)

```
append Utterance                                       synchronous, immediate
   ▼  Task(correct)
Router: 1 call, measured 97 s   →  reading · targets · replacement payloads
   ▼
for each TARGETED decision: new DecisionVersion, dependencies recorded
   untargeted decisions: NOT re-derived, and NOT silently still valid  ──► E4
   ▼
recompute stale(v) over the dependency graph
   ▼
INTEGRITY over the current decision set
   ▼
report: reading · claimed vs actual · unclaimed drift · violations · WHAT IS NOW STALE
```

**V1 problem solved:** §3's central finding — *"a correction replaces whole decision objects
with no cross-check"* — and both measured corrections changed a structural relationship
unnoticed, in opposite directions `[MEASURED]`. `generate-01`'s correction took phantoms
7 → 4 **incidentally** while answering a content complaint, and nothing noticed either the
repair or the four that remained.

**Rev. 1's gap, now closed:** it said untargeted decisions are not re-derived and stopped
there, leaving Integrity to inspect a set that could be internally consistent and
semantically obsolete. Staleness is now computed and reported in the same act. See E4.

## C3 — Planning (Task)

```
Task(plan)   each step: envelope → reusable? reuse : derive → write DecisionVersion

  1  SubjectStructure     (subject, frame, source versions, model, prompt, taxonomy)
  2  Projection           + situation version, job version
  3  Scope                Coverage{depth, RepresentationNeed} · Cut{concept, cons., when}
  4  Partition            Module identities ASSIGNED
  5  Sections             per module — member-keyed
  6  Ordering             per level — over identities, with a basis
     ─────────────────────────────────────────────────────────────
  7  Extent        dom    calibrated density · never authored
  8  Feasibility   dom    reads the Capability Declaration OF THE SELECTED TEMPLATE
  9  INTEGRITY     dom    violations + decisions implicated
```

**Steps 1 and 2 are joint only when step 1 actually derives.** Rev. 1 called this
*"architecturally joint"* and that was wrong once reuse exists:

```
structure MISS  →  derive structure + projection together
                   (V1's reason: "relevance must judge every concept the same pass derived")
structure HIT   →  projection consumes the stored structure; no joint call possible
```

And the property that *matters* is not the packaging — it is **S3** (`judged =
structure.concepts`, equality), which Integrity checks either way. `unjudged` was **0 in
every record** `[MEASURED]`, so jointness is the heuristic that achieved the invariant, not
the invariant. Hard-wiring it would have been P1's error inverted: treating a means as the
end.

**Everything else about call packaging is a prompt-level choice bounded by output size**,
because A5 is real: `derive_v1` returned truncated JSON in **2 of 10 cases** `[MEASURED]`,
and the same failure already forced V1's landscape/body split once `[OBSERVED]`. The
architecture supplies the bound and the typed failure, not the packaging.

## C4 — Approval (synchronous)

```
1. stale(v) over the committed candidate set   →  any stale? REFUSE, list them
2. INTEGRITY                                   →  violations? REFUSE, list decisions
                                                  implicated, do not choose a repair
3. Feasibility shortfalls                      →  attach as DISCLOSURE, never refuse
4. mint Commitment: exact DecisionVersions, keyed by member
   pinning: models · prompt versions · taxonomy version · source versions ·
            selected template + its Capability Declaration version
   idempotent on the version-set hash
```

**Measured cost:** 0.04s plus deterministic checks `[MEASURED]`. §3: *"the cheapest stage in
the product. Anything added here is nearly free in latency terms."*

**Why stale versions cannot be committed.** A `Commitment` is *"the system is answerable for
producing this"* — the contract reading the domain model chose. Being answerable for a plan
whose scope was derived from a superseded `job` is precisely CC2's *"failure that looked like
a success."* This is a **separate precondition from Integrity**: a stale set can be perfectly
internally consistent.

**Invariant 8 is now complete.** V1's `decision_environment` carries 2 of the 5 required
fields `[OBSERVED]`; the pin list above carries all five plus the template.

## C5 — Generation (Task, fan-out)

```
precondition: RENDERER AVAILABLE                   ◄── engine operational? Chromium present?
              NOT "can it draw every approved need" ◄── that was disclosed at C4 and
              checked BEFORE any model call: "the model call between the two takes
              minutes and is billed"  [OBSERVED]
   ▼
orders ← one per Section of this module, from the Commitment
         each order carries its concepts, depths, AND the RepresentationNeed
         plus any DISCLOSED SHORTFALL for those needs        ◄── new, see below
   ▼
fan out, bounded by the MODEL-CALL cap (not the render cap)
   per section: envelope (commitment, section identity, situation version, model, prompt)
       Content Memo hit  → reuse, 0 calls
       RESERVED by another worker → wait on that reservation, 0 calls   ◄── D17
       miss → RESERVE atomically, then up to 2 attempts,
              KEEP THE BETTER, write to the CONTENT MEMO STORE
   ▼
ALL sections present?
   ├─ no  → Task INCOMPLETE. Per-section reasons recorded. NO Document.
   │         Resuming costs ONLY the missing sections — because the memo is durable.
   └─ yes → Document Builder
```

**Two terms Rev. 1 collapsed into one, which the review correctly caught as a contradiction
with H2:**

| | Means | If absent |
|---|---|---|
| **Renderer availability** | is the engine operational | **refuse before the model call** — V1's `browser_missing()`, deliberately narrow: *"it must never be the reason a healthy run does not happen"* `[OBSERVED]` |
| **Representation capability** | can it draw *this* need | **disclose at plan time, never refuse** (H2) |

**The fallback for an approved shortfall — corrected in Rev. 3.** Rev. 2 said every approved
shortfall becomes a `Reference`, generalising X1 beyond its evidence. `agent/treatment.py`
shows why that is wrong: **exactly two of the seven prose failures are unserved, and for
different reasons.** See C6 for the two rules.

Either way the shortfall must reach the writer, which closes a measured gap: `anticipates`
has **zero matches** in `generate.py` and `unit_v1.md` `[OBSERVED]`, so V1's representation
judgment never arrives where it would be acted on. Approving with open eyes is meaningless
unless generation knows what was approved.

**"Keep the better attempt" is deterministic and costs nothing extra** — Rev. 2 left it
implicit, which invited the reading that a judge decides. V1's rule: `check_unit(order,
candidate)` returns `concepts_missing`, and the kept attempt is the one covering **more of
the section's assigned concepts**, by normalized substring match `[OBSERVED]`. No model call,
no judge, no change to the cost or latency model. The reason is recorded and survives: *"a
retry that covers less than the first would otherwise make asking again actively harmful."*
Note what this does **not** measure — depth, treatment or extent, all of which the plan
promises and nothing enforces (§4's table). That is OQ-1's territory, not a scoring choice.

**A deliberate behaviour change against V1.** V1 produces a document with a missing unit,
*"recorded as ungenerated, and the reason travels with it"* `[OBSERVED]`. Under S12 an
incomplete Document is not a Document, so V2 produces none. V1 could not afford that rule
because resuming meant re-spending all five calls; with D14 it costs the missing section
only. **The mechanism is what makes the invariant affordable.** The failure mode V1's comment
protects — *"same symptom, opposite fix"* — is preserved by keeping per-section reasons on
the Task.

**Trade-off:** a user wanting four of five sections gets nothing until the fifth succeeds.
Correct for a document whose claim is *what gets written is what you approved*; wrong for a
preview — so a preview would be a different, explicitly-partial object, not a relaxation of
S12.

## C6 — Document construction

```
front matter ← the PLAN, never the model
   "asking a model to restate them would let them drift from what was approved
    for no gain"  [OBSERVED]
   ▼
blocks per Section, in the Ordering's order — addressed by SECTION IDENTITY
   ▼
validate:  every StructuralClaim carries a Licence           ◄── S6, closes A7
           the perceptual-referent guard, kept VERBATIM      ◄── X1
           approved-shortfall rule, TWO CASES                ◄── below
   ▼
immutable Document, written to the Document Store
```

### The approved-shortfall rule

`agent/treatment.py` marks exactly **two of seven** prose failures `served = False`, and the
reason differs — which is what decides the response. Rev. 2 collapsed both into `Reference`.

**Rev. 4 separates two questions Rev. 3 fused: which block carries it, and whether the gap is
permanent.** The block is the same in both cases.

```
WHICH BLOCK          Reference, in both cases — it "names something it cannot show",
                     which is precisely what reporting an undrawable figure is.
                     NEVER Prose: prose is the carrier the need declared insufficient.
                     NEVER a StructuralClaim for that need: that is §13's forbidden
                     substitution.
IS IT PERMANENT      that differs, and it belongs in the plan's DISCLOSURE and the
                     capability roadmap — not in the document.
```

| Need | Why unserved | Permanent? |
|---|---|---|
| **`perceptual-referent`** licenses *"image"* | **Impossible in principle.** *"Representation-Boundary calls this family E and it is the only one that cannot preserve assertions: a generated figure adds content the document never asserted"* `[OBSERVED]` | **Yes.** X1: *"admits no realization; the only legal forms are a `Reference` carrying that licence, or a corrected licence"* — no build can change this |
| **`parallel-state`** licenses *"sequence · swimlane · timeline"* | **Licensed but unbuilt.** *"No realization exists. Two actors evolving at once currently come out as prose, which is the substitution §13 forbids"* `[OBSERVED]` | **No.** A swimlane or timeline would be honest; the repair is to *build* one, and the plan's disclosure should say so rather than implying a permanent limit |

**Why Rev. 3's version was wrong.** It said `parallel-state` should *"report the gap as a marked
omission"* — and *marked omission* names nothing in the block vocabulary. `MarkedGap` is
**front matter**, derived from `consequence.exclusions`, for concepts that were **cut**. A
`parallel-state` concept is **covered**; only one aspect of it is undrawable. So Rev. 3 invented
a block by implication. Rev. 2's answer — `Reference` — was right about the block; Rev. 3's
review was right that the *reasons* differ. Both hold, at different layers.

**The governing rule is §13's, quoted in `treatment.py`'s own docstring:**

> *"If we cannot produce anatomical figures, the correct response is to **report the
> limitation**, not to substitute a diagram that answers a different failure."*

So the validation is: a concept whose `RepresentationNeed` was **disclosed as unservable and
approved anyway** may carry **no realizing `StructuralClaim` for that need** — and in
particular may not fall back to `Prose`, since prose is the carrier the need declared
insufficient. The two legal forms above are exhaustive **for the two failures currently
unserved**; a third unserved failure would need its own row, and **which** row is a product
decision, not an architectural one (U14).

Rev. 2's error is worth naming: it took a rule the domain model states for *one* licence and
applied it to a class. The review was right to reject the generalisation; its own proposal —
a fallback defined per need — is under-determined without the impossible/unbuilt distinction,
which is what actually chooses.

A7 measured **36 departures, 6 undiagnosed, `clean: false`, and the PDF rendered**
`[MEASURED]`. §5 pinned the cause to one field's optionality — the guard fires only
`if self.realizes and self.diagnosis is not None`, so *absence* passes.
Required-with-escape (`unlisted:<name>`) is the resolution, with precedent in the same file;
V1's argument against a closed enum is good and survives: *"an enum would make the one
interesting reading impossible — a model that needed a failure the taxonomy does not list."*

## C7 — Rendering and artifact creation

```
merge (Jinja, StrictUndefined) → HTML        measured 38 ms · ~1% of a render
   ├─ MERGE-TIME checks, no browser:
   │    unrendered block kinds          ← the template emitted the marker
   │    realization pairing IN SOURCE ORDER  ← fixes the pop(0) misattribution
   │    HONESTY: each (relation, geometry, reading convention) triple is a
   │             permitted pairing in Representation-Boundary §2's table   ◄── D8
   ▼
render slot (bounded by min(memory budget / 240 MB, vCPU)) → Chromium
   → bytes + overflow + scale                ← the two probes that DO need layout
   ▼
Artifact: content-addressed (Document identity + render environment + bytes)
          immutable · written AFTER the Document exists
```

**Two probes leave the browser.** `_UNRENDERED_PROBE` reads `.unrendered` elements *the
template emitted* and `_REALIZATION_PROBE` reads `data-realization` attributes *the template
wrote* `[OBSERVED]` — *"asking a browser is a round trip to learn something authored two
steps earlier."* Moving them **fixes a real bug**: `_representation_report` does
`drawn.pop(0)` against a list that omits unrendered blocks, so with three relation blocks
where the second is unrendered, **block 2 is reported with block 3's geometry** `[OBSERVED]`
— and the triggering condition is normal in three of four templates.

*(`V1-Pipeline-Map.md`'s O4 headline says "3 of 4 probes"; its own body and §6's table both
say **two**. Two is right; the headline is a slip.)*

## C8 — Delivery

```
authorize (Decision Store read)
   ├─ artifact ≤ threshold → stream inline, content-disposition set deliberately
   └─ above, or under load → short-TTL signed object-storage URL  ◄── Rev. 2
export
   ├─ small curriculum → package synchronously (8 modules × ~235 KB ≈ 1.9 MB, measured)
   └─ large            → Task, delivered as an artifact of its own
ordering from the COMMITTED Ordering, never from filenames
```

The signed URL preserves the failure-domain property that motivated inline bytes — a
signature is a store read plus a hash, with no gateway and no Task dependency — while not
proxying every PDF byte through the API. **TTL must be short**, because the URL is a bearer
token for private content once issued; that is the trade the redirect introduces.

V1's export reasoning survives: separate files, not a merged PDF, because *"each module is
its own document with its own cover and page numbering, and merging them is a render-engine
job … not a packaging one"* `[OBSERVED]`. The `NN-` prefix becomes unnecessary — artifacts
are content-addressed and ordering comes from the commitment, so nothing depends on filename
sort order.

---

# D. Component responsibilities and ownership

| Component | Kind | Owned state | Writes | May decide | May NOT decide |
|---|---|---|---|---|---|
| Conversation API | orch | — | `Utterance` | nothing | anything derived |
| Intake | orch + dom | — | `situation`, `job` versions | what to ask, when to stop | scope, structure, coverage |
| Sufficiency policy | **dom** | — | — | askable · blocking · priority · budget | the readings themselves |
| Source Registry | orch + infra | source bytes, extracted structure, versions | `ScopeTier`, `SourceStructure`, source **kind** | the tier; the source's **kind**; what it contains | the `Authority` **profile** — see below |
| Subject Knowledge | orch | — | `structure` versions | what exists in the subject | what is in play |
| Planner | orch | — | projection·scope·partition·sections·ordering | coverage, depth, grouping, order | whether the plan is admissible |
| Extent, Feasibility | **dom** | — | — | nothing — they compute | what to do about the result |
| **Integrity** | **dom** | **none** | nothing | **refusal**, and which decisions are **implicated** | which one to change, and how |
| Commitment | orch | commitments | `Commitment` | that this version set is in force | anything derived |
| Generator | orch | — | section results → **Content Memo** | what is written | the plan, front matter, section identity |
| Document Builder | **dom** | — | **returns** a `Document`; the Generator's orchestration persists it | nothing — assembles and validates | any content |
| **Template Policy** | **dom** | — | **returns** a template id | which template this situation gets | anything about content; and it is not user-selectable (locked) |
| Renderer | infra | browser processes | `Artifact` | geometry, pagination, fonts | what is said; which relation holds |
| Capability Declaration | **decl** | versioned, per **(renderer build × template)** | — | ① which `ProseFailure`s are served, and each one's weight and licensed family · ② the honest (relation, geometry, convention) pairings | whether a plan may proceed; what to do about a shortfall |
| Model Gateway | infra | in-flight calls, budget ledger | nothing durable | when an attempt is over, when a Task is over | content |
| Work Coordinator | orch | Tasks, leases | Task state | scheduling, **three caps**, resumption | anything domain |
| Stores | store | the data | — | nothing | nothing |

**Who produces `Authority`** — Rev. 1 left a domain field with no architectural producer,
which is the V1 anti-pattern it exists to remove. `Foundation.md` §3.1 already answers it and
the answer is a clean split:

```
source KIND          a judgment — declared by the user or classified by a model
      ↓
Authority PROFILE    a LOCKED LOOKUP, not a judgment
                     syllabus: high scope, low factual · textbook: the reverse
                     slides: high terminology · past papers: high assessment
```

So the Source Registry classifies; the locked table decides. That is why it *"may not decide
what a source is authoritative for"* and still leaves nothing unowned. §0's open question —
*"who assigns authority scores: declared, inferred, or asked?"* — narrows to **how the kind
is established**, which is a much smaller question.

**Three ownership rules worth stating:**

1. **Integrity owns no state and makes no call.** That is what makes H5 — *"refuse
   automatically only on a deterministic check"* — structurally true rather than a
   convention.
2. **The Renderer never learns the domain's types.** V1's `engine/` is test-forbidden from
   importing `agent/` `[OBSERVED]`; *"it renders whatever satisfies the shape."* That is why
   a template fix costs ~3.4s instead of 323s, and what makes an engine swap possible.
3. **The Capability Declaration is read by `Feasibility` and never reaches a prompt.** V1
   leaks it the other way: `anticipates` is the only channel by which planning learns what
   can be drawn, and the table describing the renderer lives in `agent/treatment.py`
   `[OBSERVED]`.

---

# E. State, invariants, and Task lifecycle

## E1 — Process state vs domain state

| Not domain state `[Domain §6]` | Where it lives |
|---|---|
| generation running / failed / retried | `Task` |
| Task identity, leases, attempts | `Task` |
| provider attempts, deadline and budget spend | `Task` + Gateway |
| **a section's generated content** | **Content Memo — durable, not a domain object** |

The last row is D14 and it is the Rev. 1 fix. A section result is **not** a `DecisionVersion`
and **not** a domain object — the model is explicit that `Content` is not an entity and a
partially-generated document is process state. But it is expensive derived data, and the
argument for retaining it is one V1 already made one level up: *"a template fix should not
cost another generation"* `[OBSERVED]`. One level down: **a section failure should not cost
the other sections.**

`status`, `freshness` and `supersession` remain **computed relations**, so no store holds a
mutable column for them. Not stylistic: V1 declares `freshness` and writes `"current"`
exactly once, forever `[OBSERVED]` — a mutable field nothing maintains is worse than a query.

## E2 — Task lifecycle

```
                   ┌──────────────────────────────────────────┐
                   ▼                                          │
  accepted ──► leased ──► running ──┬──► succeeded             │
     ▲                              ├──► incomplete ──────────┘  resume: only what
     │                              │                             the memo lacks
     │                              ├──► failed(transient) ────┐
     │                              └──► failed(terminal)      │ bounded retry,
     └──────────────────────────────────────────────────────────┘ jitter, within budget

  orphaned  ←  leased or running at coordinator start with no live lease  → re-run
```

**Re-running is cheap and needs no checkpoint table**, because two stores answer *"already
done?"*: the Decision Store for decisions, the Content Memo for sections. Rev. 1 claimed only
the first and used it for both.

**And *"already done?"* must be asked atomically** — D17. Rev. 2 said the stores are consulted
and never said what happens when two askers arrive together. The lease covers one Task; it
does not cover two Tasks whose steps share an envelope, and lease expiry does not stop the
original worker.

| Mechanism | V1 | V2 |
|---|---|---|
| memoization | `inputs_hash` written, never read `[OBSERVED]` | envelope lookup |
| idempotency | `JOBS.forget(key)` + `start(key)`, **positional** key `[OBSERVED]` | envelope lookup |
| restart, decisions | *"a restart loses running jobs"* `[OBSERVED]` | Decision Store lookup |
| restart, sections | not attempted | **Content Memo lookup** |
| staleness | `freshness` declared, never set `[OBSERVED]` | **E4, two relations** |

**Honest limit, unchanged:** the envelope makes *retries* free; it does not make *progress*
cheaper. Intake re-reads the whole transcript every turn (O7) `[OBSERVED]`, and the transcript
grows every turn, so the envelope changes every turn and caches nothing for real conversation.
Incremental re-reading remains an open optimisation.

And a reused result is *a* valid result, not *the* result — the model is non-deterministic.
That is the point of reuse, but it means B1's variance (29 → 42 concepts for one subject
`[MEASURED]`) is **frozen** by reuse, not reduced by it.

## E3 — Checkpoint granularity equals promise granularity

The unit that makes generation **correct** (P3: one call, one section, one checkable concept
list) is the unit that makes it **resumable** — but only once the unit's output is durable,
which is why Rev. 1's version of this claim was empty. Planning's checkpoint is one
`DecisionVersion`, which is the unit a correction targets. §4's instruction stands: *"any
redesign that makes generation one large call, or removes the per-unit check, re-opens the
2-of-17 defect."*

## E4 — Dependency graph, and the two staleness relations

The graph, which is architecture and not an implementation detail:

```
 sources ──┬──────────────────────────────┐
           │                              │
 subject ──┼──► ScopeTier                 │
 purpose ──┘        │                     │
                    ▼                     ▼
 transcript ──► situation ──► job    SubjectStructure ◄── subject, frame, sources
                    │           │         │
                    └─────┬─────┴─────────┘
                          ▼
                     projection
                          ▼
                        scope
                          ▼
                     partition ──┬──► sections (per module)
                                 └──► ordering (per level)
                          │
                          ▼
              extent   ·   feasibility ◄── Capability Declaration (per template)
```

Note what is **not** an edge: `job` does not feed `SubjectStructure`. Structure answers
*"what exists in this subject"* — situation-independent — so a `job` correction re-derives the
whole projection→ordering subtree and **reuses the structure**, which is the expensive call
and the one that truncates (A5). That is the graph earning its keep.

**Two relations, and Rev. 1 conflated them:**

```
reusable(v)  ⟺  envelope match: dependencies AND derivation environment
                → skip the call
stale(v)     ⟺  a recorded DEPENDENCY has a newer version
                → blocks a NEW Commitment; does not trigger regeneration
```

Why they must differ: reuse has to key on the environment or *"reproducible"* is false and
the Commitment's pin is a lie. But a **prompt-version bump** changes the environment without
making an approved plan *wrong* — so if staleness keyed on the environment too, every prompt
edit would invalidate every approved plan in the system. A decision that is `¬stale ∧
¬reusable` is entirely fine: it stays valid and nothing re-derives it.

**Uniqueness, which Rev. 2 omitted and which D17 supplies:** at most **one** `DecisionVersion`
exists per `(decision, envelope)`. Without that constraint two concurrent derivations produce
two versions under one envelope, and `stale(v)` — *"a recorded dependency has a newer
version"* — would fire on every dependent, marking a correct plan stale for no reason. The
uniqueness constraint is therefore not an optimisation; **`stale` is only well-defined
because of it.**

### The Capability Declaration is neither a dependency nor in any envelope

Rev. 2 said the declaration's version *"enters the derivation environment"* and then that a
renderer upgrade makes committed plans **stale** — which its own definitions forbid, since the
environment governs `reusable`, not `stale`. The review is right that those cannot both hold.
The resolution is not to pick a horn; it is that **the premise is wrong**.

`Feasibility` is a **computed fact**, not a `DecisionVersion`. The domain model puts it in the
computed column (C2), and V1 confirms it: `derive_feasibility` is a function, and `feasibility`
is **not one of the eight persisted decision kinds** `[OBSERVED]`. Computed facts are not
versioned and cannot be stale — they are recomputed on read. So:

```
Capability Declaration  is NOT a dependency of any decision
                        is NOT in any decision's envelope
                        IS pinned in the Commitment, for reproducibility of the
                        DISCLOSURE the user actually saw
```

**Consequently a renderer upgrade makes no decision stale.** It changes what `Feasibility`
computes *now*, while the pinned declaration version keeps the approved disclosure
reproducible. The difference between then and now is surfaced at the next point of decision —
a regeneration, or a render under a different template — as a **disclosure**, which is H2's
rule and not an invalidation. Rev. 2's *"fleet-wide invalidation event"* was simply wrong, and
in the alarming direction.

**And staleness does not regenerate**, which the domain model already fixed: *"invalidation
produces `stale`, never regeneration: corrections accumulate, regeneration is expensive, and
the user may change their mind again."* Re-derivation is a user-initiated Task, and the
envelope makes it minimal — the stale subtree has diverged envelopes, so re-running the
planning Task re-derives exactly it. **Nothing special-cases the subtree; the two mechanisms
agree by construction.**

## E5 — How each invariant is enforced, and who is implicated

P1 applied to the invariants: **an invariant a type can make inexpressible should not be a
runtime check.** Seven of fourteen are enforced by construction, which halves Integrity's
runtime surface.

| | Rule | Enforced by | Decisions implicated on violation |
|---|---|---|---|
| **S1** | `covered = ⊎ Module.covers` | runtime | `scope`, `partition` — **not unique** |
| **S2** | `in_play = covered ⊎ cut` | runtime | `projection`, `scope` |
| **S2b** | `judged = in_play ⊎ out_of_play` | runtime | `projection` — **unique** |
| **S3** | `judged = structure.concepts` | runtime | `structure`, `projection` |
| **S4** | `⋃ Section.covers = Module.covers` | runtime | `partition`, `sections` |
| **S5** | `Ordering` bijection over identities | runtime | `ordering` + the member producer; **usually a staleness symptom** |
| **S12** | Section ≥1 Block; Module ≥1 Section | runtime (plan + Document build) | `sections`, `partition` |
| S6 | every StructuralClaim has a Licence | **construction** — required field with escape | — |
| S7 | every Cut carries consequence + when | **construction** — `Cut` is one value object, so the violation is inexpressible | — |
| S8 | `Job` ∈ the five | **construction** — closed vocabulary | — |
| S9 | Artifact identified by content | **construction** | — |
| S10 | Commitment names exact versions, keyed by member | **construction** | — |
| S11 | `Utterance` append-only | **construction** — store | — |
| S13 | `DecisionVersion` immutable | **construction** — append-only | — |
| S14 | identity assigned, not positional | **construction** | — |

**Integrity reports violations and the decisions implicated. It does not choose.** Rev. 1
said *"names the decision that must change"*, singular, and the review is right that this is
usually not determined. `Scope.covered = {A}` with `Module.covers = {A,B}` is repairable by
removing B from `partition` **or** adding B to `scope`, and which is correct is a judgment
about intent.

This is the parked patch's own rule generalised: *"Reported, never repaired. Placing a
stranded concept would be a partition decision, and this layer must not make one."*
`[OBSERVED]` Extended: **choosing between two legitimate repairs is also a decision, and
Integrity must not make one either.** So approval refuses, names the implicated decisions,
and offers each as a re-derivation target — which P5 makes cheap.

## E6 — The operational chain

```
Utterance*  ──►  DecisionVersion*  ──►  Commitment  ──►  Document  ──►  Artifact
append-only     immutable, deps        exact versions,  immutable      immutable,
authoritative   recorded, envelope-    keyed by member, whole or not   content-
                addressed              env fully pinned  at all        addressed
                                                ▲
                                   Content Memo ┘  durable, derived, not in the chain
```

Read backwards, which is how support questions arrive:

| Question | Answerable by |
|---|---|
| *"why does my document say this?"* | Artifact → Document → Commitment → exact `DecisionVersion`s → the `Utterance` and `EvidenceSpan` behind each reading |
| *"is this still what I approved?"* | `stale(v)` over the commitment's versions |
| *"give me my March document"* | Artifact, retained and immutable; supersession is computed and writes nothing to it |
| *"what changed when I corrected it?"* | the targeted decisions' predecessors; untargeted ones are unchanged **by construction**, and any now-stale ones are listed |
| *"why is module 3 different?"* | it is not module 3 — below |

**Re-partitioning breaks the chain deliberately.** Under P4 a re-partition mints **new**
`Module` identities, so prior Documents reference modules no longer in the current partition.
Those documents become **historical**, not superseded. Matching an old module to a new one
would be a partition decision, and *"this layer must not make one"* `[OBSERVED]`. V1 does the
opposite: `_job_key(project_id, index)` silently re-points *"module 3"* at different content,
and `ml-weekend` went 5 modules → 3 in one correction `[MEASURED]`.

---

# F. Failure and retry model

## F1 — Two deadlines, not one

Rev. 1 had a single deadline and made *"deadline exhausted → no retry"* a rule, which the
review correctly questioned. Reaching an attempt ceiling is not evidence that the request is
permanently bad.

```
ATTEMPT deadline    one model call's ceiling
                    exceeded → TRANSIENT · retry if the Task budget allows
TASK budget         total calls, total wall time, total spend
                    exhausted → TERMINAL · no retry, and DISTINGUISHABLE from
                                a model failure
```

**This is the mechanism V1 has no equivalent of.** `TIMEOUT = 600s` ×
`_TRANSIENT_ATTEMPTS = 3` plus linear backoff means **a single call can burn ~30 minutes**,
and nothing above it can say *"give up after N minutes"* `[OBSERVED]`. That produced
`contract-act-authority`'s **11,537 seconds — 3.2 hours across 4 calls, ending in
`getaddrinfo failed`** `[MEASURED]`. The retry is right in principle; the missing piece is a
caller-side bound, and it belongs in the Gateway because that is the only place that knows
both the attempt count and the elapsed total.

## F2 — Failure classes that must stay distinguishable

§4's lesson in its own words: a swallowed exception produced a document reported only as
*"doesn't match what was approved,"* which reads as model omission when the cause was a spent
rate limit — ***"same symptom, opposite fix"*** `[OBSERVED]`. The taxonomy is the difference
between two opposite repairs, not bookkeeping.

| Class | Origin | Retry | Surfaced as |
|---|---|---|---|
| Provider unavailable | network, 5xx, attempts exhausted | yes — bounded, **exponential with jitter**, within budget | *"the provider is down; press again"* |
| **Rate limited** | **429, or any `Retry-After`** | **yes** — honour `Retry-After` where given, else backoff with jitter; within budget | *"throttled; waiting"* |
| Provider refused | **invalid request · content policy · billing disabled · hard quota** | **no** | the specific refusal |
| Attempt deadline | one call exceeded its ceiling | yes, within budget | counted as transient |
| Output truncated | partial JSON | once, **narrowed**; then terminal | *"this derivation is too wide"* |
| **Task budget exhausted** | cost ceiling | **no — terminal** | *"gave up after N calls / N minutes"* |
| Renderer unavailable | Chromium absent | no — refused **before** the model call | the install command |
| Render failure | crash, timeout | yes — the Document survives | a short re-render Task |
| Integrity violation | a deterministic check | **not a failure — a result** | violations + decisions implicated |
| Stale decision set | a dependency moved | **not a failure — a result** | what is stale, and offered re-derivation |

**Jitter is a real fix, not hygiene.** V1's backoff is linear with **no jitter**
`[OBSERVED]`, so concurrent callers hitting one overloaded provider retry in lockstep — and
the provider is measurably overloaded: **7 network failures across two baseline attempts**
`[MEASURED]`.

**Rate limiting is split out in Rev. 4, and "4xx" was too coarse.** V1 maps all 4xx to
`ProviderRefused` and does not retry `[OBSERVED]` — which is right for an invalid request and
**wrong for a 429**, the one 4xx that means *try again shortly*. This matters here more than
most places: the free tier is **20 requests/min** and D6's fan-out deliberately pushes several
calls at once, so 429 is not an exotic case — it is the expected consequence of the concurrency
this architecture adds. Treating it as terminal would make fan-out fail exactly when it works.

## F3 — Retry is per-Task, because the two memo stores make it equivalent

A per-step retry table is unnecessary: re-running reuses every completed decision **and every
completed section**, so per-Task retry has per-step cost. One policy.

**A failed attempt writes nothing**, so a retry genuinely re-does it, and *"keep the better
of two attempts"* `[OBSERVED]` means a restart mid-attempt loses at most one attempt — never
a better earlier result.

## F4 — Write ordering, which is the disaster-recovery story

```
Content Memo  ──before──►  Document  ──before──►  Artifact  ──before──►  referenced
```

Never the reverse. Recovery costs, from §B:

**Costs are sums over what was lost, not constants** — Rev. 2 wrote *"323 s per module"*, which
is the measured **5-section** module. That is the same error G1 corrected and then reintroduced
here: a 12-section module costs roughly `12 × 65 s`, not 323 s. Stated properly:

| Lost | Cost to recover |
|---|---|
| Task Store | in-flight progress and leases. **No model calls, conditional on D17** |
| Artifact Store | ≈ render time per document — **~3.4 s** measured for a 54-block document |
| Content Memo | ≈ Σ over the sections not yet built into a Document — **~65 s each** measured |
| Document Store | ≈ Σ over that module's sections — **~65 s × sections**; 323 s was a 5-section module |
| Decision Store | **unrecoverable** — utterances and commitments are authoritative |

That ranking is the domain model's authoritative / derived / computed table read as a
durability requirement, with the Content Memo inserted where Rev. 1 had a hole. **And the
Content Memo changes Document-Store loss materially**: a memo that still holds the sections
reduces the cost to a rebuild, so the row above is the worst case (memo collected), not the
normal one.

**And it is why V1's `_write` is the cheapest fix in the repository.** `write_text` truncates
before writing, no lock, no atomic rename `[OBSERVED]`: a crash mid-write leaves invalid
JSON, `_read` raises, and *"the project becomes unopenable"* — holding a plan that took
**342 seconds** `[MEASURED]`.

---

# G. Scaling model

Reasoned in calls, concurrency, memory, latency and failure domains. No user count appears.

## G1 — Unit economics, corrected

**Rev. 1's *"11 calls / 670 s per module"* was wrong, and the review understated it.** The
measured project — `generate-01`, agentic-ai-interview — had **8 modules**, with
`concepts_per_module = [5, 3, 4, 5, 7, 4, 9, 3]` = **40 concepts** `[MEASURED]`. Planning was
**6 calls / 342 s once, for all eight modules**. Generation was **5 calls / 323 s for module 1
alone** (5 concepts → 5 sections, 1:1 by construction — Q8).

So planning is **per project**, generation is **per section**, rendering is **per module**:

```
project  =  planning                      6 calls · 342 s      [MEASURED]
         +  Σ over sections   1 call each · ~65 s               [MEASURED]
         +  Σ over modules    1 render    · ~3.4 s              [MEASURED]
```

Rev. 1 counted planning eight times. The review's corrected formula — *"planning calls + 12
generation calls"* for a 12-section module — **repeats the same mistake** by attaching
planning to a module.

For the measured project (8 modules, 40 sections):

| | Calls | Wall |
|---|---|---|
| **Rev. 1's model** (11 × 8) | 88 | ~5,360 s |
| **Actual, fully serial** | **46** | ~2,970 s ≈ **50 min** |
| Sections parallel within a module, modules serial | 46 | ~890 s ≈ **15 min** |
| Modules and sections both parallel | 46 | ~410 s ≈ **7 min** |

The bottom two rows are why D6 matters, and they are `[INFERENCE]` — no concurrent generation
run has been made.

## G2 — One benchmark definition

Rev. 1 mixed three memory figures. One definition, used everywhere below:

```
process RSS  =  app baseline  +  n × browser incremental
app baseline          65 MB      fixed · NOT per render · MEASURED with the real backend
browser incremental  233–254 MB  per concurrent render
```

Measured this session on **16 logical cores**, sampled at 30–40 ms.

**The app baseline was re-measured in Rev. 4, because Rev. 3's 48–50 MB was the bench
*script*.** The review is right that a bench harness is not an application. With
`backend.api` imported — FastAPI, Pydantic v2, the whole `agent` and `engine` packages —
plus `uvicorn` and `httpx`, and after one Jinja merge:

```
peak RSS   65.4 MB        settled   45.8 MB
```

So the honest figure is **~65 MB peak, not ~50** — and the conclusion below does not change.
`psycopg` is not installed in V1's environment, so a connection pool is unmeasured; it is
conventionally 10–20 MB, which still leaves 512 MB at one render.

**Still unmeasured, and U3 stays open for it:** per-request overhead under concurrent load
(request buffers, simultaneous Pydantic validation), and everything about a real cloud
instance. A one-process import measurement is a floor, not a deployment number.

The browser figure is a **delta** against a noisy baseline (the machine's own Chrome held
~1.4 GB), which is valid as a delta and worth stating.

| concurrency | browser delta | **per render** | app | wall/render | **latency each** |
|---|---|---|---|---|---|
| 1 | 254 MB | 254 | 42 | 4.54 s | **3.43 s** |
| 3 | 731 MB | 244 | 48 | 1.34 s | 3.86 s |
| 6 | 1,396 MB | 233 | 48 | 0.84 s | 4.97 s |
| 8 | 1,897 MB | **237** | 50 | 0.70 s | **5.55 s** |

And the cost split within one render `[MEASURED]`:

```
merge (Jinja)               38 ms    ~1%
chromium launch + close  1,390 ms   ~41–55% depending on machine load
print + probes           remainder
```

## G3 — The two measured ceilings, and a third the measurement found

**Memory is linear, slightly sublinear, and now measured to 8** — so Rev. 1's extrapolation
was right, but it was luck rather than method, and it missed the constraint that actually
binds:

**CPU is a real ceiling and Rev. 1 did not mention it.** Per-render latency degrades
**3.43 s → 5.55 s (+62%)** from concurrency 1 to 8, while throughput still improves
(4.54 → 0.70 s/render, 6.5×). Total CPU at concurrency 8 is ~8 × 5.55 s = 44 CPU-s in 5.58 s
wall — **about eight cores busy**, i.e. roughly **one core per render for its duration**. On
16 logical cores that is comfortable. **On a 2 vCPU cloud instance it is not**, and no cloud
instance was measured `[UNKNOWN]`.

So the sizing model is not memory alone — and it is an **initial sizing model, not a law.** It
is fitted to four points on **one machine with 16 logical cores**, and no cloud instance has
been measured (U3). It is the right shape to start from and must be re-fitted on the target
instance:

```
render slots  ≈  min( (memory budget − 65 MB) / 240 MB ,  vCPU count )
```

| instance | memory permits | vCPU typically permits | **slots** |
|---|---|---|---|
| 512 MB | **1** — 65 + 240 = 305 MB; two would need **545 MB** | 1 | **1** |
| 2 GB | 8 (measured: 1,897 + 65 = 1,962 MB) | 1–2 | **1–2** |
| 4 GB / 4 vCPU | 16 | 4 | **4** |
| 8 GB / 16 vCPU | 33 | 16 | **8, measured** |

**Provider capacity** is per *call*, not per module, and it is a **formula with a shape
parameter** — the review is right that Rev. 3's numbers still read like general economics when
they describe one project shape:

```
calls(project)     =  planning_calls  +  Σ sections(project)          + retries
projects/min       =  requests-per-min ÷ calls(project)
renders/min needed =  projects/min × modules(project)
```

The measured project is **one instance** of that formula, not the model:

| project shape | calls | 20 rpm | 1,000 rpm | renders/min at 1,000 rpm |
|---|---|---|---|---|
| **measured: 8 modules / 40 sections** | 46 | 0.43/min | 21.7/min | 174 |
| small: 2 modules / 6 sections | 12 | 1.7/min | 83/min | 166 |
| large: 20 modules / 150 sections | 156 | 0.13/min | 6.4/min | 128 |

Note what the table shows and Rev. 3 obscured: **render demand is roughly flat across project
shapes** (128–174/min) while project throughput varies **13×**. Sections dominate the call
budget; modules dominate the render budget; and the ratio of sections to modules is what moves
them apart.

At 21.7 projects/min the render demand is 174 modules/min; one 8-slot worker delivers
**86 renders/min measured**, so **two workers**. Rendering is therefore still not the
binding constraint at volume — but the margin is ~2×, not the ~10× Rev. 1 implied.

## G4 — What the measurements do and do not prove

Rev. 1 wrote *"concurrency is bounded by exactly two things … not CPU, not our throughput,
not the database."* **That was indefensible** — it generalised one benchmark into a theorem,
and it asserted something about a database that does not exist yet (V1 uses `FileStore`). The
CPU finding in G3 disproves it directly.

**Correct statement:**

> The **currently measured binding constraints** are provider capacity and renderer
> memory/CPU. The following are architectural capacity limits that have **not** been
> measured and must be before any volume claim: CPU on a small-vCPU instance · DB
> connections and write throughput · object-storage throughput · queue throughput · provider
> concurrency as distinct from RPM · provider TPM · network bandwidth · per-tenant quotas.

**What survives, and why it is robust.** Of ~2,970 s for the measured project, ~27 s is our
own compute — a **~110:1 ratio**. No plausible database or queue cost reorders that, so the
structural conclusion holds: **the system is latency-bound on a third party**, in-flight work
is mostly waiting, and instances are cheap relative to provider capacity. CC7 said it first:
*"11 calls and ~89k tokens per module is cents; 857 seconds and a Chromium process are the
real bill."* The conclusion is sound; Rev. 1's phrasing of it was not.

## G5 — Three caps, not one

Rev. 1 said *"one global concurrency budget rather than a semaphore per stage."* **That was a
misreading of my own source.** §8's point is that parallel units *multiply against* render
concurrency — an argument for bounding **both**, not for a shared counter. The two resources
are unrelated:

```
model calls        long (~65 s) · network-bound · provider-limited · ~0 local RAM
renders            short (~3.4 s) · CPU+RAM-bound · local · provider-irrelevant
```

A single counter would let eight in-flight generations starve a render, or a render batch
starve generation. So:

```
in-flight Task cap           how many Tasks may be LEASED at once
backlog bound                how many may WAIT — beyond it, SHED (reject with a reason)
per-user quota               so one project cannot consume the backlog
model-call cap, per provider bounds provider load · the RPM/TPM constraint lives here
render slots                 ≈ min(memory, vCPU) — G3, an initial model
DB connection pool           separate, and unmeasured (U9)
```

**Rev. 2 said the admission cap *"bounds queue depth"*, and it does not.** Capping in-flight
Tasks at 100 permits 10,000 waiting behind them; the queue is unbounded and the Task Store
grows without limit. Those are four distinct decisions, and only the **backlog bound** produces
an honest overload behaviour — refusing a Task with a reason, rather than accepting it into a
queue that will not drain. The per-user quota exists because §8 already measured what one
tenant can do to a shared resource: *"a public URL drains the quota."*

The Work Coordinator may hold an overall workload cap, but the resource-specific caps are the
load-bearing ones.

## G6 — Failure domains

| Lost | Still works | Cost |
|---|---|---|
| Provider | plan view, delivery, export, approval, Integrity, Task status | nothing — resume |
| Render worker | everything but new artifacts; Documents survive | ≈ render time per document |
| Task Store | plan view, delivery; **Task status degrades to "unknown"**; in-flight Tasks lost | re-run; memos make it cheap, given D17 |
| Content Memo | plans, documents, artifacts | Σ over unbuilt sections |
| Artifact Store | plan view, documents; **existing PDF delivery is unavailable** | ≈ render time per document, from the surviving Document |
| Document Store | plans, commitments | Σ over that module's sections |
| Decision Store | nothing meaningful | **unrecoverable** |

**Scoped per read — and Rev. 4's version of this sentence contradicted its own table.** It
claimed *"plan view and artifact delivery survive every failure except the Decision Store"*,
which cannot be true when the Artifact Store is the thing lost. Correctly:

| Read | Survives | Needs |
|---|---|---|
| **plan view** | everything except the Decision Store | Decision Store only |
| **artifact delivery** | everything except the **Artifact Store** and the Decision Store — and an Artifact Store loss is **recoverable by re-render from the Document** | Decision Store (authorize) + Artifact Store (bytes) |
| **Task status** | everything except the Task Store | + Task Store |

None of the three depends on the Model Gateway, the Work Coordinator, or a live worker — which
is the property that matters and the one Rev. 4 over-stated. When Task status is unavailable the
honest answer is *"unknown — press again"*, safe precisely because Tasks are envelope-idempotent
and D17 makes pressing again free.

## G7 — Async, and exactly how much

**Async I/O everywhere except a bounded render pool.** `sync_playwright` anchors CC4
`[OBSERVED]` and does not need un-anchoring: if renders are bounded to `min(memory, vCPU)`
slots — measured at 1–8 — a small dedicated thread pool for the renderer is *correct*, not a
compromise. Everything else is waiting on HTTP and should not pay a thread to wait.

**Trade-off:** two concurrency models in one process. Accepted because the boundary is
already test-enforced and because the alternative buys nothing at the measured concurrency.

---

# H. Deployment topology

Four tiers with **numeric conditions** for moving between them. V1 has no Dockerfile, no
deploy config and no CI `[OBSERVED]`, so T1 is the first that exists at all.

### T0 — Laptop (today, and the measurement baseline)

One uvicorn process, Chromium in-process, `FileStore` under `out/`, frontend separate. Works,
well-documented, and **must stay reproducible** — every measurement in `V2/runs/` is
comparable against it.

### T1 — One small host, actually deployable

```
  [browser] ─► Next.js (Vercel) ─NEXT_PUBLIC_API─► one backend process
                                                     ├─ API + Intake (async)
                                                     ├─ Work Coordinator, three caps
                                                     ├─ render pool, size 1 at 512 MB
                                                     └─ Chromium, pinned fonts
                                                          │
                                       Postgres ──────────┘  + object storage
```

**Render pool size is 1 at 512 MB, not 1–2.** Rev. 1 said 1–2 while its own arithmetic showed
2 renders need ~545 MB against the measured baseline. 1–2 becomes available at ≥768 MB **and**
≥2 vCPU (G3).

**512 MB is a candidate, not a validated production size.** With the real app baseline
(65 MB measured, G2) plus one render (240 MB) plus an unmeasured connection pool, one render
fits and two do not — on the arithmetic. What has **not** been measured is per-request overhead
under concurrent load, or anything on an actual cloud instance with its own vCPU limit. So T1
at 512 MB is *the current lower-bound candidate*, and **one real deployment benchmark is a
precondition for committing to it** (U3). The review is right that Rev. 3 read as though the
sizing were settled.

Required for T1, all specified somewhere in V1 and none of it built:

- **A Playwright base image with pinned fonts.** `Runtime-Dependencies.md` §5 specifies it
  *including the version-matching rule and the `PLAYWRIGHT_BROWSERS_PATH` trap*
  `[OBSERVED]` — written as a recipe, and there is no image.
- **Drop `networkidle`; stop fetching webfonts at render time.** Three of four templates
  fetch `fonts.googleapis.com`; without egress `networkidle` waits out the timeout then
  prints with fallbacks, **which changes pagination** — and pagination is artifact-owned
  truth `[OBSERVED]`. Also makes the boundary test's purity claim true instead of false.
- **Env-driven CORS and an access gate.** Hardcoded to `localhost:3000` `[OBSERVED]`; no
  auth, one shared provider key, so *"a public URL drains the quota."* **A shared code is not
  auth and must not be described as auth.**
- **Durable stores**, because ephemeral disk wipes project state, artifacts and the retained
  Document JSON, and free instances restart on idle `[INFERENCE]`.

The frontend boundary needs no work: `lib/api.ts` uses `NEXT_PUBLIC_API`, so the browser
calls the backend directly and **no serverless timeout enters the path** `[OBSERVED]` — the
one deployment decision V1 already got right.

### T2 — Render worker split out

**Condition:** `render slots needed > min((instance memory − 65 MB)/240 MB, vCPU)`, or bulk
re-render becomes a real operation.

```
  backend (no Chromium, small image) ──► render worker(s) ──► object storage
```

The second condition is where **D7's refusal of pooling reverses, in a scoped way**: launch
is 1.39 s — ~41–55% of a render but **0.05% of a project** — so pooling is pointless during
generation and *correct* inside a batch rendering many documents back to back. A template fix
across N documents is that batch, and V1 deliberately retained the Document JSON to make it
possible `[OBSERVED]`. **Pool per batch, never per server.**

### T3 — Horizontal Task workers

**Condition:** in-flight Tasks exceed one process's event loop, or provider concurrency
exceeds one gateway.

N identical workers leasing from the Task Store. **Worker assignment is irrelevant** — any
worker can run any Task, because the two memo stores make re-running cheap and no worker
holds state. That is why T3 is a configuration change rather than an architecture change.

---

# I. Key architectural decisions

### D1 — Two synchronous surfaces: conversational turns, and reads

**Solves** O8 — `force_plan` is sync, measured 342 s and once 11,537 s `[OBSERVED +
MEASURED]` — and *"restart during planning is worse than generation: the HTTP request dies;
no Task to resume"* `[OBSERVED]`.
**Evidence** `timeout_keep_alive=900` is described as *"not a tuning knob"* `[OBSERVED]` — a
900-second admission that the request path is carrying something it should not.
**Cost** every long operation needs a status surface; the frontend gains polling or
subscription; two code paths for *"run a decision."*
**Rule** an operation is synchronous iff it fits the conversational **SLA** (≤ 30 s, a
product target — C1) and no model call within it can exceed that.

### D2 — Durable Task records replace the in-process dict

**Solves** *"a restart loses running jobs"*, and `_jobs` growing for the life of the process,
retaining a `GenerateResult` or a full traceback string forever `[OBSERVED]`.
**Evidence** `jobs.py` states its own replacement condition: *"Not a job queue. No
persistence, no retries, no fan-out, no worker pool … When M4 arrives this is replaced, not
extended."*
**Cost** a Task table can disagree with the Decision Store — resolved by making the stores
authoritative and the Task record advisory.

### D3 — A derivation is addressed by (target, inputs envelope, derivation environment)

**Solves** O6/CC5 (`inputs_hash` written, never read), CF-6 (positional `_job_key`), and
restart of decision work `[OBSERVED ×3]`.
**Evidence** `commit_hash` already proves the mechanism `[OBSERVED]`; the domain model already
requires a `DecisionVersion` to carry its inputs, dependencies and environment.
**Cost** envelope granularity is the main new correctness risk (U1). Too coarse: false reuse.
Too fine: no reuse, and a correction costs a full re-plan again.
**Scope, corrected from Rev. 1:** this covers decisions. Sections need D14; staleness needs
E4's second relation.

### D4 — Integrity is a separate deterministic component, called at three moments

**Solves** A1 and A2. `approve()` has no refusal path `[OBSERVED]`; `serves_everything:
False` in 6 of 8 plans, all 5 that reached approval were approved `[MEASURED]`; 40
module-claimed concepts against 36 in scope, approved `[MEASURED]`. And §2's central fact:
**five arithmetic relationships between the planning decisions, zero enforced** `[OBSERVED]`.
**Evidence** §5's guard is the one working instance in V1 — it compares two recorded
judgments and **raises** — and §5 concludes *"A1, A2, A6, A7 all want exactly this shape."*
**Cost** a refused plan needs a repair path (C4), and running Integrity after every
correction adds conversational friction.
**Corrected from Rev. 1:** it reports **decisions implicated**, not *the* decision, because
most violations have more than one legitimate repair (E5). And half the invariants are
enforced by construction and are not its business at all.

### D5 — Feasibility reads a versioned Capability Declaration owned by the renderer

**Solves** A1's other half and P7's boundary error. `derive_feasibility` is **code** —
*"the model says what the content needs, code says what we can serve"* `[OBSERVED]` — which
makes A1 worse than first stated: **approval discards a computed fact.** `parallel-state: "No
realization exists"` appears in 4 of 8 plans, computed before approval, and nothing blocks
`[MEASURED]`.
**Two tables, not one — corrected in Rev. 3.** Rev. 2 described the declaration as relation →
geometry, which cannot answer the question `Feasibility` asks. `agent/treatment.py` is the
other half and its docstring draws the line: *"This module only says that prose will fail, and
in which of the seven ways … Selecting a realization is decision 11, at the demo gate, over
Representation-Boundary Rev. 3's honesty table."*

```
① NEED COVERAGE      ProseFailure → {served, weight, licenses, note}
                     read by FEASIBILITY (served) and EXTENT (weight)
② HONEST REALIZATION relation → permitted (geometry, reading convention)
                     read by the MERGE-TIME CHECK (D8)
bridge               `licenses` names the realization family ① expects,
                     e.g. topology → "nested regions · layered flow",
                     which ② then constrains to honest pairings
```

Both are per `(renderer build × template)`. Note that ① **already records ②'s gap**: the
`topology` row's note reads *"Composition, causation and association have no realization built
yet — Representation-Boundary §3"* `[OBSERVED]`, which is the same defect D8's check catches at
merge time. The two tables agree, and neither is derivable from the other.

**Cost, and the correction Rev. 2 needed.** Rev. 2 said the declaration enters the derivation
environment and therefore a renderer upgrade makes committed plans **stale** — which its own
definitions forbid, and which was alarming in the wrong direction. `Feasibility` is a
**computed fact**, not a `DecisionVersion` (`feasibility` is not among V1's eight persisted
kinds `[OBSERVED]`), so the declaration is neither a dependency nor in any envelope. It is
pinned in the Commitment so the **disclosure the user saw stays reproducible**; the current
computation may differ, and that difference is surfaced as a disclosure at the next point of
decision. See E4.

### D6 — Generation fans out over sections, bounded by the model-call cap

**Solves** O1's latency and Q8's granularity — sections are one-per-concept in V1 *by
construction* (`plan_for`: *"Every concept the module covers becomes one section"*), which is
why 11 concepts produced 11 sections `[OBSERVED]`.
**Evidence** units are provably independent: `_unit_brief` reads the request, the situation
and its own order, nothing from a prior section `[OBSERVED]`.
**The speedup is `[INFERENCE]`, not `[MEASURED]`** — Rev. 1 mislabelled it. Sequential 323 s
over 5 calls is measured; ideal parallel is one call ≈ 65 s ≈ **5×**, and *"~4×"* is an
engineering estimate after overhead. §4's own evidence grading already said so: *"that
parallelism is safe: `[INFERENCE]`, strong. That it does not degrade output or trip
throttling: `[UNKNOWN]`."* **A concurrent generation benchmark is required before any
latency claim.**
**Cost** provider throttling `[UNKNOWN]`.
**Rule** the per-section check is *"every concept assigned to this section is taught here"*,
never *"in exactly one section"* — OR-1 stays open.

### D7 — Chromium stays, bounded, unpooled, behind a replaceable seam

**Solves** the memory question, with numbers.
**Evidence, measured this session:** launch 1.39 s = ~41–55% of a render, **0.05% of a
project**; memory linear at 233–254 MB per concurrent render through 8; merge 38 ms.
**Pooling refused on measurement:** it saves 1.4 s on a ~2,970 s project and costs ~240 MB
held *permanently* instead of transiently — backwards on the instance size where it matters.
Build-Spec §8 specifies pooling and **the code does the opposite of its own spec**
`[OBSERVED]`; the spec is wrong for the measured workload, and that is worth recording rather
than quietly following.
**Cost** every render pays a cold launch, so the re-render path is launch-dominated — the
scoped exception in T2. And §6's deeper question stands unanswered: *"is overflow detection
worth a browser?"* — a product decision, not a technical one.

### D8 — Two probes move to merge time; honesty becomes a **table-driven** check

**Solves** O4, a latent misattribution bug, and a measured honesty violation in three
templates.
**Evidence** the two probes read markers the template emitted `[OBSERVED]`;
`_representation_report`'s `drawn.pop(0)` pairs against a list omitting unrendered blocks, so
**block 2 is reported with block 3's geometry** `[OBSERVED]`, and the triggering condition is
normal in 3 of 4 templates. Those three render `is-subset-of` and `precedes` as one
`layered-flow` `[OBSERVED]`.
**Corrected from Rev. 1, and against the review's replacement.** Rev. 1's rule — *"no two
relations may share one geometry"* — is **wrong**, and so is the review's *"same form with
different labels is fine."* `Representation-Boundary.md` §2 settles it:

```
is-subset-of  honest: Euler/Venn nesting, indented layers
              dishonest: ARROWS — "asserts process where there is none"
is-part-of    honest: tree, bracket, exploded view, treemap nesting
              dishonest: EULER nesting — "asserts is-a: a wheel is not a car"
precedes      honest: arrows, numbered steps
causes        honest: labelled arrows
              dishonest: arrows SHARED with precedes — "collapses order into causation"
associates-with  honest: undirected graph, adjacency matrix
```

Rows 1 and 2 **share a geometry legitimately** — both are nesting, distinguished by reading
convention — which my uniqueness rule would have flagged as a defect. And the reason labels
cannot rescue a shared form is in the same section: *"the picture makes the claim whether or
not you intended it."* The reference states the rule outright:

> *"Honesty is a property of the (relation, geometry, reading convention) **triple**, not of
> the geometry alone … That table is the real deliverable of the relational family, and it is
> what a renderer needs that nothing currently supplies."*

So the check is: **each realization is a permitted triple in the table** — which catches the
measured defect directly (`layered-flow` is arrows; arrows for `is-subset-of` is row 1's named
dishonesty) without inventing a rule. And the table's home is now named: **the Capability
Declaration**, which is exactly the thing §2 says nothing supplies.
**Cost** merge parses its own HTML output, so the template's marker convention becomes a
contract.

### D9 — Artifacts are content-addressed; supersession is computed

**Solves** §7's worst finding. A module's PDF is addressed by `slugify(title)` `[OBSERVED]`,
so **a correction that renames a module orphans its artifact** — the endpoint says *"this
module has not been written yet"* while the file sits beside it — a regeneration overwrites in
place, and two titles sharing a 60-character prefix collide silently.
**Evidence** corrections demonstrably re-partition (`ml-weekend`, 5 → 3 `[MEASURED]`), so
renames are normal. System-Design Rev. 4 already identifies an artifact version by
`doc_model_hash + render_environment_hash + bytes hash` `[OBSERVED]`; `commit_hash` is the
working precedent.
**Cost** URLs change, and a module needs a *current artifact* pointer — a **computed
relation**, keyed `(Document, template)` per CF-8, never a mutable field.

### D10 — Persistence splits **four** ways

**Solves** the lost-update and corruption hazards, and the reason three V1 mechanisms are
unwired. §7's diagnosis: `inputs_hash`, `freshness` and `feasibility` are unwired *for the
same reason* — **each needs a per-decision addressable store**, and one JSON blob per project
cannot provide one `[INFERENCE]`.
**Evidence** `psycopg[binary]` is declared and `migrations/0001_init.sql` is **written and
unapplied** `[OBSERVED]`; the `Store` Protocol with nine methods means **the replacement seam
already exists and is honoured** `[OBSERVED]`.
**Corrected from Rev. 1:** four stores, not three — the Content Memo is the fourth (D14).
**Cost** four stores, four failure domains, **no single transaction across them** — resolved
by F4's write ordering, not by distributed transactions.
**Technology note, corrected in Rev. 4.** Postgres fits the Decision Store exactly (atomicity,
per-decision addressability, dependency queries for `stale`). The Document, Artifact and
Content Memo **payloads** want object storage. But D17's claim mechanism is a compare-and-set,
and object storage does not provide one — so the **memo index and reservations live in the
transactional store** beside the decisions, holding small rows (key, state, lease, payload
pointer) rather than content. Rev. 3 said *"four stores"* and left that coordination
unaccounted for.

```
transactional store   decisions · commitments · utterances · sources
                      + memo index and reservations · Document identity rows
object storage        memo payloads · Documents · Artifacts
```

### D11 — `SubjectStructure` identity, stated as a function

**Solves** the mechanism behind B1: the same subject produced **29 and 42 concepts** on two
days, and across all eight plans landscape breadth tracks how richly `interpret` restated the
subject `[MEASURED]`.
**Corrected from Rev. 1**, which said *"keyed subject × frame"* and *"reusable across
projects"* in the same breath while its own envelope included source versions. Two distinct
keys:

```
THE key      (subject, frame, source versions, model, prompt version, taxonomy version)
             identity. Nothing else permits skipping the call.

(subject, frame)  is NOT a key — it is what the structure is ABOUT, which is the
                  domain model's statement, not an identity claim
```

**Rev. 3 drops the phrase "domain key", which Rev. 2 used for `(subject, frame)`.** Calling it
a key implied a shareability the real key denies, and the review was right to press on it — a
structure derived over the Indian Contract Act and one derived over UK legislation are **not
the same structure** merely because subject and frame agree. Identity correctness comes before
privacy policy; privacy then follows for free, because a project with private sources has a key
no other project can match — which is the correct answer to *"a shared composition asset built
from private sources is a real disclosure risk"* (System-Design §12) `[OBSERVED]`.
**And `frame` has no operational definition yet.** `select_frame` returns **zero matches
anywhere in the codebase** `[OBSERVED]` — it is specified in the locked references and
unimplemented. An envelope component with no producer is a hole, and it is U2.
**Cost, and a deliberate limit:** the architecture makes derivation addressable and reusable;
it does **not** claim sharing improves quality. HY-3 and HY-4 are open, and reuse *freezes*
variance rather than reducing it.

### D12 — The Model Gateway owns the attempt deadline **and** the Task budget

**Solves** the unbounded retry cost — 600 s × 3 attempts plus linear backoff means **~30
minutes per call** with no caller-side bound `[OBSERVED]`, the mechanism behind **11,537
seconds** `[MEASURED]` — and lockstep retries from missing jitter `[OBSERVED]`.
**Evidence** V1 already types provider failures and maps them to 503/502 rather than leaking
tracebacks `[OBSERVED]`. The taxonomy is right; the bound is missing.
**Corrected from Rev. 1:** two bounds, not one. An attempt ceiling is transient and retriable
within budget; only the Task budget is terminal (F1).
**Cost** a deadline can kill a call that would have succeeded — acceptable **only** because
budget exhaustion is distinguishable from model failure, since an indistinguishable cost
failure recreates §4's *"same symptom, opposite fix."*

### D13 — Conditional capabilities record non-applicability; `ScopeTier` is always computed

**Solves** §0's fourth state: *"unknown whether an authority exists"* is **the actual V1 state
for all 10 cases** `[OBSERVED]`, so a plan for a documented subject and one for an asserted
subject are indistinguishable in the output.
**Evidence** Build-Spec §1 locks *"a conditional capability is never silently skipped"* and
types three outcomes (`SourceStructure | NotApplicable | Infeasible`) `[OBSERVED]`; Foundation
§3.2 requires the tier **during intake**. Corpus `[MEASURED]`: 1 of 10 cases has a real
authority in play, 3 more would if the user brought one.
**Corrected from Rev. 1:** the tier's key is **subject × situation**, per the frozen model —
not subject alone (C1).
**Cost** the tier is a judgment that gates an intake question, so a wrong tier means either an
unnecessary syllabus request or a silently asserted scope. **This is the architectural floor,
not ingestion** — extraction and grounding are deferred; §0 concludes the cheap structural
half delivers Q6, ordering and terminology, and *"conflating them is what makes ingestion look
like a large project."*

### D14 — A durable Content Memo store — **NEW, and the Rev. 1 bug fix**

**Solves** the contradiction at the centre of Rev. 1: *"the decision store is the checkpoint"*
beside section results living in a store described as *"disposable · loss costs 0."* A
generated section is **not** a `DecisionVersion`, so resumption would have re-spent every
completed section — tens of seconds and a paid call each `[MEASURED: ~65 s per section]`.
**Evidence, and it is V1's own argument one level up.** The Document JSON is retained
deliberately: *"a template fix should not cost another generation"* `[OBSERVED]`. One level
down: **a section failure should not cost the other sections.**
**Why it is not a domain object.** The domain model is explicit that `Content` is not an
entity and that a partially-generated document is process state. The memo holds **no domain
object** — it is immutable, envelope-keyed, derived data whose loss costs model calls and not
truth. It is therefore exactly where Rev. 1's *"whole or nothing" Document* rule becomes
affordable (C5), and it is what makes *"Task Store loss costs no model calls"* true.
**Cost** a fourth store, and a retention policy — a memo for a Document already built is dead
weight, so it is collectable once its Document exists.

### D15 — Capability is **per template**, and the template is pinned before Feasibility — NEW

**Solves** a coupling Rev. 1 hid. §6 measured it: `study-notes` realizes 4 geometries over all
5 relations; `module-guide`, `night-lab` and `grimoire` realize **1** geometry over 2
relations `[OBSERVED]`. So *"can the renderer draw this"* has no answer until the template is
known — and Rev. 1 ran Feasibility without one. A plan approved against `study-notes`'
capability and rendered with `grimoire` would be approved against facts that did not apply.
**Resolution, without a domain change.** The template is **not** a new domain decision. The
Capability Declaration is **per (renderer build × template)** — both tables, D18 — the
template is selected before Feasibility (by the
system — `template` is `askable=False` by locked policy: *"Presentation-Boundary rule 1 —
internal. Users never select one"* `[OBSERVED]`), and the selected template plus its
declaration version are **pinned into the Commitment's derivation environment**, which
System-Design invariant 8 already requires a commitment to carry.
**Consequence** rendering with a different template later is a legitimate, *disclosed*
re-render — a sibling artifact under CF-8, not a silent substitution. Its feasibility differs,
and that difference is a **disclosure at the point of that decision, not staleness** — see E4.
*(Rev. 3 left one sentence here saying E4 surfaces it as staleness, which contradicted D5 and
E4. Corrected: nothing about a renderer or template change makes a `DecisionVersion` stale,
because `Feasibility` is computed, not derived.)*

**`template` must be a content hash, not a name — and V1 already computes one.**
`engine/render.py:_template_version` returns a SHA-256 prefix of the template source, with the
reason in its docstring: *"A CSS edit repaginates; Rev. 4 §4 requires that to be visible in the
render environment"* `[OBSERVED]`. So the pinned identity is:

```
renderer build            playwright + chromium version
template id               "study-notes"
template content hash     _template_version()  ◄── without this, a CSS edit silently
                                                   invalidates the pinned capability
capability declaration    version, per (renderer build × template hash)
```

Rev. 3 said *"per (renderer build × template)"* and left `template` unversioned, which would
let a template edit change what the declaration describes while the Commitment's pin still
read `study-notes`. The review is right, and V1's answer is the one to use.

**Who selects the template.** Rev. 3 said *"the system"* and named no owner, which is P1's
error applied to a non-domain decision. Owner: **Template Policy** — a `dom` function
alongside Sufficiency, reading the situation and returning a template id. It is policy in code
for the same reason `sufficiency.py` is: `template` is `askable=False` by locked policy —
*"Presentation-Boundary rule 1 — internal. Users never select one"* `[OBSERVED]` — so the
choice must be principled and inspectable rather than incidental.

**Cost** template selection moves earlier, so a template added later does not retroactively
improve an approved plan's disclosed shortfalls.

### D16 — Three independent concurrency caps, not one — NEW

**Solves** Rev. 1's *"one global concurrency budget"*, which was a misreading of §8: parallel
units *multiply against* render concurrency, which argues for bounding both, not for sharing a
counter. Model calls are long, network-bound and provider-limited with ~0 local RAM; renders
are short, CPU- and RAM-bound and locally limited. A shared counter couples two unrelated
resources.
**Evidence** measured: a render is ~3.4 s, ~240 MB and ~1 core `[MEASURED]`; a model call is
~65 s and no local resource `[MEASURED]`.
**Cost** more caps to tune, and the DB pool is unmeasured.
**Corrected in Rev. 3:** *"Task admission bounds queue depth"* was false — in-flight cap,
backlog bound, and per-user quota are three separate decisions, and only the backlog bound
gives honest overload behaviour (G5).

### D17 — `(decision, envelope)` is unique, and `MISS → deriving` is an atomic reservation — NEW

**Solves a race Rev. 2 left open**, and the damage is worse than duplicated cost. The lease
covers one Task; it does **not** cover two different Tasks whose steps share an envelope — two
projects on the same subject both deriving `SubjectStructure`, which is precisely the case
D11's sharing exists for — nor a lease expiring while the original worker is still alive.

**The correctness half, which matters more than the cost half.** Two versions under one
envelope make `stale(v)` — *"a recorded dependency has a newer version"* — fire on every
dependent, so **a duplicate derivation would mark a correct plan stale**. `stale` is only
well-defined if the envelope is unique.

**The guarantee, generalised in Rev. 4 to every reusable derived result** — not just
decisions, because the Content Memo and the Document are reusable results too:

```
For EVERY reusable derived result, the result key has an atomic claim mechanism.

  DecisionVersion     key = (decision, envelope)          at most one
  Content Memo entry  key = section envelope              at most one
  Document            key = (commitment, module,
                             set of section envelopes,
                             DOCUMENT BUILDER VERSION)    at most one    ◄── Rev. 5

  lookup → reserve → derive → commit   is single-flight:
        the MISS-to-RESERVED transition is atomic, and a second asker observes
        RESERVED and waits.

  A reservation carries a LEASE and a monotonic CLAIM EPOCH (a fencing token).
  A commit is conditional on still holding the current epoch.
  A committed entry is WRITE-ONCE: envelope → content never changes.
```

**Leases are not sufficient, and Rev. 4 stopped at leases.** A lease expiring does not prove the
holder stopped — the architecture says as much itself, that lease expiry can occur while the
original worker is alive. So:

```
Worker A reserves, epoch 7, starts a 65 s call
   lease expires (A is slow, not dead)
Worker B re-reserves, epoch 8, generates, COMMITS
Worker A returns and attempts to commit
   → its epoch is 7, the current epoch is 8  → REJECTED, result discarded
```

Uniqueness alone does not catch this: there is **one row**, and A's late write is a
*state transition on that row*, not a second insert. The epoch check is what rejects it, and
write-once is what makes the rejection unambiguous — **first commit wins.**

**And write-once is load-bearing beyond the race.** If content under an envelope could change,
then a Document keyed by *"the exact set of section envelopes"* would not be keyed to the content
it was built from, and a late overwrite would alter a finished Document's inputs retroactively.
Fencing makes `envelope → content` immutable, which is the property everything downstream keyed
by envelope silently assumed.

**Discarding A's result is correct, not wasteful.** The work was duplicated but neither result is
wrong; this is the at-least-once window stated below, and paying for it once is cheaper than
tolerating a torn read.

**Document construction identity includes the builder version**, by the same argument that puts
model and prompt version in a section envelope and renderer build plus template content hash in
the render environment. Without it:

```
Worker A builds with builder v1, crashes before persisting
   deploy → builder v2
Task resumes; Worker B builds the SAME declared identity with v2
   → same key, different structure
```

The Document Builder is a pure `dom` function, so its output varies only when its *code* does —
front-matter defaults, block ordering, a validation rule. That is exactly the kind of change the
render environment already tracks for templates. Including the version makes a builder change a
**different production event** rather than a silent variant, and it costs nothing: construction
involves no model call, so the worst case is one extra free build.

*(This sits beside, not instead of, the domain model's statement that a `Document` has **content
identity**. The construction key is an idempotency key for one production event; content identity
is what a Document **is**. Two construction keys yielding byte-identical content are the same
Document, which is the desirable outcome.)*

**Document construction needs this too, and Rev. 3 omitted it.** Two workers can each observe
*"all sections present"* and each build a Document — a crash between building and marking the
Task succeeded is enough. The domain permits many Documents per Module **over time**, but these
would be *duplicate attempts at one production event*, not genuine regenerations, and they
would corrupt `superseded(d)` (*"a later Document exists for the same Module"*), the `latest`
pointer, and the support history. So a Document's construction identity is
`(commitment, module, the exact set of section envelopes it was built from)` — which makes a
duplicate attempt a no-op rather than a second Document.

**Execution is at-least-once, and no architecture makes it otherwise.** Stated plainly because
the alternative is a guarantee that cannot be kept:

> A model call that succeeds and whose worker dies before the memo commit **will be repeated.**
> Durable memoisation makes *committed* work reusable; it cannot make an external API call
> exactly-once across a crash. The window is one call wide, and the reservation lease bounds how
> long a duplicate is blocked, not whether one can occur.

So B's *"Task Store loss costs no model calls"* means *no **completed and committed** work is
re-spent* — not that zero duplication is possible.

**The claim mechanism needs a durable coordination primitive, which object storage is not.**
D10 puts the Content Memo's *payload* in object storage, and that is right for bytes. But the
reservation is a compare-and-set, and a plain object store gives no atomic
claim. So the memo splits:

```
memo PAYLOAD      object storage — large, immutable, write-once
memo INDEX +      the transactional store — small rows: key, state
RESERVATION       (reserved | committed), lease expiry, payload pointer
```

The same store that gives the Decision Store its uniqueness constraint gives the memo its
claim. Rev. 3 said *"four stores"* and did not close this loop.

**Evidence for needing it at all:** the expensive step is a model call at ~65 s (section) or
the widest call in the system (`derive`, which truncates in 2 of 10 cases `[MEASURED]`).
Duplicating either is not a rounding error.
**Cost** a reservation is a third state beside hit and miss, so a waiting worker needs a
timeout and a decision about what to do when a reservation dies mid-derivation — re-reserve,
which is safe because a failed attempt writes nothing (F3).
**Consequence** this is what makes *"Task Store loss costs no model calls"* true (B), since
reservations and results both live in the durable stores, not in the Task record.

### D18 — the Capability Declaration is two tables with a named bridge — NEW

Stated as its own decision because Rev. 2 conflated them and `Feasibility` was left unable to
answer its own question. Content in D5. The architectural points: **① is read by `Feasibility`
and `Extent`, ② by the merge-time check; neither is derivable from the other; both are per
`(renderer build × template)`; and the whole declaration is pinned for reproducibility rather
than tracked as a dependency.**

`treatment.py`'s weights are worth one caution it states about itself: *"Every value is a guess
and none has been measured — but a wrong multiplier is a wrong number, while assuming 1.0
everywhere is a wrong *model*."* So ①'s `served` column is factual and its `weight` column is
unmeasured, and `Extent` inherits that uncertainty (OQ-2).

---

# J. Caching, deferred questions, and experiments

## J1 — Four reuse mechanisms, each with a number

All four are **single-flight** under D17: a second asker observes a reservation and waits
rather than duplicating the call.

| Reuse | Justified by | Saving |
|---|---|---|
| Decision versions by envelope | O6/CC5; a correction targets one decision, V1 re-derives all | **97 s vs 342 s** per correction `[MEASURED]` |
| **Section results by envelope (D14)** | the Rev. 1 resumability bug | **~65 s per section** not re-spent `[MEASURED]` |
| `SubjectStructure` by reuse key | B1; Architecture §8 | one `derive` call — and it is the call that truncates (A5) |
| Retained `Document` → re-render | already V1's reasoned decision | **3.4 s vs 323 s — 95×** `[MEASURED]` |

**One explicit refusal, with a number:** browser pooling — 1.4 s saved on a ~2,970 s project,
~240 MB held permanently instead of transiently `[MEASURED]`. Build-Spec §8 specifies it; the
measurement says no, except per batch (T2).

**Not cached, and why:** prompt/token caching — CC7 says tokens are cents and latency is the
bill, so it optimises the cheap axis `[INFERENCE]`. HTML merge output — 38 ms `[MEASURED]`.

## J2 — Decisions vs unresolved questions

**Decided here (D1–D18).** Synchronous boundary · durable Tasks · **atomic claim on every
reusable derived result**, including Documents · Integrity as the only refusal over a *plan*,
reporting implicated decisions · **two-table** capability declarations keyed by renderer build ×
**template content hash**, pinned rather than tracked · Template Policy as a named owner ·
section fan-out · Chromium bounded and unpooled · merge-time table-driven honesty check ·
content-addressed artifacts · persistence split into a transactional store (including the memo
index) and object storage (payloads) · a single `SubjectStructure` identity function · attempt
deadline **and** Task budget, with 429 retriable · **at-least-once execution, stated** ·
conditional-capability recording · resource-specific caps plus a backlog bound · `dom` returns
and `orch` persists.

| | Question | Blocks | Why architecture cannot settle it |
|---|---|---|---|
| **U1** | **Envelope granularity** per decision kind | correctness of all reuse | Needs one deliberate pass over each decision's real inputs. The new risk D3 introduces, and the first thing to get wrong |
| **U2** | **What identifies a `frame`?** | the `SubjectStructure` reuse key | `select_frame` returns **zero matches anywhere** `[OBSERVED]` — specified in the locked references, unimplemented. An envelope component with no producer |
| **U3** | Render capacity **and total footprint on a real cloud instance** | T1/T2 sizing; whether 512 MB is viable at all | Measured on 16 logical cores with a ~65 MB app baseline. Unmeasured: per-request overhead under load, a connection pool, and any cloud instance's vCPU limit. **A one-process import measurement is a floor, not a deployment number** |
| **U4** | Does concurrent generation degrade quality or trip limits? | D6's entire latency claim | Never benchmarked. The `~4–5×` figure is `[INFERENCE]` until it is |
| **U5** | Is overflow detection worth a browser? | whether D7 is permanent | §6: *"the honest form of the Chromium question"* — whether uninspectable pagination is acceptable |
| **U6** | Portfolio link or product? | auth, retention, quota, T1's shape | §8 names it; it changes several answers at once |
| **U7** | What does a project cost on a paid provider? | whether the measurement programme can run | ~57k in / 32k out per module, **never priced** `[UNKNOWN]`. A stable provider is a prerequisite for measuring anything else, and it is a spending decision |
| **U8** | Retention obligation, incl. Content Memo collection | Artifact and Memo policy | *"kept forever"* was explicitly demoted from invariant to policy and never settled `[OBSERVED]` |
| **U9** | DB connection and write throughput | G4's unmeasured list | No database exists yet; V1 uses `FileStore` |
| **U10** | How is a source's **kind** established? | the `Authority` producer | Narrowed from §0's *"who assigns authority scores"* — the profile is a locked lookup; only the kind is a judgment |
| U11 | OR-1 — section exclusivity | plan quality, not architecture | §0: architecture consumes totality only |
| U12 | OQ-3 — source axis vs stated reference | intake's question vocabulary | §0: both route through the same two capabilities |
| U13 | Is `Table` a `Presentation` or a `StructuralClaim`? | whether `Table` needs a `Licence` | OR-2. §5's test — *could two meanings produce this block and one be false?* — is arguably yes for a comparison vs a lookup table |
| **U14** | **What is the legal response for a *third* unserved prose failure?** | C6's approved-shortfall rule | Two of seven are unserved today and the two rules cover them (C6). A renderer change could unserve a third — `cross-reference`, say — and whether that becomes a `Reference`, a marked omission, or a different licensed realization is a **product** decision about what the reader is owed |
| **U15** | `treatment.py`'s **`weight` column** — every multiplier is an unmeasured guess, by its own admission | `Extent`, and therefore A4 | Overlaps OQ-2. The `served` column is factual; the weights are not, and `Extent` inherits the uncertainty |

**Deliberately not decided, because it is a prompt-level choice:** how many model calls the six
planning decisions occupy. The architecture fixes only that **structure and projection are
joint when structure derives** (C3) and that output size is bounded with a typed truncation
failure. A5 is a size problem, not a decomposition problem.

## J3 — Experiments, labelled as experiments

- **HY-1** — does a consequential `Job` constrain admissible depths and licences? The only
  non-prompt route to Q1 → Q2 → Q5; §1 and §2 both recorded its effect as unpredictable.
- **HY-2** — does a supplied structural skeleton improve plans or add noise? Testable on
  contract-act against the reference. §0's caution: *plausible that a section list fixes Q6
  and worsens Q1 by adding context noise.*
- **HY-4** — is subject phrasing causal for landscape breadth? **The cheapest experiment in the
  programme** (~3 calls: pin the subject string across trials) and the biggest reframe if true,
  because it moves B1 from §2 to §1.
- **OQ-1** — where does factual correctness live? `Fulfilment` verifies *mention* by substring
  (M4). Nothing closes this without `Source`, and the product ships without it today.
- **OQ-2** — the calibrated density constants. One data point: **~2.8 pages per concept**
  against the table's most generous **1.0** `[MEASURED]` — so A4 is three numbers and a
  calibration run, **and A2 must be fixed first** or the measurement is polluted by the phantoms
  `derive_extent` silently skips.

**Two measurements that are now prerequisites, not optional:** a concurrent generation
benchmark (U4 — D6's claim rests on it) and render capacity on a small-vCPU instance (U3 — T1's
sizing rests on it). Both cost little: the second costs nothing but a cloud instance and the
saved document JSON.

## J4 — What this architecture would look like having failed

- A judgment is computed and nothing consumes it. **P1 was decoration.**
- Integrity refuses a plan and the user's only route forward is abandoning the project.
  **C4's repair path did not work.**
- Envelope reuse serves a plan built on a superseded structure. **U1 was underestimated.**
- Resuming a generation re-spends completed sections. **D14 was implemented as a cache with a
  TTL rather than a durable store.**
- Two workers derive the same envelope and a correct plan is reported stale. **D17's
  uniqueness constraint was treated as an optimisation rather than as what makes `stale`
  well-defined.**
- A plan discloses *"we cannot draw this"* and the document quietly contains prose instead.
  **C6's rule was enforced on the licence and not on the need.**
- A CSS edit changes pagination and every prior artifact's pinned environment still claims to
  describe it. **The template was pinned by name rather than by content hash.**
- Two workers each build a Document for one commitment and `superseded(d)` starts reporting a
  regeneration that never happened. **D17's Document identity was treated as advisory.**
- Fan-out hits a 429 on the third section and the Task fails terminally. **429 was left inside
  the `ProviderRefused` class, so the concurrency this architecture adds became the thing that
  breaks it.**
- A `dom` function is handed a store in the first week of implementation, and by the third the
  Document Builder is writing rows. **B's boundary was a label rather than a constraint.**
- A slow worker returns after its successor committed and overwrites a section, and a finished
  Document's inputs change underneath it. **D17's fencing was implemented as a lease without a
  claim epoch — the failure a unique key cannot catch.**
- A builder deploy lands mid-Task and two structurally different Documents claim one identity.
  **The builder version was left out of the construction key.**

---

# K. Freeze status

Three tiers, because they are frozen to different degrees and conflating them is how a freeze
becomes fiction.

### Component set — **FROZEN**

Five planes, the component list in §B, the ownership table in §D, and D1–D18. Four review passes
have now run. The residue changed in kind every time and has converged:

```
Rev. 1  → conceptual        a missing store, a shared counter, a wrong gating rule
Rev. 2  → structural        durable memo, split concurrency, per-template capability
Rev. 3  → boundary semantics  two vocabularies needing names, one wrong generalisation
Rev. 4  → consistency       one surviving contradiction, one invented block, one stale number
Rev. 5  → concurrency detail  fencing, one survival claim, one missing version
```

Rev. 5 is the first pass where nothing was stale and nothing needed reverting. **No finding in
four passes has added or removed a component.** That is the test for freezing this layer, and it
is met.

### Implementation contract — **NOT frozen**

Four things must be settled before code, and none of them changes a component:

| | What | Why it is contract, not architecture |
|---|---|---|
| **U1** | Envelope granularity per decision kind | The architecture fixes *that* there is an envelope and what happens when it is wrong; *what is in each one* is one deliberate pass over each decision's real inputs. **Still the first thing to get wrong** |
| **U2** | What identifies a `frame` | `select_frame` returns **zero matches anywhere** `[OBSERVED]`. An envelope component with no producer |
| — | **D17's claim epoch** — the exact fencing and commit-rejection semantics | Architecturally mandatory, stated as a guarantee above; the mechanism (conditional update, sequence, conditional object write) is technical design |
| — | **Document Builder versioning** — how the version is derived and when it changes | Same shape as `_template_version`'s content hash, which is the precedent to follow |

### Deployment parameters — **measured later**

U3 (real cloud footprint and vCPU behaviour) and U4 (concurrent generation: quality and
throttling). Neither decides a component; both tune a number. The 65 MB baseline is a **floor**,
not a deployment figure, and the `~4–5×` fan-out win stays `[INFERENCE]` until benchmarked.

**What this does not freeze:** the domain model is separately frozen at Rev. 4.1, and the
experiments in J3 stay experiments. The next layer is technical design — data model, interfaces,
Task lifecycle implementation — and it inherits this document's guarantees, not its prose.
- A plan is approved against one template's capability and rendered with another.
  **D15's pin was not enforced at render time.**
- Re-render becomes the dominant operation and every one pays a cold launch. **D7 needed T2's
  batch pooling sooner than predicted.**
- Provider **cost**, not provider latency, turns out to be the binding constraint. **CC7 was a
  free-tier artifact**, and G2–G4's whole inversion goes with it.
