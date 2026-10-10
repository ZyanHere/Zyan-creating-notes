# MyNotes V2 — Technical System Design

**Rev. 11 — tenth correction pass.** Follows `Domain-Model.md` Rev. 4.1 (frozen) and `Architecture.md`
Rev. 5 (component set frozen). This document closes the two items Architecture §K listed as
blocking the implementation contract — **U1 envelopes** and **U2 frame** — and specifies the D17
protocol precisely enough that schema and code are mechanical.

## Rev. 11 — what changed

Six findings. **All six real, all applied.** The review's central distinction is the one worth keeping:
**reachability is weaker than mandatory use**, and Rev. 10's new guard only tested the weaker property.

| | Finding | Verdict |
|---|---|---|
| **1** | `FIND_RESULT` is wired into the generic `step()` and the **concrete** render and extraction flows still print their own `LOOKUP → MISS → RESERVE` | **Real, P1, and mine — the same defect in a milder form.** No longer a paid-call loop (adopt-on-conflict plus the strengthened `ArtifactIndex` constraint), but a claim loss still meant redoing a 3.4 s render or a full extraction and discarding it. Fixed **structurally**: the duplicate branches are deleted and every workflow calls `step()` (§7.3) |
| **2** | A document claim loss returns the right content with **no `DocumentProvenance`**, because the attach lived on the `HIT` branch and `RECONCILE` returns directly | **Real, P1, and it violated the rule §9.6a states.** Fixed by moving the attach into `step()`'s `on_result` hook, which runs on **all three** arrival paths — `HIT`, `RECONCILE`, and fresh `PUBLISH` |
| **3** | *"200 calls/hour"* is not the enforced guarantee; the primitive is a fixed bucket that admits up to 2× across a boundary | **Real.** Reworded to **"200 per fixed UTC hour"**, with enforced / implied / reported stated separately (§14) |
| **4** | The per-provider concurrency cap is declared in §14 and in Work Coordinator prose, and **`MODEL_CALL` acquires nothing** | **Real, P0 for the implementation contract.** The defined-but-unreachable class in the worst place: without it, synchronous intake bypasses the very cap §8.6b had just centralised. `ACQUIRE_PROVIDER_SLOT` is now step ③, FIFO, with release in `finally` (§8.6b) |
| **5** | *"Every execution context passes the gate"* is a document-level assertion, not a mechanical boundary | **Real.** Added an **import-level** boundary test, using V1's own working precedent — `tests/test_boundaries.py` already forbids `engine/` from importing `agent/`, `httpx`, `requests` and `socket` `[OBSERVED]` |
| **6** | §8.2 says *"four independent limits"* against §14's six | **Real.** Qualified as *four **Task-admission** limits*, with the reason the other two are elsewhere |

### The recurrence, and the fix that ends it

Findings #1 and #2 are one defect: **a concrete workflow restating the canonical flow and drifting from
it.** Rev. 10 diagnosed the family correctly and then patched the generic primitive only, leaving three
copies of the branches in §9.

```
Rev. 10's guard   test_every_defined_operation_is_reachable
                  → proves FIND_RESULT is called SOMEWHERE
                  → cannot prove every MISS branch calls it,
                    because the duplicate branches ARE the defect
```

So Rev. 11 **deletes the copies** rather than synchronising them. `step(domain, identity, derive_fn,
on_result)` is the only place claim branches exist; every workflow supplies two functions and nothing
else. And §15.8 gains `test_no_workflow_restates_the_claim_branches` — an assertion about *mandatory
use*, which is what the previous one could not express.

That also resolves #2 for free: with the attach as `on_result`, there is no per-branch placement to
forget.

---

## Rev. 10 — what changed

Eight findings. **All eight real, all applied.** Two get a stronger fix than proposed. **Three of the
eight are defects Rev. 9 itself introduced**, which is the pattern worth naming rather than
apologising for.

| | Finding | Verdict |
|---|---|---|
| **1** | `RECONCILE` is defined in §7.3c and the canonical `step()` still reads `MISS → RESERVE_NEW` | **Real, P0, and mine.** Two protocols in one document, with §15.5's test asserting the one that wasn't wired. An implementer following `step()` recreates Rev. 8's paid-call loop. `FIND_RESULT` now sits in `step()` and `step_shared()` (§7.3) |
| **2** | `RoutingResult` has a 90-day retention whose unit names no claim — the false-HIT class, recreated one domain along | **Real, P0, and mine.** Having fixed it for memos I wrote the same defect for a new domain in the same pass. The rule is now stated **over every claim domain** instead of for memos (§10.6a) |
| **3** | Synchronous intake calls pass no admission, appear in no ledger, and count against no quota | **Real, P0, and the largest omission since D17.** Both headline guarantees — *"200 calls/hour"* and *"the ledger is the single source for spend"* — were false on the one path a user drives directly. One gate in the Gateway for every origin (§8.6b) |
| **4** | Whether `structure` depends on `extractor_version` is undefined | **Real — and resolvable from the references, so Rev. 10 settles it rather than recording a choice.** Structure consumes the **extracted skeleton**, not raw bytes (§0: *"an ordered list of addressable units"*), so the extractor is an input. `source_set` gains `extractor_version` (§5.3b) |
| **5** | §10.5 still says the claim key is *"the envelope"* | **Real**, and ironic — the drift class §5.11 exists to kill |
| **6** | T11 logs an `envelope` for results that have none | **Real.** `result_domain` + `result_identity` (§1, §17) |
| **7** | `RECONCILE` inserts `epoch=1` against a *"monotonic per key"* invariant | **Real.** Qualified to *monotonic over the lifetime of a claim **row***, and the reason it is safe is now stated: a reconciled row is born `COMMITTED`, so no CAS ever reads its epoch |
| **8** | The DB permits two Artifacts per `(document, environment)`; only the claim protocol prevents it | **Real, and I went further than proposed.** Rather than add a test over a protocol-only guarantee, the constraint is **strengthened** to `UNIQUE (document_id, render_env_hash)` — enforced where it cannot be bypassed (§4.2) |

### What this pass actually says about the process

Rev. 9 fixed six findings and introduced three. All three are the same shape:

```
#1  a mechanism defined in its own section, and the canonical path not updated to call it
#2  a rule generalised for one domain, and a new domain added in the same pass without it
#3  a mechanism specified for one execution context, and a second context left outside it
```

None is a design error. All three are **a fact stated in one place and bypassed in another** — the
failure mode §5.11, §5.11a, §5.12a and §15.8 were built to catch, which they did not, because each of
those guards checks *identities and enum coverage* and none checks **whether a defined operation is
actually reachable from the canonical flow.**

So §15.8 gains the assertion that would have caught #1 and #3:

```
test_every_defined_operation_is_reachable
    for every operation defined in §7.3's table and §8.6a/§8.6b, assert at least one
    canonical flow in §7.3 / §9 invokes it by name
test_every_execution_context_passes_the_gate
    for every place a model call occurs (§9's flows), assert it routes through §8.6b's
    MODEL_CALL — no call site may reach a provider directly
```

---

## Rev. 9 — what changed

Five residuals plus a GC gap. **All six real, all applied.** Two warrant a different severity or a
different fix than proposed.

| | Finding | Verdict |
|---|---|---|
| **1** | Two extractor versions race the unfenced `Source.extracted_ref` / `state` cell; a late v1 can regress a v2 extraction, or mark a working source `infeasible` | **Real.** But the proposed fix — version the pointer and condition the update — is **strictly weaker than available.** Rev. 9 **removes the cell**: extraction state is a computed relation over `SourceExtraction` for the running build's extractor version (§9.8b). There is nothing to race for, which is C4's pattern one object further. `not_applicable` left with it — it was never a property of a source's bytes |
| **2** | §5.11's identity table was not updated for Rev. 8: `I4` still says *"envelope alone"*, and `SourceExtraction` / `RoutingResult` are absent | **Real, and the exact drift this table exists to prevent.** `I4` corrected; **I17–I20 added** |
| **3** | `UserQuotaBucket` is used in §8.6a and absent from §4.2; no cold-bucket rule | **Real, both halves — and the second is a bug, not an omission.** A bare `UPDATE` matches 0 rows on the first call of each hour, which is **indistinguishable from over-cap**, so every tenant would be refused once an hour. Now an atomic upsert with the condition on `DO UPDATE` (§8.6a) |
| **4** | Claim-loss recovery is promised (*"claims rebuild lazily"*) and never specified | **Real, and this is P0, not P1.** Traced: a lost claim means `MISS → derive → PAID CALL → UNIQUE conflict → full rollback → lease expiry → takeover → derive again`. **A permanent loop burning one model call per lease period.** The uniqueness guard protects the data and guarantees the failure repeats forever. Fixed with a pre-derive existence check plus adopt-on-conflict (§7.3c) |
| **5** | T1, T4 and §5.2's *"everything else"* no longer describe the three-construction reality | **Real** — and it is how the next real bug gets introduced, so corrected rather than tolerated |
| **GC** | `SourceExtraction` and `RoutingResult` have no retention rule | **Real.** Added, with `UserQuotaBucket` (§10.6) |

### Why #4 is P0

```
Claim for K gone;  DecisionVersion V with envelope K remains
  LOOKUP → MISS → RESERVE → derive (PAID) → PUBLISH
       ① CAS ✓     ② INSERT → UNIQUE conflict → ROLLBACK, including ①
  claim back to RESERVED → lease expires → takeover → derive (PAID) → … forever
```

The review read this as *"it doesn't rebuild the claim."* It is worse: **the result tables' uniqueness
constraints, which exist to make claim loss survivable, are what make the loop permanent.** §7.3c adds
the two operations that were assumed: find the result by its canonical identity before deriving, and
**adopt** an existing row at publish instead of rolling back. A lost claim now costs at most one call.

---

## Rev. 8 — what changed

Seven findings plus one identity contradiction. **All eight real, all applied.** Four share one root,
and the sharpest finding is conceptual rather than a missing line.

| | Finding | Verdict |
|---|---|---|
| **1** | `source_extract` publishes to a `SourceExtraction` table that does not exist, under a `Claim.kind` that does not admit it; and its Task key omits `extractor_version`, so an **extractor upgrade re-extracts nothing** | **Real, both halves.** The identity contradiction is the familiar class: the claim says *"new result"*, the Task says *"same request"* |
| **2** | `render` has a claim with **no key construction** — `Claim.key` was documented as *"the envelope"* and §5.9 says an artifact has none | **Real.** The protocol said *use a claim*, the schema said *claims are envelopes*, and nothing bridged them |
| **3** | `routing` is specified as an envelope while the kind domain excludes it, and it is absent from §5.10 | **Real** — and precisely the duplicated-fact class §15.8 exists to catch, which it did not, because of #7 |
| **4** | `CallLedger.task_id` is declared `FK → Task` while Tasks are collected at 30 days and the ledger retained a year | **Real.** Postgres defaults to `NO ACTION`, so the delete fails; `CASCADE` destroys the ledger the quota depends on |
| **5** | The ledger is **post-call**, so `max_calls` and the tenant quota are not enforceable under concurrency | **Real, and the most valuable finding in the review.** *"The ledger is being asked to do both accounting and admission control, which are not the same thing"* is exactly right. See below |
| **6** | §15.5 still asserts on `spent` / `spent_lifetime` — columns Rev. 7 deleted | **Real.** The test contract described a different implementation than the design |
| **7** | §15.8's *"every ClaimKind is handled"* is forward-only, so it passes while whole workflows sit outside the enum | **Real.** A test over an enum's members cannot find what the enum forgot; added the inverse assertion |

### The root behind #1, #2, #3 and #7

Rev. 7 added three claim-producing workflows — `render`, `source_extract`, `routing` — and extended
**none** of: the `Claim` domain, a key construction, the PUBLISH branches, the result tables, or the
summary table. One omission, four symptoms.

The fix is a third canonical construction rather than a widened envelope, because **not every reusable
result is a derived decision**:

```
envelope(kind, member, inputs, env)   derived DECISIONS      → versions, slots, edges
task_key(kind, inputs)                PROCESS state          → leases, budgets
claim_key(domain, identity)           COORDINATION           → six domains, one key  ◄── new
```

Widening `envelope()` would have claimed decision semantics for an artifact, an extraction and a
routing — none of which has a slot, a `version_number`, dependency edges, or a place in a
`Commitment`. `ClaimDomain` is therefore **broader** than `DecisionKind` (§4.2, §5.12a), and
`SourceExtraction` + `RoutingResult` are now real tables.

### #5 — two mechanisms, and Rev. 7 had one

```
budget.max_calls = 2;  generation fans out (D6)
A: Σ ledger = 1 → allowed        B: Σ ledger = 1 → allowed
both call                         ledger = 3
```

Worst-case overshoot is `model_call_cap − 1` = 7 calls, on a tier measured at **20 requests/min**
`[MEASURED]`. The tenant quota had the same hole, where it matters more.

So Rev. 8 separates them (§8.6a): **admission is an atomic conditional increment before the call**
(`Task.calls_admitted`, and an hourly `UserQuotaBucket`), **accounting stays the append-only ledger
after it.** `calls_admitted` may run conservatively high if an admitted call dies — the safe
direction, and the reason admission cannot be derived from the ledger at all.

One honest consequence: Rev. 7 claimed *"RESUME has nothing to reset."* That was true of accounting and
false of admission. `RESUME` resets `calls_admitted`.

---

## Rev. 7 — what changed

Eleven findings, two U1 concerns and one stale sentence. **All fourteen real, all applied.** Three
of the eleven shared one root, so the fix removes two columns rather than patching three places.

| | Finding | Verdict |
|---|---|---|
| **1** | Memo GC deletes a payload while its claim stays `COMMITTED`, so `LOOKUP` returns a **false HIT** | **Real, and the one I would fix first too.** Worse than a cold cache: it turns a successful claim into a dangling promise, breaking D14's only guarantee. Fixed by a **deletion-order rule that mirrors F4** — reference before referent — stated as an invariant because both halves follow from it (§10.6a) |
| **2** | Spend accounting is epoch-fenced, so R2's fenced worker's **paid call is discarded** | **Real.** Fencing a *monotonic fact* discards information rather than protecting anything. See the root below |
| **3** | `CANCEL` has no state predicate, so it mutates a finished Task; no cancel operation in the API | **Real** — §8.8's "no-op after completion" was a statement about intent, not about code (§8.7, §18.1) |
| **4** | `engine_version` is in `render_env_hash` and not in `renderer_build`, so `capability_decl_version` does not identify the environment | **Real.** The three hashes are now **nested**, so they cannot drift (§12.1) |
| **5** | Export's artifact lookup names `capability_decl_version`; `ArtifactIndex` stores only `render_env_hash` | **Real** — a lookup with no column to use. Added, captured in the engine beside the other (§4.2, §9.9) |
| **6** | `frame` and `scope_tier` are derived **before** the situation whose readings they consume | **Real, and it made §6.3's precedence rule 3 unreachable.** Reordered (§9.1) |
| **7** | `render`, `source_extract` and `routing` have no publication contract — rendering was literally *"See §12"* | **Real, all three.** §9.8, §9.8a, §5.9a. Render **does** need a claim, and for a reason I had not stated: unlike export, its output is not canonicalised, so two unclaimed renders make two Artifacts for one environment |
| **8** | Wall budget charges reservation waiting; nothing accounts for waiting | **Real.** Dissolved — see the root |
| **9** | Quota is *"per window"*; no windowed primitive exists | **Real.** Dissolved — see the root |
| **10** | `approved_extent` appears in `BriefInputs` and is defined nowhere | **Real, and it contradicted §5.5.** Following the rules as written, a calibration change would have invalidated **every generated section**. Now pinned in the `Commitment` (§9.4a) |
| **11** | §15.8's completeness assertion is **false as specified** | **Real** — `Project.id`, `Source.id` and three composite PKs are deliberately absent from the I-table. Narrowed to *derived* identities, which is what the table is for (§15.8) |
| **U1-a** | Decoding/sampling config and model revision unpinned, so the addressed function is not specified as deterministic | **Real.** `decode_params` added to every model-backed `env`, **and the limit stated plainly**: pinning makes an approval *auditable*, not *reproducible* (§5.1a) |
| **U1-b** | `situation`, `job`, `scope_tier` lack the field-by-field treatment the other kinds got | **Real**, and `routing` had none at all. All five specified (§5.9a) |
| **§21** | A bullet still read as though `request_id` were missing from the schema | **Fair** — reworded as the regression to watch rather than a current state |

### The root behind #2, #8 and #9

All three were the same defect: **two denormalised counters, two writers, and no time dimension.**
Rev. 5 updated `spent_lifetime` only in `RESUME`; Rev. 6 moved it to the Gateway and fenced it; neither
could answer *"per window"* at all.

So Rev. 7 **removes `spent` and `spent_lifetime`** and derives every spend question from an
append-only **`CallLedger`** (§4.2, §8.8a):

```
spent(T)          = Σ(task_id, task_epoch = current)     → the attempt budget
spent_lifetime(T) = Σ(task_id)                           → includes fenced workers' calls
quota(user, W)    = Σ(user_id, started_at > now() − W)   → the window §14 asks for
wall budget       = now() − attempt_started_at           → waiting counts because time passes
```

Three consequences, all simplifications: `RESUME`'s budget reset **disappears** (a new epoch sums to
zero), the wall-time accounting operation **disappears**, and *"a failed call still counts"* stops
being a rule to remember and becomes a row that exists.

---

## Rev. 6 — what changed

Ten items, **all real, all applied.** Two are worse than stated, and the sweep in item 10 came back
clean afterwards.

| | Item | Verdict |
|---|---|---|
| **1** | `RESUME` lists `incomplete` as resumable and the SQL excludes it; the cancel/complete race has no linearization rule | **Real.** The one state D14 exists for could not be resumed — the predicate was written from the cancellation prose and never checked against its own table. Race rule added: **completion wins a tie**, because discarding a committed result to honour a later cancel wastes paid calls (§8.8) |
| **2** | Export Task key `{commitment_id}` is insufficient | **Real.** A module re-rendered under the same commitment yields a new Artifact (I10), so the key must be the **resolved** set. Now `task_key("export", {export_hash})` (§9.9 ③) |
| **3** | Export resolves *"latest Document"* instead of the Commitment's | **Real, and a correctness bug.** An export of C₁ would package content belonging only to C₂ — a zip labelled with an approved plan containing material never approved. Now resolved **down from the Commitment** (§9.9 ①) |
| **4** | A document-construction `HIT` never attaches `DocumentProvenance` | **Real, and it is the same hole as Rev. 5's shared-derivation HIT, one object along.** `construction_key` excludes `commitment_id` by design, so a second commitment HITs and `PUBLISH` — where the provenance insert lives — is never reached. Fixed with `ATTACH_PROVENANCE` (§9.6a), and the underlying rule is now stated |
| **5** | `spent_lifetime` is advanced only by `RESUME` | **Real, and worse than stated:** a Task that never resumes carried `spent_lifetime = 0` while `spent` held the real cost — and §14's quota reads `spent_lifetime`, so **the counter guarding spend counted nothing for almost every Task**. Both counters now advance together on every call (§8.8a) |
| **6** | `renderer_build` described as pinned, absent from the Commitment environment | **Real.** Resolved without adding a field: `capability_decl_version` is **defined** as a hash over renderer build, template identity and declaration content, so pinning it pins all three (§12.1) |
| **7** | No canonical zip serialisation | **Real, and worse than stated:** the path derives from the *input* hash, so non-deterministic bytes mean two workers write **different bytes to one path** — §7.4's key-addressed hazard, reintroduced. §9.9a is therefore normative (§9.9a) |
| **8** | §12.2 says `Extent` reads NEED COVERAGE; `extent()` has no such parameter | **Real.** A pure function cannot read a table it was not handed. Signature corrected, with the invalidation consequences stated (§12.2a) |
| **9** | Six regression tests missing | Added, plus eight more the fixes imply (§15.5, §15.9) |
| **10** | §15.8 grep test promised and never written; no literal sweep run | **Written (§15.8), and the sweep is clean** — every remaining occurrence of a stale pattern is inside a change-log entry or the test spec itself. Two legitimately nullable columns (`result_ref`, `owner`) made my first grep pattern too broad; narrowed to `member` |

### The discipline this pass institutionalises

Four of the last fourteen findings were **one fact stated in two places with one copy updated.**
Rev. 6 stops treating that as carelessness and makes it a tested property:

```
§5.2a   is_shared(kind)     sharedness is a predicate, not a kind
§5.11   identities I1–I16   nothing else may state an identity
§5.11a  member encoding     one table, all kinds
§5.12   task_key()          separate domain, provably disjoint from envelopes
§15.8   grep test in CI     fails the build on a stale second copy
```

---

## Rev. 5 — what changed

Rev. 4's pass was cut off partway. A sweep confirmed **seven items, all real**: three intended
fixes landed only half, one was never written, and three are new residuals. One claim in the review
is wrong on a detail, noted below.

| | Item | Verdict |
|---|---|---|
| **1** | `Claim.kind = 'decision' \| 'memo' \| 'document'` admits none of the shared kinds, while §4.2a coordinates them through the global claim and §7.3a's `PUBLISH` refers to a `SHARED` kind | **Real, and the fix removes a concept rather than adding one.** `SHARED` was never a kind — sharedness is a **property of a decision kind**, and §5.2's family table already says which. Fixed (§4.2, §5.2a) |
| **2** | `member: null` survived in §5.6 after the sentinel fix | **Real — the third-location pattern I flagged myself.** Fixed, and the **full member encoding now has one home** (§5.11a) rather than being restated per kind |
| **3** | `request_fingerprint` is in the §18.3 contract and not in the `Utterance` schema | **Real**, and only half of #7 landed before the pass stopped. Fixed (§4.2) |
| **4** | `envelope("task", …)` uses a `kind` the canonical envelope construction does not admit | **Real, and the prescription is right for the right reason:** a Task is **process state**, not a reusable derived result (§4.1's tiers), so it gets its own construction rather than widening the envelope. Fixed (§5.12) |
| **5** | `RESUME` promises a fresh budget; the transition changes neither `budget` nor `spent` | **Real, and sharper than it looks** — a resume from `task_budget_exhausted` would re-exhaust immediately. Fixed, with lifetime spend kept separate so resume cannot become an unbounded spend loop (§8.8) |
| **6** | §3.4 still says *"idempotent on target"* | **Real** — stale since Rev. 3 |
| **7** | §9.10 Export does not exist, though the Rev. 4 log claims it | **Real.** Written now (§9.10) |

**One detail the review has wrong:** it states the file *"ends at §20 Traceability, so there is no
§21."* §21 exists and has since Rev. 2; what was missing is its **content for these fixes**, which
is a fair criticism of substance. Both are addressed.

### The pattern, and the response

The review's closing observation is correct and worth adopting as a rule: **the architecture is no
longer where the risk is — duplicated specification facts are.** Four of the last ten findings were
one fact stated in two places, with one copy updated.

§5.11's identity table was the first application. Rev. 5 extends the same discipline to the three
areas that kept drifting:

```
§5.11   identities        I1–I16   nothing else states an identity
§5.11a  member encoding   one table, all kinds
§5.12   task keys         separate construction, separate domain
§5.2a   shared kinds      one predicate, is_shared(kind)
```

**The rule going forward:** a fact that appears twice is a defect, and the second appearance must be
a reference. §15.8 adds a grep-level test that enforces it.

---

## Rev. 4 — what changed

Seven findings. **All seven accepted.** Two are worse than the review states, and **#1 is a hole
the Rev. 3 fix itself opened** — worth saying plainly, because it is the pattern to watch.

| | Finding | Verdict |
|---|---|---|
| **1** | The `SharedDerivation` `HIT` path cannot create the project-local pointer: generic `step()` returns at HIT, and `PUBLISH` starts with a `RESERVED → COMMITTED` CAS that a committed claim fails | **Real, and it is my own regression.** §4.2a's prose said *"a second project HITs at ① and performs only ③"*, and no operation existed that could do that. The protocol and `test_second_project_reuses_shared_derivation` contradicted each other. Fixed with **`ATTACH`** (§7.3b) |
| **2** | Cancellation is declared terminal and non-re-leasable, which makes the promised resume impossible — while the API calls the operation *"start/resume"* and a test expects a later run costing only the remainder | **Real.** §8.7's last sentence — *"the caller gets the cancelled one and must change something to proceed"* — was simply wrong, and contradicted the paragraph above it. Fixed with an explicit `RESUME` transition (§8.8), **without** a successor identity: an epoch bump makes double-resume safe on its own |
| **3** | `Decision.member` is nullable and in the primary key, which Postgres forbids | **Real, and worse than "DDL aesthetics".** In Postgres `UNIQUE` treats NULLs as **distinct**, so `UNIQUE (project_id, kind, member, envelope)` with `member = NULL` would **not prevent duplicate versions for one envelope** — which is the constraint §11 relies on as the second guard behind claim loss. Fixed with a non-null canonical sentinel (§4.2, §5.1) |
| **4** | §5.9 still orders `superseded(a)` by `created_at` | **Real** — the same residual-in-a-third-place pattern as the D15 sentence in Architecture Rev. 4. Fixed (§5.9) |
| **5** | §10.5 still prints the generic `(project, kind, target)` formula and §18.3 still says approval is idempotent on `version_set_hash` alone | **Real, and the prescription is right**: the fix is not correcting two lines but having **one canonical identity table** that everything references (§5.11) |
| **6** | `export` appears in Task kinds, storage kinds, failure/recovery and the API, with no workflow or publication protocol | **Real.** Specified rather than deferred (§9.10) — it is short, and it turns out to be the one derived result that correctly has **no claim**, for a reason worth recording |
| **7** | Reusing a `request_id` with a different payload has unspecified semantics | **Real.** Fixed with a request fingerprint (§4.2, §18.3) |

**Confirmed not reopened:** monotonic sequences (§10.2a), the publication transaction (§7.3a), and
the `SharedDerivation`/pointer split itself (§4.2a) all stand.

---

## Rev. 3 — what changed

Six new findings. **All six accepted.** One had its example corrected, one is answered by proof
rather than a schema change, and **two are worse than the review states.**

| | Finding | Verdict |
|---|---|---|
| **1** | Cross-project content-addressed results have no clean storage owner: `DecisionVersion` carries `project_id` and FKs a project-scoped slot, yet `UNIQUE (kind, member, envelope)` is **global** | **Real, and worse than stated.** Project B literally *cannot* insert its own row for a shared envelope. And the reason the reviewer's Option B fails is one they did not spot: **slot-based `version_number` ordering would leak staleness across projects** — A bumping its derive prompt would stale B's plan. Fixed with a global `SharedDerivation` table plus per-project **pointer** versions (§4.2a) |
| **2** | Plan Task key omits planning roots, so a change that alters `structure` leaves the key unchanged | **Right finding, wrong example.** A source change *does* propagate — `scope_tier` and `frame` envelopes both include the source set, so `tier_v` and `frame_v` move. The real hole is the **derivation environment**: bumping the derive prompt, model, taxonomy or `frontier` changes the `structure` envelope and **nothing else**. Fixed by keying on the structure envelope itself (§8.1) |
| **3** | The API promises request-id idempotency for intake; `Utterance` has no such column | **Real.** Contract and schema disagreed. Fixed — and while there, `ord` needed the same slot-bump treatment as §10.2a, which was a latent race of my own (§4.2) |
| **4** | `content_hash` is labelled *"the domain's content identity"* but only `construction_key` is UNIQUE, so two rows can hold identical content | **Real.** The domain model says a `Document` **is** its content, and the schema permitted otherwise. Fixed by making content the identity and construction keys a many-to-one index onto it (§4.2, §5.8) |
| **5** | `select_frame(subject, situation, candidates)` — the envelope has no `candidates` | **Accepted as a question, answered by proof.** V2 has **no frame catalogue** (§0.2: the first project derives; promotion is deferred), so `candidates` is not a system-supplied input — it is model knowledge, already covered by `model_id + prompt_version`. Adding a hash for a set that does not exist would be cargo cult. **The condition under which it becomes a real input is now stated** (§6.3a) |
| **6** | `UNIQUE (project_id, version_set_hash)` returns the old `Commitment` when the pinned environment has changed | **Real, and worse than stated.** A template edit changes `template_content_hash`; re-approval would return a commitment pinning a template hash **that no longer exists on disk**, and `disclosed` would be the old feasibility. Fixed: identity includes the environment (§4.2, §9.4) |

**Confirmed not reopened:** monotonic version ordering (§10.2a) and the publication transaction
(§7.3a) both stand as written in Rev. 2.

---

## Rev. 2 — what changed

A review raised 5 issues and 4 smaller inconsistencies. **All nine accepted**, one with a caveat.
Three were correctness bugs; two of the three I would not have found by re-reading.

| | Finding | Verdict |
|---|---|---|
| **1** | Task idempotency keyed on `{target}` alone, so re-generating a module under a **new Commitment** finds the old succeeded Task | **Real bug.** Same class as CF-6: an identity that does not capture what makes two things different. Fixed with **per-kind keys** (§8.1) |
| **2** | The claim `COMMIT` publishes a `result_ref` but nothing binds it atomically to `DecisionVersion` / `MemoIndex` / `DocumentIndex` | **Real bug, and the most important of the five.** A crash between them leaves the claim saying *"done"* and the store saying *"nothing here."* Fixed with a **publication transaction** gated by the epoch CAS (§7.3, §10.2) |
| **3** | `frame` cached **by subject**, contradicting §6.3's own precedence rules, in which a source or the situation selects it | **Real bug, and embarrassing:** `scope_tier` in the same document is keyed `(subject, purpose, sources)` — correctly. Fixed with a frame-selection envelope and a principled input filter (§6.3) |
| **4** | T6's memo locality claim is weaker than it reads, because `situation_version_id` and `job_version_id` are global | **Accepted with a caveat.** The document says *"a correction **touching module 5**"*, which does not change situation or job, so the claim is literally accurate. But it invites over-reading — and chasing it found a genuine improvement: by T6's own logic (*the brief is the input*), the envelope should carry **exactly the brief's inputs**, not whole situation versions (§5.7) |
| **5** | `stale()` orders versions by `created_at` — wall-clock, ties possible, and not the semantic ordering | **Real, and it propagates further than noted:** `superseded(d)` and `superseded(a)` use the same ordering. Fixed with **monotonic per-slot sequences** (§4.2, §10.2) |
| **A** | `scope_tier` labelled content-addressed in §5.10 while §5.2 says content-addressed = `structure` only | **Accepted** — my own table contradicted itself (§5.2) |
| **B** | T1 says *"object storage or a volume"* while signed-URL delivery assumes object storage | **Accepted** — made conditional (§16) |
| **C** | Security promises Tasks are *"cancellable"*; the state list has no `cancelled` | **Accepted**, and the semantics are pleasant: cancellation is **non-destructive**, because committed memos survive it (§8.7) |
| **D** | *"`Utterance` text … is never sent anywhere but the provider"* is too absolute — the application stores it | **Accepted** — reworded (§13.4) |

**No contradiction against the frozen architecture was introduced or found.** Every fix is
internal to this layer.

**Labels used throughout.** `DECIDED` — follows from the frozen layers or from evidence.
`CHOICE` — an implementation choice with a named alternative; reversible. `UNKNOWN` — requires
measurement; not to be treated as settled.

**Evidence key** — `[OBSERVED]` in V1 code/spec · `[MEASURED]` in the 11 records or a bench run ·
`[LOCKED]` in a frozen reference · `[INFERENCE]`.

**No SQL, no endpoint code, no prompts.** Structures are defined to the point where schema design
is transcription.

---

# 0. Contradictions found against the frozen architecture

Architecture Rev. 5 is frozen and the instruction is to flag any contradiction before changing
anything. **I found none.** I did find two places where the frozen layers are *silent* in a way
that a technical design must resolve, and one consequence that costs something. Recording all
three here rather than burying them.

### 0.1 Structure derivation must be situation-free, and V1's is not

D11 makes `SubjectStructure` addressable by a key containing `(subject, frame, source versions,
model, prompt version, taxonomy version)` — **no situation.** V1's call is `derive(situation)`
`[OBSERVED]`, which passes the whole `Situation` object. If V2 kept that, the envelope would be
dishonest: it would claim reusability across projects for a result that depended on the
requesting project's purpose, capacity and entry point.

So: **the structure derivation call receives subject + frame and nothing else.** `DECIDED`, and it
is what D11 already implies.

This is not a contradiction because the frozen references already draw the line. `Architecture.md`
§8's stable/projected table `[LOCKED]`:

| stable — property of subject × frame | projected — property of the traversal |
|---|---|
| concepts exist | prerequisite order |
| typed constitutive relations | difficulty *for this learner* |
| dense regions | centrality |
| names and aliases | presentation order |
| | module cuts, omission consequence |
| | **granularity — the resolution the graph is read at** |

The last projected row is the one that matters. §1's worry — *"if the landscape is built assuming
API fluency, API foundations are never in the graph"* — is a **granularity** concern, and
granularity is projected. So `entry_point` belongs in **Projection's** envelope, never in
Structure's, and S3 (`Projection.judged = SubjectStructure.concepts`) is exactly the statement
that Projection judges *all* of them and decides which are in play.

**The cost, stated honestly.** A situation-free structure is broader than a situation-narrowed
one, and `derive` is already the widest output in the system — **A5 truncated 2 of 10 runs**
`[MEASURED]`. So this design **raises** truncation risk. Mitigations, all already specified:
`Architecture.md` §8's *"hard expansion limit … a safety net, not the stopping condition"*
`[LOCKED]`, which becomes the `frontier` parameter (§5.3); and D12's typed `OutputTruncated` with
a narrowing retry. **Whether a situation-free derive truncates more often is `UNKNOWN`** and is
the first thing the plan pipeline should be instrumented for.

### 0.2 Asset growth (promotion) is a seam, not a component

`Architecture.md` §8 `[LOCKED]` specifies more than Rev. 5 carries:

```
shared asset (read-only)  +  situation
            ↓
   project-local exploration
            ↓
   candidate graph  ─────→  relevance · traversal · consequence
            ↓
   discovered candidates ──→ promotion proposal (gated, §5)
```

And: *"Promotion requires a situation-free adjudicator … the only operation that must not be
[situation-conditioned] — which makes it a different kind of actor from anything else in the
architecture."*

V2's initial build has **no asset library to read**: the first project for a `(subject, frame,
sources, env)` derives the structure and every later project with a matching envelope reuses it.
That is the whole of D11, and it needs no new component. **Promotion is deferred**, and the seam
is named here so it is not rediscovered: it needs the situation-free adjudicator §8 flags, and it
belongs with HY-3. `DECIDED` to defer.

### 0.3 One domain-model relation needs a technical reading, not a change

`superseded(d) ⟺ a later Document exists for the same Module`. If Document construction identity
included the `Commitment`, then **every re-approval would mint a new Document even when nothing
about that module changed**, and every prior artifact would be superseded for no reason. So
Document identity is **content-derived** and the commitment is recorded as provenance (§5.8).
This preserves the domain relation rather than altering it.

---

# 1. Executive summary

Eleven decisions carry this design. Everything else follows from them.

| | Decision | Closes |
|---|---|---|
| **T1** | Every reusable result has a **128-bit canonical identity**, built by one of **three** constructions with disjoint domains — `envelope()` for derived decisions, `claim_key()` for coordination, `task_key()` for process state (§5.1, §5.12, §5.12a) — each with a golden test asserting both inclusion and exclusion | **U1** |
| **T2** | `frame` is the axis along which **constitutive relations vary** — jurisdiction, school, standard version — produced by `select_frame`, recorded as `NotApplicable` for single-frame subjects | **U2** |
| **T3** | Two envelope families: **content-addressed** (shareable: structure) and **version-addressed** (project-scoped: everything else) | D11's sharing being real rather than nominal |
| **T4** | One `Claim` table coordinates every result whose **production** is worth single-flighting — six domains (§5.12a): `state · epoch · lease · result_ref`, commit conditional on epoch. **Export is the one deliberate exception**, because its output is canonicalised so duplicate work is harmless (§9.9a) | **D17**, fencing |
| **T5** | Payloads are **content-addressed in object storage and written before the claim commit**; only the committed claim references one | the Postgres↔object-storage transaction gap |
| **T6** | Content Memo envelopes are **section-content-derived, not commitment-derived**, so a correction to module 5 does not invalidate module 1's generated sections | the largest avoidable cost in the system |
| **T7** | `stale` is computed by walking **recorded dependency edges**; `reusable` is an envelope equality check. Two queries, never one | E4 |
| **T8** | Tasks carry their own epoch and lease, for the same reason claims do | a re-leased Task being completed by its predecessor |
| **T9** | `dom` functions take and return values only; **ports** are the sole I/O surface and `orch` owns every transaction | B's `dom`/`orch` boundary becoming a constraint |
| **T10** | Waiting on someone else's reservation **yields the slot** rather than blocking it | fan-out deadlocking itself under the model-call cap |
| **T11** | Every derivation logs `{result_domain, result_identity, reused, claim_epoch, fenced, attempt, failure_class}` — **`result_identity`, not `envelope`**, because `render`, `source_extract` and `routing` are claim domains with no envelope (§5.12a) | *"why did this project cost 46 calls"* being answerable |

**What this design does not settle:** U3 (cloud footprint), U4 (concurrent generation), U5
(overflow worth a browser), and the density constants (OQ-2). All stay `UNKNOWN`.

---

# 2. Technical architecture

The frozen component set, with the concrete artefact each becomes. **Kind** is from
Architecture §B: `dom` pure, `orch` orchestration, `infra` adapter behind a port, `store`, `decl`.

| Component | Kind | Concrete form | Port(s) it uses |
|---|---|---|---|
| Conversation API | orch | request handlers | DecisionStore, ClaimStore, TaskStore, ModelGateway |
| Intake | orch + dom | `interpret` orchestration + `sufficiency` pure policy | ModelGateway |
| Sufficiency policy | **dom** | pure function over readings | — |
| Source Registry | orch + infra | tier/kind classification (sync) + extraction (Task) | ModelGateway, SourceStore |
| Subject Knowledge | orch | structure derivation, content-addressed | ModelGateway, DecisionStore, ClaimStore |
| Planner | orch | six-step pipeline | ModelGateway, DecisionStore, ClaimStore |
| Extent · Feasibility | **dom** | pure functions | — |
| **Integrity** | **dom** | pure function → `list[Violation]` | — |
| Template Policy | **dom** | pure function → `TemplateId` | — |
| Commitment | orch | predicate + mint | DecisionStore |
| Generator | orch | bounded fan-out over sections | ModelGateway, MemoStore, ClaimStore |
| Document Builder | **dom** | pure function → `Document \| BuildError` | — |
| Renderer | infra | `merge` (pure) + `print` (browser) | RenderSlots |
| Capability Declaration | **decl** | two versioned tables | — |
| Model Gateway | infra | HTTP client + deadline/budget/jitter | — |
| Work Coordinator | orch | admission, leasing, caps, orphan recovery | TaskStore |
| Stores | store | Postgres + object storage | — |

**The `dom` surface, in full.** These are the only functions that may contain domain logic, and
none of them can perform I/O — which is enforced by their signatures having no port parameter:

```
sufficiency(readings, utterances, stated, scope_tier)        -> Verdict
template_policy(situation, job)                              -> TemplateId
extent(scope, partition, density_constants, capability_decl) -> Extent      ◄── §12.2a
feasibility(scope, capability_declaration)                   -> list[Shortfall]
integrity(decision_set, capability_declaration)              -> list[Violation]
build_document(front_matter, ordered_sections, builder_ver)  -> Document | BuildError
validate_blocks(document, capability_decl, shortfalls)       -> list[Violation]
check_unit(order, section)                                   -> UnitReport
merge(document_mapping, template_source)                     -> Html + MergeReport
envelope(kind, member, inputs, env)                          -> Envelope
```

`merge` is `dom` despite living in the renderer: it is pure Jinja, **38 ms measured**, and V1
already proves the boundary by test-forbidding `engine/` from importing `agent/` `[OBSERVED]`.

---

# 3. Runtime and process model

## 3.1 Processes

**T0 and T1 are one OS process** (Architecture §H). Inside it, three execution contexts:

```
┌─ asyncio event loop ─────────────────────────────────────────────┐
│  HTTP handlers (sync-path requests)                              │
│  Work Coordinator: admission, leasing, heartbeats, orphan sweep   │
│  Model Gateway: all provider I/O                                 │
│  Task workers: async coroutines, one per leased Task              │
└──────────────────────────────────────────────────────────────────┘
┌─ render thread pool, size = render slots (1–8) ──────────────────┐
│  sync_playwright · one Chromium per render · CPU + 240 MB each    │
└──────────────────────────────────────────────────────────────────┘
┌─ DB connection pool ────────────────────────────────────────────┐
```

`CHOICE` — render work stays on a small thread pool rather than being made async. Rationale from
Architecture G7: `sync_playwright` anchors the sync code, renders are bounded to ≤ 8 anyway, and
rewriting it buys nothing at the measured concurrency. *Alternative:* a separate render process
now instead of at T2; rejected because it adds a deployment unit before the measurement that
would justify it (U3).

## 3.2 Synchronous paths and their budgets

An operation is synchronous iff it fits the conversational SLA and no model call inside it can
exceed it (Architecture D1).

| Path | Model calls | Measured | SLA | On breach |
|---|---|---|---|---|
| create project | 0 | — | 1 s | error |
| append utterance | 0 | — | 1 s | error |
| **intake turn** | 1–2 `[OBSERVED]` | 17.7 s first question `[MEASURED]` | **30 s** `CHOICE` | fail **retriably**; the `Utterance` is already durable, so a retry costs ≤ 1 call |
| scope tier | 1, cached | — | inside the intake turn | reading falls back to `unknown`, disclosed |
| read plan | 0 | — | 500 ms | error |
| **approve** | 0 | 0.04 s + checks `[MEASURED]` | 2 s | error |
| task status | 0 | — | 200 ms | *"unknown — press again"* |
| artifact | 0 | — | 500 ms + transfer | error |

**The 30 s SLA is a product target, not a measurement** (Architecture C1). §1 records **1–2 calls
per answer**, so a two-call turn plausibly exceeds it; no p95 exists. `UNKNOWN`.

## 3.3 Request lifecycle, synchronous

```
receive → authorize (user × project) → open tx → read → close tx
        → [0–2 gateway calls under the request deadline]
        → open tx → claim + write → commit → respond
```

**No transaction is held across a model call.** `DECIDED` — a 65 s transaction holds a connection
and a row lock for the duration; at the DB pool sizes in §14 that is self-inflicted exhaustion.

## 3.4 Background Task lifecycle

```
POST → Task created (idempotent on I14 — task_key, PER KIND: §5.12, §8.1) → admitted or shed
     → leased (epoch, lease_until) → running
     → per-step: step(domain, identity, derive_fn, on_result) — §7.3, the only claim path
     → succeeded | incomplete | failed(transient → retry | terminal)
     → heartbeat throughout; orphan sweep re-leases the abandoned
```

---

# 4. Data model

Precise enough that schema design is transcription. **Names are logical**, not column names.

## 4.1 Three tiers, and the rule that separates them

| Tier | Durability | Recompute cost | Members |
|---|---|---|---|
| **Domain truth** | never lose | impossible | `Utterance`, `Source` bytes, `Commitment`, `Artifact` bytes |
| **Derived data** | lose at a price | model calls | `DecisionVersion`, memo payloads, `Document` |
| **Process state** | free to lose | none | `Task`, leases, attempt counters |
| **Infrastructure state** | rebuildable | none | `Claim` rows, render slots, GC cursors |

`Claim` rows are infrastructure state and **not** domain state — but they are durable, because
losing them loses the uniqueness guarantee that makes `stale` well-defined (§7.6).

## 4.2 Transactional store (Postgres) — small rows, strong constraints

```
Project
  id            : uuid, assigned            PK
  user_id       : text                      not null
  title         : text
  taxonomy_version : text
  next_ord      : int, default 1            the serialisation point for Utterance.ord
  created_at    : timestamptz

Utterance                                   APPEND-ONLY (S11)
  id            : uuid, assigned            PK
  project_id    : uuid                      FK
  ord           : int                       UNIQUE (project_id, ord)
                                            assigned by bump_slot on Project.next_ord —
                                            NOT max(ord)+1, which races (§10.2a's pattern)
  request_id    : text                      UNIQUE (project_id, request_id)   ◄── Rev. 3
                                            client-supplied; the concrete mechanism §18.3
                                            promised and Rev. 2 never stored
  request_fingerprint : bytes32             ◄── Rev. 5 · sha256(canonical_json({role, text}))
                                            Rev. 4 defined the 200/409 rule in §18.3 and never
                                            added the column, so the rule was unimplementable.
                                            Matching fingerprint → return the existing turn;
                                            mismatch → 409 request_id_reused (§18.3)
  role          : 'user' | 'system'
  text          : text
  created_at    : timestamptz
  ── no update, no delete, ever. Enforced by revoking UPDATE/DELETE, not by convention.
  ── retry semantics: the second INSERT violates (project_id, request_id); the handler
     reads the existing row and proceeds. The derivation then HITs its envelope, so a
     lost response costs nothing.

Source
  id            : uuid, assigned            PK
  project_id    : uuid                      FK        (private by default, §13)
  content_hash  : bytes32                   the version identity (invariant 8)
  kind          : 'syllabus'|'textbook'|'slides'|'past_papers'|'statute'|'other'
  authority      : derived from kind by LOCKED lookup — NOT stored as a judgment
  payload_ref   : ContentRef → object storage
  created_at
  ── Rev. 9: NO `extracted_ref`, NO `state`. Both were a project-local MUTABLE CELL that
     two extractor versions raced for, unfenced — see §9.8b. Extraction outcome is now a
     COMPUTED relation over SourceExtraction, which is the same treatment `status`,
     `freshness` and `supersession` already get (C4).
  ── `not_applicable` also left with them: it never belonged here. "This project needs no
     source" is a property of the project's scope_tier (§9.1), not of a source's bytes.

Decision                                    the SLOT
  project_id    : uuid
  kind          : DecisionKind
  member        : text NOT NULL, default ''  module id, or "<level>:<module id>" for ordering;
                                             **'' is the canonical root sentinel** — see below
  next_version  : bigint, default 1          ◄── §10.2a · bumped inside the publish tx;
                                                 the serialisation point for one slot
  ── PK (project_id, kind, member)                                          S-identity
  ── member is NOT NULL. Rev. 3 wrote `text | null` in a primary key, which Postgres
     forbids — and the consequence was worse than DDL: **Postgres treats NULLs as
     DISTINCT in a UNIQUE constraint**, so `UNIQUE (project_id, kind, member, envelope)`
     with member = NULL would NOT have prevented two versions for one envelope. That
     constraint is exactly §11's second guard behind claim loss, so a nullable member
     would have silently disabled it.

SharedDerivation                            GLOBAL · no project · §4.2a
  id            : uuid                      PK
  kind          : 'scope_tier'|'frame'|'structure'      the content-addressed family only
  envelope      : bytes16                   UNIQUE (kind, envelope)   ◄── the global claim
  payload_ref   : ContentRef
  payload_hash  : bytes32
  env           : jsonb
  created_at
  ── NO slot, NO version_number, NO next_version: the envelope IS the identity, so there is
     no "newer version of this". A different derivation is a different envelope.

DecisionVersion                             IMMUTABLE (S13) · PROJECT-SCOPED
  id            : uuid, assigned            PK
  project_id, kind, member                  FK → Decision
  envelope      : bytes16
                  UNIQUE (project_id, kind, member, envelope)   ◄── project-scoped, §4.2a
  shared_id     : uuid | null               FK → SharedDerivation, for the shared kinds;
                                            then payload_ref mirrors the shared row
  version_number: bigint                    UNIQUE (project_id, kind, member, version_number)
                                            ◄── §10.2a · the SEMANTIC ordering, not created_at
  payload_ref   : ContentRef                → object storage
  payload_hash  : bytes32
  env           : jsonb                     model, prompt_version, taxonomy_version,
                                            frontier, capability_decl_version?  (§5)
  created_at                                OBSERVABILITY ONLY — no relation reads it
  ── no UPDATE. `status` and `freshness` are NOT columns (C4).

DependencyEdge                              the graph E4 walks
  version_id    : uuid                      FK → DecisionVersion
  depends_on_id : uuid                      FK → DecisionVersion
  ── PK (version_id, depends_on_id); INDEX on depends_on_id for the stale query
  ── recorded at write time from the envelope's `inputs`, never inferred later

Commitment                                  domain truth
  id            : uuid                      PK
  project_id    : uuid
  version_set_hash : bytes32
  environment   : jsonb    models · prompt_versions · taxonomy_version ·
                           source_versions · template_id · template_content_hash ·
                           capability_decl_version              ── invariant 8, all five
  environment_hash : bytes32
  ── UNIQUE (project_id, version_set_hash, environment_hash)      ◄── Rev. 3, §9.4
     Rev. 2 keyed on the version set alone, so re-approving after a TEMPLATE EDIT
     returned a commitment pinning a template_content_hash that no longer exists,
     with the OLD feasibility in `disclosed`.
  approved_by   : text
  disclosed     : jsonb    the feasibility shortfalls the user saw    ◄── H2 evidence
  approved_extent : jsonb  ◄── Rev. 7 · the extent the user actually approved, per module
                           and per section, PINNED at approval. `BriefInputs` reads THIS,
                           never a recomputed value — see §9.4a
  created_at

CommitmentMember                            per-member, keyed (S10) — closes B2
  commitment_id : uuid
  kind          : DecisionKind
  member        : text NOT NULL, default ''   same '' root sentinel as Decision.member
  version_id    : uuid
  ── PK (commitment_id, kind, member)

Claim                                       D17 — one row per reusable result key
  key           : bytes16                   PK      claim_key(domain, identity) — §5.12a
  domain        : ClaimDomain               ◄── Rev. 8 · BROADER than DecisionKind:
                  'decision:<DecisionKind>' | 'memo' | 'document'
                  | 'render' | 'source_extract' | 'routing'
                  ── Rev. 7 declared claims for render, source_extract and routing while
                     this column admitted none of them, and gave them no key construction.
                     Three workflows outside the schema that coordinated through it.
                     `scope_tier`, `frame` and `structure` remain DecisionKinds that are
                     SHARED — a PROPERTY (§5.2a is_shared), never a separate domain.
  state         : 'RESERVED' | 'COMMITTED'
  epoch         : bigint                    the FENCING TOKEN · monotonic **over the lifetime
                  of a claim ROW**, not over the key for all time ◄── Rev. 10, and the
                  qualification matters: RECONCILE (§7.3c) inserts a replacement row at
                  epoch 1 after a loss, which the unqualified wording forbade. Safe because
                  a reconciled row is born COMMITTED and therefore admits no transitions —
                  its epoch is never compared against anything
  lease_until   : timestamptz | null        null iff COMMITTED
  owner         : text                      worker id + task id, for diagnosis only
  result_ref    : text | null                null iff RESERVED
  created_at, committed_at

MemoIndex                                   the Content Memo's index half
  key           : bytes16                   PK = the section envelope
  project_id    : uuid                      for quota and GC, not for identity
  payload_ref   : ContentRef                content-addressed
  payload_hash  : bytes32
  covered       : text[]                    from check_unit, for the resume report
  created_at
  ── the CLAIM is what makes it write-once; this table carries no state machine

Document                                    IDENTIFIED BY CONTENT · Rev. 3
  id            : uuid                      PK
  project_id    : uuid
  module_id     : text
  content_hash  : bytes32
                  UNIQUE (project_id, module_id, content_hash)   ◄── the domain's
                  "content identity", now ENFORCED. Rev. 2 labelled it and left only
                  construction_key unique, so two rows could hold identical content.
  payload_ref   : ContentRef
  seq           : bigint    UNIQUE (project_id, module_id, seq)
                            ◄── §10.2a · the ordering superseded(d) reads. Bumped only
                                when a genuinely NEW content hash appears
  created_at                                observability only

DocumentConstruction                        many construction keys → one Document
  construction_key : bytes16                UNIQUE                  ◄── §5.8, the D17 claim key
  document_id   : uuid                      FK → Document
  builder_version : text                    which builder produced this attempt
  ── a builder refactor that changes the hash but not the output yields a SECOND
     construction key and the SAME Document — which is what §5.8 intends

DocumentProvenance                          many commitments → one Document
  document_id   : uuid
  commitment_id : uuid
  ── PK (document_id, commitment_id)                                  §0.3

ArtifactIndex
  id            : uuid                      PK
  document_id   : uuid
  template_id   : text
  template_content_hash : bytes32
  render_env_hash : bytes32                 captured IN the engine [OBSERVED]
  capability_decl_version : bytes32          ◄── Rev. 7 · ALSO captured in the engine, in the
                          same call, from the same source. Without it export could not
                          resolve "the artifact under the environment this Commitment
                          pinned" — the Commitment stores capability_decl_version and
                          ArtifactIndex stored only render_env_hash, with no mapping.
                          INDEX (document_id, capability_decl_version)
                          ── these cannot drift: §12.1 nests the two hashes, so
                             capability_decl_version determines render_env_hash
  bytes_hash    : bytes32
  ── UNIQUE (document_id, render_env_hash)        ◄── Rev. 10 · STRENGTHENED
     Rev. 9 keyed on (document_id, render_env_hash, bytes_hash), so the DATABASE permitted
     two artifacts for one (document, environment) whenever Chromium's bytes differed —
     only the render claim prevented it, and a protocol-only guarantee is one bug from
     being lost. Now the invariant is enforced where it cannot be bypassed, and a
     second render adopts the existing row (§7.3c ②) instead of inserting.
     `bytes_hash` remains a recorded column and part of S9's content identity.
  seq           : bigint    UNIQUE (document_id, template_id, seq)
                            ◄── §10.2a · the ordering superseded(a) reads, keyed
                                (Document, template) per CF-8 — NOT the full render env
  payload_ref, size, page_count, scale, overflows : jsonb
  created_at                                observability only

Task                                        process state
  id            : uuid                      PK
  project_id, user_id
  kind          : 'source_extract'|'plan'|'correct'|'generate'|'render'|'export'
  target        : jsonb                     e.g. {module_id} for generate
  idempotency_key : bytes16                 UNIQUE (project_id, kind, idempotency_key)
  state         : 'accepted'|'leased'|'running'|'succeeded'|'incomplete'
                  |'failed_transient'|'failed_terminal'|'cancelled'    ◄── §8.7
  cancel_requested : bool, default false     observed at step boundaries and heartbeats
  epoch         : bigint                    T8 — Task fencing
  lease_until   : timestamptz | null
  owner         : text | null
  attempts      : int
  budget        : jsonb   {max_calls, max_wall_ms}
  attempt_started_at : timestamptz             ◄── Rev. 7 · the WALL budget is measured from
                          here, not accumulated from call durations, so waiting on a
                          reservation (§7.7) counts automatically with no accounting op
  calls_admitted : int, default 0              ◄── Rev. 8 · ADMISSION control, §8.6a.
                          Conditionally incremented BEFORE each call; reset by RESUME.
                          Not a spend record — the ledger is. May run conservatively
                          high if an admitted call dies before writing its row.
  resumes       : int, default 0                                    ◄── §8.8
  ── NO `spent` / `spent_lifetime` columns. Both were denormalised aggregates with two
     writers and no window; they are now derived from CallLedger (§8.8a). Rev. 6 fenced
     their update on `epoch`, which silently DISCARDED a fenced worker's paid call.

SourceExtraction                            ◄── Rev. 8 · GLOBAL, content-addressed (§9.8a)
  content_hash  : bytes32                   the source bytes
  extractor_version : text
  ── PK (content_hash, extractor_version)                           the claim identity
  outcome       : 'extracted' | 'infeasible'  ◄── Rev. 9 · P8: the conditional capability's
                                            non-applicability is RECORDED, not an absence
  payload_ref   : ContentRef | null          null iff infeasible
  payload_hash  : bytes32 | null
  reason        : text | null                why infeasible, for the user
  created_at
  ── no project, no mutable state: identical bytes extract identically for everyone, and
     each extractor version gets its OWN immutable row. Rev. 8 recorded only successes and
     wrote failure into a Source column, which is what created §9.8b's race.

RoutingResult                               ◄── Rev. 8 · the correction router's own output
  envelope      : bytes16                   PK — §5.9a's routing envelope
  project_id    : uuid
  payload_ref   : ContentRef                reading · targets · replacement payloads
  created_at
  ── NOT a DecisionVersion: no slot, no version_number, no dependency edges, and no
     Commitment names it. The replacement payloads it carries BECOME DecisionVersions
     (§9.3 step 3); the routing itself is a memoised computation kept because it cost
     ~97 s [MEASURED] and because §3's "claimed vs actual" audit reads it.

UserQuotaBucket                             ◄── Rev. 9 · ADMISSION control, §8.6a
  user_id       : text
  window_start  : timestamptz               floor_hour(now())
  ── PK (user_id, window_start)
  calls_admitted : int, default 0
  ── Rev. 8 gave the admission UPDATE and never added the table, so the admission
     subsystem was not transcribable. Retention: §10.6.

CallLedger                                  ◄── Rev. 7 · one row per model call attempt
  id            : uuid                      PK
  origin        : 'task' | 'sync'            ◄── Rev. 10 · §8.6b. Intake runs model calls
                  synchronously, with no Task, so a non-null task_id could not represent
                  them and Rev. 9's spend formulas could not see them at all.
  operation     : text                       e.g. 'situation' | 'ask' | 'frame' — what the
                  call was for when there is no Task to name it
  task_id       : uuid | null                ◄── Rev. 8: a RECORDED VALUE, no FK.
                  NULL iff origin = 'sync'.  INDEX (task_id, task_epoch)
                  ── Rev. 7 declared `FK → Task` while GC collects Tasks at 30 days and
                     retains the ledger a year. Postgres defaults to NO ACTION, so the
                     delete would fail; CASCADE would destroy the ledger the quota and
                     audit depend on. An append-only audit row must OUTLIVE its subject,
                     so it carries values, not references — see the self-containment rule
  task_kind     : TaskKind                  denormalised, so a collected Task leaves meaning
  project_id    : uuid                      denormalised, same reason
  user_id       : text                      INDEX (user_id, started_at)  → windowed quota
  task_epoch    : bigint                    which attempt incurred it — RECORDED, never
                                            used to reject the row (§8.8a)
  provider, model_id : text
  prompt_version : text
  started_at, ended_at : timestamptz         INDEX (started_at) for the rolling window
  wall_ms       : int
  tokens_in, tokens_out : int
  outcome       : 'ok'|'provider_unavailable'|'rate_limited'|'provider_refused'
                  |'attempt_deadline'|'output_truncated'
  envelope      : bytes16 | null             which derivation this call served, for §17
  ── APPEND-ONLY, and SELF-CONTAINED: no foreign keys, because every entity it refers to
     is collectable on a shorter horizon than the ledger's own. The rule, since it applies
     to any audit row added later:
       **an append-only record whose referents are collectable stores values, not
         references** — otherwise its retention and theirs are in contradiction.
  ── This is the single source for every spend REPORTING question (admission is §8.6a):
       spent(T)          = Σ over (task_id = T, task_epoch = current)
       spent_lifetime(T) = Σ over (task_id = T)                     ── ALL epochs
       quota(user, W)    = Σ over (user_id, started_at > now() − W)  ── the window §14 needs
  progress      : jsonb   per-member state, for the resume report
  failure       : jsonb | null   {class, message, per_member_reasons}
  created_at, updated_at
```

## 4.2a Who owns a shared derived result — the Rev. 3 fix

Rev. 2 said `scope_tier`, `frame` and `structure` are content-addressed and shareable, and stored
them as ordinary `DecisionVersion`s. **Those two statements were incompatible**, in two ways:

```
① UNIQUE (kind, member, envelope) was GLOBAL, so Project B could not insert its own row
   for an envelope Project A already owned. B had nothing to reference.

② Worse, and not obvious: version_number is per SLOT (project, kind, member), and
   stale(v) means "a recorded dependency has a HIGHER version_number in that slot".
   If B's projection depended on A's structure version, then A bumping its derive
   prompt would create version 2 in A's slot — and STALE B's approved plan.
   Staleness would leak across projects.
```

② is why "just let `DecisionVersion` be globally reusable" does not work. The fix is a **hybrid**,
and each half earns its place:

```
SharedDerivation   GLOBAL, envelope-keyed        holds the PAYLOAD and the model call
                   no versions, no slot          → one call across all projects (D11)

DecisionVersion    PROJECT-SCOPED pointer        shared_id → SharedDerivation
                   own slot, own version_number  → staleness stays inside one project
                                                 → a Commitment pins a LOCAL version id,
                                                   so the domain model is unchanged
```

| Question the review raised | Answer |
|---|---|
| What does B reference? | **B's own `DecisionVersion`**, whose `shared_id` points at the shared row. B never references A's version |
| Can a project's `Decision` point at another project's version? | **No** — and that is the point |
| What if A is deleted? | The `SharedDerivation` is global and unowned; it survives. Its payload is content-addressed. GC only when no pointer references it `CHOICE` |
| Authorization? | A project's plan only ever reads its own version rows, so project isolation (§13.1) is unaffected by sharing |
| What is duplicated? | One small pointer row per project. **Not** the payload, and **not** the model call — which is the only expensive part |

**Two claims, two layers, and the reservation sits on the shared one.** The claim key for a shared
kind is its envelope, so the D17 single-flight is global: two projects racing the same structure
derivation produce **one** model call (§7.5 R1 applies verbatim). The pointer insert is then a
local, cheap, second publication.

```
PUBLISH(shared kind):
  BEGIN
    ① claim CAS on the ENVELOPE                       global single-flight
    ② INSERT SharedDerivation (or read the existing)
    ③ INSERT DecisionVersion(shared_id=…, version_number=bump_slot(project,…))
       INSERT DependencyEdge × n
  COMMIT
```

A second project cannot reach ① — its claim is already `COMMITTED` — so it runs **`ATTACH`**
(§7.3b) instead: no call, no payload write, one pointer insert. Rev. 3 described this outcome
without defining the operation, which was a real hole.

## 4.3 Object storage — large, immutable, content-addressed

```
ContentRef = "<bucket>/<kind>/<sha256-hex>"            CHOICE: hex, not base64url — greppable

kinds:  decision-payload · memo-payload · document · artifact-pdf
        artifact-html · source-payload · source-extract · export-zip
```

**Content-addressed, not key-addressed, and this follows from fencing.** `DECIDED`. If a payload
were stored at a path derived from its envelope, two racing workers would write to the **same
path** and a fenced-out worker could overwrite the committed payload's bytes. Content addressing
makes each write land at its own path; only the committed claim references one; the loser's
payload is an orphan. See §7.4.

## 4.4 Immutability, enforced rather than documented

| Rule | Mechanism | Not this |
|---|---|---|
| `Utterance` append-only (S11) | revoke `UPDATE`/`DELETE` on the table | code review |
| `DecisionVersion` immutable (S13) | revoke `UPDATE`; envelope is `UNIQUE` | an `updated_at` column |
| `Document`, `Artifact` immutable | write-once object paths; index rows insert-only | — |
| Committed `Claim` never re-written | `WHERE state = 'RESERVED'` in the commit statement | application check |
| `status`/`freshness`/`supersession` never stored (C4) | **no such columns exist** | a nullable column "for now" |
| `Module`/`Section` identity assigned (S14) | uuid generated at partition time, stored in the payload | array index |

The last row is CF-6's fix and the one most likely to be undone by convenience: V1 keys
generation by `_job_key(project_id, index)` `[OBSERVED]`, and `ml-weekend` went 5 modules → 3 in
one correction `[MEASURED]`.

---

# 5. Envelope and identity design — **closes U1**

## 5.1 The construction, exactly

```
Envelope = first 16 bytes of SHA-256( canonical_json({
    "v":      1,                     envelope format version
    "kind":   <DecisionKind | "memo" | "document">,
    "member": <member identity, or "" for a root decision>,
    "inputs": { ... },               per-kind, below
    "env":    { ... }                per-kind, below
}) )
```

**Canonical JSON** `DECIDED`: UTF-8; keys sorted by Unicode code point; no insignificant
whitespace; strings NFC-normalised; integers only (no floats — a float's textual form is not
stable across languages); arrays ordered where order is semantic and **sorted** where it is not,
with the per-kind spec stating which. Version ids appear as lowercase hex, never as objects.

`CHOICE` — 128 bits, not 256. Collision probability is negligible at any plausible corpus size and
the key is half the width in every index. *Alternative:* full 256-bit; rejected for index size.
`v: 1` makes a widening non-breaking.

**`member` is never `null`, in the envelope or in the column.** `DECIDED` — the canonical root
sentinel is the empty string `""`. Two reasons, and the second is the load-bearing one:

1. Postgres forbids a nullable primary-key column, so `PK (project_id, kind, member)` could not be
   transcribed literally.
2. **Postgres treats `NULL`s as distinct in a `UNIQUE` constraint.** With `member = NULL`,
   `UNIQUE (project_id, kind, member, envelope)` would admit two rows for the same envelope — and
   that constraint is §11's independent guard behind claim loss. A nullable member would have
   disabled the safety net silently.

`""` is unambiguous because every real member is a uuid or a `"<level>:<uuid>"` string, so no
collision with a legitimate value is possible. `CHOICE` — `""` over a sentinel like `'-'` or
`'∅'`: it sorts first, it is obviously not a uuid, and it needs no explanation in a query.

## 5.1a What the envelope addresses, and the limit of that claim

An envelope addresses the output of a function. **Rev. 6 never pinned the parameters that make that
function's output vary**, which is a real gap in U1's closure:

```
env, for every model-backed kind, now includes:
  model_id         provider/model, exact
  prompt_version
  taxonomy_version  where the kind reads a vocabulary
  decode_params     {temperature, top_p, max_tokens, seed?}      ◄── Rev. 7
```

**And the honest limit, stated rather than implied.** Even with all four pinned, the envelope does
**not** promise identical bytes on re-derivation:

| | |
|---|---|
| the envelope **does** guarantee | at most one committed result per key, and that a `HIT` returns *a* result derived under exactly this declared environment |
| it does **not** guarantee | byte-identical regeneration. `temperature > 0` is non-deterministic by construction, and a provider may revise a model behind a stable `model_id` without notice |

§E2 already said *"a reused result is **a** valid result, not **the** result"* — this is that sentence
made operational. The consequence for `Commitment`: pinning the environment makes an approval
**auditable** (you can see exactly what produced it) and **not** reproducible (you cannot necessarily
recreate it). That distinction is worth being blunt about, because invariant 8's phrase *"pins its
whole derivation environment"* invites the stronger reading.

`UNKNOWN` — **N4:** whether any provider in use exposes an immutable model revision id. If one does,
it belongs in `env` and auditability becomes reproducibility for that provider. Not assumed here.

## 5.2 Two envelope families

`DECIDED`, and this is what makes D11's sharing real rather than nominal.

| Family | Inputs reference | Shareable across projects | Kinds |
|---|---|---|---|
| **content-addressed** | content hashes and normalised strings | **yes** | `scope_tier`, `frame`, `structure` |
| **version-addressed** | `DecisionVersion` ids | no | everything else |

*(Rev. 1's table said `structure` only, while §5.10 correctly labelled `scope_tier` as
content-addressed — the table contradicted the spec. All three per-subject classifications belong
to the same family, and `frame` is content-addressed as of §6.3's correction.)*

Why the split: a content-addressed envelope for `projection` would need the situation's *content*,
and two projects never have the same transcript, so sharing would never occur and the extra
indirection would buy nothing. A version-addressed envelope for `structure` would embed
project-local uuids and make sharing **impossible**, which defeats D11.

**`memo` is a third shape and worth naming**: version-addressed by family, but its inputs are a
*content* hash of the brief rather than version ids (§5.7a) — because the question it answers is
*"is this the same content to write?"*, not *"is this the same project state?"*

**And "everything else" means every *envelope* kind, not every reusable result.** `render`,
`source_extract` and `routing` are reusable results that are **not envelope kinds at all** — they are
claim domains with their own identities (§5.12a, §5.10). Rev. 8 widened the claim system without
qualifying this sentence, which read as though the two families covered the whole space.

### 5.2a `is_shared(kind)` — one predicate, and it is a property, not a kind

```
is_shared(kind)  ⟺  kind ∈ { scope_tier, frame, structure }        a static set
```

**Rev. 4 introduced a `SHARED` pseudo-kind in `PUBLISH` and left `Claim.kind` as the literal
`'decision'`.** Three names for one thing, none of them implementable together. Withdrawn: there is
one decision domain, and sharedness is a predicate over it.

| | Value |
|---|---|
| `Claim.kind` | `DecisionKind \| 'memo' \| 'document'` — the full domain |
| `SharedDerivation.kind` | any `kind` with `is_shared(kind)` |
| `PUBLISH` branch | `is_shared(kind)` selects the shared path (§7.3a) |
| `step()` selection | `is_shared(kind)` selects `step_shared` (§7.3b) |

The set is static because it is a *design* statement, not configuration: these are the three
decisions whose output is a property of the subject rather than of the project (§0.1, §6). Adding a
fourth is a design change requiring the same argument, not a config edit.

## 5.3 `structure` — `SubjectStructure`

```
inputs:
  subject_key      normalised subject (§5.3.1)
  frame            {axis, value} | null                          ◄── U2, §6
  source_set       sorted list of {content_hash, kind, extractor_version} for sources
                   bound to scope/terminology authority for this subject
                                                                  [LOCKED: Foundation §3.1]
                   ── extractor_version is Rev. 10. See §5.3b: structure consumes the
                      EXTRACTED skeleton, not the raw bytes, so the extractor is an input
env:
  model_id         provider/model, exact
  prompt_version   e.g. "derive_v2"
  taxonomy_version relation-type vocabulary version
  frontier         expansion limit — the "hard expansion limit … a safety net" [LOCKED §8]
```

**Not in the envelope, and each exclusion is a claim:**

| Excluded | Why |
|---|---|
| `project_id`, `user_id` | would make sharing impossible — the point of D11 |
| utterance ids or text | the subject is the only part of the transcript this consumes |
| `purpose`, `capacity`, `target_capability`, `job` | §8's projected column; they belong to Projection |
| **`entry_point`** | **granularity is projected** `[LOCKED §8]`. §1's *"API foundations never in the graph"* is a granularity failure, and Projection owns it |
| `capability_declaration` | Feasibility is computed, never derived (D5) |
| `template` | presentation; §12 |

**Changes that make it different:** a different subject after normalisation · a different frame ·
adding, removing or re-versioning any bound source · a new model, derive prompt, taxonomy version,
or frontier limit.

**Example.** Two students, different universities, both *"Indian Contract Act 1872"*, neither
uploading a source: `subject_key` equal, `frame = {statute, "IN-ICA-1872"}` equal, `source_set`
empty, env equal → **same envelope, one derivation, the second project pays nothing.** Add a
syllabus to one and the envelopes diverge — which is also the privacy property (§13.2).

### 5.3b Does `structure` depend on the extractor? **Yes** — and Rev. 9 left it unstated

The review flags this as an ambiguity. It is resolvable from the references rather than being a
judgment call, so Rev. 10 settles it rather than recording a choice.

**Structure consumes the extracted skeleton, not the raw bytes.** §0's investigation is explicit about
what the structural use of a source *is*: *"an ordered list of addressable units — section numbers,
chapter names, syllabus items"*, and the whole point is checkability — *"a missing section is a fact, not
a judgment"*. HY-2 is *"does a supplied structural skeleton improve plans"*, and §9.8a names the
extraction payload a `SourceStructure`. A model cannot read a PDF's bytes; it reads what extraction
produced.

So the dependency is real, and Rev. 9's envelope was wrong:

```
Rev. 9   source_set = [{content_hash, kind}]
            ↓
         extractor v1 → skeleton A → structure S
         upgrade to v2 → skeleton B → structure envelope UNCHANGED → S reused
            ↓
         a better extraction is derived and then silently ignored
```

`DECIDED` — **`extractor_version` is part of each source's contribution to the structure envelope.**
Consequences, both intended:

| | |
|---|---|
| an extractor upgrade | invalidates structures derived **from sources** — correct, the skeleton changed |
| a project with **no** sources | unaffected: `source_set` is empty, so no extractor appears. **This is most of the corpus** — 1 of 10 cases had a source in play `[MEASURED]` |
| the extraction itself | already immutable per `(content_hash, extractor_version)` (§9.8b), so both skeletons remain and each structure stays reproducible against the one it used |

*Alternative considered and rejected:* declare extractor changes *representation-preserving* for
structure, so reuse is intentional. That would be a claim about every future extractor change, which
nothing supports — the first extractor improvement anyone makes will be one that extracts **more**
units, which is precisely a change structure should see.

### 5.3.1 `subject_key` normalisation

`CHOICE`, and it is deliberately conservative: lowercase, NFC, collapse internal whitespace, strip
surrounding punctuation. **No stemming, no synonym mapping, no embedding.**

Rationale: B1 measured breadth tracking *how richly `interpret` restated the subject* — `'agentic
AI'` → 29 concepts, an 11-word restatement → 42 `[MEASURED]`. Aggressive normalisation would
collapse genuinely different subjects into one asset and make that variance **silent instead of
visible.** Conservative normalisation under-shares; over-sharing is a correctness fault and
under-sharing is only a cost.

**Consequence to accept:** `"Indian Contract Act"` and `"Indian Contract Act 1872"` are different
keys and derive twice. `UNKNOWN` whether that matters in practice; measurable from the
`reused` flag in §14 once there is traffic. Note `SubjectRef` in the domain model already removes
free-text restatement, which is the real fix and lives upstream.

## 5.4 `projection`

```
inputs:
  structure_version_id
  situation_version_id
  job_version_id
  scope_tier_version_id | null
env: model_id, prompt_version, taxonomy_version
```

Not included: `capability_declaration` (computed), any partition or scope version (downstream),
`template`. **This is where `entry_point` first enters**, via `situation_version_id`.

## 5.5 `scope`

```
inputs: projection_version_id, situation_version_id, job_version_id
env:    model_id, prompt_version, taxonomy_version
```

Not included: `density_constants` — `Extent` is computed from the scope, not derived with it (C1),
so recalibrating the constants changes `Extent` **without** invalidating `scope`. That is the
whole point of C1 and it saves a full re-plan per calibration run (OQ-2).

## 5.6 `partition`, `sections`, `ordering`

```
partition
  inputs: scope_version_id, situation_version_id, job_version_id
  env:    model_id, prompt_version, taxonomy_version
  member: ""                                 root — §5.11a

sections                                     member = module_id (assigned, S14)
  inputs: partition_version_id
          module_id
          module_covers_hash                 sorted concept ids + depths + needs
          situation_version_id, job_version_id
  env:    model_id, prompt_version, taxonomy_version

ordering                                     member = "modules" | "sections:<module_id>"  §5.11a
  inputs: member_producer_version_id         partition, or that module's sections
          member_identity_list_hash          ORDERED is not semantic here — sorted
          situation_version_id, job_version_id
          bound_constraints_hash             the Constraints targeting `ordering`
  env:    model_id, prompt_version, taxonomy_version
```

`module_covers_hash` is included **so a re-partition that leaves one module untouched reuses that
module's sections.** Without it, `partition_version_id` alone would invalidate every module's
sections on any partition change — and corrections re-partition routinely (`ml-weekend`, 5 → 3
`[MEASURED]`).

`bound_constraints_hash` on `ordering` is the channel §0 measured as missing: *"section wise"* →
`depth_register`, and `traversal.why` then explained a **derived** order `[MEASURED]`. With the
constraint in the envelope, a stated ordering both binds and invalidates correctly.

## 5.7 `memo` — one generated section

```
inputs:
  section_id                                 assigned, S14
  brief_inputs_hash                          EXACTLY what the brief renders — §5.7a
env:
  model_id, prompt_version, max_tokens
```

### 5.7a `brief_inputs_hash` — Rev. 2 narrows this, by T6's own logic

Rev. 1 listed `situation_version_id` and `job_version_id` as inputs. The review is right that those
are **global**: a correction targeting `job` changes every memo envelope, including modules the
correction never touched.

**Two things are true and Rev. 1 only stated the first clearly.**

1. For a **module-local** correction — the case Rev. 1 described — neither `job` nor `situation` is
   targeted, so their versions do not move and only module 5's memos change. The claim was
   accurate for what it described.
2. For a correction that **does** change `job` or `situation`, every section's envelope changes —
   and that is **correct**, not a defect. If the job goes from `construct` to `orient`, every
   section must be rewritten. Re-spending 40 sections is the right answer, not a regression.

But chasing it exposed a real over-inclusion. T6's justification is *"the brief **is** the input, so
the envelope should be the brief"* — and a whole `situation` version is broader than the brief.
V1's `_unit_brief` renders a specific list `[OBSERVED]`: the request, purpose, entry point, target
capability, stated constraints, the heading, `why_here`, the approved size, and each concept with
its depth and `why`. A correction to an axis the brief does **not** render should not invalidate
written content.

```
BriefInputs = {
  request, purpose, entry_point, target_capability,     from the situation
  stated_constraints,                                    rendered, so included
  job,                                                   HY-1 is open; if job gains
                                                         consequences it changes writing
  heading, why_here, approved_extent,                    from the section decision
  concepts: [ {name, depth, why, representation_need} ], ordered
  disclosed_shortfalls                                   the approved shortfalls for THESE
                                                         needs (§9.7)
}
brief_inputs_hash = sha256(canonical_json(BriefInputs))
```

**The implementation rule that keeps this honest:** the brief renderer and the hash **take the same
struct**. One `BriefInputs` value, two consumers. `DECIDED` — if the hash were computed from a
separately maintained field list, it would drift from what the prompt renders and the envelope
would lie. A test asserts the two agree (§15.2).

**Excluded, and now provably so:** `capacity` and `depth_register` (not rendered by the brief),
sibling sections (independence is the measured property), `commitment_id` (§8.1's asymmetry), and
`template` (presentation).

**`commitment_id` is deliberately absent.** `DECIDED`, **T6**, and it is the largest avoidable
cost in the system. The measured project has **8 modules and 40 sections** `[MEASURED]`; a
correction touching module 5 mints a new commitment, and a commitment-keyed memo would re-spend
**all 40 sections** — 40 × ~65 s. Section-content keying re-spends only what changed.

The justification is measured, not aesthetic: `_unit_brief(request, situation, order, missing)`
reads the request, the situation and **its own order** — nothing from a prior section
`[OBSERVED]`. So the brief *is* the input, and the envelope should be the brief.

Not included: sibling sections (independence is the measured property); `template` (presentation);
the commitment (above); `capability_declaration` — the *disclosed shortfall* is in the envelope,
which is the part that changes what is written.

## 5.8 `document` — construction identity

```
construction_key = envelope(
  kind:   "document",
  member: module_id,
  inputs: {
    front_matter_hash      title · subtitle · assumed_entry · target_capability ·
                           marked gaps — all PLAN-derived, never model-derived [OBSERVED]
    section_memo_keys      ORDERED list of memo envelopes, in the Ordering's order
  },
  env: { builder_version }
)
```

**`builder_version` is in the environment** because the Document Builder is a pure function whose
output changes when its *code* does — front-matter defaults, block ordering, a validation rule.
This is the same discipline that puts model + prompt in a memo envelope and renderer build +
template content hash in the render environment. `CHOICE` for how it is derived: a content hash
over the builder module's source, exactly as `engine/render.py:_template_version` already hashes a
template `[OBSERVED]`. *Alternative:* a hand-bumped constant; rejected — hand-bumped versions get
forgotten, and this one is invisible when wrong.

**`commitment_id` is absent, and §0.3 explains why:** including it would mint a new Document on
every re-approval and supersede every prior artifact for nothing. The commitment is recorded in
`DocumentProvenance`, many-to-one.

**Ordered, not sorted** — section order is semantic here, and two orderings of the same sections
are different documents.

**The construction key is an idempotency key, not the Document's identity** — and Rev. 2's schema
did not honour that distinction:

```
Document              identified by CONTENT     UNIQUE (project, module, content_hash)
DocumentConstruction  identified by the KEY     UNIQUE (construction_key) → document_id
```

Two construction keys can legitimately reach the same content — a builder refactor that changes
`builder_version` without changing the output is the obvious case. Under Rev. 2 that produced **two
Document rows with identical bytes**, each bumping `seq`, so `superseded(d)` would report a new
version the reader cannot distinguish from the old one. Now the second construction maps onto the
existing Document and `seq` is untouched.

`PUBLISH` for a document therefore reads: claim CAS → upsert `Document` on content hash (bumping
`seq` only on insert) → insert `DocumentConstruction` → insert `DocumentProvenance`. One
transaction (§7.3a).

## 5.9 `artifact` — identity, not an envelope

An artifact is not derived from a model call, so it has no envelope; it has **content identity**
(S9):

```
artifact CONTENT identity  = (document_id, render_env_hash, bytes_hash)        S9
uniqueness CONSTRAINT      = (document_id, render_env_hash)      ◄── Rev. 10, STRICTER
   ── one artifact per document × environment, enforced by the DB and not only by the
      render claim. The bytes_hash stays part of what an artifact IS; it is not part of
      what makes two artifacts distinguishable, because two byte-different renders of one
      document under one environment are a duplicate, not a pair.
render_env_hash   = hash(playwright_version, chromium_build, template_id,
                         template_content_hash, font_set_hash, engine_version)
supersedes        = ordering over ArtifactIndex.seq, unique per
                    (document_id, template_id)               CF-8 · §10.2a
                    ── Rev. 3 left `created_at` in this line while §10.2a had already
                       made it observability-only. The schema's `seq` is authoritative.
```

## 5.9a `situation`, `job`, `scope_tier`, `frame`, `routing` — the five Rev. 6 under-specified

§5.1 said per-kind fields are *"defined below"* and the subsections covered `structure`, `projection`,
`scope`, `partition`/`sections`/`ordering`, `memo` and `document`. **Five kinds never got the
field-by-field treatment**, so §15.2's golden tests had nothing to assert for them — and `routing` was
referenced by §9.3 and defined nowhere at all.

```
situation                                    version-addressed, project-scoped
  inputs: transcript_hash        ordered (ord, role, text) of every Utterance
  env:    model_id, prompt_version, taxonomy_version, decode_params
  NOT:    sources (a source is not testimony) · capability declaration (computed)
          frame or tier (they read FROM this — §9.1's ordering)

job                                          its own Decision — CF-2
  inputs: transcript_hash, situation_version_id
  env:    model_id, prompt_version, taxonomy_version, decode_params
  NOT:    structure (job does not depend on the subject's shape)

scope_tier                                   CONTENT-addressed, shareable
  inputs: subject_key, purpose_reading, target_capability_reading, source_set
  env:    model_id, prompt_version, decode_params
  NOT:    project_id · entry_point · capacity · the transcript itself
          ── readings, not version ids, so two projects phrased alike share the answer

frame                                        CONTENT-addressed, shareable — §6.3
  inputs: subject_key, source_set, frame_selecting_readings {subject, purpose}
  env:    model_id, prompt_version, decode_params
  NOT:    candidates (no catalogue exists — §6.3a) · entry_point · capacity

routing                                      version-addressed — the correction router
  inputs: correction_utterance_id
          current_decision_set_hash    the (kind, member, version_id) triples it was shown
  env:    model_id, prompt_version, taxonomy_version, decode_params
  NOT:    the targets it returns (that is the output)
  ── keyed on the utterance AND the set it routed against, because the same sentence
     against a different plan is a different routing problem
```

**`decode_params` is new in Rev. 7 and applies to every model-backed kind** — see §5.1a.

## 5.10 Summary table, and the test that makes U1 safe

| Kind | Family | Member | Model call | Key inputs |
|---|---|---|---|---|
| `situation`, `job` | version | — | yes | transcript |
| `scope_tier` | **content** | — | yes | subject, purpose, target_capability, sources |
| `frame` | **content** | — | yes | subject, sources, frame-selecting readings (§6.3) |
| `structure` | **content** | — | yes | subject, frame, sources — **no situation** (§0.1) |
| `projection`, `scope`, `partition` | version | — | yes | upstream version ids |
| `sections` | version | module_id | yes | partition version + `module_covers_hash` |
| `ordering` | version | (level, module_id?) | yes | member producer + bound constraints |
| `memo` | version | section_id | yes | **`brief_inputs_hash` only** (§5.7a) |
| `document` | version | module_id | **no** | front matter + ordered memo keys + builder version |
| **`routing`** | version | — | yes | correction utterance + the decision set it routed against (§5.9a) |

**Three claim domains are not envelope kinds at all**, and Rev. 7 left them out of this table while
giving them claims (§5.12a):

| `ClaimDomain` | Keyed by | Result row | Model call |
|---|---|---|---|
| `render` | `{document_id, render_env_hash}` | `ArtifactIndex` | **no** — a browser, not a model |
| `source_extract` | `{source_content_hash, extractor_version}` | `SourceExtraction` | depends on the extractor |
| `routing` | its envelope above | `RoutingResult` | yes |

## 5.11 The canonical identity table — one source, referenced everywhere

**Rev. 3 fixed the identities in §8.1 and §9.4 and left the old formulas printed in §10.5 and
§18.3.** The review is right that the fix is not correcting two lines: it is having one table that
every other section points at. **This is that table. Nothing else in this document may restate an
identity; it must link here.**

| # | Thing | Identity | Guard |
|---|---|---|---|
| I1 | `DecisionVersion` | `(project_id, kind, member, envelope)` | UNIQUE |
| I2 | `SharedDerivation` | `(kind, envelope)` — global, no project | UNIQUE |
| I3 | `DecisionVersion` ordering | `(project_id, kind, member, version_number)` | UNIQUE; `bump_slot` |
| I4 | `Claim` | **`claim_key(domain, identity)`** — global, six domains (§5.12a) | PK |
| I5 | `MemoIndex` | section envelope = `(section_id, brief_inputs_hash)` + env | PK |
| I6 | `Document` | **content**: `(project_id, module_id, content_hash)` | UNIQUE |
| I7 | `DocumentConstruction` | `construction_key` → many-to-one onto I6 | UNIQUE |
| I8 | `Document` ordering | `(project_id, module_id, seq)` | UNIQUE |
| I9 | `Artifact` | **content identity** `(document_id, render_env_hash, bytes_hash)` (S9), constrained to **one per `(document_id, render_env_hash)`** — Rev. 10, §4.2 | UNIQUE on the pair |
| I10 | `Artifact` ordering | `(document_id, template_id, seq)` | UNIQUE |
| I11 | **`Commitment`** | **`(project_id, version_set_hash, environment_hash)`** | UNIQUE |
| I12 | `Utterance` order | `(project_id, ord)`, assigned by `bump_slot(Project.next_ord)` | UNIQUE |
| I13 | `Utterance` request | `(project_id, request_id)` + payload fingerprint | UNIQUE |
| I14 | **`Task`** | `(project_id, kind, idempotency_key)`, **per-kind inputs — §8.1** | UNIQUE |
| I15 | Export | content-addressed path over the ordered artifact set — **no claim**, §9.10 | — |

| I16 | `Task` ordering / resume | the Task record itself; `epoch` fences, resume is a transition (§8.8) | — |
| **I17** | `SourceExtraction` | `(content_hash, extractor_version)` — global, no project | PK |
| **I18** | `RoutingResult` | the routing envelope (§5.9a) | PK |
| **I19** | `UserQuotaBucket` | `(user_id, window_start)` — admission, not accounting (§8.6a) | PK |
| **I20** | extraction state | **computed**: `SourceExtraction` for `(content_hash, active extractor version)` — no stored pointer (§9.8b) | — |

*(I17–I20 were defined in §5.12a, §8.6a and §9.8a and **not** carried here, which is the drift this
table exists to prevent. §15.8's `test_derived_identities_are_tabled` now covers them.)*

**Two identities that are deliberately *not* one thing:** I6 vs I7 (a Document is its content; a
construction key is an idempotency key onto it), and I14 vs I5 (a Task key asks *"is this the same
request?"*, a memo key asks *"is this the same content to write?"*). Collapsing either pair is the
mistake §21 names.

## 5.11a `member` encoding — one table

**Rev. 4 fixed the schema and the envelope spec and left `member: null` in §5.6.** That is the
third-location pattern again, so the encoding now has exactly one home and every other section
references it.

```
member : text NOT NULL       '' is the root sentinel; never null, in the column OR the envelope
```

| Kind | `member` | Note |
|---|---|---|
| `situation`, `job`, `scope_tier`, `frame` | `""` | root |
| `structure`, `projection`, `scope`, `partition` | `""` | root |
| `sections` | `"<module_id>"` | a uuid |
| `ordering`, module level | `"modules"` | one per project |
| `ordering`, section level | `"sections:<module_id>"` | one per module |
| `memo` | `"<section_id>"` | a uuid |
| `document` | `"<module_id>"` | a uuid |

**No encoding is ambiguous**, which is what makes `""` safe: a root member is empty, a level member
is a known literal or `literal:uuid`, and a member member is a bare uuid. No real value can collide
with `""`.

Why it must not be null, restated once because it is the reason and not a style note: Postgres
forbids a nullable primary-key column, **and** treats `NULL`s as *distinct* in a `UNIQUE`
constraint — so `member = NULL` would let `UNIQUE (project_id, kind, member, envelope)` admit two
versions for one envelope, silently disabling §11's second guard behind claim loss.

## 5.12 Task keys are not envelopes

**Rev. 4 wrote `envelope("task", kind, inputs, {})`, and `"task"` is not in the envelope's kind
domain** (§5.1: `DecisionKind | "memo" | "document"`). The document said *"this is the only envelope
construction"* and then used one the construction does not admit.

The right fix is separation, not widening, and the reason is §4.1's tiers: **a Task is process
state; an envelope identifies a reusable derived result.** They answer different questions and have
different lifetimes — a Task row is collectable after 30 days (§10.6), an envelope must be stable
forever.

```
task_key(kind, inputs) = first 16 bytes of SHA-256( canonical_json({
    "v":     1,
    "domain": "task",              ◄── a separate domain, not an envelope kind
    "kind":   TaskKind,
    "inputs": { ... }              per-kind, §8.1
}) )
```

Same canonical-JSON rules (§5.1), deliberately — one serialiser, two domains. The `"domain"` field
makes a task key and an envelope over identical inputs **provably distinct**, so neither can ever be
mistaken for the other in a store or a log.

`TaskKind = source_extract | plan | correct | generate | render | export`, and the per-kind inputs
are in §8.1. Nothing else may construct a task key.

## 5.12a `claim_key()` — the third construction, and the one Rev. 7 omitted

Rev. 7 gave `render`, `source_extract` and `routing` claims and **no way to key them.** `Claim.key` was
documented as *"the envelope"*, `envelope()`'s kind domain admitted none of the three, and §5.9
explicitly says an artifact *has no envelope*. So the protocol said *"use a claim"* while the schema
said *"claims are envelopes"* — not mechanically transcribable, which is this document's own bar.

**Not every reusable result is a derived *decision*.** A rendered artifact, an extracted source and a
routing judgment are reusable and worth single-flighting, but none is a `DecisionVersion`: none gets a
slot, a `version_number`, dependency edges, or a place in a `Commitment`. So widening `envelope()`
would have been the wrong fix — it would have claimed decision semantics for three things that have
none.

```
claim_key(domain, identity) = first 16 bytes of SHA-256( canonical_json({
    "v":        1,
    "domain":   ClaimDomain,          ◄── the discriminator, as in task_key()
    "identity": { ... }               per-domain, below
}) )
```

| `domain` | `identity` | Result row |
|---|---|---|
| `decision:<kind>` | `{envelope}` — the envelope **is** the identity | `DecisionVersion` / `SharedDerivation` |
| `memo` | `{envelope}` | `MemoIndex` |
| `document` | `{construction_key}` | `Document` + `DocumentConstruction` |
| **`render`** | `{document_id, render_env_hash}` | `ArtifactIndex` |
| **`source_extract`** | `{source_content_hash, extractor_version}` | `SourceExtraction` |
| **`routing`** | `{envelope}` — §5.9a's routing envelope | `RoutingResult` |

**Three canonical constructions now, with disjoint domains** — `envelope()` for derived decisions,
`task_key()` for process state, `claim_key()` for coordination. Each carries a `"domain"` or kind
discriminator, so no two constructions can collide, and §15.8 asserts it.

`CHOICE` — `claim_key` wraps the envelope for the three decision-shaped domains rather than using the
envelope directly as the claim key. *Cost:* one extra hash. *Benefit:* `Claim.key` has **one**
construction for all six domains instead of being *"an envelope, except for three cases"* — which is
exactly the shape of the bug being fixed.

---

**U1 stops being a risk when it is a test, not a specification.** For every kind, a golden test
asserts both directions:

```
for each listed input:   mutate it     → envelope MUST change
for each listed exclusion: mutate it   → envelope MUST NOT change
```

The exclusion half is the one that catches real bugs, and it is the half a specification alone
never enforces. See §15.2.

---

# 6. `frame` — **closes U2**

Answered from LOCKED text, not invented. `Architecture.md` §8 is the source.

## 6.1 What it is

> *"'a contract requires consideration' is true in common law and false in civil law; the
> money→inflation mechanism differs by school; DSM-IV and DSM-5 disagree about subtype relations.
> These are **constitutive relations that vary** — not by learner situation, but by jurisdiction,
> school, or standard version."* `[LOCKED]`

So: **a frame is the axis along which a subject's *constitutive* relations vary.** It is not a
learner property, not a difficulty level, not a presentation choice. The test is §8's own: *does
this change which relations are true about the subject, independently of who is learning?*

```
parallel frames      jurisdictions — assets sit side by side, a project selects one
authority versions   DSM-IV vs DSM-5 — "a frame indexed by time"
single-frame         "Backend development has exactly one frame, which is why the key
                      looked like 'subject'"                                    [LOCKED]
```

## 6.2 Representation

`CHOICE` — the shape is a technical-design decision; the semantics above are locked.

```
Frame = { axis: 'jurisdiction'|'school'|'standard'|'edition', value: text } | null
```

`null` means **`NotApplicable`, recorded** — not absent. P8: *"a conditional capability is never
silently skipped"* `[LOCKED Build-Spec §1]`. Backend development stores `null` with a reason; it
does not skip the decision.

**Time is part of the value, not a separate field.** DSM-IV and DSM-5 are two frames
(`{standard, "DSM-5"}`), not one frame at two times — which is what *"a frame indexed by time"*
means when read as identity. `CHOICE`; *alternative:* `{axis, value, as_of}`, rejected because it
invites interpolation between versions, which is exactly the DSM-IV/DSM-5 disagreement §8 uses as
its counter-example.

## 6.3 Who produces it, and from what

`select_frame(subject, situation, candidates) -> Frame | NotApplicable`
`[LOCKED System-Design §6]` — conditional, *"multi-frame subjects only"*, Architecture §3
decision 2. **Currently unimplemented: `select_frame` returns zero matches anywhere in the
codebase** `[OBSERVED]`.

Owner: **Source Registry**, in the synchronous intake path, one model call. `CHOICE` — it sits
beside `ScopeTier`, which is also a per-subject classification made during intake, and both feed
the same decision (*"do we need to ask the user something?"*).

**Rev. 1 said "cached by subject", which contradicted the precedence rules below.** Two projects on
*"Contract Law"*, one supplying an Indian statute and one UK material, select **different frames**
from the same subject string. `scope_tier` in this same document is keyed
`(subject, purpose, target_capability, sources)` — correctly — so the inconsistency was internal,
not conceptual. Corrected:

```
frame_selection envelope
  inputs:
    subject_key            §5.3.1
    source_set             sorted {content_hash, kind}
    frame_selecting_readings   the subset of AxisReadings that can select a frame
  env: model_id, prompt_version
```

**Which readings, and the filter is §8's own test, not my judgment** — *does this change which
relations are **true** about the subject, independently of who is learning?*

| Reading | Can select a frame? | Why |
|---|---|---|
| `subject` | **yes** | *"The subject names its own frame in the first four words"* `[LOCKED]` |
| `purpose` | **yes** | *"for my Indian law semester"* names a jurisdiction |
| `entry_point` | no | a learner property; it cannot make a relation true or false |
| `capacity`, `depth_register`, `artifact_type`, `template` | no | same |
| `target_capability` | no | a goal, not a jurisdiction `CHOICE` — the weakest of these calls |

So the frame envelope is **content-addressed** and shareable, exactly like `scope_tier` and
`structure`: two projects that agree on subject, sources and frame-selecting readings resolve the
frame once.

### 6.3a Why `candidates` is not in the envelope — and when it becomes one

The signature is `select_frame(subject, situation, candidates)` `[LOCKED]`, and the envelope above
has no `candidates`. That is deliberate and provable rather than an omission.

**In V2 there is no frame catalogue.** §0.2 establishes it: the shared asset library starts empty,
the first project for a `(subject, frame, sources, env)` derives, and promotion — which is what
would *build* a catalogue — is deferred and needs the situation-free adjudicator §8 calls *"a
different kind of actor from anything else in the architecture"* `[LOCKED]`.

So nothing in the system supplies `candidates`. The model enumerates them from its own knowledge,
which makes the candidate set a **function of `model_id` and `prompt_version`** — both already in
the envelope. Adding a `candidate_set_hash` for a set that does not exist would be cargo cult: it
would hash a constant.

**The condition under which this changes, stated so it is not rediscovered:**

> When a frame catalogue exists — whether from promotion, a curated list, or a source-derived
> registry — `candidates` becomes a **system-supplied input** and the frame envelope must gain a
> `catalogue_version`. Until then it is model knowledge and `model_id + prompt_version` cover it.

`UNKNOWN` — whether a catalogue is ever worth building. §6.5 already notes that of ten corpus
cases, one names its frame and the rest are plausibly single-frame, so the mechanism is *required
for correctness and rare in practice*.

Four sources of the answer, in precedence order:

| Precedence | Source | Evidence |
|---|---|---|
| 1 | a supplied `Source` selects it | a statute or syllabus *is* a jurisdiction/standard |
| 2 | **the subject names it** | *"The subject **names its own frame** in the first four words"* — §8 on *"the Indian Contract Act"* `[LOCKED]` |
| 3 | the situation implies it | *"for my Indian law semester"* |
| 4 | one frame exists | `NotApplicable`, recorded with a reason |

**Ambiguity is a question, not a guess.** If a subject is multi-frame and nothing selects one,
that is a `blocking` sufficiency axis — the frame changes which relations are *true*, so guessing
it is not a recoverable error. `CHOICE`, and it follows the `entry_point` precedent: *"assuming
wrongly is not recoverable by any later decision"* `[OBSERVED]`.

## 6.4 Versioning, and the two versions that are not the same thing

```
frame identity      {axis, value} — stable; DSM-5 is not a version of DSM-IV
asset version       WHICH SNAPSHOT of the derived structure  [LOCKED: "asset_version —
                    which subject × frame snapshot"]  →  the DecisionVersion id
```

A `Commitment` pins the `DecisionVersion` id, so it pins the snapshot. §8's asset-drift
reconciliation (*"two concepts you excluded were split; one you covered was merged"*) is the
deferred promotion machinery of §0.2 and is **not** needed until an asset is ever re-derived under
the same envelope — which, with a content-addressed envelope, cannot happen.

## 6.5 Participation in identity

`frame` is a direct component of the `structure` envelope (§5.3), so:

| Situation | Result |
|---|---|
| same subject, same frame, same sources | one asset, shared |
| same subject, **different frame** | **two assets, side by side** — §8's *"parallel frames"* |
| single-frame subject | `frame = null`, one asset |
| frame unresolved | intake asks; derivation does not run |

**`UNKNOWN` — how often frame ambiguity actually arises.** Of §0's ten corpus cases, one names its
frame (`contract-act`, an Indian statute) and the rest are plausibly single-frame. So the
mechanism is **required for correctness and rare in practice**, which argues for implementing the
recording and the question, and deferring any frame *catalogue*.

---

# 7. Reservation and fencing protocol — D17

The single most correctness-critical mechanism in the design. Specified as a state machine, then
proved against six timelines.

## 7.1 States

```
        ┌──────────┐  INSERT (epoch=1)   ┌──────────┐   CAS commit   ┌───────────┐
        │  ABSENT  │ ──────────────────► │ RESERVED │ ─────────────► │ COMMITTED │
        └──────────┘                     └──────────┘                └───────────┘
                                          │      ▲                     terminal —
                          lease expired    │      │ CAS re-reserve      no transition
                                          └──────┘  (epoch+1)          out, ever
```

`COMMITTED` is terminal. That is **write-once**, and it is implemented by the commit statement's
`WHERE state = 'RESERVED'`, not by an application check.

## 7.2 The five operations

Each is **one statement**, which is what makes it atomic without an explicit transaction.

```
LOOKUP(K)
  SELECT state, epoch, lease_until, result_ref WHERE key = K
    no row                              → MISS
    COMMITTED                           → HIT(result_ref)
    RESERVED, lease_until >  now()      → BUSY(retry_after = lease_until − now)
    RESERVED, lease_until <= now()      → EXPIRED(observed_epoch)

RESERVE_NEW(K, kind, lease)
  INSERT (key, kind, state='RESERVED', epoch=1, lease_until=now()+lease, owner=me)
    ON CONFLICT (key) DO NOTHING
    1 row → OWNED(epoch=1)      0 rows → LOST → re-LOOKUP

RESERVE_TAKEOVER(K, observed_epoch, lease)
  UPDATE SET epoch = epoch+1, lease_until = now()+lease, owner = me
   WHERE key = K AND state = 'RESERVED'
     AND epoch = observed_epoch                     ◄── the CAS
     AND lease_until <= now()                       ◄── only a dead lease
  RETURNING epoch
    1 row → OWNED(new epoch)    0 rows → LOST → re-LOOKUP

HEARTBEAT(K, my_epoch, lease)
  UPDATE SET lease_until = now()+lease
   WHERE key = K AND state = 'RESERVED' AND epoch = my_epoch
    1 row → still mine          0 rows → FENCED → abort, discard

COMMIT(K, my_epoch, result_ref)              ── statement ① of PUBLISH, §7.3a
  UPDATE SET state='COMMITTED', result_ref = R, lease_until = NULL, committed_at = now()
   WHERE key = K AND state = 'RESERVED' AND epoch = my_epoch
    1 row → I won               0 rows → FENCED or ALREADY COMMITTED
                                       → discard my result, re-LOOKUP for theirs
  ── NOT issued alone. It is the first statement of the publication transaction, so the
     metadata rows land with it or not at all.  THE CORRECTNESS BOUNDARY IS THAT
     TRANSACTION, not this statement.
```

`CHOICE` — lease 60 s, heartbeat every 20 s, one takeover per lookup. Rationale: a section call
measures ~65 s `[MEASURED]`, so the lease must be shorter than the work and extended, or a slow
call would look dead. *Alternative:* a lease longer than the longest call (600 s); rejected
because a crashed worker would then block a waiter for ten minutes.

## 7.3 The full step, as orchestration

**Four operations build on §7.2's five statements. They are siblings, not a sequence**, so the
subsections below are definitions rather than steps — read them in this logical order:

| | Operation | When | Defined in |
|---|---|---|---|
| 1 | **`PUBLISH`** | a derivation completed; commit the claim **and** its result atomically | §7.3a |
| 2 | **`ATTACH`** | a *shared* claim already `COMMITTED`; this project needs its pointer | §7.3b |
| 3 | **`ATTACH_PROVENANCE`** | a *document* claim already `COMMITTED`; this commitment needs a provenance row | §9.6a |
| 4 | **`RECONCILE`** | the result exists and its claim does **not** — recovery, §7.3c |

```
step(domain, identity, derive_fn, on_result = identity_fn):      ◄── Rev. 11 signature
  K = claim_key(domain, identity)                               §5.12a
  loop:
    r = LOOKUP(K)
    HIT      → return FINISH(r.result)                             0 calls
    BUSY     → YIELD  (T10 — see §7.7), retry later
    MISS     → existing = FIND_RESULT(domain, identity)      ◄── Rev. 10 · §7.3c
                 if existing: RECONCILE(K, domain, existing)
                              return FINISH(existing)              0 calls
               c = RESERVE_NEW(K);     if LOST: continue
    EXPIRED  → c = RESERVE_TAKEOVER(K, r.epoch);  if LOST: continue

    # OUTSIDE any DB transaction — this is where the 65 s lives
    result = derive_fn(heartbeat = λ: HEARTBEAT(K, c.epoch))
             ── if HEARTBEAT returns FENCED: abort, discard, continue loop
             ── if derive raises: leave the reservation to expire; write nothing (F3)

    ref = PAYLOAD_PUT(result)      # content-addressed; idempotent; before any metadata
    if PUBLISH(K, c.epoch, ref, metadata):  return FINISH(result)
    else:                                   discard result; continue loop   ── fenced

  where FINISH(x) = on_result(x)      ── runs on ALL THREE arrival paths
```

**`on_result` is the per-domain attach, and it runs on every path a result can arrive by.** Rev. 10
had the attach on the `HIT` branch of two *concrete* workflows and not on the `RECONCILE` branch of
the generic one, so a claim loss would return correct content with a **missing audit link**:

| `domain` | `on_result` |
|---|---|
| `decision:<kind>` where `is_shared(kind)` | **`ATTACH`** — the project-local pointer (§7.3b) |
| `document` | **`ATTACH_PROVENANCE(commitment_id)`** (§9.6a) |
| everything else | identity — nothing to attach |

`FINISH` is **idempotent** in every case (both attaches are `ON CONFLICT DO NOTHING`), so running it on
the fresh path as well as on `HIT` and `RECONCILE` is safe. `PUBLISH` additionally performs the attach
inside its transaction, which makes the fresh path atomic; `FINISH` is what covers the other two.

### Every claiming workflow calls this function. None restates it.

`DECIDED`, and this is the Rev. 11 rule that replaces three copies of the same branches:

```
memo            step("memo",            {brief_envelope},                  generate_section)
document        step("document",        {construction_key}, build_document,
                     on_result = λd: ATTACH_PROVENANCE(d, commitment_id))
render          step("render",          {document_id, render_env_hash},    merge_and_print)
source_extract  step("source_extract",  {content_hash, extractor_version}, extract)
routing         step("routing",         {envelope},                        route_correction)
decision        step("decision:"+kind,  {envelope}, derive,
                     on_result = λ: ATTACH(...) if is_shared(kind) else identity)
```

Rev. 10 fixed `FIND_RESULT` in this function and left §9.8's render flow and §9.8a's extraction flow
printing their own `LOOKUP → MISS → RESERVE` branches, which therefore skipped it. With adopt-on-conflict
and the strengthened `ArtifactIndex` constraint, that was no longer the paid-call loop — but a claim
loss still meant **redoing a 3.4 s render or a full extraction and then discarding it.**

The deeper point, and it is the review's: **reachability is weaker than mandatory use.** §15.8's
`test_every_defined_operation_is_reachable` proves `FIND_RESULT` is called *somewhere*. It cannot prove
every `MISS` branch uses it — because the duplicate branches are the problem. Deleting them is the only
fix that holds, and §15.8 now asserts *no workflow contains its own claim branches*.

## 7.3c RECONCILE — an existing result with no claim, and why this is P0

§11 says claim loss is survivable because *"claims rebuild lazily"* and the result tables carry
independent uniqueness constraints. **Rev. 8 never defined that rebuild, and the consequence is worse
than a missing convenience.** Trace it:

```
Claim for K is gone;  DecisionVersion V with envelope K remains
   LOOKUP(K)      → MISS
   RESERVE_NEW(K) → OWNED(epoch 1)
   derive         → A PAID MODEL CALL
   PUBLISH        → ① CAS succeeds
                    ② INSERT DecisionVersion → UNIQUE conflict with V → ERROR
                    → the whole transaction ROLLS BACK, including ①
   claim reverts to RESERVED, epoch 1
   lease expires  → takeover, epoch 2 → derive → ANOTHER PAID CALL → conflict → rollback
   …
```

**That is a permanent loop burning one model call per lease period**, not a one-off waste. The
uniqueness constraint protects the data and guarantees the failure repeats forever. So this is P0, and
the review's P1 rating understates it.

Two mechanisms, both cheap, and the first makes the second rare:

**Rev. 9 defined this and did not wire it in.** The canonical `step()` still read
`MISS → RESERVE_NEW`, so an implementer following the orchestration literally would recreate the
loop above, while §15.5's test asserted the opposite. Two protocols in one document, and the test
contract disagreed with the code contract. `step()` and `step_shared()` now call `FIND_RESULT`
between `MISS` and `RESERVE_NEW` (§7.3), which is the only place this check can live.

```
① FIND_RESULT(domain, identity) — on MISS, BEFORE reserving, look for the result by its
   CANONICAL IDENTITY (not by the claim key):
      decision : (project_id, kind, member, envelope)
      shared   : (kind, envelope) in SharedDerivation
      memo     : the MemoIndex row
      document : DocumentConstruction by construction_key
      render   : (document_id, render_env_hash) in ArtifactIndex
      extract  : (content_hash, extractor_version) in SourceExtraction
      routing  : RoutingResult by envelope
   found → RECONCILE and return it; 0 model calls

RECONCILE(K, domain, existing_result_ref):
  INSERT Claim(key=K, domain, state='COMMITTED', epoch=1, result_ref=existing)
    ON CONFLICT (key) DO NOTHING
  ── idempotent; a concurrent reconciler is harmless because the row is identical
  ── epoch=1 on a replacement row does not break §7.1's monotonicity: the row is born
     COMMITTED, which is terminal and write-once, so no CAS ever reads this epoch. A
     pre-loss worker still holding epoch 8 is rejected by `state = 'RESERVED'` alone.

② ADOPT-ON-CONFLICT — inside PUBLISH, make ②'s result insert
      INSERT … ON CONFLICT DO NOTHING
   and if 0 rows, READ the existing row and point result_ref at it.
   The claim COMMITS pointing at the pre-existing result instead of rolling back.
```

So a lost claim costs **at most one** model call (if the loss is discovered after deriving rather than
before), never a loop. And ② also closes the narrow race where two publishers reach ② together after a
claim loss.

`DECIDED` — adopt rather than roll back. The alternative reading is *"a UNIQUE conflict means a bug,
so fail loudly"* — but here the conflict means *"someone already produced exactly this,"* which is the
outcome the whole protocol exists to achieve. Failing on success is the wrong default.

**And one honest consequence:** with ① in place, `Claim` rows become a **cache of a derivable fact**
rather than the sole record. §11's claim that claim loss is survivable is now true, and §10.6's rule
that committed claims are never collected independently (§10.6a) remains the right policy — this is
the recovery path, not a licence to drop them.

## 7.3b ATTACH — the shared-kind HIT path

**Rev. 3 introduced `SharedDerivation` and left this operation undefined.** §4.2a claimed *"a second
project HITs at ① and performs only ③"*, but generic `step()` returns at `HIT` and never reaches
`PUBLISH` — and `PUBLISH` opens with a `RESERVED → COMMITTED` CAS that an already-committed claim
cannot pass. So the stated invariant *one shared derivation, N local pointers* was not reachable,
and `test_second_project_reuses_shared_derivation` asserted behaviour the protocol could not
produce.

**A shared kind has two independent idempotency questions**, and Rev. 3 conflated them:

```
"has anyone derived this?"       the global claim on the envelope     → guards the MODEL CALL
"does THIS project have a        UNIQUE (project_id, kind, member,    → guards the POINTER
 pointer to it?"                  envelope) on DecisionVersion
```

The second needs no claim: the unique constraint is the guard, and the work is one insert.

```
ATTACH(K, project, kind, member, deps):
  BEGIN
    ① SELECT id FROM DecisionVersion
        WHERE (project_id, kind, member, envelope) = (project, kind, member, K)
      found → COMMIT, return it                        already attached; idempotent
    ② SELECT id, payload_ref FROM SharedDerivation WHERE (kind, envelope) = (kind, K)
      not found → ROLLBACK, return INCONSISTENT
        ── unreachable under §7.3a, because the claim and the SharedDerivation row are
           written in ONE transaction. Surfaced rather than ignored: if it ever fires,
           the publication transaction has been split.
    ③ INSERT DecisionVersion(project, kind, member, envelope=K, shared_id,
                             payload_ref, version_number = bump_slot(project, kind, member))
        ON CONFLICT (project_id, kind, member, envelope) DO NOTHING
      0 rows → ROLLBACK and retry from ①               lost a concurrent attach
    ④ INSERT DependencyEdge × n
  COMMIT
```

**The shared-kind step, in full:**

```
step_shared(K, project, kind, member, derive_fn, deps):
  loop:
    r = LOOKUP(K)
    HIT   → return ATTACH(K, project, kind, member, deps)      0 model calls  ◄── the fix
    BUSY  → yield (T10), retry
    MISS  → existing = FIND_RESULT("decision:"+kind, {envelope})      ◄── Rev. 10 · §7.3c
              if existing: RECONCILE(K, …, existing); return ATTACH(…)   0 model calls
            RESERVE → derive → PAYLOAD_PUT → PUBLISH_SHARED(…)
            where PUBLISH_SHARED = §7.3a's transaction, whose step ② writes the
            SharedDerivation and whose step ③ is ATTACH's ③–④ inlined
```

So the **first** project pays the call and gets its pointer in one transaction; **every later**
project runs `ATTACH` alone. `ATTACH` is safe to call any number of times (①), and safe under
concurrency (③'s `ON CONFLICT`).

**Note what `ATTACH` does *not* do:** it never touches the global claim, and it never reads another
project's `DecisionVersion`. That is what keeps §4.2a's two guarantees — one model call, and
staleness confined to one project — true at the same time.

## 7.3a PUBLISH — one transaction per result type

**Rev. 1 stopped at `COMMIT(claim)` and left the metadata unbound, which was a real hole.** The
claim carries only `state · epoch · result_ref`; the *result* also needs a `DecisionVersion` and
its `DependencyEdge`s, or a `MemoIndex` row, or a `Document` plus its `DocumentConstruction` and
`DocumentProvenance` rows. With
those written separately, a crash between them leaves:

```
Claim         : COMMITTED, result_ref = R      "done"
Decision Store: no version for this envelope   "nothing here"
```

— and `stale` would walk edges that do not exist, silently un-staling every dependent. That is
CC2's class: every surface reports success.

**All of it is in Postgres, so all of it is one transaction, with the epoch CAS as its gate.**
`DECIDED`:

```
PUBLISH(K, epoch, payload_ref, metadata):
  BEGIN
    ① UPDATE Claim SET state='COMMITTED', result_ref=payload_ref,
                       lease_until=NULL, committed_at=now()
        WHERE key=K AND state='RESERVED' AND epoch=<epoch>
      0 rows → ROLLBACK, return FENCED          ── nothing else is attempted
    ② per kind:
       a DecisionKind, is_shared(kind) FALSE:                          ── §5.2a
                   next_version = bump_slot(project, kind, member)      ── §10.2a
                   INSERT DecisionVersion(..., envelope=K, version_number=next_version)
                   INSERT DependencyEdge × n
       a DecisionKind, is_shared(kind) TRUE:                            ── §4.2a
                   INSERT SharedDerivation(kind, envelope=K, payload_ref)
                   then ATTACH's ③–④ inlined: the project-local pointer with shared_id set
       memo      : INSERT MemoIndex(key=K, payload_ref, covered)
       render    : seq = bump_artifact_seq(document_id, template_id)        ◄── Rev. 8
                   INSERT ArtifactIndex(..., render_env_hash,
                                        capability_decl_version, bytes_hash, seq)
       source_extract : INSERT SourceExtraction(content_hash, extractor_version,
                                                outcome, payload_ref, reason)
                        ── Rev. 9: NO Source update. The project-local pointer is gone;
                           extraction state is computed (§9.8b). Rev. 8's UPDATE was an
                           unfenced write to a shared cell that two extractor versions
                           could reach in either order.
       routing   : INSERT RoutingResult(envelope=K, project_id, payload_ref)  ◄── Rev. 8
                   ── the replacement payloads become DecisionVersions in §9.3 step 3,
                      each through its OWN claim; this row is the routing itself
       document  : UPSERT Document ON (project, module, content_hash)
                     on INSERT: seq = bump_module_doc_seq(project, module_id)
                     on CONFLICT: reuse the existing document_id, seq UNTOUCHED  ── §5.8
                   INSERT DocumentConstruction(construction_key=K, document_id, builder_version)
                   INSERT DocumentProvenance(document_id, commitment_id)
  COMMIT
```

Three properties, each load-bearing:

- **The CAS is statement ①**, so a fenced worker performs no inserts at all. Cheaper, and it means
  a rollback is never partially observable.
- **`UNIQUE (project_id, kind, member, envelope)` — plus `UNIQUE (kind, envelope)` on
  `SharedDerivation` — is a second, independent guard.** If claims were ever lost
  (§11), two publishers would race and one would violate it → rollback. Belt and brace, because
  this failure is silent.
- **The payload is written first and is content-addressed**, so the transaction only ever commits a
  reference to bytes that already exist. A crash before `PUBLISH` leaves an orphan object, which is
  garbage; a crash after leaves nothing inconsistent.

**The fencing check and the result publication are now one atomic boundary**, which is what Rev. 1
claimed of the single `UPDATE` and only achieved for the claim row itself. There is no window
between *"I verified I still own this"* and *"the result is visible."*

## 7.4 Why payloads are content-addressed

`DECIDED`, and it is a consequence of fencing rather than a style preference.

```
key-addressed  path = f(K)      A and B write the SAME path
                                → a fenced-out A can overwrite B's committed bytes
                                → the claim says COMMITTED(B) and the bytes are A's
content-addressed path = f(sha256(payload))
                                → A and B write different paths
                                → only the committed claim references one
                                → the loser's payload is an ORPHAN: harmless, GC-able
```

The key-addressed variant is a **silent corruption**: every index says the right thing and the
bytes are wrong. That is CC2's class — *"a failure that looked like a success."*

## 7.5 Race timelines

**R1 — two workers, cold. One call.**
```
A: LOOKUP → MISS            B: LOOKUP → MISS
A: RESERVE_NEW → OWNED(1)   B: RESERVE_NEW → LOST (ON CONFLICT DO NOTHING)
A: derive (65 s)            B: LOOKUP → BUSY → yield → later HIT
A: PAYLOAD_PUT, COMMIT(1) ✓
```
Safe: `INSERT ... ON CONFLICT` is atomic, so exactly one owner. **1 call, 1 result.**

**R2 — the fencing case. A is slow, not dead. Two calls, one result.**
```
t0    A: RESERVE_NEW → OWNED(epoch 1), lease→t60
t20   A: HEARTBEAT ✓ lease→t80
      ── A's process stalls (GC pause, VM freeze, network stall in the SDK)
t80   lease expires
t85   B: LOOKUP → EXPIRED(1);  RESERVE_TAKEOVER(1) → OWNED(epoch 2)
t150  B: PAYLOAD_PUT(pB), COMMIT(epoch 2) ✓  → COMMITTED, result_ref = pB
t160  A: wakes, model call returns
      A: PAYLOAD_PUT(pA)          → an orphan object
      A: COMMIT(epoch 1) → WHERE epoch = 1 → 0 rows → FENCED
      A: discards, LOOKUP → HIT(pB)
```
Safe: A's epoch is stale **and** the row is no longer `RESERVED`; either clause alone rejects it.
**The at-least-once window: 2 calls, 1 committed result, 1 orphan object.**

**R3 — crash after model success, before commit. Two calls, one result.**
```
A: derive ✓ (paid) → process dies before PAYLOAD_PUT
   lease expires → B takes over (epoch 2) → derives → commits
```
Safe, and **unavoidable**: no protocol makes an external API call exactly-once across a crash. The
cost is bounded at one call, and the lease bounds how long the successor waits.

**R4 — crash between payload write and commit. Orphan only.**
```
A: PAYLOAD_PUT(pA) ✓ → dies before COMMIT
   pA is referenced by nothing; claim stays RESERVED until the lease expires
   B takes over, derives, commits pB.   GC reclaims pA.
```
Safe: an unreferenced object is invisible to every read path. GC is a sweep over object paths with
no index row older than the longest lease (§10.6).

**R5 — two workers race the takeover.**
```
both LOOKUP → EXPIRED(observed_epoch = 1)
A: RESERVE_TAKEOVER(1) → 1 row → OWNED(2)
B: RESERVE_TAKEOVER(1) → 0 rows (epoch is now 2) → LOST → re-LOOKUP → BUSY
```
Safe: the CAS on `epoch = observed_epoch` serialises takeovers. This is why the observed epoch
must be carried from the lookup and not re-read.

**R6 — commit against an already-committed key.**
```
A: COMMIT(epoch 1) → row is COMMITTED → WHERE state='RESERVED' fails → 0 rows
```
Safe: write-once holds even if epochs somehow matched. Two independent clauses guard one
transition, deliberately.

## 7.6 What breaks without fencing

Not merely a duplicated call. Without the epoch check, R2's timeline ends with **two
`DecisionVersion` rows for one envelope** — or, with a `UNIQUE` constraint but no fencing, with A's
late `UPDATE` replacing B's `result_ref`. Either way:

```
stale(v) ⟺ a recorded dependency has a newer version
```

fires on every dependent, because the dependency now has a second version. **A duplicate
derivation would mark a correct, approved plan stale.** `stale` is only well-defined because the
envelope is unique, and the envelope is only unique because of the CAS.

## 7.7 Waiters yield; they do not block — T10

`DECIDED`. A `BUSY` result returns the section to the Task's pending queue with a retry-after,
and the worker takes the next section. Blocking would be a deadlock generator: with a model-call
cap of *N* and *N* workers all waiting on reservations held by workers that cannot be scheduled,
nothing progresses.

A waiter's elapsed wait counts against the **Task budget**, so waiting cannot be unbounded, and
budget exhaustion is a *distinguishable* terminal failure (§9.3) — never reported as a model
failure. That distinction is §4's measured lesson: *"same symptom, opposite fix"* `[OBSERVED]`.

---

# 8. Task system

## 8.1 Creation and idempotency

**Rev. 1 used one generic formula over `{target}`, and that was wrong.** A module can legitimately
be generated again under a **new Commitment** — the correction flow makes it a normal operation —
and a key of `(project, generate, module_id)` would return the *old succeeded Task* instead of
starting the new production event. That is CF-6's error class again: an identity that does not
capture what makes two things different.

**The key must identify the production event, and it is per kind.** `DECIDED`:

```
UNIQUE (project_id, kind, idempotency_key)

kind             idempotency_key = task_key(kind, inputs)            ◄── §5.12, NOT envelope()
─────────────────────────────────────────────────────────────────────────────────
source_extract   { source_content_hash,            ◄── Rev. 8: NOT {source_id}. The claim
                   extractor_version }                 identity is (content_hash, extractor
                                                       _version), so keying the Task on the
                                                       source alone meant an extractor
                                                       UPGRADE returned the old succeeded
                                                       Task and no extraction ever ran —
                                                       the claim said "new result", the Task
                                                       said "same request"
plan             { structure_envelope,             ◄── Rev. 3: ALL planning roots.
                   situation_v, job_v,                  The structure envelope already
                   tier_v, frame_v }                    carries subject, frame, sources
                                                        AND the derivation environment
correct          { utterance_id }                  exactly one Task per correction utterance
generate         { commitment_id, module_id }      ◄── THE FIX
render           { document_id, render_env_hash }  a re-render under a new engine is new work
export           { export_hash }                   ◄── Rev. 6: the RESOLVED artifact set,
                                                       not {commitment_id} — the set can change
                                                       while the commitment does not (§9.9 ①–③)
```

**Why the plan key needs the structure envelope — and the review's example was the wrong one.**
A *source* change does propagate already: the `scope_tier` and `frame` envelopes both include the
source set, so `tier_v` and `frame_v` move, and the plan key with them. The actual hole is the
**derivation environment**:

```
bump the derive prompt / model / taxonomy_version / frontier
    → the STRUCTURE envelope changes
    → no other envelope changes, because each has its OWN prompt version
    → Rev. 2's plan key was identical  →  "already done"  →  never re-planned
```

The structure envelope is computable at admission (subject, frame, sources and env are all known
before the Task runs), so keying on it is cheap and covers every root at once — better than
enumerating environment fields, which is a list that rots.

**Why `commitment_id` is in the generate key and *not* in the memo envelope (§5.7).** They answer
different questions and the asymmetry is deliberate:

```
Task key    "is this the same REQUEST?"        → commitment, because the user asked
                                                 again after approving something new
memo key    "is this the same CONTENT?"        → the brief, because a correction to
                                                 module 5 does not change module 1's writing
```

So a generate request under a new commitment creates a new Task, which then **HITs every memo
whose brief did not change** — new production event, near-zero cost. Putting the commitment in
both would re-spend 40 sections; putting it in neither would refuse to regenerate at all.

V1 gets the double-click case right by a different route — `JOBS.forget(key)` then
`JOBS.start(key)`, where `forget` only removes non-running jobs `[OBSERVED]` — and its stated
reason survives: *"a double-click on Generate must not spend two model calls."*

## 8.2 Admission, backlog, shedding

**Four Task-admission limits** — the ones that decide whether a Task is accepted, queued or shed.
§14 lists **six** resource limits in total; render slots (§12.5) and the DB pool are resource gates that
no Task-admission decision consults, which is why they are not here. *(Rev. 10 said "four independent
limits" with no qualifier, against a §14 table of six.)*

```
accepted → in-flight cap reached? → stay accepted (queued)
         → backlog bound reached? → SHED: reject with 503 + reason, do not enqueue
         → per-user quota reached? → SHED with a quota reason
```

`DECIDED` — shedding is honest and queueing indefinitely is not. §8 already measured what one
tenant does to a shared resource: *"a public URL drains the quota"* `[OBSERVED]`.

## 8.3 Leasing, heartbeat, fencing — T8

Identical mechanism to §7, applied to `Task`, and for the identical reason: a re-leased Task must
not be completed by its predecessor.

```
LEASE     UPDATE SET state='leased', epoch=epoch+1, lease_until=now()+L, owner=me
           WHERE id=T AND state IN ('accepted','leased','failed_transient')
             AND (lease_until IS NULL OR lease_until <= now())
           RETURNING epoch
HEARTBEAT UPDATE SET lease_until=now()+L WHERE id=T AND epoch=E   → 0 rows ⇒ abandon
COMPLETE  UPDATE SET state=<terminal>, ...  WHERE id=T AND epoch=E → 0 rows ⇒ discard
```

`CHOICE` — Task lease 120 s, heartbeat 30 s. Longer than a claim lease because a Task's unit of
progress is a whole section, not a call.

## 8.4 Orphan recovery

On coordinator start and every 30 s: any Task `leased`/`running` with `lease_until <= now()` is
re-leasable. **No separate recovery path exists** — re-leasing *is* recovery, because every step
is envelope-idempotent. This is what Architecture E2 means by *"re-running is cheap and needs no
checkpoint table"*, now with the two memo stores and the claim protocol making it true.

## 8.5 Retry and failure classification

Per-Task retry, not per-step — the envelope makes them equivalent (F3).

| Class | Origin | Retry | Terminal |
|---|---|---|---|
| `provider_unavailable` | network, 5xx, attempts exhausted | yes, exp + jitter | no |
| `rate_limited` | **429 or any `Retry-After`** | yes, honour `Retry-After` | no |
| `provider_refused` | invalid request · content policy · billing · hard quota | **no** | yes |
| `attempt_deadline` | one call exceeded its ceiling | yes, within budget | no |
| `output_truncated` | partial JSON | once, **narrowed**; then terminal | then yes |
| `task_budget_exhausted` | calls/wall/spend ceiling | **no** | yes |
| `renderer_unavailable` | Chromium absent | no — refused **before** any model call | yes |
| `render_failed` | crash, timeout | yes — the Document survives | no |
| `integrity_violation` | deterministic check | **not a failure — a result** | — |
| `stale_decision_set` | a dependency moved | **not a failure — a result** | — |

**Jitter, and why it is not hygiene.** V1's backoff is linear with **no jitter** `[OBSERVED]`, so
concurrent callers retry in lockstep against a provider measured as overloaded — **7 network
failures across two baseline attempts** `[MEASURED]`. `CHOICE`: full jitter,
`sleep = random(0, min(cap, base·2^n))`.

**429 is the expected case, not an exotic one.** The free tier is 20 requests/min and fan-out
deliberately issues several calls at once, so treating 429 as terminal would make concurrency fail
exactly when it works. V1 maps all 4xx to `ProviderRefused` and does not retry `[OBSERVED]`.

## 8.6 Budgets

```
Task budget      {max_calls, max_wall_ms}   — enforced by the orchestrator, spent recorded
Attempt deadline per model call             — enforced by the Model Gateway
Provider budget  per-tenant calls/window    — enforced at admission and per call
```

This is the mechanism V1 lacks. `TIMEOUT = 600 s` × `_TRANSIENT_ATTEMPTS = 3` plus linear backoff
means **~30 minutes per call** with no caller-side bound `[OBSERVED]` — the mechanism behind
`contract-act-authority`'s **11,537 s: 3.2 hours across 4 calls, ending in `getaddrinfo failed`**
`[MEASURED]`. `CHOICE`: attempt deadline 120 s; plan Task budget 20 calls / 30 min; generate Task
budget `2 × sections + 4` calls / 60 min.

## 8.7 Cancellation — and it is non-destructive

Rev. 1's §13.4 promised Tasks are *"cancellable"* and the state list had no `cancelled`. Added,
with semantics that fall out of D14 rather than being invented:

```
CANCEL(T):
  UPDATE Task SET cancel_requested = true
   WHERE id = T AND state IN ('accepted', 'leased', 'running')     ◄── Rev. 7: the predicate
  1 row → cancelling      0 rows → already terminal; return the terminal state

observed    at each step boundary and each heartbeat
effect      the worker stops taking new steps and transitions to 'cancelled' (epoch-fenced)
            an IN-FLIGHT model call is allowed to finish and its result IS published
```

**Rev. 6 wrote this as *"set `cancel_requested` = true — one statement, no lease needed"* with no
state predicate**, while §8.8 claimed a cancel arriving after `COMPLETE` is a no-op. As written the
flag would happily mutate a `succeeded` Task, so the no-op was a statement about intent rather than
about the code. The predicate above makes it true: a terminal Task matches 0 rows, and the caller is
told the terminal state instead of being led to believe a cancel took effect.

**Committed results are never rolled back.** `DECIDED`, for a reason: a committed memo is a paid
call whose content is valid, and discarding it would make cancelling *expensive* and make resuming
later cost full price. So:

```
cancel generation after 3 of 5 sections
   → Task 'cancelled', no Document
   → 3 memos remain committed
   → restarting later costs 2 calls, not 5
```

That is the same property as crash resumption (§9.5), reached by a different route. `CHOICE` —
letting an in-flight call finish rather than abandoning it; abandoning would pay for the call and
throw the result away, which is strictly worse than paying and keeping it.

## 8.8 RESUME — and Rev. 3's last sentence here was wrong

Rev. 3 ended §8.7 with *"a `cancelled` Task is terminal and not re-leasable … the caller gets the
cancelled one and must change something to proceed."* That contradicted the paragraph above it,
the API's own *"start/resume generation"*, and `test_cancel_keeps_committed_memos`. If committed
memos survive a cancel precisely so a later run is cheap, there must be a later run.

**`cancelled` is terminal to the *sweep*, not to the *user*.** The orphan sweep (§8.4) never
re-leases it; an explicit resume does:

```
RESUME(T):
  UPDATE Task SET state    = 'accepted',
                  cancel_requested = false,
                  epoch    = epoch + 1,              ── fences the pre-cancel worker
                  lease_until = NULL, owner = NULL,
                  budget   = <fresh allocation for this kind>,
                  attempt_started_at = now(),        ── the WALL budget restarts here
                  calls_admitted = 0,                ── ADMISSION resets (§8.6a)
                  resumes  = resumes + 1,
                  failure  = NULL
                  ── NO spend reset: "spent this attempt" is Σ over the NEW epoch in
                     CallLedger (§8.8a), zero because the epoch just changed.
                     Rev. 7 said "nothing to reset", which was true of ACCOUNTING and
                     false of ADMISSION — `calls_admitted` is a real counter and does.
   WHERE id = T
     AND state IN ('cancelled', 'incomplete', 'failed_transient', 'failed_terminal')
     AND (state <> 'failed_terminal'
          OR (failure->>'class') IS DISTINCT FROM 'provider_refused')
  1 row → resumed      0 rows → not resumable; return the current state and failure class
```

**`incomplete` was listed as resumable and excluded by the SQL.** Rev. 5's table says *"`incomplete`
— **yes** — the ordinary resume path; this is what D14 exists for"*, and the predicate admitted only
`cancelled` and `failed_terminal`. So the one state the Content Memo was built for could not be
resumed. Fixed above; `failed_transient` is admitted too, since a transient failure whose retries
were exhausted is the same situation as `incomplete` from the user's side.

**Committed progress is preserved across every resume**, and `RESUME` touches none of it:

```
untouched   progress (per-member state) · MemoIndex rows · every committed Claim ·
            the entire CallLedger — lifetime spend survives, by construction
reset       budget · attempt_started_at · failure
advanced    epoch · resumes
```

So a resumed Task re-runs `step()` per section, HITs each committed memo, and spends only on what is
missing — which is the property §8.7 claims and §15.5 tests.

### The cancel/complete race, linearised

`cancel_requested` is a flag a worker observes, so a cancel can arrive while the worker is already
committing. Rev. 5 left the outcome unstated. **The rule, and it is decided by one principle: a
committed result is never discarded** (§8.7).

```
The Task's `epoch` serialises every terminal transition. A worker's COMPLETE is
  UPDATE Task SET state = <terminal> WHERE id = T AND epoch = E
so exactly one terminal transition wins, and `cancel_requested` does not fence anything.

cancel observed BEFORE the worker's last step committed
    → worker stops taking steps, transitions to 'cancelled'
    → committed memos remain; resume is cheap

cancel observed AFTER the final step committed but BEFORE the Document was published
    → the worker still transitions to 'cancelled'; the memos are kept, no Document
    → resuming publishes the Document with 0 model calls

cancel arrives AFTER the worker's COMPLETE already won
    → the cancel is a NO-OP: the UPDATE matches a terminal state and changes nothing
    → the API returns the terminal state, not "cancelled"
    → correct, because the work is done and discarding it would waste paid calls
```

`DECIDED` — **completion wins a tie with cancellation.** The alternative (cancel wins, roll back the
Document) would delete a result the user already paid for in order to honour a request that arrived
after it existed. The user-visible contract is *"cancel stops further spending"*, never *"cancel
undoes what finished."*

**The budget reset is part of the same statement, and Rev. 4 omitted it.** The prose promised a
resume from `task_budget_exhausted` *"grants a fresh budget"* while the transition touched only
`state`, `epoch`, `lease_until` and `owner` — so the resumed Task would carry `spent.calls = budget.
max_calls` and re-exhaust on its first step. The promised behaviour was unreachable.

### 8.8a Spend accounting — a ledger, not counters

Rev. 5 updated `spent_lifetime` only inside `RESUME`, so a Task that never resumed carried zero while
the quota read that column. Rev. 6 moved the update to the Gateway and **fenced it on `epoch`** —
which fixed the common case and introduced a quieter one: in §7.5's R2 timeline, worker A makes a
**paid call** on epoch 1 and B takes over on epoch 2, so A's accounting `UPDATE … WHERE epoch = E`
matches 0 rows and **the call is discarded from accounting.** `spent_lifetime` then did not mean
*"what this Task has cost."*

Three findings had the same root — two denormalised counters, two writers, and no time dimension —
so Rev. 7 removes the counters and derives everything from an append-only **`CallLedger`** (§4.2).

```
after EVERY model call, whatever its outcome:
  INSERT INTO CallLedger (task_id, user_id, task_epoch, provider, model_id,
                          started_at, ended_at, wall_ms, tokens_in, tokens_out,
                          outcome, envelope)
  ── UNFENCED, deliberately. The epoch is RECORDED, not a predicate.
     A cost that was really incurred is true regardless of who incurred it;
     fencing a monotonic fact discards information rather than protecting anything.
```

| Question | Derivation |
|---|---|
| may this attempt spend more? | `Σ(task_id = T, task_epoch = current)` against `budget` |
| what has this Task cost, ever? | `Σ(task_id = T)` — **includes fenced workers' calls** |
| is this tenant over quota? | `Σ(user_id = U, started_at > now() − W)` — the window §14 asks for |
| why did this project cost 46 calls? | the rows themselves, with `envelope` per call (§17) |

**Three consequences worth naming:**

1. **`RESUME`'s budget reset becomes free.** It bumps `epoch`; *"spent this attempt"* is a sum over
   the current epoch, which is zero for a new one. No reset statement, nothing to forget.
2. **The wall budget stops being an accumulation.** §7.7 charges reservation *waiting* to
   `max_wall_ms`, and no counter was ever advanced for waiting (a real gap). Now the wall budget is
   `now() − attempt_started_at`, so waiting counts because time passes. One fewer mechanism.
3. **A failed call still counts**, because it consumed provider capacity and possibly money. Rev. 6
   said so; the ledger makes it structural rather than a rule to remember.

`CHOICE` — a ledger row per call rather than cached aggregates. *Cost:* one insert per call (against
a ~65 s operation) and a `SUM` per budget check, indexed on `(task_id, epoch)`. *Alternative:*
keep counters and add a window table; rejected — it is three sources of truth for one fact, which is
the defect §5.11 and §15.8 exist to stop.

`CHOICE` — a **soft** cap on `resumes`: the honest surface is *"this module has cost N calls across M
attempts, continue?"* rather than a silent refusal. *Alternative:* no lifetime accounting; rejected —
it makes *resume* a free-money button.

### 8.6a Admission control is not accounting — and Rev. 7 conflated them

**The ledger is post-call. It can tell you that you overspent; it cannot stop you.** Rev. 7 said the
orchestrator compares `Σ CallLedger` against `budget.max_calls`, which is a read-then-act under
concurrency — and generation deliberately fans out (D6):

```
budget.max_calls = 2
A: Σ = 1 → allowed          B: Σ = 1 → allowed
A: calls provider           B: calls provider
ledger = 3                  budget was 2
```

Worst-case overshoot is `model_call_cap − 1` = 7 calls at §14's settings, on a tier measured at **20
requests/min** `[MEASURED]`. The same TOCTOU applies to the 200-calls/hour tenant quota, where the
consequence is worse because that one exists to protect other tenants.

**So there are two mechanisms, and Rev. 8 stops pretending one does both work:**

```
ADMISSION   an atomic conditional increment, BEFORE the call      ← prevents overspend
ACCOUNTING  an append-only ledger row, AFTER the call            ← reports what happened
```

**Task-level admission** — one statement, atomic, no transaction needed:

```
UPDATE Task SET calls_admitted = calls_admitted + 1
 WHERE id = T AND epoch = E
   AND calls_admitted < (budget->>'max_calls')::int
RETURNING calls_admitted
  1 row → proceed      0 rows → task_budget_exhausted (terminal, §8.5)
```

**Tenant admission** — a windowed counter, because a rolling sum cannot be conditionally incremented:

```
INSERT INTO UserQuotaBucket (user_id, window_start, calls_admitted)
VALUES (U, floor_hour(now()), 1)
ON CONFLICT (user_id, window_start) DO UPDATE
   SET calls_admitted = UserQuotaBucket.calls_admitted + 1
 WHERE UserQuotaBucket.calls_admitted < <cap>          ◄── the condition lives on DO UPDATE
RETURNING calls_admitted
  1 row → admitted      0 rows → rate_limited at admission, not a provider 429
```

**It must be an upsert, and Rev. 8's bare `UPDATE` had a cold-start bug.** On the first call of every
hour the bucket does not exist, so `UPDATE … WHERE window_start = floor_hour(now())` matches 0 rows —
**indistinguishable from "over cap."** Every tenant would be refused once per hour, and the refusal
would be reported as a quota failure. The upsert form creates the bucket and increments it in one
atomic statement, so there is no initialisation step to get wrong and no separate "create the bucket"
race.

*(Note the `WHERE` attaches to `DO UPDATE`, not to the `INSERT`: a fresh bucket is always admitted
because `VALUES … 1` is the insert path, and an existing bucket is admitted only below the cap.)*

`CHOICE` — **fixed hourly buckets for admission, the ledger's rolling window for reporting.** A fixed
window admits up to 2× the cap across a boundary; that is acceptable for a spend guard and it is the
only form that supports an atomic conditional increment. The ledger still answers the exact rolling
question for the quota *display* and for audit. *Alternative:* a sliding-window reservation table;
rejected as real machinery for a bound that does not need to be tight.

**`calls_admitted` is an admission counter, not a spend record, and the distinction is the point.**
It may legitimately exceed the ledger count — an admitted call whose process died before inserting its
row. That direction is **safe**: it over-counts admissions and under-admits future calls. The reverse
could never be allowed, which is why admission cannot be derived from the ledger.

| | `calls_admitted` | `CallLedger` |
|---|---|---|
| written | **before** the call, conditionally | **after** the call, unconditionally |
| purpose | refuse the next call | report what happened |
| reset | per epoch, by `RESUME` | never |
| may drift | yes, conservatively high | no — it is the record |

`RESUME` therefore regains exactly one reset (`calls_admitted = 0`), and that is honest: Rev. 7's claim
that *"RESUME has nothing to reset"* was true of accounting and false of admission.

### 8.6b Synchronous calls — the path that had no contract at all

**Every admission and accounting mechanism above is Task-shaped, and intake is not a Task.** An intake
turn issues up to four model calls synchronously (§9.1: `situation`, `job`, `scope_tier`, `frame`, plus
`ask`). Under Rev. 9 those calls:

```
consumed provider capacity          ✓
cost real money                     ✓
passed Task admission               ✗ — there is no Task
appeared in CallLedger              ✗ — task_id was non-nullable
counted against the tenant quota    ✗ — only named inside the Task flow
```

So the two headline guarantees — *"200 calls/hour per tenant"* and *"the `CallLedger` is the single
source for spend"* — were both false on the one path a user can drive directly and repeatedly.

`DECIDED` — **the Model Gateway owns admission and accounting for every call, whatever its origin.**
There is exactly one gate, and Task budgets are an *additional* constraint layered on it:

```
MODEL_CALL(user_id, project_id, operation, origin, task_ref?):
  ① TENANT admission   — the §8.6a UserQuotaBucket upsert, ALWAYS, both origins
  ② per-origin cap
       origin='task'   → Task.calls_admitted conditional increment (§8.6a)
       origin='sync'   → a per-TURN counter, in-process                ◄── see below
  ③ ACQUIRE_PROVIDER_SLOT(provider)   ◄── Rev. 11 · THE CAP §14 DECLARES, now mechanical
       bounded FIFO wait; on timeout → `rate_limited` (transient, retriable)
  ④ try:    provider call, under the attempt deadline (§8.6)
     finally: RELEASE_PROVIDER_SLOT(provider)        ── released on every exit path
  ⑤ INSERT CallLedger(origin, operation, task_id?, user_id, …)        ALWAYS
```

**§14 declares `model-call cap, per provider = 8` and Rev. 10's `MODEL_CALL` did not acquire
anything** — the cap existed in a table and in Work Coordinator prose, and nothing enforced it. This is
the *defined-but-unreachable* class that §15.8 exists to catch, in the one place that matters most:
without step ③, **synchronous intake bypasses the exact resource cap §8.6b had just centralised.**

```
ACQUIRE_PROVIDER_SLOT(provider)
  a FIFO-ordered, in-process semaphore of size <cap>, one per provider
  wait is bounded by the attempt deadline (CHOICE: 120 s, §8.6)
  timeout → `rate_limited`, which is TRANSIENT (§8.5) — the call never happened
```

Three properties, each with a reason:

- **FIFO, not a bare semaphore.** `CHOICE` — with 8 slots and ~65 s calls `[MEASURED]`, a LIFO or
  random wake can starve a waiter past its Task's wall budget, which would surface as a budget failure
  caused by scheduling. FIFO makes the wait bounded by queue position.
- **Waiting costs wall budget automatically**, because the wall budget is `now() − attempt_started_at`
  (§8.8a). No accounting operation is needed — the same property that made reservation waiting count.
- **Timeout is transient, not terminal.** The provider was never reached, so nothing about the request
  is known to be bad. It retries within the Task budget.

**And this is the mechanism behind D6's fan-out bound.** Generation fans out over sections *"bounded by
the model-call cap"* — that cap is this semaphore, and until Rev. 11 the bound was a sentence. The
render slot pool (§12.5) is the same shape for a different resource, which is why §14 keeps them
separate.

`CHOICE` — in-process, per provider. *Alternative:* a durable distributed slot table, needed at T3 when
workers multiply (Architecture H). Called out rather than assumed: **at T3 this becomes a shared
counter**, and the FIFO property becomes per-worker rather than global.

**The sync cap needs no durable row**, which is why this costs nothing: a turn is a single request that
cannot fan out, so an in-process counter bounded at the turn's call budget (`CHOICE`: 5, from §9.1's
worst case of 4 plus one retry) is sufficient. Concurrent turns by one user are separate requests, and
step ① already covers them.

**The spend formulas need no change**, which is the sign the ledger was the right primitive:

```
spent(T)       = Σ(task_id = T, task_epoch = current)      unaffected — sync rows have NULL
quota(user, W) = Σ(user_id = U, started_at > now() − W)    now covers BOTH origins, correctly
```

`CHOICE` — one gate in the Gateway rather than admission at each call site. *Alternative:* make intake
a Task so everything is uniform; rejected because it would put a durable Task record and a lease on the
30-second conversational path (D1), for a bound an in-process counter already provides.

**The epoch bump is what makes this safe, and it is why Tasks have epochs at all (T8).** Any worker
still holding the pre-cancel lease is fenced at its next heartbeat or completion attempt. **No
successor identity is needed** — the review suggested one, and it turns out to be unnecessary: a
second `RESUME` sees `state = 'accepted'`, matches 0 rows, and is a no-op. Double-resume is safe by
construction.

**Which terminal states resume, and why the distinction is not arbitrary:**

| From | Resumable | Why |
|---|---|---|
| `cancelled` | **yes** | the user stopped spending, not the work |
| `failed_terminal` / `task_budget_exhausted` | **yes** | *"keep going, I will pay"* is a legitimate action; resume grants a fresh budget |
| `failed_terminal` / `provider_refused` | **no** | content policy, invalid request, billing — retrying cannot change the answer |
| `succeeded` | **no** | there is a Document; a new production event needs a new `Commitment` (§8.1) |
| `incomplete` | **yes** | the ordinary resume path; this is what D14 exists for |

**The idempotency key does not change**, which is the whole point: the resumed Task carries the same
`{commitment_id, module_id}` and therefore **HITs every memo already committed**. A cancel after 3
of 5 sections resumes at 2 calls, not 5 — the property §8.7 claims, now reachable.

`CHOICE` — the API exposes this on the same operation as start (§18.1): a `POST …/generate` finds
the existing Task and resumes it if resumable, or returns the terminal failure with its class
otherwise. *Alternative:* a separate `resume` endpoint; rejected because a button labelled
*Generate* should do the obvious thing, and the class-based refusal keeps it honest for the one
case where retrying is pointless.

---

# 9. End-to-end workflows

## 9.1 Intake turn (synchronous)

```
1  authorize; append Utterance                        tx, no model
2  step(situation envelope) → Situation payload        ≤1 call     ◄── FIRST, see below
   step(job envelope)       → Job payload             CF-2: its own decision
3  subject strong?  → step(scope_tier envelope)       ≤1 call, cached — reads purpose,
                    → step(frame envelope)              target_capability, sources from (2)
                                                      ≤1 call, cached   §6
4  sufficiency(readings, utterances, stated, tier, frame)   dom, pure
     tier = documented → do NOT request a syllabus    [LOCKED Foundation §3.2]
     multi-frame ∧ unresolved frame → BLOCKING        §6.3
5  asking non-empty → ask(...)  ≤1 call → questions
   else → ready
6  respond: readings WITH strength, questions | ready
```

**Rev. 6 ran `scope_tier` and `frame` *before* the situation they read, which could not work.**
`select_frame(subject, situation, candidates)` consumes the situation `[LOCKED]`, §6.3's precedence
has *"the situation implies it"* as rule 3, and the frame envelope's inputs include
`frame_selecting_readings` — which **are** situation readings. The `scope_tier` envelope likewise
contains `purpose` and `target_capability`. Both were being computed from a situation that did not
exist yet, so rule 3 was unreachable and the tier's `purpose` input was undefined.

Reordered: situation and job first, then the two per-subject classifications, then sufficiency —
which needs all of them. Nothing else moves, and the latency story is unchanged because the same
calls happen in the same turn.

*On the first turn with no subject:* `situation` still runs (it is what determines subject strength),
`verdict = needs_subject` short-circuits before step 3, and neither classification is attempted. The
`subject strong?` gate is therefore on the **derived** reading, which is the only place it can be.

Step 6's *"with strength"* closes §1's finding: V1 hands planning *"a bare string"* while the
confidence lives in a separate `intake_strategy` record, so *"a plan derived from a guessed entry
point looks identical to one derived from a stated entry point"* `[OBSERVED]`.

**The deadline is the SLA, and steps 2–4 must fit inside it.** With two cached classifications and
two derivations, a cold turn is up to 4 calls. `UNKNOWN` whether that fits 30 s; if it does not,
the fix is to make `scope_tier` and `frame` a Task on first encounter and answer `unknown` for that
turn — recorded here as the pre-planned fallback rather than discovered later.

## 9.2 Planning Task

```
step(structure)   inputs: subject_key, frame, source_set  │ env: model, prompt, taxonomy,
                  ── SITUATION-FREE (§0.1)                │      frontier
step(projection)  + situation, job, tier
step(scope)
step(partition)   → mints module_ids (assigned, S14)
for each module:  step(sections[module_id])               ── FAN OUT, model-call cap
step(ordering[modules])
for each module:  step(ordering[sections, module_id])
────────────────────────────────────────────────────────── all dom from here, 0 calls
extent(scope, partition, density_constants, capability_declaration)   ◄── §12.2a
template_policy(situation, job) → template_id             ── BEFORE feasibility (D15)
feasibility(scope, capability_declaration(template_id))
integrity(current_decision_set, capability_declaration)
```

**Reuse per step, and this is where the design pays for itself:**

| Step | Reused when |
|---|---|
| `structure` | another project shares subject × frame × sources × env — **often, in principle** |
| `projection` … `partition` | a re-plan where nothing upstream moved |
| `sections[m]` | that module's `covers` is unchanged, **even after a re-partition** (§5.6) |
| `ordering` | members and bound constraints unchanged |
| `extent`, `feasibility`, `integrity` | never cached — pure, free, and caching a computed fact is how V1's `feasibility` became inert (CC1) |

**Steps 1 and 2 are joint only on a structure MISS** (Architecture C3). On a HIT, projection
consumes the stored structure and no joint call is possible. The property that matters is **S3**
(`judged = structure.concepts`), which `integrity` checks either way; `unjudged` was **0 in every
record** `[MEASURED]`, so jointness is the heuristic that achieved the invariant, not the
invariant.

## 9.3 Correction Task

```
1  append Utterance                                   sync, before the Task
2  step(routing envelope) → targets, reading, replacement payloads     1 call, ~97 s [MEASURED]
3  for each TARGETED kind: write a new DecisionVersion + DependencyEdges
   untargeted: NOT re-derived                         ── the point
4  stale_set = walk_dependents(changed_version_ids)   §10.2
5  integrity(current_decision_set, capability_declaration)
6  report: reading · claimed vs actual · unclaimed drift · violations · WHAT IS NOW STALE
```

Step 5 is §3's option E and the thing that stops corrections *creating* structural violations:
both measured corrections changed a relationship unnoticed, in opposite directions — `generate-01`
took phantoms **7 → 4 incidentally** while answering a content complaint `[MEASURED]`.

**Re-planning after a correction is the ordinary planning Task.** Nothing special-cases the stale
subtree: a stale decision's envelope has diverged, so `step()` misses and re-derives it, while
everything upstream hits. The two mechanisms agree by construction — and `structure` is exactly
the expensive call that gets reused when `job` changes, because `job` is not one of its inputs
(§5.3).

## 9.4 Approval (synchronous)

```
1  stale_set non-empty?          → 409 {stale: [...]}      ── a stale set can be perfectly
                                                              internally consistent
2  integrity → violations?       → 409 {violations, decisions_implicated}
3  feasibility → shortfalls      → DISCLOSED in the response, never a refusal   (H2)
4  mint Commitment + CommitmentMember rows, per member (S10 — closes B2)
   pin: models · prompt_versions · taxonomy_version · source_versions ·
        template_id · template_content_hash · capability_decl_version
   store `disclosed` — the shortfalls the user actually saw
5  idempotent on (version_set_hash, environment_hash)          ◄── Rev. 3
```

**Why the environment is part of approval identity.** Rev. 2 keyed on the version set alone, which
looked right — *"same decisions approved twice is one approval."* It is not, because the
environment is pinned **and** `disclosed` is derived from it:

```
approve under template study-notes@abc123     → Commitment C1, disclosed = {parallel-state}
someone edits the template's CSS              → template_content_hash = def456
approve again, same decisions                 → Rev. 2 returned C1
                                                 C1 pins abc123, which no longer exists
                                                 C1's `disclosed` describes the old capability
```

Since `Feasibility` reads a per-`(renderer build × template hash)` declaration (D18), a template or
engine change *is* a different approval context — the user is agreeing to different disclosures.
`DECIDED`: **identity is `(version_set, environment)`**; a genuine double-click, where the
environment is stable, still yields one commitment.

*Alternative considered:* refuse approval when the environment has moved since the plan was
computed, and require a recompute. Rejected as more machinery for the same outcome — minting a new
commitment already records exactly what changed, and §10.2a's sequences order them.

### 9.4a `approved_extent` must be pinned, and Rev. 6 left it floating

`BriefInputs` (§5.7a) includes `approved_extent` — V1's brief says *"Approved size for this part:
~4 pages"* `[OBSERVED]` — and **nothing in Rev. 6 said where that value comes from.** Following the
other rules as written produced a contradiction:

```
Extent is COMPUTED and recomputed on read (C1, §12.2a)
density_constants are deliberately OUTSIDE every envelope (§5.5)
         ↓
recalibrate the constants (OQ-2: measured ~2.8 pages/concept vs the table's 1.0)
         ↓
extent() returns a different number for the SAME Commitment
         ↓
approved_extent in BriefInputs changes  →  every memo envelope changes
         ↓
ALL generated content invalidated by a calibration change
```

That defeats §5.5's stated purpose — *"recalibrating the constants changes `Extent` **without**
invalidating `scope`"* — one level down, where it matters more, because memos are the expensive
results.

`DECIDED` — **the approved extent is pinned in the `Commitment`.** It is part of what the user agreed
to, not a derived view: approval is a contract over *"a document about this long"*, and that number
cannot change under them. So:

| | Value | Changes when |
|---|---|---|
| `extent(...)` | a **computed view**, recomputed on read | constants or declaration change |
| `Commitment.approved_extent` | **pinned at approval**, immutable | never — a new approval mints a new Commitment |
| `BriefInputs.approved_extent` | reads the **pinned** value | only when the Commitment does |

**Consequences, both wanted:** recalibration improves *future* plans and invalidates *no* committed
content; and the honest comparison for A4 becomes available — *promised* (pinned) against *produced*
(measured), per module, which is the feedback loop §2 found missing entirely.

**Integrity reports decisions implicated, never a unique repair.** `Scope.covered = {A}` with
`Module.covers = {A,B}` is repairable by removing B from `partition` **or** adding B to `scope`;
which is right is a judgment about intent. The parked patch's rule generalises: *"Reported, never
repaired. Placing a stranded concept would be a partition decision, and this layer must not make
one"* `[OBSERVED]`.

## 9.5 Generation Task

```
0  renderer_available()?  → NO: terminal, with the install command, BEFORE any model call
   ── "the model call between the two takes minutes and is billed" [OBSERVED]
   ── this is RENDERER AVAILABILITY, not representation capability (P2, C5)
1  orders = one per Section of this module, from the Commitment
   each carries: concepts+depths+needs, extent, why_here, AND the disclosed shortfalls
2  pending = orders;  while pending and budget remains:
     for order in pending, bounded by the MODEL-CALL cap (§8.6b ③):
       step("memo", {brief_envelope(order)}, derive_fn = two_attempts_keep_better)
         ── §7.3. The claim branches are NOT restated: HIT, BUSY→keep pending (T10),
            MISS→FIND_RESULT→RECONCILE, EXPIRED→takeover and PUBLISH all come from
            step(). `derive_fn` is the only thing generation supplies.
         ── Rev. 11: this was a FOURTH copy of the branches, found by the sweep rather
            than by review, which is the argument for deleting copies over syncing them.
3  all present? → build; else → INCOMPLETE with per-section reasons, no Document
```

**Two attempts, and "better" is deterministic.** `check_unit(order, candidate)` returns
`concepts_missing`; the kept attempt covers **more of the section's assigned concepts**, by
normalized substring match `[OBSERVED]`. No judge, no extra call. V1's reason survives: *"a retry
that covers less than the first would otherwise make asking again actively harmful."* Note what it
does **not** measure — depth, treatment, extent — all promised and unenforced (§4's table); that is
OQ-1, not a scoring choice.

**Incomplete is a first-class terminal-ish state, and no partial Document is written.** S12 makes
an incomplete Document not a Document. V1 could not afford that rule because resuming re-spent all
five calls; here it costs the missing sections only. **The mechanism is what makes the invariant
affordable**, and the failure attribution V1's comment protects is preserved on the Task, not in
an artifact.

## 9.6 Document construction

```
1  front_matter ← the PLAN (title, subtitle, assumed_entry, target_capability, marked gaps)
   ── never the model: "asking a model to restate them would let them drift from what was
      approved for no gain" [OBSERVED]
2  construction_key = §5.8;  step(construction_key) → HIT ⇒ nothing to do
3  document = build_document(front_matter, ordered_sections, builder_version)   dom
4  validate_blocks(document, capability_declaration, disclosed_shortfalls)      dom
     every StructuralClaim carries a Licence                 S6 — closes A7
     the perceptual-referent guard, VERBATIM                 X1
     approved-shortfall rule                                 §9.7
   violations → terminal failure; NO Document
5  PAYLOAD_PUT(document) → COMMIT(construction_key)
```

**Duplicate construction is a no-op**, by the same claim protocol. Two workers can each observe
*"all sections present"*; one commits, the other is fenced and discards. Without this, two
structurally distinct Documents could claim one production event and corrupt `superseded(d)`, the
`latest` pointer, and the support history.

### 9.6a ATTACH_PROVENANCE — the document claim's HIT path

**The same hole `ATTACH` closed for shared derivations exists here**, and Rev. 5 did not catch it.
`construction_key` deliberately excludes `commitment_id` (§5.8, §0.3), so two commitments that agree
on a module's front matter and memos produce the **same** construction key. The second one therefore
`HIT`s the claim — and `PUBLISH`, which is where `INSERT DocumentProvenance` lives, is never reached.
Result: a Document with no provenance row for the commitment that asked for it, so *"which plan
produced this?"* has an incomplete answer.

```
ATTACH_PROVENANCE(K, commitment_id):
  BEGIN
    ① SELECT document_id FROM DocumentConstruction WHERE construction_key = K
       not found → ROLLBACK, INCONSISTENT
         ── unreachable under §7.3a: the claim and DocumentConstruction are written in one
            transaction. Surfaced, not swallowed.
    ② INSERT DocumentProvenance(document_id, commitment_id)
         ON CONFLICT (document_id, commitment_id) DO NOTHING          idempotent
  COMMIT
  return document_id
```

So the document step reads:

```
step("document", {construction_key}, derive_fn = build_document,
     on_result = λ d: ATTACH_PROVENANCE(d, commitment_id))                  ◄── §7.3
```

**`on_result`, not a `HIT`-branch call — and that distinction is Rev. 11's fix for a real gap.**
Rev. 10 attached provenance on the `HIT` branch only. The generic `step()`'s **`RECONCILE`** branch
returned the existing Document directly, so:

```
Commitment C2 · Document D already exists · DocumentProvenance(D, C2) absent · Claim lost
   FIND_RESULT finds D → RECONCILE rebuilds the claim → D returned
   → no ATTACH_PROVENANCE  →  "which plan produced this?" has a missing answer for C2
```

Content correct, audit link lost — and it violated the rule §9.6a itself states. Routing the attach
through `on_result` makes it run on **all three** arrival paths (`HIT`, `RECONCILE`, fresh `PUBLISH`),
which is the only placement that cannot be forgotten per-branch.

**No Document is duplicated and none is rebuilt** — the point of §5.8's content identity. The pattern
is now consistent across all three claim families: a `HIT` on a *shared* claim attaches a pointer
(§7.3b), a `HIT` on a *document* claim attaches provenance, and a `HIT` on a *memo* claim needs
nothing because a memo has no per-project or per-commitment attachment.

That symmetry is worth stating as a rule, because it is what both holes violated: **if a result is
reachable from more than one context, a claim `HIT` must still attach the calling context.**

## 9.7 The approved-shortfall rule

Exactly **two of seven** prose failures are `served = False` in `agent/treatment.py` `[OBSERVED]`,
and the *reason* differs while the *block* does not.

```
WHICH BLOCK     Reference, in both cases — it "names something it cannot show"
                NEVER Prose: prose is the carrier the need declared insufficient
                NEVER a StructuralClaim for that need: Architecture §13's forbidden
                substitution
IS IT PERMANENT differs — and belongs in the plan's DISCLOSURE, not the document
```

| Need | `treatment.py`'s note | Permanent? |
|---|---|---|
| `perceptual-referent` (licenses *"image"*) | *"the only one that cannot preserve assertions: a generated figure adds content the document never asserted"* | **yes** — X1; no build changes it |
| `parallel-state` (licenses *"sequence · swimlane · timeline"*) | *"No realization exists. Two actors evolving at once currently come out as prose, which is the substitution [Architecture] §13 forbids"* | **no** — the repair is to build a licensed realization |

Governing rule, quoted in that docstring: *"if we cannot produce anatomical figures, the correct
response is to **report the limitation**, not to substitute a diagram that answers a different
failure."* (That is `Architecture.md` §13, the V1 reference — not a section of this document.)

`validate_blocks` therefore asserts: for every concept whose `RepresentationNeed` appears in the
commitment's `disclosed` shortfalls, the document contains **no realizing `StructuralClaim` for
that need**, and contains a `Reference` carrying that need's licence.

## 9.8 Rendering — the Task, not the mechanics

§12 defines how a render works. **Rev. 6 pointed here and left the Task's result publication
undefined**, which is the half that decides whether two concurrent renders produce one artifact or
two.

```
Task(render, {document_id, render_env_hash})
   ▼
① renderer_available()?  → NO: terminal, before any work
   ▼
② step("render", {document_id, render_env_hash}, derive_fn = ③–⑤ below)    ◄── §7.3
   ── the claim branches are NOT restated here. HIT, BUSY, MISS→FIND_RESULT→RECONCILE,
      EXPIRED→takeover and PUBLISH all come from the canonical step(). Rev. 10 printed
      them again and dropped FIND_RESULT in the copy.
   ▼
③ merge → MergeReport; honesty + unrendered checks (§12.3)   violations → terminal
   ▼
④ acquire a render slot (§12.5) → print → bytes + LayoutReport
   ▼
⑤ PAYLOAD_PUT(pdf), PAYLOAD_PUT(html)        content-addressed, before any metadata
   ▼
⑥ PUBLISH: BEGIN
     claim CAS on K
     seq = bump_artifact_seq(document_id, template_id)        §10.2a
     INSERT ArtifactIndex(document_id, template_id, template_content_hash,
                          render_env_hash, capability_decl_version, bytes_hash,
                          seq, payload_ref, page_count, scale, overflows)
   COMMIT
```

**Why render gets a claim and export does not.** Export is a deterministic function of bytes that
already exist (§9.9a), so duplicate work is harmless. A render is **not** guaranteed byte-identical:
the same document under the same environment can produce different `bytes_hash` values, since Chromium
is not a canonicalised serialiser the way §9.9a's zip is. Two unclaimed concurrent renders would
therefore create **two Artifacts for one (Document, environment)** — both bumping `seq`, which makes
`superseded(a)` report a successor that is merely a duplicate. The claim makes it one.

`CHOICE` — claim key `(document_id, render_env_hash)`, not including `bytes_hash`: the point is to
single-flight the *production*, and the bytes are the output. *Alternative:* no claim plus a
dedupe-on-`bytes_hash` upsert; rejected because it still burns a second browser slot, which is the
scarce resource (§12.5).

**Render failure is transient** and the Document survives, so a retry is this same Task — which now
`HIT`s nothing and re-reserves after the lease expires.

## 9.8a Source extraction

```
Task(source_extract, {source_id})
   ▼
K = claim_key("source_extract", {source_content_hash, extractor_version})   §5.12a
    ── CONTENT-addressed and global; the Task key carries the SAME pair (§8.1), so an
       extractor upgrade is a new Task and not a cached success
   ▼
step("source_extract", {content_hash, extractor_version}, derive_fn = extract)   ◄── §7.3
  ── no on_result: nothing to attach, because Rev. 9 removed the Source pointer (§9.8b)
  ── the claim branches come from step(). Rev. 10 restated them here and skipped
     FIND_RESULT, so a lost claim meant re-extracting and discarding the result.

PUBLISH's branch for this domain (§7.3a):
         BEGIN  claim CAS
                INSERT SourceExtraction(content_hash, extractor_version,
                                        outcome='extracted', payload_ref)
         COMMIT
non-transient extraction failure → the SAME publication, outcome='infeasible' + reason
         ── P8: recorded as a result, not as an absence or a mutated flag
```

**Extraction is content-addressed and global for the same reason structure is** (§4.2a): identical
bytes extract identically regardless of who uploaded them, so two users supplying the same syllabus
extract once. And it is the third instance of the HIT-must-attach rule (§9.6a) — a global result
reached from a project context has to attach that context.

### 9.8b Extraction state is computed, not a pointer — and this removes a race rather than fencing it

**Rev. 8 kept `Source.extracted_ref` and `Source.state` and updated them at publish.** Two extraction
Tasks for one source under **different extractor versions** have different claim keys and different
Task keys, so both may legitimately run — and both wrote the same project-local cell, unfenced:

```
v2 publishes first  → Source → extraction-v2
v1 publishes later  → Source → extraction-v1        ◄── a silent regression to the older extractor
```

Worse, the failure path was equally unfenced: a late `infeasible` from v1 would mark the source
unusable **after v2 had already succeeded.**

`DECIDED` — **remove the cell.** There is no shared mutable state to race for:

```
extraction(source)  =  SELECT outcome, payload_ref, reason
                         FROM SourceExtraction
                        WHERE content_hash = source.content_hash
                          AND extractor_version = <the running build's active version>

  row, 'extracted'   → usable, payload_ref is the SourceStructure
  row, 'infeasible'  → recorded, with a reason to show the user       ◄── P8
  no row             → 'pending' if a Task exists for this pair, else 'uploaded'
```

A v1 row left behind after v2 deploys is simply **not consulted**. Both rows stay — each is a true,
immutable statement about what that extractor produced from those bytes — and the question *"what is
the extraction now?"* is answered by the build, not by whoever wrote last.

This is C4's pattern applied one object further: `status`, `freshness` and `supersession` are computed
for exactly this reason, and Rev. 8 reached for a column instead. *The fix a version-fenced update
would have given is strictly weaker* — it would make the race safe while leaving a cell whose meaning
depends on write order.

`CHOICE` — the active extractor version is **deployment configuration**, not data: it is the version
the running build ships. *Alternative:* a per-project pinned extractor version; rejected unless a
`Commitment` ever needs to pin extraction, which it does not today — a source's content hash is what
invariant 8 pins (§4.2), and that is version-independent.

**P8 is satisfied more completely than before:** *"a conditional capability is never silently
skipped"* `[LOCKED]`. An `infeasible` extraction is now an immutable row with a reason, not a flag that
a later writer can overwrite.

## 9.9 Export — the one derived result with no claim

Rev. 4's log said this was written. It was not; the API promised `202 + task ref` and nothing
defined what the ref pointed at. Written here, and it turns out to be short because export is
**packaging, not rendering** — V1's own reasoning, and it survives: *"each module is its own
document with its own cover and page numbering, and merging them is a render-engine job …
not a packaging one"* `[OBSERVED]`.

```
input      a Commitment
   ▼
① resolve the ordered artifact set — FROM THE COMMITMENT, never "latest"   ◄── Rev. 6
     modules, in the order of the Commitment's `ordering` member version
     for each module m:
       section set  ← the Commitment's `sections` version for m
       Document     ← the Document whose construction_key's memo set matches
                      THAT section set                       (§9.6, I7)
       Artifact     ← SELECT … FROM ArtifactIndex
                      WHERE document_id = <that Document>
                        AND capability_decl_version = C.environment.capability_decl_version
                      ── a direct index read (§4.2), not a described intention.
                         Rev. 6 named a lookup that had no column to use.
   ▼
② export input identity — deterministic, over resolved content
     export_input = [ {module_id, ordinal, document_id, artifact_id, bytes_hash} ... ]
     export_hash  = sha256(canonical_json(export_input))
   ▼
③ Task key = task_key("export", {export_hash})      ◄── Rev. 6, NOT {commitment_id}
   ▼
④ if export-zip/<export_hash> already exists → done. No claim, no reservation.
   ▼
⑤ build a CANONICAL zip (§9.9a) — byte-identical for identical input
   ▼
⑥ PUT to export-zip/<export_hash>
   ▼
⑦ Task succeeds with result = {export_hash, path, size, export_input}
   ▼
⑧ delivery: ≤ threshold stream inline, above → short-TTL signed URL (§13.3)
```

**Two corrections in step ①, and the first is a real correctness bug.**

Rev. 5 said *"the current Artifact for (**latest Document** of that module, pinned template)."* That
is wrong, and the way it is wrong matters: a `Commitment` is *"the system is answerable for producing
this"*, so an export of commitment C₁ must contain **what C₁ approved.** Resolving by *latest* would
package content belonging only to a later commitment C₂ — the user downloads a zip labelled with
their approved plan and gets material they never approved. That is CC2's class precisely: every
surface reports success.

So export resolves **down from the Commitment**: its `ordering` version gives the module order, its
`sections` version per module gives the section set, and the Document is the one built from exactly
those memos. The `seq` relations I8/I10 are for answering *"what is current?"* — a different question
that export must not ask.

**And the Task key must be `export_hash`, not `commitment_id`** (step ③). The artifact set can change
while the commitment does not — a module re-rendered after a template fix produces a new Artifact
under the same commitment (I10). Keying on `commitment_id` would return the old succeeded Task and
hand back a stale zip. Keying on the resolved input makes a changed artifact set a new Task, which is
what it is.

*Note the ordering of steps ② and ③:* resolution happens **before** admission, because the key is
derived from the resolution. `CHOICE` — resolution is a handful of indexed reads with no model call,
so doing it in the request path to compute the key is cheap. *Alternative:* a two-phase Task that
resolves then re-keys; rejected as machinery for no gain.

### 9.9a Canonical zip serialisation — and why this is required, not cosmetic

**Rev. 5 said *"write identical bytes to the same path"* without specifying what makes them
identical, and that gap reintroduces the exact hazard §7.4 exists to rule out.** The path is derived
from `export_hash`, which is a hash of the **inputs** — not of the output bytes. So if two workers
build non-deterministic zips, they write **different bytes to the same path**, and the second
overwrites the first. §7.4's argument against key-addressed payloads applies verbatim: every index
says the right thing and the bytes differ between reads.

Determinism closes it. `DECIDED`:

```
format        ZIP, store or deflate — one setting, never "whatever the library defaults to"
compression   deflate, level 6, no zip64 unless size forces it (then always)
entry order   by `ordinal` from export_input — the committed order, fixed
entry names   NN-<slug>.pdf, NN from ordinal, zero-padded to the width of the largest
              ── the slug is from the module title AT COMMITMENT TIME, so a later rename
                 cannot change the bytes
timestamps    fixed constant 1980-01-01T00:00:00Z for every entry      ◄── the usual culprit
mode bits     0644 for files, no directory entries
extra fields  none — no UT/Unix extended timestamps, no platform attributes
comment       empty, archive and per-entry
no extras     no manifest, no README, nothing carrying a build time or hostname
```

With those fixed, `bytes = f(export_input)` exactly, so two workers produce identical bytes and the
overwrite is harmless. **A test asserts it** (§15.9) rather than trusting the library.

`CHOICE` — fixed 1980 timestamps over "the artifact's creation time": a zip's timestamp field has no
reader that needs truth here, and using any real time makes the output non-reproducible, which is the
property the path depends on. *Alternative:* address the object by output-bytes hash instead;
rejected because then the path is unknown until after the build, so step ④'s cheap existence check
becomes impossible and every export rebuilds.

### Why export has no claim — a principled exception, now that determinism holds

D17's claim protocol exists to prevent duplicate **model calls** (§7.6). Export makes none: it is a
deterministic function of bytes that already exist. Two concurrent exports resolve the same
`export_input`, compute the same `export_hash`, build **byte-identical** zips (§9.9a), and step ④
makes the second a no-op. Single-flighting would guard nothing.

`DECIDED` — no claim, no `MemoIndex`-style row, no publication transaction. The object store's
content path *is* the idempotency — **conditional on §9.9a**, which is why that subsection is
normative and not advice.

**What happens when an artifact is missing or superseded** — the case the review asked for, and the
only place export needs a judgment:

| State at step ① | Behaviour |
|---|---|
| a module committed by C has **no** Document yet | **refuse**: `409 export_incomplete`, naming the modules. A package that looks complete and is not is CC2's class |
| the committed Document exists, but **no Artifact** under C's pinned render environment | **refuse**, naming the modules: this is *"not rendered yet"*, and the fix is a render Task, not a silent substitution with a differently-rendered artifact |
| a **newer** Artifact exists for that Document and template (higher `seq`) | **use the one matching C's pinned `capability_decl_version`** — not the newest. An export of C must be what C promised. If C's pinned environment is no longer reproducible, see the next row |
| C's pinned template or renderer build no longer resolves | **refuse**, and say which: C's environment is unsatisfiable. §9.4's concern surfacing late, and it is honest to name it rather than render something else |
| a later commitment C₂ has newer content for a module | **irrelevant, and deliberately so** — export reads from C. Report it as an informational note (*"module 3 has newer approved content under a later plan"*) so the user can choose to export C₂ instead |

Rows 1, 2 and 4 refuse; row 5 informs. That is P2 applied one level down: an **absence** or an
**unsatisfiable pin** is an error the user cannot act around inside this operation; the existence of a
newer plan is a choice they can make.

**Export is never authoritative.** It is derived from artifacts, collectable at any time (§10.6),
and re-derivable in seconds. Losing every export costs nothing but CPU — which is why it sits below
artifacts in §11's durability ranking.

---

# 10. Persistence, transactions, and consistency

## 10.1 What is transactional and what cannot be

```
ONE transaction (Postgres)     decisions · versions · dependency edges · utterances ·
                               sources · commitments + members · claims · tasks ·
                               memo index · document index · artifact index
NEVER one transaction          Postgres  ✗  object storage
```

`DECIDED` — no two-phase commit, no distributed transaction. The gap is closed by **write
ordering** plus content addressing, not by coordination.

## 10.2 Transactional units

| Operation | Transaction | Why |
|---|---|---|
| append `Utterance` | single insert | append-only |
| `RESERVE` / `HEARTBEAT` | **one statement each** | §7.2 — atomicity without a transaction |
| **`PUBLISH`** — claim CAS **+** `DecisionVersion` + `DependencyEdge`s + slot bump | **ONE transaction, CAS first** (§7.3a) | Rev. 1 issued the CAS and the metadata separately; a crash between them leaves the claim saying *"done"* and the store empty, and `stale` then walks edges that do not exist |
| **`PUBLISH`** — claim CAS + `MemoIndex` | **ONE transaction** | same |
| **`PUBLISH`** — claim CAS + `Document` upsert-on-content + `DocumentConstruction` + `DocumentProvenance` (+ doc seq on insert) | **ONE transaction** | same |
| **`PUBLISH`** — shared kind: claim CAS + `SharedDerivation` + project-local pointer version | **ONE transaction** (§4.2a) | a shared payload with no pointer is unreachable; a pointer with no payload is dangling |
| mint `Commitment` + `CommitmentMember`s | **one transaction** | a commitment with partial members is a contract with holes |
| `stale_set` computation | one read transaction, `REPEATABLE READ` | a version arriving mid-walk would give a torn answer |
| Task lease / complete / cancel | one statement each | fenced by epoch |

**The rule behind every row:** a write is in one transaction with whatever makes it *visible*, and
a write is never in one transaction with a model call or an object-storage put.

## 10.2a Version ordering is a monotonic sequence, never wall-clock

**Rev. 1 ordered versions by `created_at`, and that was too weak for the load it carries.**
Timestamps tie, and concurrent transactions produce timestamps whose order is not the semantic
order. The domain concept is *"a newer `DecisionVersion`"*, not *"a row with a later timestamp."*

**And it propagates further than the review noticed:** `superseded(d)` (*"a later Document exists
for the same Module"*) and `superseded(a)` (ordering over `(document_id, template_id, created_at)`)
were both wall-clock too. All three are domain relations, so all three get sequences. `DECIDED`:

```
Decision slot gains          next_version : bigint, default 1
DecisionVersion gains        version_number : bigint
                             UNIQUE (project_id, kind, member, version_number)

bump_slot(project, kind, member):
  UPDATE Decision SET next_version = next_version + 1
   WHERE (project_id, kind, member) = (...)  RETURNING next_version - 1
  ── serialises on the SLOT row, which is exactly the right granularity: two versions of
     different decisions never contend, two versions of the same decision must.

Module gains a document sequence   bump_module_doc_seq(project, module_id)
(document, template) gains an artifact sequence
```

Issued inside the publication transaction (§7.3a step ②), so a rolled-back publish consumes no
sequence number — or, if it does under a retry, gaps are harmless because only *order* is used,
never contiguity.

`created_at` is retained **for observability only** (§17) and no relation reads it.

**`stale` is then a graph walk over sequences:**

```
stale(v) ⟺ ∃ e ∈ DependencyEdge(version_id = v) :
             ∃ v' : v'.project_id = e.depends_on.project_id
                  ∧ v'.kind      = e.depends_on.kind
                  ∧ v'.member    = e.depends_on.member
                  ∧ v'.version_number > e.depends_on.version_number
```

Equivalently, and cheaper: `e.depends_on.version_number < Decision.next_version − 1` for that
slot — a single join against the slot row, with no scan over sibling versions. `CHOICE` — the
second form; the first is the definition.

Transitive staleness follows by walking dependents of every changed version, which is why
`DependencyEdge` is indexed on `depends_on_id`.

`reusable` is not this query. It is `SELECT ... WHERE (kind, member, envelope) = ...` — a point
lookup. **Two mechanisms, two queries, and conflating them was Rev. 2's error** (Architecture E4):
a prompt-version bump changes the envelope (not reusable) without making an approved plan wrong
(not stale).

## 10.3 Write ordering

```
payload (object storage, content-addressed)
   └─► index/claim COMMIT (Postgres)
          └─► referenced by anything else

Content Memo  ──before──►  Document  ──before──►  Artifact  ──before──►  delivered
```

Never the reverse. A forward crash leaves an orphan object; a reverse crash would leave a
**dangling reference**, which is unrecoverable state rather than garbage.

## 10.4 Crash windows, enumerated

| Window | Consequence | Recovery |
|---|---|---|
| after `Utterance` insert, before the derivation | the turn is lost | retry: 1 call, envelope reuse if unchanged |
| during a model call | nothing written | lease expires → takeover |
| **after model success, before `PAYLOAD_PUT`** | **one call paid, lost** | takeover re-derives. **The at-least-once window; irreducible** |
| after `PAYLOAD_PUT`, before `PUBLISH` | orphan object | takeover re-derives; GC reclaims |
| **mid-`PUBLISH`** | **nothing** — the claim CAS and every metadata row land together or not at all | takeover re-derives; the orphan payload is reclaimed |
| after `PUBLISH`, before the Task records progress | nothing lost | re-run HITs the claim, 0 calls |
| **claim `COMMITTED` but no version row** | would make `stale` walk missing edges and report a drifted plan as current | **impossible** — §7.3a, one transaction. *This was reachable in Rev. 1* |
| after `DecisionVersion` insert, before `DependencyEdge`s | would un-stale dependents | **impossible** — same transaction |
| after Document `PUBLISH`, before Artifact | Document survives | re-render Task, ~3.4 s `[MEASURED]` |
| cancel requested mid-derive | the in-flight call completes and publishes | Task → `cancelled`; committed memos survive (§8.7) |
| after Artifact object write, before index row | orphan PDF | re-render; GC reclaims |
| coordinator dies with N Tasks leased | Tasks orphaned | lease expiry + sweep (§8.4) |

## 10.5 Idempotency boundaries

```
HTTP request      → Task idempotency_key       I14 — PER KIND, §8.1
Task              → per-step claim key         I4  — claim_key(domain, identity), §5.12a
step              → payload content hash       object path, §4.3
shared step       → ATTACH's pointer check     I1, §7.3b
approval          → version set + environment  I11, §9.4
utterance append  → request id + fingerprint   I13, §18.3
```

Six nested levels, each idempotent, so a retry at any level is safe. **Every identity is defined
once in §5.11** — Rev. 3 restated two of them here, with the pre-Rev. 3 formulas, which is exactly
the contradictory sentence an implementer follows.

## 10.6 Garbage collection

`CHOICE` — a periodic sweep, not reference counting.

| Class | Collectable when |
|---|---|
| orphan payloads | no index row references the path **and** older than `max(lease) × 2` |
| **ANY claimed result: claim + index/result row + payload, as ONE unit** | per that domain's rule below. **Deleted in reverse write order** — §10.6a |
| `Claim` rows, committed | never **independently** of the result they reference; only as part of that result's unit |
| `Task` rows, terminal | older than the status-visibility window `CHOICE`: 30 days |
| `DecisionVersion` | **never** — a Commitment may name it |
| **`SharedDerivation`** | **never while any pointer references it**, and `CHOICE` never at all — it is unowned by any project (§4.2a), so deleting a project must not touch it. A derivation no project points at is still a cached model call worth keeping |
| **`Document`** | **never** — an `Artifact` and a `DocumentProvenance` row may reference it |
| **export objects** | no non-expired `Task` result references the path. Same unit rule: the Task row's result goes first |
| **`CallLedger`** | **never** while any quota window or audit horizon could read it `CHOICE`: retain 1 year, U8 |
| **`SourceExtraction`** | **never** `CHOICE` — it is global reusable derived data with no owner, exactly like `SharedDerivation`, and an extraction no project currently consults is still a cached extraction worth keeping. Its payload follows §10.6a's unit rule if that is ever revisited |
| **`RoutingResult`** | **with its claim**, after the correction-audit horizon `CHOICE`: 90 days. It is a memoised 97 s computation and an audit record of *"claimed vs actual"* (§3). Rev. 9 gave it a retention and **left its claim out of the unit** — see §10.6a |
| **`UserQuotaBucket`** | buckets older than the longest quota window `CHOICE`: 7 days. Admission state, not accounting — the `CallLedger` is what answers historical spend |

### 10.6a Deletion order — the mirror of F4, and Rev. 6 had it backwards for memos

**The rule is per claim domain, not per table — and Rev. 9 wrote it for memos only.** Having fixed the
memo case, Rev. 9 then gave `RoutingResult` a 90-day retention whose unit named no claim, recreating
the identical defect one domain along:

```
t+90d   RoutingResult(K) deleted,  Claim(routing, K) still COMMITTED → result_ref = R
t+90d   LOOKUP(K) → HIT → R does not exist
```

Reachable: a user re-submitting the same correction against the same decision set hits that key. So
the rule is stated once, over **every** claim domain:

> **A claimed result is one GC unit: its `Claim`, its index/result row, and its payload.** They are
> collected together, in reverse write order, or not at all. No domain may be given a retention
> policy without naming its claim in the same breath.

**The original bug, for the record:** §10.6 allowed a memo *payload* to be collected once its Document
existed, while the memo `Claim` stayed `COMMITTED` with `result_ref` pointing at the deleted object.
`LOOKUP` would then return **`HIT`** and hand back a dangling reference.

That is not a lost cache — it is a **false HIT**, and it breaks D14's one guarantee. It is reachable:
`construction_key` excludes `commitment_id`, so a *different* commitment or a changed front matter
yields a new document claim while sharing memo keys. Generation looks those up, gets `HIT`, and
resolves nothing.

```
WRITE order (F4)     referent BEFORE reference
                     payload → index/claim → referenced by anything else

DELETE order (here)  reference BEFORE referent        ◄── the exact mirror
                     claim + index (one transaction) → THEN the payload
```

Why that order and not the other: after the claim is gone, a lookup is a clean `MISS` and the next
asker re-derives — correct, costing one call. Crash between the two leaves an **orphan payload**,
which the first row of the table above already reclaims. The reverse order leaves a false `HIT`,
which nothing detects.

**Stated as the invariant**, because both halves follow from it:

> A reference and its referent are never both live-and-unreachable. Writes create the referent first;
> deletions remove the reference first. Any crash window in either direction leaves **garbage**, never
> a **dangling promise.**

`CHOICE` — collect memos at all. *Alternative:* keep every memo forever, making the hazard
unreachable; rejected only because U8 (retention) is unsettled, and this rule makes collection safe
whenever that is answered. If U8 says *keep forever*, this subsection becomes dead code rather than
wrong code.

---

# 11. Failure and recovery model

Per store, with what relies on D17 stated explicitly.

| Lost | Readable | Work lost | Recomputed | Never recomputed | Relies on D17 |
|---|---|---|---|---|---|
| **Provider** | plan view, delivery, export, approval, integrity, Task status | none | — | — | no |
| **Render worker** | everything but new artifacts | in-flight renders | artifact from the Document, ≈ render time | — | no |
| **Task Store** | plan view, delivery; **status → "unknown"** | in-flight progress, leases | re-run; **no committed work re-spent** | — | **yes — this is the guarantee** |
| **Claim rows** | everything | **none** | rebuilt by `RECONCILE` (§7.3c) from the result's canonical identity — **0 model calls** if detected before deriving, at most 1 if after | — | the result tables' own UNIQUE constraints are what make the rebuild possible |
| **Content Memo** | plans, documents, artifacts | Σ unbuilt sections | ~65 s each `[MEASURED]` | — | no |
| **Artifact Store** | plan view, documents; **existing PDF delivery unavailable** | delivered bytes | ≈ render time per document | the *exact bytes* under a superseded render env | no |
| **Document Store** | plans, commitments | Σ that module's sections | ~65 s × sections | — | no |
| **Decision Store** | nothing meaningful | everything | — | **utterances, commitments — authoritative** | — |

**Reads, scoped per read** (Architecture G6) — none depends on the Model Gateway, the Work
Coordinator, or a live worker:

| Read | Needs |
|---|---|
| plan view | Decision Store |
| artifact delivery | Decision Store (authorize) + Artifact Store (bytes) |
| Task status | + Task Store |

**Losing `Claim` rows deserves its own note.** They are infrastructure state, but while they are
missing the uniqueness guarantee is gone, so two concurrent derivations could produce two versions
for one envelope — and §7.6 shows that spuriously marks plans stale. So: claims live **in the same
database as the versions**, and the `UNIQUE (project_id, kind, member, envelope)` constraint on
`DecisionVersion` is a **second, independent** guard that survives claim loss. `DECIDED` — belt and
brace, because the failure is silent.

---

# 12. Renderer subsystem

## 12.1 Template selection and identity

```
template_id            = template_policy(situation, job)        dom, BEFORE feasibility (D15)
template_content_hash  = sha256(template source)                _template_version [OBSERVED]
renderer_build         = sha256(playwright_version ‖ chromium_build ‖ font_set_hash
                                ‖ engine_version)              ◄── Rev. 7: engine_version
render_env_hash        = sha256(renderer_build ‖ template_id ‖ template_content_hash)
capability_decl_version= sha256(render_env_hash ‖ declaration_content_hash)
                         ◄── Rev. 6: the formal identity of (renderer_build × template);
                             Rev. 7 nests it on render_env_hash so the two cannot drift
```

**Rev. 6 left `engine_version` out of `renderer_build` while `render_env_hash` included it**, so two
artifacts could differ by engine version and share a `capability_decl_version` — and the Commitment
pins only the latter, so it did **not** fully identify the environment that produced its artifact.
`engine_version` is the Python engine package: it owns the document→HTML mapping, so it changes
output. It belongs in the build.

**The three hashes now nest, which is what makes them unable to disagree:**

```
renderer_build          what this binary set is          playwright · chromium · fonts · engine
   └─ render_env_hash   what produced these bytes        + template id · template content
        └─ capability_decl_version
                        what it could draw               + declaration content
```

So `capability_decl_version` determines `render_env_hash`, and pinning the former pins the whole
chain. Rev. 6 built them as siblings over overlapping inputs, which is how they came apart.

**`capability_decl_version` is the immutable identity of the pair, which resolves a gap Rev. 5 left.**
§12.1 described `renderer_build` as *"pinned in the Commitment"*, and the `Commitment.environment`
schema listed `template_id`, `template_content_hash` and `capability_decl_version` — **not**
`renderer_build`. So the thing described as pinned was not among the pinned fields.

`DECIDED` — rather than add a fourth field and have the same fact in two places (the pattern §5.11
exists to stop), `capability_decl_version` is **defined** as a hash over the renderer build, the
template identity and the declaration's own content. Pinning it therefore pins all of them, and a
change to any one yields a different version. Consequences:

| Change | `capability_decl_version` | Effect |
|---|---|---|
| Chromium or Playwright upgrade | **changes** | prior artifacts keep their own pinned value; a re-render is a successor (CF-8) |
| template CSS edit | **changes** | via `template_content_hash` |
| font set changes in the image | **changes** | via `renderer_build` — and this one matters, because fallback fonts change pagination `[OBSERVED]` |
| declaration table edited (e.g. `parallel-state` becomes served) | **changes** | feasibility answers differ, so the context differs |

*Alternative considered:* store `renderer_build` explicitly beside the version. Rejected — two
fields that must agree is exactly the duplicated-fact defect that has produced four of the last
fourteen findings.
```

All four are pinned in the `Commitment`. **The content hash, not the name**, with V1's own reason:
*"A CSS edit repaginates; Rev. 4 §4 requires that to be visible in the render environment."*
Without it, a CSS edit silently changes what the pinned declaration describes.

`template` is **not** user-selectable — `askable=False` by locked policy: *"Presentation-Boundary
rule 1 — internal. Users never select one"* `[OBSERVED]`.

## 12.2 The Capability Declaration, two tables

```
① NEED COVERAGE      ProseFailure → {served, weight, licenses, note}
                     the seven of Architecture §13 · read by FEASIBILITY and EXTENT
② HONEST REALIZATION relation → permitted (geometry, reading convention)
                     Representation-Boundary §2 · read by the MERGE-TIME CHECK
bridge               `licenses` names ①'s realization family; ② constrains it
```

`agent/treatment.py`'s docstring draws the line `[OBSERVED]`: *"This module only says that prose
will fail, and in which of the seven ways … Selecting a realization is decision 11, at the demo
gate, over Representation-Boundary Rev. 3's honesty table."*

**Table ② is the honesty table, verbatim** `[LOCKED Representation-Boundary §2]`:

| Relation | Honest | Dishonest, and why |
|---|---|---|
| `is-subset-of` | Euler/Venn nesting, indented layers | **arrows** — *"asserts process where there is none"* |
| `is-part-of` | tree, bracket, exploded view, treemap nesting | **Euler nesting** — *"asserts is-a: a wheel is not a car"* |
| `precedes` | arrows, numbered steps | nesting; **evenly-spaced timeline** |
| `causes` | labelled arrows | **arrows shared with `precedes`** — *"collapses order into causation"* |
| `associates-with` | undirected graph, adjacency matrix | any arrow; any ordering |

**Uniqueness is not the rule.** Rows 1 and 2 share *nesting* legitimately, distinguished by
**reading convention** — which is why the declaration keys on the **triple**: *"honesty is a
property of the (relation, geometry, reading convention) triple, not of the geometry alone"*
`[LOCKED]`.

`UNKNOWN`/`CHOICE` — `treatment.py` warns about itself: *"Every value is a guess and none has been
measured — but a wrong multiplier is a wrong number, while assuming 1.0 everywhere is a wrong
model."* So ①'s `served` column is factual and its `weight` column is not, and `Extent` inherits
that (OQ-2, U15).

### 12.2a `Extent` reads the declaration too, and Rev. 5's signature omitted it

Table ① is read by **both** `Feasibility` (the `served` column) and `Extent` (the `weight` column) —
V1's `derive_extent` multiplies a concept's page cost by `weight(anticipates)` `[OBSERVED]` — but
§2's `dom` list gave `extent(scope, partition, density_constants)`, with no declaration parameter.
A pure function cannot read a table it was not handed, so the stated contract was unimplementable.

Corrected signature: `extent(scope, partition, density_constants, capability_declaration)`.

**Two consequences worth being explicit about**, because they change what invalidates what:

- `Extent` now depends on the declaration, so a **renderer or template change alters the promised
  page count** — not just the feasibility disclosure. That is correct: if a build stops serving
  `parallel-state`, those concepts' page weight changes with it.
- It does **not** make `Extent` a `DecisionVersion` or put the declaration in any envelope. `Extent`
  stays a computed fact (C1), recomputed on read, exactly like `Feasibility` (§5.5, E4). The
  declaration remains pinned for reproducibility and tracked as no decision's dependency.

`density_constants` stays a separate parameter rather than being folded into the declaration: the
constants are a **calibration** of real output (OQ-2, measured at ~2.8 pages/concept against the
table's 1.0), while the declaration describes **what the renderer can draw.** Different authorities,
different change cadence, and §5.5 depends on the constants being outside the envelope so a
recalibration does not invalidate `scope`.

## 12.3 Merge-time checks — no browser

```
merge(document_mapping, template_source) → Html + MergeReport
MergeReport:
  unrendered_kinds     from .unrendered markers THE TEMPLATE EMITTED
  realizations         from data-realization attributes THE TEMPLATE WROTE,
                       paired IN SOURCE ORDER                      ◄── fixes the bug
  honesty_violations   each (relation, geometry, convention) ∉ table ②
```

**Source-order pairing fixes a real misattribution.** `_representation_report` does
`drawn.pop(0)` against a list that omits unrendered blocks, so with three relation blocks where
the second is unrendered, **block 2 is reported with block 3's geometry** `[OBSERVED]` — and the
triggering condition is normal in three of four templates.

**The honesty check catches a measured defect.** Three of four templates render both
`is-subset-of` and `precedes` as `layered-flow` `[OBSERVED]` — a flow geometry for containment is
table ②'s row-1 dishonesty, *"asserts process where there is none."*

`CHOICE` — the markers are parsed from the merged HTML rather than returned as structured data
alongside it. *Alternative:* templates emit a JSON sidecar; rejected because the marker convention
already exists and works, and a sidecar is a second thing to keep in step. **The consequence: the
marker convention becomes a contract**, tested in §15.

## 12.4 Browser-required checks

Only two of four probes need live layout `[OBSERVED]`:

```
overflow  getBoundingClientRect() vs the 794 px A4 limit     ── needs layout
scale     what Chromium shrank the document to               ── needs layout, and is
                                                                Chromium-SPECIFIC behaviour
```

Print sequence preserved verbatim from V1, including two hard-won constraints `[OBSERVED]`:
**no `margin` argument** (*"CSS owns the page geometry … passing margins here would silently
override them"*, including `@page :first` for a full-bleed cover), and **viewport set to A4 CSS
pixels** (*"Playwright's viewport is 1280 px, so a `width: 100%` element … appears to overrun A4
by 486 px while printing perfectly"*).

`UNKNOWN` — **U5: is overflow detection worth a browser?** Architecture §6 calls this *"the honest
form of the Chromium question"*, and it is a product decision about whether uninspectable
pagination is acceptable. Not settled here.

## 12.5 Slots, fonts, failure

```
render_slots ≈ min( (memory_budget − 65 MB) / 240 MB , vCPU )     initial sizing model
```

Measured on **16 logical cores**: 254 · 244 · 233 · 237 MB per concurrent render at concurrency
1 · 3 · 6 · 8; latency 3.43 → 5.55 s (+62%); throughput 4.54 → 0.70 s/render `[MEASURED]`. App
baseline **65.4 MB peak** with the real backend imported `[MEASURED]`. **`UNKNOWN` — U3:** real
cloud footprint, per-request overhead under load, and a small-vCPU instance's behaviour. *A
one-process import measurement is a floor, not a deployment number.*

**No pooling.** Launch is 1.39 s — ~41–55% of a render but ~0.05% of a project — and a pooled
browser holds ~240 MB permanently rather than transiently `[MEASURED]`. Build-Spec §8 specifies
pooling and the code does the opposite `[OBSERVED]`; the measurement says the code is right for
this workload. **Exception:** pool *within a batch* re-render, never per server (T2).

**Fonts.** Pin a font set in the image; **drop `networkidle`**. Three of four templates fetch
`fonts.googleapis.com`; without egress `networkidle` waits out the timeout and prints with
fallbacks, **which changes pagination** — and pagination is artifact-owned truth `[OBSERVED]`. This
also makes the boundary test's network-purity claim true instead of false.

**Render failure** is transient: the Document is already committed, so a re-render is a short Task.
This is F4's write ordering paying off.

---

# 13. Security and isolation

## 13.1 Project isolation

`DECIDED` — every read path takes `(user_id, project_id)` and filters on both. No path serves an
artifact by filesystem name. V1's flat `/artifacts/{name}` endpoint guards traversal correctly
(*resolve-then-verify-ancestry* `[OBSERVED]`) but has **no authorization check at all** — correct
for one local user and *"the first thing that breaks with a second one."* It does not survive.

## 13.2 Source privacy, and a disclosure to name

Privacy follows from identity rather than from a policy layer: the `structure` envelope includes
**source content hashes**, so a project with private sources has a key no other project can match.
That answers System-Design §12's *"a shared composition asset built from private sources is a real
disclosure risk"* `[OBSERVED]`.

**Isolation survives sharing, because sharing is one-directional.** A `SharedDerivation` is
unowned and is only ever read *through* a project's own pointer version (§4.2a), so there is no
cross-project read path and no way to enumerate what another project derived. Deleting a project
removes its pointers and leaves the shared row, which holds no project reference.

**One residual, stated rather than hidden.** Two projects uploading the **same bytes** share the
derived asset. Content is identical so no content leaks — but a party who *already has* a document
could detect that someone else derived against it, from a latency/cost side channel. `CHOICE` —
accepted for now; the mitigation if it matters is to include the owning tenant in the envelope for
sources marked private, which trades the sharing away. Recorded as an open decision (§17).

## 13.3 Artifact authorization and signed URLs

```
authorize (Decision Store)  →  ≤ threshold: stream inline, content-disposition set
                            →  above:       short-TTL signed URL
```

V1's inline-vs-attachment reasoning survives: *"`filename=` alone sets `content-disposition:
attachment`, which makes the browser save the file instead of showing it"* `[OBSERVED]`; a signed
URL must set the same header.

`CHOICE` — TTL 5 minutes, single artifact, no listing permission, not renewable without
re-authorizing. **The trade the redirect introduces: the URL is a bearer token for private content
once issued**, which is why the TTL is short.

## 13.4 Task ownership, quotas, secrets

| | Rule |
|---|---|
| Task ownership | a Task is readable and cancellable only by its project's owner (§8.7 defines cancellation); the `owner` column is a **worker** id, never a user |
| Tenant quota | per-user in-flight Tasks, backlog share, and provider calls per window — enforced at **admission** (§8.2) |
| Provider credentials | environment or secret manager; **never in any store**, never in a `DecisionVersion` env (which records the *model id*, not the key) |
| Access gate at T1 | **a shared code is not auth and must not be described as auth** (Architecture H) |
| PII | `Utterance` text is user content and authoritative. The application receives, stores and serves it back to its owner, as it must. **It is not transmitted to any external service other than the selected model provider**, and that provider is named in the `Commitment`'s pinned environment, so *"where did my words go"* is answerable per artifact. *(Rev. 1's wording — "never sent anywhere but the provider" — was too absolute and read as a claim about storage.)* |

---

# 14. Concurrency model

Six independent resources. Independent because they are exhausted by different things.

| Limit | Bounds | Exhausted by | `CHOICE` at T1 |
|---|---|---|---|
| **in-flight Task cap** | leased Tasks | worker coroutines, DB connections | 20 |
| **backlog bound** | queued Tasks | Task Store growth; **shed above it** | 200 |
| **per-user quota** | one tenant's share of both, **plus provider calls per admission bucket** | a single project | 5 in-flight, 40 backlog, **200 calls per fixed UTC hour** `CHOICE` — see the note below |
| **model-call cap, per provider** | concurrent provider calls | provider RPM/TPM | 8 — **enforced by `ACQUIRE_PROVIDER_SLOT` in `MODEL_CALL` step ③** (§8.6b), FIFO, both origins. Rev. 10 declared it here and nothing acquired it |
| **render slots** | concurrent Chromium | **memory and CPU** | `min((mem−65)/240, vCPU)` |
| **DB pool** | connections | handlers + workers + coordinator | 20 `UNKNOWN` |

**The tenant quota is "200 per fixed UTC hour", not "200 per rolling hour", and the difference is
real.** Rev. 10's table said *"200 calls/hour"* while §8.6a's admission primitive is a **fixed hourly
bucket** that can admit up to **2×** the cap across a boundary (199 at 10:59, 200 at 11:00). The precise
contract:

```
ENFORCED   ≤ 200 admissions per fixed UTC hour bucket   (§8.6a's conditional upsert)
IMPLIED    ≤ 400 across an adversarially-chosen rolling 60 minutes
REPORTED   the exact rolling-window figure, from CallLedger (§8.8a)
```

`CHOICE` — accept the 2× boundary for admission. A rolling window cannot be conditionally incremented
in one atomic statement, which is the property that makes admission correct under concurrency (§8.6a);
and this is a **coarse spend guard**, not a billing meter. The ledger still answers the exact question
for display and audit. *Alternative:* a sliding-window reservation table; rejected as real machinery for
a bound that does not need to be tight. **If a true rolling 200/hour is ever a requirement, this is the
decision to revisit** — not the wording.

**Why not one counter.** A model call is ~65 s, network-bound, provider-limited, ~0 local RAM. A
render is ~3.4 s, CPU- and memory-bound, provider-irrelevant `[MEASURED]`. A shared counter would
let eight in-flight generations starve a render, or a render batch starve generation.

**Why the backlog bound is separate from the in-flight cap.** Capping in-flight at 20 permits
10,000 waiting; the queue is unbounded and the Task Store grows without limit. Only the backlog
bound produces honest overload behaviour — refusing with a reason rather than accepting into a
queue that will not drain.

**Capacity, as a formula with the measured project as one instance:**

```
calls(project)      = planning_calls + Σ sections(project) + retries
projects/min        = provider_rpm ÷ calls(project)
renders/min needed  = projects/min × modules(project)
```

| shape | calls | 20 rpm | 1,000 rpm | renders/min @1,000 |
|---|---|---|---|---|
| **measured: 8 modules / 40 sections** `[MEASURED]` | 46 | 0.43 | 21.7 | 174 |
| 2 modules / 6 sections | 12 | 1.7 | 83 | 166 |
| 20 modules / 150 sections | 156 | 0.13 | 6.4 | 128 |

Render demand is roughly **flat** (128–174/min) while project throughput varies **13×**. Sections
dominate the call budget; modules dominate the render budget.

---

# 15. Testing strategy

## 15.1 Domain invariants — `dom`, no I/O

Pure-function tests over constructed decision sets. One test per runtime invariant
(Architecture E5): S1, S2, S2b, S3, S4, S5, S12. The seven construction-enforced invariants (S6,
S7, S8, S9, S10, S11, S13, S14) get **type/constraint tests instead** — asserting the violation is
*inexpressible*, not that a checker catches it.

```
test_S1_phantom_detected          module claims a concept scope lacks → violation naming
                                  BOTH scope and partition (never one)
test_S7_inexpressible             constructing a Cut without a consequence RAISES
test_S14_identity_not_positional  re-partition 5→3; assert prior module ids are ABSENT,
                                  not re-pointed                            ◄── CF-6
```

## 15.2 Envelope correctness — **this is what makes U1 safe**

Table-driven, per kind, both directions:

```
for kind in ALL_KINDS:
  for field in INCLUDED[kind]:  mutate → assert envelope CHANGES
  for field in EXCLUDED[kind]:  mutate → assert envelope UNCHANGED
```

The exclusion half catches the real bugs. Named cases:

```
structure:  mutate entry_point   → UNCHANGED     ── granularity is projected [LOCKED §8]
            mutate project_id    → UNCHANGED     ── sharing must survive
            add a source         → CHANGES
frame:      mutate sources        → CHANGES      ── §6.3's bug: subject alone is NOT the key
            mutate purpose        → CHANGES      ── it can name a jurisdiction
            mutate entry_point    → UNCHANGED    ── a learner property cannot make a
                                                    relation true or false
memo:       mutate commitment_id  → UNCHANGED    ── T6, the 40-section saving
            mutate a sibling section → UNCHANGED ── independence
            mutate capacity / depth_register → UNCHANGED  ── not rendered by the brief §5.7a
            mutate disclosed shortfalls → CHANGES
sections:   re-partition leaving THIS module's covers intact → UNCHANGED
document:   bump builder_version  → CHANGES
            mutate commitment_id  → UNCHANGED    ── §0.3, superseded(d) stays meaningful
```

Plus two structural tests:

```
test_canonical_json_stable        same logical input in different key orders, whitespace and
                                  Unicode normalisations → one envelope
test_brief_hash_matches_renderer  the fields BriefInputs carries are EXACTLY the fields the
                                  brief renders — one struct, two consumers (§5.7a).
                                  Without this the envelope silently lies when the prompt
                                  gains or loses a line.
```

## 15.3 `stale` vs `reusable`

```
test_job_correction_stales_downstream_not_structure
    bump job → projection..ordering stale; structure NOT stale; structure envelope still hits
test_prompt_bump_is_not_stale
    bump prompt_version → nothing stale; nothing reusable      ── E4's whole point
test_stale_blocks_approval_when_integrity_is_clean
    a stale set that passes integrity must still refuse        ── two preconditions
test_ordering_is_sequence_not_wallclock                       ── §10.2a
    two versions of one slot with an IDENTICAL created_at → ordering is still total and
    correct, because version_number decides it
test_superseded_uses_sequence
    two Documents for one module with identical timestamps → superseded(d) is unambiguous
```

## 15.4 Concurrent reservation and fencing — the critical suite

```
test_two_workers_one_envelope
    N=16 threads, one key → assert exactly ONE committed row and exactly ONE derive call
test_fencing_rejects_slow_worker                              ── R2
    A reserves; force lease expiry; B takes over and commits; A commits
    → assert A rejected, B's payload is the referenced one, A's is an orphan
test_takeover_race                                            ── R5
    two takeovers from the same observed epoch → exactly one wins
test_committed_is_write_once                                  ── R6
    commit against a COMMITTED key → rejected
test_heartbeat_detects_fencing
    fence A mid-derive → A's heartbeat returns false → A aborts before spending the commit
test_content_addressed_payload_prevents_overwrite             ── §7.4
    A and B write payloads; assert DIFFERENT paths and that B's bytes are intact

── publication atomicity, §7.3a ──────────────────────────────────────────────
test_publish_is_atomic
    inject a failure at step ② → assert the claim is STILL 'RESERVED' and NO version row
    exists.  The Rev. 1 hole was exactly this: claim COMMITTED, version absent.
test_fenced_publish_writes_nothing
    fence A, then PUBLISH → assert zero inserts attempted (CAS is statement ①)
test_version_row_never_without_edges
    inject a failure between the version insert and the edge inserts → assert neither lands,
    because an edgeless version would silently un-stale every dependent
test_unique_envelope_survives_claim_loss
    delete the claim row, then two concurrent publishes → one succeeds, one violates
    UNIQUE (project_id, kind, member, envelope) and rolls back               ── §11's guard

── cross-project sharing, §4.2a ──────────────────────────────────────────────
test_second_project_reuses_shared_derivation
    two projects, identical structure envelope → ONE model call, ONE SharedDerivation,
    TWO pointer DecisionVersions
test_shared_derivation_does_not_leak_staleness                ◄── the Rev. 2 bug
    project A re-derives structure under a new derive prompt (new envelope, A's slot
    version 2) → assert project B's plan is NOT stale
test_shared_derivation_survives_project_deletion
    delete A → assert B's pointer still resolves and the payload is intact
test_shared_claim_is_single_flight_across_projects
    16 threads across 4 projects, one envelope → exactly one derive call
```

`CHOICE` — lease expiry is injected via a clock port, not by sleeping. Sleeping makes these tests
slow and flaky, and they are the tests that must never be skipped.

## 15.5 Crash, retry, resume

```
test_crash_between_payload_and_commit     orphan object; next run succeeds; GC reclaims
test_at_least_once_is_bounded             crash after model success → exactly one extra call
test_generation_resume_costs_the_remainder
    kill after 3 of 5 sections → resume issues exactly 2 calls          ◄── D14's whole point
test_incomplete_writes_no_document        1 of 5 fails → NO Document; per-section reasons present
test_duplicate_document_construction      two builders, same key → ONE Document
test_429_is_retried / test_400_is_terminal                            ◄── §8.5
test_task_budget_exhaustion_is_distinguishable
    assert the failure class is task_budget_exhausted, NOT a provider class
test_regenerate_under_new_commitment_is_a_NEW_task                    ◄── §8.1, the Rev. 1 bug
    C1 → generate module-3 → succeeds; correct → C2 → generate module-3
    assert a SECOND Task exists, and that it HITs every memo whose brief did not change
test_regenerate_under_same_commitment_is_idempotent
    same request twice under C1 → one Task
test_cancel_keeps_committed_memos                                     ◄── §8.7
    cancel after 3 of 5 → state 'cancelled', no Document, 3 memos committed;
    a later run costs 2 calls
test_resume_incomplete_task                                           ◄── §8.8, Rev. 6
    1 of 5 sections fails → state 'incomplete' → RESUME → assert it is admitted
    (Rev. 5's predicate excluded 'incomplete', the one state D14 exists for)
    and that it issues exactly 1 call
test_resume_after_budget_exhaustion_admits_again                       ◄── §8.8, §8.6a
    exhaust the budget → RESUME → assert calls_admitted == 0, budget restored,
    progress intact, and that the next admission SUCCEEDS
    ── Rev. 7 asserted `spent == 0` against a column it had just deleted
test_resume_refused_for_provider_refused
    content-policy failure → RESUME matches 0 rows; the class is returned
test_double_resume_is_a_noop
    RESUME twice → one epoch bump, one 'accepted' state
test_lifetime_spend_is_derivable_without_a_resume                     ◄── §8.8a
    run a Task to completion with NO resume
    → assert Σ(ledger, task_id) == Σ(ledger, task_id, current epoch), both non-zero
    (these are DERIVED sums now; Rev. 7 left this test asserting on deleted columns)
test_lifetime_spend_accumulates_across_resumes
    two attempts → Σ(task_id) == a1 + a2;  Σ(task_id, current epoch) == a2
test_failed_call_is_in_the_ledger
    a timed-out call → a row exists with outcome='attempt_deadline' and non-zero wall_ms
test_budget_is_enforced_under_concurrency                             ◄── §8.6a, Rev. 8
    budget.max_calls = 2, launch 8 concurrent sections
    → assert EXACTLY 2 admissions succeed and 6 are refused; the ledger holds ≤ 2 rows
    ── the TOCTOU the ledger alone could not prevent
test_tenant_quota_is_enforced_at_admission
    cap = N, launch 4N concurrent calls across 2 projects of one user
    → assert ≤ 2N admitted (one fixed-window boundary's worth), never unbounded
test_admitted_but_crashed_call_fails_safe
    admit, then kill before the ledger insert
    → assert calls_admitted > ledger count, and that the NEXT admission is refused sooner,
      never later
test_completion_wins_tie_with_cancel                                  ◄── §8.8's race rule
    cancel arrives after COMPLETE won → assert the terminal state stands, NOT 'cancelled',
    and no Document is rolled back
test_document_provenance_attaches_on_hit                              ◄── §9.6a, Rev. 6
    two Commitments yielding one construction_key → ONE Document, TWO provenance rows
    (the second arrives via ATTACH_PROVENANCE, since PUBLISH is never reached on a HIT)
test_request_id_mismatch_returns_409                                  ◄── §18.3
    same request_id, different text → 409 request_id_reused; the first turn is unchanged
test_request_id_match_returns_the_same_turn
    same request_id, same text → 200, one Utterance, one ord
test_memo_gc_cannot_produce_a_false_hit                               ◄── §10.6a, Rev. 7
    collect a memo unit → assert LOOKUP returns MISS (not HIT), and that a crash injected
    between the claim delete and the payload delete leaves an ORPHAN, never a dangling HIT
test_fenced_worker_call_is_still_accounted                            ◄── §8.8a, Rev. 7
    run R2's timeline: A pays on epoch 1, B takes over and commits on epoch 2
    → assert spent_lifetime counts BOTH calls, and spent(current epoch) counts only B's
test_windowed_quota_is_computable
    calls spread across time → assert the rolling-window sum matches the ledger rows
test_wall_budget_counts_reservation_waiting                           ◄── §8.8a, Rev. 7
    force a BUSY wait → assert the wall budget advances with elapsed time, no counter needed
test_cancel_on_terminal_task_is_rejected                              ◄── §8.7, Rev. 7
    cancel a succeeded Task → 0 rows, cancel_requested unchanged, terminal state returned
test_render_claim_prevents_duplicate_artifacts                        ◄── §9.8, Rev. 7
    two concurrent renders of one (document, render_env_hash) → ONE Artifact, one seq bump
test_source_extraction_is_shared                                      ◄── §9.8a
    two projects upload identical bytes → ONE extraction; both compute 'extracted' (§9.8b)
test_late_old_extractor_cannot_regress_the_source                     ◄── §9.8b, Rev. 9
    v2 publishes, then v1 publishes afterwards
    → assert the computed extraction is still v2's, and that a late v1 'infeasible' does
      NOT make the source unusable (Rev. 8 had an unfenced shared cell both could write)
test_infeasible_extraction_is_a_recorded_row
    a non-transient extraction failure → a SourceExtraction row with outcome='infeasible'
    and a reason; never an absence                                    ◄── P8
test_claim_loss_costs_at_most_one_call                                ◄── §7.3c, Rev. 9
    delete a committed Claim whose DecisionVersion remains → next step RECONCILEs and
    issues ZERO calls; and with the pre-derive check disabled, exactly ONE call, never a
    loop (Rev. 8 rolled back on the UNIQUE conflict and retried forever)
test_publish_adopts_an_existing_result
    force a UNIQUE conflict at PUBLISH step ② → assert the claim COMMITS pointing at the
    existing row, rather than rolling back
test_step_checks_for_an_existing_result_before_reserving              ◄── §7.3, Rev. 10
    instrument FIND_RESULT; delete a claim; run step()
    → assert FIND_RESULT was CALLED and zero derivations occurred
    (Rev. 9 defined §7.3c and left step() going MISS → RESERVE_NEW, so the test and the
     orchestration contract disagreed)
test_routing_gc_retires_its_claim                                     ◄── §10.6a, Rev. 10
    age a RoutingResult past retention → assert the Claim is gone too, and LOOKUP MISSes
    → the same false-HIT assertion as the memo case, over the new domain
test_sync_intake_call_is_admitted_and_ledgered                        ◄── §8.6b, Rev. 10
    drive an intake turn → assert each model call appears in CallLedger with origin='sync',
    task_id IS NULL, and that it decremented the tenant bucket
test_sync_calls_count_toward_tenant_quota
    exhaust the hourly cap with sync intake calls alone → the next turn is refused with
    rate_limited at admission, not a provider 429
test_turn_call_cap_bounds_one_turn
    force repeated intake derivations in one request → assert the in-process cap stops it
test_extractor_upgrade_invalidates_structure                          ◄── §5.3b, Rev. 10
    a project WITH a source: bump extractor_version → assert the structure envelope CHANGES
test_extractor_upgrade_does_not_touch_sourceless_projects
    a project with no sources → assert the structure envelope is UNCHANGED
test_render_claim_loss_does_not_re_render                             ◄── §7.3, Rev. 11
    delete a committed render claim whose ArtifactIndex row remains
    → assert FIND_RESULT found it, RECONCILE rebuilt the claim, and ZERO browser slots
      were acquired (Rev. 10's concrete flow would have re-rendered and discarded)
test_extraction_claim_loss_does_not_re_extract                        ◄── §7.3, Rev. 11
    same shape over source_extract
test_document_claim_loss_rebuilds_provenance                          ◄── §9.6a, Rev. 11
    Document D exists, DocumentProvenance(D, C2) absent, claim lost
    → RECONCILE path must still produce DocumentProvenance(D, C2), because on_result runs
      on the RECONCILE arrival path and not only on HIT
test_provider_cap_holds_across_both_origins                           ◄── §8.6b, Rev. 11
    launch N task-origin calls and M sync-origin intake calls together
    → assert concurrent provider calls NEVER exceed the cap, and that a slot timeout is
      classified `rate_limited` (transient), not terminal
test_provider_slot_is_released_on_failure
    a call that raises → assert the slot is released (the `finally`), so one failure cannot
    permanently shrink the pool
test_one_artifact_per_document_environment                             ◄── §4.2, Rev. 10
    force two renders producing DIFFERENT bytes for one (document, render_env_hash)
    → assert the DB refuses the second and §7.3c adopts the first
test_cold_quota_bucket_admits                                         ◄── §8.6a, Rev. 9
    first call of a new hour → ADMITTED (Rev. 8's bare UPDATE matched 0 rows, which is
    indistinguishable from over-cap, so every tenant was refused once an hour)
test_approved_extent_survives_recalibration                           ◄── §9.4a, Rev. 7
    approve, then change density_constants → assert every memo envelope is UNCHANGED and
    extent() as a view DOES change
test_frame_reads_situation_readings                                   ◄── §9.1, Rev. 7
    a purpose naming a jurisdiction selects the frame — only reachable if situation
    precedes frame
test_task_key_is_separate_from_envelope                               ◄── §5.12, Rev. 6
    construct a task_key and an envelope over identical inputs → assert they DIFFER
    (the "domain" discriminator), and that no envelope kind is ever "task"
test_derive_prompt_bump_yields_a_new_plan_task                        ◄── §8.1, Rev. 3
    bump the derive prompt version only → assert a SECOND plan Task, because the
    structure envelope moved and nothing else did
test_source_change_yields_a_new_plan_task
    add a source → tier_v and frame_v both move → new Task (this path already worked)
test_intake_retry_does_not_double_append                              ◄── §4.2, Rev. 3
    same request_id twice → one Utterance, one ord, and the derivation HITs
test_concurrent_appends_get_distinct_ord
    N concurrent appends → ords are 1..N with no gap and no duplicate
test_identical_content_is_one_document                                ◄── §5.8, Rev. 3
    two builder_versions producing identical bytes → ONE Document, TWO
    DocumentConstruction rows, seq bumped ONCE
test_reapproval_after_template_edit_is_a_new_commitment               ◄── §9.4, Rev. 3
    edit a template's CSS, re-approve the same decision set → a SECOND Commitment whose
    pinned template_content_hash and `disclosed` are current
test_double_click_approve_is_one_commitment
    same set, same environment, twice → one Commitment
```

The last one is §4's measured lesson as a test: a swallowed cause produced a report that read as
model omission when the real cause was a spent rate limit — *"same symptom, opposite fix."*

## 15.6 Renderer

```
test_honesty_table_enforced        a template mapping is-subset-of to a flow geometry → violation
test_realization_paired_in_source_order
    three relation blocks, middle unrendered → assert NO misattribution      ◄── the pop(0) bug
test_unrendered_kind_reported      a block kind with no branch is reported, never dropped
test_no_margin_argument            golden HTML/PDF: @page geometry survives
test_viewport_is_a4                a width:100% element does not report false overflow
test_no_network_at_render          assert zero outbound requests during a render  ── makes the
                                   boundary test's purity claim TRUE
```

`CHOICE` — golden-file PDF comparison on page count, `scale`, and text extraction, **not** pixel
diffs. Pixel diffs across Chromium builds are noise, and the render environment is pinned anyway.

## 15.7 End-to-end

```
test_intake_to_artifact            one module, stubbed gateway, real stores → artifact exists,
                                   provenance chain walks back to the Utterance
test_correction_reuses_structure   assert the structure call count is 0 on the re-plan
test_approval_refuses_then_repairs targeted re-derivation of the named decision → approvable
```

`CHOICE` — the gateway is stubbed with **recorded** responses from `V2/runs/`, so the suite needs
no provider and no quota. This is what makes the invariant tests runnable in CI, and it is the
direct answer to CC6 (*free-tier reliability contaminates every measurement*).

## 15.8 Single-source specification — a grep-level test

Promised in Rev. 5's change log and not written. **Four of the last fourteen findings were one fact
stated in two places with one copy updated**, so this is the regression suite for the document
itself, run in CI against `Technical-Design.md`:

```
test_no_duplicated_identity_formulas
    the document contains NO occurrence of these outside §5.11 / §5.12 / §5.11a:
      "idempotent on target"                   stale since Rev. 3
      "(project, kind, target)"                stale since Rev. 3
      "version_set_hash)" without environment  stale since Rev. 3
      "member: null" / "member = (" / "member *: text | null"   stale since Rev. 4
        ── narrowed to `member`: `result_ref` and `owner` are legitimately nullable,
           so the bare pattern `: text | null` would false-positive on them
      'envelope("task"'                        stale since Rev. 5
      "created_at)" used as an ORDERING        stale since Rev. 3
      "'decision' | 'memo' | 'document'"       stale since Rev. 5
      "latest Document"                        stale since Rev. 6
      "{ commitment_id }" as an export key     stale since Rev. 6

test_derived_identities_are_tabled
    every UNIQUE constraint in §4.2 whose columns include a HASH or a DERIVED key
    (envelope · *_hash · construction_key · idempotency_key · version_number · seq · ord)
    appears as a row in §5.11's I-table.
    ── Rev. 6 asserted "every UNIQUE / PK", which is FALSE as specified: Project.id,
       Source.id, the Decision PK, DependencyEdge's PK, CommitmentMember's PK and Task.id
       are surrogate or natural composite keys, deliberately absent from the I-table. The
       table exists for identities that are COMPUTED and can therefore drift; a surrogate
       uuid cannot drift. The test would have failed literally, or forced "identity" to
       mean whatever made it pass.

test_every_claim_domain_is_handled
    for each ClaimDomain, §7.3a's PUBLISH names a branch, and is_shared() classifies the
    decision domains

test_every_claiming_workflow_is_representable                          ◄── Rev. 8, the INVERSE
    for EVERY workflow in §9 that reserves or commits a Claim, assert all four:
        its result type ∈ ClaimDomain
        its key construction is defined in §5.12a
        its PUBLISH branch exists in §7.3a
        its result/index row exists in §4.2
    ── Rev. 7's forward-only version passed while `render`, `source_extract` and `routing`
       sat entirely outside the claim schema. A test over an enum's existing members can
       never find a workflow the enum forgot; only the inverse direction can.

test_every_defined_operation_is_reachable                              ◄── Rev. 10
    for every operation in §7.3's table (PUBLISH, ATTACH, ATTACH_PROVENANCE, RECONCILE)
    and §8.6a/§8.6b's admission gates, assert at least one canonical flow in §7.3 or §9
    invokes it BY NAME.
    ── this is what would have caught RECONCILE being defined and never called. The
       identity and enum-coverage guards cannot: they check that things are NAMED
       consistently, not that a defined operation is REACHABLE.

test_every_execution_context_passes_the_gate                           ◄── Rev. 10
    for every place §9's flows make a model call — Task steps AND synchronous intake —
    assert it routes through §8.6b's MODEL_CALL. No call site reaches a provider directly.
    ── what would have caught sync intake bypassing admission and the ledger entirely.

test_no_workflow_restates_the_claim_branches                           ◄── Rev. 11
    no §9 flow may contain its own LOOKUP / RESERVE / HIT / MISS / EXPIRED branches —
    every claiming workflow calls step() (§7.3) and supplies derive_fn + on_result.
    ── `test_every_defined_operation_is_reachable` proves FIND_RESULT is called SOMEWHERE.
       It cannot prove every MISS branch uses it, because the duplicate branches ARE the
       defect. **Reachability is weaker than mandatory use**, and this is the assertion
       that encodes the difference.

test_provider_boundary_is_mechanically_exclusive                        ◄── Rev. 11
    an IMPORT-level boundary test, not a document grep: only the Model Gateway module may
    import the provider SDK or open an HTTP client to a provider host. Intake, Planner,
    Generator, Document Builder and the Renderer are all forbidden.
    ── V1 already proves this pattern works: `tests/test_boundaries.py` forbids `engine/`
       from importing `agent/`, `httpx`, `requests` and `socket` via a FORBIDDEN table
       [OBSERVED]. A spec-level assertion is a convention; an import test is a wall.
    ── caveat V1's own experience teaches: that test passed while the BROWSER it drives
       fetched webfonts (§12.5), so an import boundary bounds what the Python imports,
       never what a subprocess does. Scoped accordingly.

test_three_key_constructions_are_disjoint                              ◄── §5.12a
    envelope(), task_key() and claim_key() over identical inputs → three different keys
    (each carries a "kind"/"domain" discriminator)

test_dom_signatures_match_section_2
    the signature list in §2 and each §5/§9/§12 restatement agree parameter-for-parameter
    ── this is what would have caught extent()'s missing capability_declaration (§12.2a)
```

`CHOICE` — a literal grep over the document rather than a prose review checklist. The failures these
catch are all *"the second copy was not updated"*, which review reliably misses and grep reliably
does not. **It is a cheap test for an expensive, repeated failure.**

## 15.9 Export

```
test_export_task_key_changes_with_artifact_set                        ◄── §9.9 ③
    same Commitment, re-render one module (new Artifact, higher seq)
    → assert a DIFFERENT export_hash and therefore a NEW Task, not the old succeeded one
test_export_uses_commitment_documents                                 ◄── §9.9 ①
    commit C1, generate; correct → C2, generate (new content)
    export C1 → assert EVERY artifact is C1's, and none is C2-only content
test_export_refuses_when_a_module_is_unrendered
    a committed module with a Document and no matching Artifact → 409 export_incomplete
test_export_refuses_unsatisfiable_pin
    delete/alter the pinned template → refuse, naming it; never substitute
test_export_reports_newer_plan_without_refusing                       ◄── §9.9 row 5
    C2 exists with newer content → export C1 succeeds AND reports the note
test_export_zip_is_byte_deterministic                                 ◄── §9.9a
    build the same export twice, in different processes, hours apart
    → assert byte-identical archives (this is what makes the content path safe)
test_export_has_no_claim_row
    assert export writes no Claim — the exception is deliberate (§9.9)
```

---

# 16. Deployment mapping

| Component | T0 laptop | T1 one small host | T2 split render |
|---|---|---|---|
| API + Intake | in-process | same process, async | same |
| Work Coordinator | in-process | same process | same |
| Planner / Generator | in-process | same process | same |
| `dom` functions | library | library | library |
| Renderer | in-process, slots = 1 | in-process, **slots = 1 at 512 MB** | **own unit**, slots = min(mem,vCPU) |
| Decision Store + claims + indexes | `FileStore` → **Postgres** | Postgres | Postgres |
| Payload stores | local `out/` | **object storage** (see below) | object storage |
| Model Gateway | in-process | same | same |
| Frontend | `npm run dev` | Vercel, `NEXT_PUBLIC_API` | same |

**T1 preconditions, all specified in V1 and none built** `[OBSERVED]`: a Playwright base image
with pinned fonts (`Runtime-Dependencies.md` §5 specifies it *including the version-matching rule
and the `PLAYWRIGHT_BROWSERS_PATH` trap*); env-driven CORS; an access gate; durable stores.

**Payloads: object storage, or a persistent volume with two consequences stated.** Rev. 1 wrote
*"object storage or a volume"* as if they were interchangeable, and they are not:

| | object storage | persistent volume |
|---|---|---|
| durability | the provider's | the volume's — **an ephemeral disk does not qualify**; free instances restart on idle `[INFERENCE]` |
| signed-URL delivery (§13.3) | available | **not available** — delivery is always streamed inline through the API |
| T1→T2 split | payloads already shared | the volume must be shared or the renderer co-located |

`CHOICE` — object storage at T1. A persistent volume is acceptable **only** if it is genuinely
persistent, and choosing it means giving up signed URLs and accepting that the API proxies every
PDF byte. Stating the trade rather than leaving the reader to discover it.

**512 MB is a candidate, not a validated size.** 65 MB app + 240 MB render = 305 MB for one; two
would need ~545 MB. `UNKNOWN` — **U3 requires one real deployment benchmark** before committing.

**T1→T2 condition:** `render slots needed > min((mem − 65 MB)/240 MB, vCPU)`, or bulk re-render
becomes a real operation.

**The frontend boundary needs no work** and is the one deployment decision V1 already got right:
`lib/api.ts` uses `NEXT_PUBLIC_API`, so the browser calls the backend directly and **no serverless
timeout enters the path** `[OBSERVED]`.

---

# 17. Observability

Every row exists because a specific V1 diagnosis was hard or impossible.

| Recorded | On | Answers | V1 pain |
|---|---|---|---|
| `result_domain`, `result_identity`, `reused: bool`, `reconciled: bool` | every step | *"why did this project cost 46 calls?"* — and `reconciled` makes claim loss visible rather than inferred from cost | `inputs_hash` written, never read |
| `claim_epoch`, `fenced: bool`, `waited_ms` | every step | *"did we pay twice?"* — the **only** way a fencing rejection is visible | — |
| `attempt`, `provider`, `model`, `failure_class`, `retry_after`, `wall_ms`, `tokens` | every model call | *"was that the model or the quota?"* | *"same symptom, opposite fix"* |
| state transitions with timestamps, `spent` vs `budget` | every Task | *"where did 11,537 s go?"* | 3.2 h across 4 calls, invisible |
| `stale_set` size, `violations`, `decisions_implicated` | approval | *"why can I not approve?"* | approval could not refuse at all |
| `construction_key`, `builder_version` | Document | *"why two documents?"* | — |
| `render_env_hash`, `template_content_hash`, `scale`, `overflows`, `unrendered`, `honesty_violations`, `slot_wait_ms` | Artifact | *"why did pagination change?"* | env captured in the engine already `[OBSERVED]` |
| per-member `decision_count` | Commitment | — | **`decision_count` was exactly 7 in every record**, for plans of 1–9 modules `[MEASURED]` |
| `orphan_payloads`, `gc_reclaimed` | GC sweep | is the at-least-once window costing anything? | — |

`CHOICE` — structured events into one table plus stdout JSON, not a metrics system, at T1. One
derived counter is worth naming: **reuse rate per kind**, because it is the only way to tell
whether §5's envelope design actually pays, and whether `subject_key`'s conservative
normalisation (§5.3.1) under-shares in practice.

---

# 18. API contracts

Contracts and dependencies, not URLs or framework detail. Every row names what it **must not**
depend on, because that is where the failure-domain guarantees of §11 are actually enforced.

## 18.1 The surface

| Operation | Sync? | Model calls | Reads | Writes | Must NOT touch |
|---|---|---|---|---|---|
| create project | yes | 0 | — | `Project` | gateway, tasks |
| **append utterance** | yes | 0 | — | `Utterance` | gateway |
| **intake turn** | yes, 30 s SLA | 1–4 (2 cached) | decisions, claims | `situation`, `job` versions | task store |
| read plan | yes | **0** | decisions, commitments, claims | — | **gateway, task store** |
| start planning | yes → task ref | 0 | — | `Task` | gateway |
| **correct** | yes → task ref | 0 | — | `Utterance`, `Task` | gateway |
| **approve** | yes | **0** | decisions, edges, capability decl | `Commitment`, members | **gateway, task store** |
| start/resume generation | yes → task ref | 0 | renderer availability | `Task` | gateway |
| task status | yes | 0 | `Task`, `CallLedger` | — | **gateway, decision store** |
| **cancel a task** | yes | 0 | `Task` | `cancel_requested` | gateway, decision store |
| **resume a task** | yes | 0 | `Task` | `Task` state + epoch | gateway |
| **artifact** | yes | 0 | artifact index (authorize), payload | — | **gateway, task store** |
| export | yes → bytes or task ref | 0 | artifacts, commitment `Ordering` | — | gateway |

**`read plan` and `artifact` take 0 model calls and no Task dependency** — that is the property
that makes a provider outage survivable, and it is a contract, not an implementation detail.

## 18.2 The four response shapes that carry design decisions

**Intake turn** — readings travel *with their confidence*, closing §1's finding that V1 hands
planning *"a bare string"* while the strength lives in a separate record:

```
{ state: 'asking' | 'ready',
  readings: [ { axis, value, strength, materiality, evidence[], asked: bool } ],
  scope_tier: 'documented'|'consensus'|'asserted'|'unknown',      ── P8, never absent
  frame: {axis, value} | 'not_applicable' | 'unresolved',         ── §6
  questions: [ { axis, options[], default_label } ] }
```

**Read plan** — carries the disclosures the gate is answerable for:

```
{ modules: [...], ordering: [...], extent: {...},
  shortfalls:    [ { failure, concepts[], licenses, permanent: bool } ],   ── H2, §9.7
  violations:    [ { invariant, decisions_implicated[] } ],                ── never one decision
  stale:         [ { kind, member } ],                                     ── E4, separate from above
  approvable:    bool }
```

`violations` and `stale` are **separate fields** because they are separate preconditions: a stale
set can be perfectly internally consistent (§9.4).

**Approve** — refuses with a reason, never silently:

```
200 → { commitment_id, disclosed: [...] }
409 → { reason: 'stale' | 'integrity',
        stale: [...], violations: [ { invariant, decisions_implicated[] } ],
        repair_targets: [ { kind, member } ] }          ── offered, never chosen
```

**Task status** — the failure class is part of the contract, because §4's measured lesson is that
*"same symptom, opposite fix"*:

```
{ state, resumes, cancel_requested,
  spent:          {calls, wall_ms, tokens_in, tokens_out},   this attempt   ── from CallLedger
  spent_lifetime: {calls, wall_ms, tokens_in, tokens_out},   all attempts   ── §8.8a
  budget: {max_calls, max_wall_ms}, wall_elapsed_ms,
  progress: [ { member, state, reason? } ],                    ── per-section, for resume
  resumable: bool,                                            ── §8.8's predicate, precomputed
  failure: { class, message, per_member_reasons } | null }
```

**Cancel and resume are explicit operations**, not implied by re-POSTing:

```
cancel  → 200 {state: 'cancelling'}        or 409 {state: <terminal>} if already terminal
resume  → 200 {state: 'accepted', epoch}   or 409 {state, failure: {class}} if not resumable
```

`CHOICE` — `resumable` is returned on status so a client can render the button correctly rather than
POSTing to discover the answer. It is `state ∈ {cancelled, incomplete, failed_transient}` or
`failed_terminal` with a class other than `provider_refused` (§8.8).

`class` is one of the ten in §8.5. A client must be able to distinguish
`task_budget_exhausted` from `provider_unavailable` without reading prose.

## 18.3 Idempotency and concurrency at the boundary

| Caller behaviour | Contract |
|---|---|
| double-click Generate | one Task — `UNIQUE (project, kind, idempotency_key)` (§8.1) |
| retry an intake turn after a timeout | the `Utterance` is not re-appended — I13 (§5.11); the derivation reuses its envelope |
| reuse a `request_id` with a **different payload** | **409, explicitly** — see below |
| re-approve an identical set, environment unchanged | the same `Commitment` — I11 (§5.11) |
| re-approve an identical set **after a template or engine change** | a **new** `Commitment`, because the pinned environment and the disclosures differ (§9.4) |
| re-request generation on a resumable Task | the **same** Task, resumed (§8.8) — memos already committed are reused |
| re-request generation on a `provider_refused` Task | refused, with the failure class — retrying cannot change the answer |
| poll task status | free; no store write, no lock |
| request an artifact above the size threshold | 302 to a short-TTL signed URL (§13.3) |
| request export of a large curriculum | 202 + task ref rather than a long-held request |

`CHOICE` — clients supply a request id on utterance append so a network retry is not a second
turn. *Alternative:* dedupe on `(project, text, window)`; rejected because a user may legitimately
repeat themselves.

**A reused `request_id` must carry the same payload.** Rev. 3 said the handler *"reads the existing
row and proceeds"*, which left `request_id = X, text = "teach transformers"` followed by
`request_id = X, text = "teach databases"` undefined — silently returning the first turn's result
for the second request. So:

```
request_fingerprint = sha256(canonical_json({role, text}))   stored on Utterance

INSERT conflicts on (project_id, request_id):
   stored fingerprint == request's  →  200, return the existing turn   (a genuine retry)
   stored fingerprint != request's  →  409 request_id_reused           (a client bug)
```

`DECIDED` — refuse rather than accept-and-append. A mismatched reuse is a client defect, and the
failure mode of guessing is the worst available: the user's second message is silently discarded
and they are shown an answer to their first.

## 18.4 What the API deliberately does not expose

`DECIDED`, each for a stated reason:

| Not exposed | Why |
|---|---|
| `template` selection | `askable=False` by locked policy — *"users never select one"* `[OBSERVED]` |
| envelopes, claim epochs, `DecisionVersion` ids | infrastructure identity; surfacing them invites clients to depend on reuse behaviour |
| a "regenerate this section" call | the unit the user owns is the **module**; a section is an internal decomposition (Q8 is a planning fix, not a user-facing one) |
| direct `Document` access | a Document is renderer-independent and not a deliverable; the deliverable is an `Artifact` |
| artifact paths | content-addressed and authorization-checked — never a filesystem name (§13.1) |

---

# 19. Open implementation decisions

| | Decision | Status | Blocks |
|---|---|---|---|
| **U1** | ~~envelope granularity~~ | **CLOSED — §5**, with the golden tests of §15.2 as the guard | — |
| **U2** | ~~what identifies a `frame`~~ | **CLOSED — §6**, from LOCKED text | — |
| **U3** | real cloud footprint, per-request overhead, small-vCPU render capacity | `UNKNOWN` | committing to 512 MB; T1→T2 |
| **U4** | concurrent generation: quality and throttling | `UNKNOWN` | the `~4–5×` fan-out claim, still `[INFERENCE]` |
| **U5** | is overflow detection worth a browser | `UNKNOWN` | whether Chromium is permanent |
| **U6** | portfolio link or product | `UNKNOWN` | auth depth, retention, quota values |
| **U7** | cost per project on a paid provider | `UNKNOWN` | whether the measurement programme can run |
| **U8** | retention: artifacts, memos, Task rows | `UNKNOWN` | GC policy (§10.6) |
| **U9** | DB pool size and write throughput | `UNKNOWN` | §14's last row |
| **U10** | how a source's `kind` is established — declared, inferred, or asked | `UNKNOWN` | the `Authority` lookup's input |
| **U14** | response for a *third* unserved prose failure | `UNKNOWN` | §9.7's two rules cover today's two |
| **U15** | `treatment.py`'s `weight` column — every value an unmeasured guess, by its own admission | `UNKNOWN` | `Extent`; overlaps OQ-2 |
| **N1** | **does a situation-free derive truncate more often?** | `UNKNOWN` — **new, from §0.1** | the `frontier` limit's value |
| **N2** | **private-source side channel** (§13.2) | `CHOICE` accepted; revisit if multi-tenant | envelope shape for private sources |
| **N3** | `subject_key` normalisation strength (§5.3.1) | `CHOICE` conservative | reuse rate; measurable from §17 |

**Also not settled, and deliberately:** the density constants (OQ-2), whether `Table` is a
`Presentation` or a `StructuralClaim` (OR-2/U13), section exclusivity (OR-1 — architecture consumes
totality only), and every experiment in Architecture J3 (HY-1, HY-2, HY-4, OQ-1).

---

# 20. Traceability matrix

`Architecture decision → Technical Design → implementation consequence`

| Arch | Technical Design | Consequence |
|---|---|---|
| **D1** two sync surfaces | §3.2 per-path budgets; no tx across a model call | handlers need a deadline parameter; intake failures are retriable |
| **D2** durable Tasks | §4.2 `Task`; §8 | a Task table with a unique idempotency key; no in-process dict |
| **D3** envelope identity | **§5 in full**; `UNIQUE (project_id, kind, member, envelope)` and `UNIQUE (kind, envelope)` on `SharedDerivation` | one `envelope()` function, one spec table, the §15.2 suite |
| **D4** Integrity separate, deterministic | §2 `dom` list; §9.4 step 2 | `integrity()` takes no port; returns `decisions_implicated` as a set |
| **D5** Feasibility reads a declaration | §12.2 two tables; declaration **not** in any envelope | `feasibility()` is pure; the declaration version is pinned in the Commitment |
| **D6** section fan-out | §9.5; model-call cap in §14 | orders are independent; the per-section check is *assigned concepts taught here* |
| **D7** Chromium bounded, unpooled | §12.5 slot formula | a fixed-size thread pool; a fresh browser per render |
| **D8** merge-time probes, table-driven honesty | §12.3 | `merge` returns a `MergeReport`; the marker convention is a tested contract |
| **D9** content-addressed artifacts | §5.9; §4.2 `ArtifactIndex` | no title-derived paths anywhere; `superseded(a)` is an index query |
| **D10** persistence split | §10.1; §4.2/§4.3 | Postgres for rows incl. the memo index; object storage for payloads |
| **D11** structure identity | §5.3; §0.1 situation-free derive | the derive call signature **changes** from V1's `derive(situation)` |
| **D12** attempt deadline + Task budget | §8.5, §8.6 | the Gateway takes a deadline; the orchestrator owns the budget; 429 split out |
| **D13** conditional capability recorded | **§4.2 `SourceExtraction.outcome`** (not a `Source` column — §9.8b); §9.1 step 2 for the tier | `Infeasible` is an immutable row with a reason; `NotApplicable` for *"this project needs no source"* lives on the tier, where it belongs |
| **D14** Content Memo | §4.2 `MemoIndex` + §4.3 payloads; **§5.7 T6** | resume costs the remainder; a correction elsewhere costs nothing |
| **D15** template pinned before Feasibility | §12.1; `template_policy` in §2's `dom` list | four values pinned in the Commitment, incl. the **content hash** |
| **D16** independent caps | §14's six rows | six separate semaphores/limits, not one |
| **D17** claim + fencing | **§7 in full**; **§7.3a publication transaction**; §15.4 | one `Claim` table; five one-statement operations; **one publication transaction per result type, gated by the CAS**; content-addressed payloads |
| **D2** durable Tasks (revisited) | **§8.1 per-kind idempotency keys**; §8.7 cancellation | the key is the *production event*, not the target: a new `Commitment` yields a new Task, which then HITs unchanged memos |
| **E4** `stale` vs `reusable` (revisited) | **§10.2a monotonic sequences** | `version_number` per decision slot; `seq` per (module, document) and per (document, template); **no relation reads `created_at`** |
| **D11** structure sharing (revisited) | **§4.2a `SharedDerivation` + project-local pointer** | sharing saves the call and the payload, never the slot — so staleness cannot leak between projects |
| **S9 / domain content identity** | **§4.2, §5.8 `Document` UNIQUE on content hash**; `DocumentConstruction` many-to-one | a builder refactor yields a new construction key and the *same* Document |
| **invariant 8** environment pinning | **§4.2, §9.4 `environment_hash` in Commitment identity**; **§12.1 `capability_decl_version` = hash(renderer_build ‖ template ‖ declaration)** | a template edit makes a genuinely new approval context; pinning one field pins the renderer build too, so the fact lives in one place |
| **D17** HIT paths (revisited) | **§7.3b `ATTACH`** (shared) · **§9.6a `ATTACH_PROVENANCE`** (document) | rule: *if a result is reachable from more than one context, a claim HIT must still attach the calling context* |
| **D2** Task identity (revisited) | **§5.12 `task_key()`** — a separate construction with a `"domain"` discriminator | a Task is process state, not a reusable derived result; the two key spaces are provably disjoint |
| **D2** resume + accounting | **§8.8 `RESUME`** admits `incomplete`/`failed_transient`; **§8.8a** advances both counters per call | `incomplete` is the state D14 exists for; the per-user quota reads a counter that is always current |
| **D5** capability reads | **§12.2a `extent(…, capability_declaration)`** | `Extent` and `Feasibility` both read table ①; a pure function must be handed what it reads |
| **export** | **§9.9** resolved from the Commitment, keyed by `export_hash`; **§9.9a** canonical zip | an export of C contains what C approved; determinism is what makes the content path safe |
| **single-source discipline** | **§5.11 identities · §5.11a member · §5.12 task keys · §5.2a `is_shared`**; **§15.8 grep test** | duplicated specification facts caused 4 of 14 recent findings; CI now fails on a stale second copy |
| **D12** budgets and quota | **§4.2 `CallLedger` · §8.8a** — counters removed, everything derived | one append-only table answers attempt budget, lifetime spend and the rolling window; a fenced worker's paid call is still counted |
| **F4** write ordering | **§10.6a deletion order** — the mirror rule | writes create the referent first; deletions remove the reference first. Every crash window leaves garbage, never a dangling promise |
| **D7/D9** renderer identity | **§12.1 nested hashes · §4.2 `ArtifactIndex.capability_decl_version`** | `renderer_build ⊂ render_env_hash ⊂ capability_decl_version`, so pinning one pins the chain and export's lookup is a direct index read |
| **D17** render + extraction | **§9.8 render claim · §9.8a shared extraction** | render is claimed because its output is *not* canonicalised; extraction is content-addressed and global, and attaches on HIT |
| **C1/§5.5** extent | **§9.4a `Commitment.approved_extent`** | recalibration improves future plans and invalidates no committed content; *promised vs produced* becomes measurable for A4 |
| **U1** closure | **§5.1a `decode_params` + the auditable/reproducible limit · §5.9a five kinds specified** | every model-backed envelope names its sampling config; invariant 8's *"pins the whole environment"* is read as auditability, not reproducibility |
| **D17** claim coverage | **§5.12a `claim_key()` · `ClaimDomain` broader than `DecisionKind` · `SourceExtraction` + `RoutingResult`** | three canonical constructions with disjoint domains; every claiming workflow has a key, a branch and a result row |
| **D12** budget enforcement | **§8.6a admission ≠ accounting** — `Task.calls_admitted` + `UserQuotaBucket` conditional increments | overspend is *prevented*, not merely *reported*; the ledger keeps reporting |
| **D2** retention | **§4.2 `CallLedger` carries values, not FKs** | an append-only record whose referents are collectable stores values — otherwise its retention contradicts theirs |
| **single-source discipline** (revisited) | **§15.8's inverse assertion** — workflows → claim domains; **§5.11 I17–I20** | a forward-only check over an enum passed while three workflows sat outside it; the identity table now carries every derived identity |
| **C4** computed, not stored (revisited) | **§9.8b extraction state is computed** | removing the mutable cell removes the race; a version-fenced update would only have made it safe |
| **D17** claim loss | **§7.3c `RECONCILE` + adopt-on-conflict** | a lost claim costs ≤ 1 model call instead of looping forever; `Claim` becomes a cache of a derivable fact |
| **D12** admission (revisited) | **§4.2 `UserQuotaBucket` + §8.6a atomic upsert**; **§8.6b one gate for every origin** | the admission subsystem is transcribable; the first call of each hour is admitted; and synchronous intake calls are admitted, capped and ledgered like any other |
| **D17** reachability | **§7.3's operation table + `FIND_RESULT` in `step()`** | a defined operation that no canonical flow calls is dead code; §15.8 now asserts reachability, not just naming |
| **D11** structure identity (revisited) | **§5.3b `extractor_version` in `source_set`** | structure consumes the extracted skeleton, so an extractor upgrade invalidates structures derived from sources — and leaves sourceless projects untouched |
| **S9** artifact identity (revisited) | **§4.2 `UNIQUE (document_id, render_env_hash)`** | one artifact per document × environment is enforced by the database, not only by the claim protocol |
| **D17** mandatory use | **§7.3 `step(domain, identity, derive_fn, on_result)`** is the only place claim branches exist; §9's flows supply two functions | duplicate branches deleted rather than synchronised; `on_result` runs on HIT, RECONCILE **and** PUBLISH, so no attach can be forgotten per-branch |
| **D16** provider cap | **§8.6b step ③ `ACQUIRE_PROVIDER_SLOT`**, FIFO, release in `finally` | the cap §14 declares is now acquired on every path, both origins; this is also the mechanism behind D6's fan-out bound |
| **D12** quota precision | **§14 enforced / implied / reported** stated separately | *"200 per fixed UTC hour"*, with the 2× boundary named and the rolling figure reported from the ledger |
| **B** `dom`/`orch` boundary | **§15.8 import-level provider boundary test** | only the Gateway may import a provider SDK — V1's `test_boundaries.py` precedent, with its own known limit (a subprocess's network is out of scope) |
| **D18** two-table declaration | §12.2 | `feasibility` reads ①; `merge` reads ② |
| **P2** only Integrity refuses a *plan* | §9.4 vs §9.5 step 0 | renderer availability and budget are *execution* preconditions, coded elsewhere |
| **P5** scoped to three jobs | §10.2 two queries | `stale` is a graph walk; `reusable` is a point lookup |
| **B** `dom` returns, `orch` persists | §2's `dom` list; §10.2 | no `dom` function takes a port parameter — enforced by a boundary test |

---

# 21. What would make this design wrong

Falsifiable, in the same spirit as Architecture J4.

- A `dom` function is handed a port and by month two the Document Builder writes rows.
  **§2's list was documentation, not a boundary test.**
- Reuse rate for `structure` is ~0 in production. **§5.3.1's conservative normalisation
  under-shares so badly that D11's sharing is theoretical** — visible immediately from §17's
  reuse-rate counter, which is why it is recorded.
- A situation-free derive truncates on most subjects. **§0.1's cost was real and the `frontier`
  limit is not a sufficient answer** (N1).
- Fencing rejections are frequent in the logs. **Leases are too short, or heartbeats are being
  starved by the event loop** — and §17 records `fenced` precisely so this is visible rather than
  inferred from cost.
- Orphan payload volume grows without bound. **GC's "no index row and older than 2×lease" rule
  misses a class**, or the at-least-once window is wider than one call.
- A correction re-spends all 40 sections. **T6 was implemented commitment-keyed**, which is the
  single most expensive mistake available in this document.
- A claim says `COMMITTED` and no version row exists, so `stale` walks missing edges and reports a
  drifted plan as current. **§7.3a's publication transaction was split back into two writes** — the
  Rev. 1 hole, and the class that reports success while being wrong.
- Re-generating a module after a correction returns *"already done"*. **§8.1's per-kind keys were
  collapsed back into one generic `{target}` formula.**
- Two versions of one decision share a timestamp and `stale` becomes non-deterministic.
  **§10.2a's sequences were dropped as ceremony**, which is how wall-clock ordering gets back in.
- Content is reused when the brief changed. **`brief_inputs_hash` drifted from what the prompt
  renders**, because the one-struct-two-consumers rule was never tested (§15.2).
- Cancelling a generation makes the next attempt cost full price. **§8.7 was implemented as a
  rollback instead of a stop.**
- One project's prompt bump marks another project's approved plan stale. **§4.2a's pointer layer
  was collapsed and `DecisionVersion` was made globally shared** — the tempting simplification, and
  the one that leaks staleness across tenants.
- A source is added and the plan is never re-derived. **§8.1's plan key lost the structure
  envelope**, so the derivation environment stopped being represented.
- `superseded(d)` reports a new document version the reader cannot tell apart from the old one.
  **§5.8's content-hash uniqueness was dropped and construction keys became Document identity.**
- A user approves, someone edits a template, the artifact renders differently, and the commitment
  still claims the old disclosure. **§9.4's `environment_hash` was left out of Commitment
  identity.**
- An intake retry appends a second `Utterance` and the turn is interpreted twice, because
  **`request_id` and its fingerprint exist in the API contract and not in the table.** *(Both are in
  the schema as of Rev. 5/6; this is the regression to watch for, not a current state — Rev. 6's
  phrasing of this bullet read as a live defect.)*
- A memo `LOOKUP` returns `HIT` and resolves to a deleted object. **GC removed the payload before the
  claim** — a false HIT, which is worse than a cold cache and which nothing detects (§10.6a).
- `spent_lifetime` under-reports because a fenced worker's paid call was rejected from accounting.
  **The `CallLedger` insert was given an `epoch` predicate** — fencing a monotonic fact (§8.8a).
- A cancel appears to succeed on a finished Task. **`CANCEL` lost its state predicate** (§8.7).
- Two Artifacts exist for one `(Document, environment)` and `superseded(a)` reports a duplicate as a
  successor. **The render claim was dropped on the grounds that rendering makes no model call** —
  true, and not the reason the claim exists (§9.8).
- A calibration run invalidates every generated section. **`approved_extent` was read from
  `extent()` instead of the Commitment** (§9.4a).
- An export resolves no artifact because the Commitment pins a `capability_decl_version` and the
  artifact index only records `render_env_hash`. **The second column was treated as redundant**
  (§4.2, §12.1).
- `frame` is derived from a situation that does not exist yet. **§9.1's step order was restored to
  "classify first, then interpret"** (§9.1).
- A Task spends 9 calls against a budget of 2. **Admission was derived from the ledger** instead of
  being a conditional increment — accounting mistaken for enforcement (§8.6a).
- An extractor upgrade silently extracts nothing. **`extractor_version` was dropped from the
  `source_extract` Task key**, so the claim and the Task disagreed about what is new (§8.1).
- A workflow acquires a claim with no key construction, no PUBLISH branch and no result row, and
  §15.8 stays green. **The inverse assertion was never added** — a check over an enum's members
  cannot find what the enum forgot (§15.8).
- Deleting a 31-day-old Task fails, or succeeds and takes the audit trail with it. **`CallLedger`
  was given a foreign key to something with a shorter retention than itself** (§4.2).
- A test asserts on a column the data model no longer has, and passes because nobody ran it.
  **§15.5 was not rewritten when the counters were removed** — Rev. 7's state.
- A deploy rolls out a better extractor and sources silently revert to the old one. **§9.8b's computed
  relation was re-implemented as a pointer column** because a pointer is easier to read.
- One lost claim row costs a model call every sixty seconds, indefinitely. **§7.3c's adopt-on-conflict
  was replaced by "fail loudly on a UNIQUE violation"** — which sounds like rigour and is a spend loop.
- Every tenant is rate-limited once an hour. **§8.6a's upsert was simplified back to an `UPDATE`**,
  making a cold bucket indistinguishable from an exhausted one.
- §5.11 is correct and §4.2 is correct and they disagree. **A new identity was added in its own
  section and not carried to the table** — which has now happened twice (I17–I20).
- An operation is specified, tested, cited in the change log, and called by nothing.
  **§7.3's canonical flow was not updated when §7.3c was added** — Rev. 9's state, and the reason
  §15.8 now asserts *reachability* and not only naming.
- A user drains the provider quota through a path that no budget mechanism watches, because that path
  has no Task. **A mechanism was specified for one execution context and the other was left outside
  it** (§8.6b).
- A retention policy is written for a new table and its claim is not retired with it.
  **The GC unit rule was stated per table instead of per claim domain** (§10.6a) — which has also now
  happened twice.
- An extractor improvement is derived, stored, and then ignored by every plan.
  **`extractor_version` was left out of `source_set`** on the assumption that extraction changes are
  representation-preserving — a claim about every future extractor, which nothing supports (§5.3b).
- A workflow is written by copying `step()`'s branches into §9 "for readability", and six months later
  one copy is missing `FIND_RESULT`. **The rule is that no workflow restates the branches** (§7.3), and
  `test_no_workflow_restates_the_claim_branches` is what enforces it — reachability tests cannot.
- Provider concurrency exceeds its cap because a new call site reaches the SDK directly.
  **The boundary was a spec assertion rather than an import test**, so the convention held only as long
  as everyone remembered it (§15.8).
- A slot leaks on an exception and the provider pool silently shrinks to zero.
  **`RELEASE_PROVIDER_SLOT` was not in a `finally`** (§8.6b).
- An audit question has a missing answer after a recovery, because an attach lived on one arrival path.
  **`on_result` was re-implemented as a `HIT`-branch call** (§7.3, §9.6a).
- A user cannot resume the one case resuming exists for. **§8.8's predicate was written from the
  prose about cancellation and never checked against the resumable-states table** — Rev. 5's state.
- The per-user quota reads zero for almost every Task. **`spent_lifetime` was advanced only on
  `RESUME`**, so the counter that guards spending counted nothing (§8.8a).
- A zip download differs between two requests for the same export. **§9.9a's canonical settings were
  treated as polish**, so two workers wrote different bytes to one content path — §7.4's hazard,
  reintroduced through the back door.
- An export of an approved plan contains content the user never approved. **§9.9 ① resolved by
  *latest* rather than from the Commitment.**
- *"Which plan produced this document?"* has a missing answer. **§9.6a was skipped because the
  document claim already said `COMMITTED`** — the same hole as the shared-derivation HIT, one object
  along.
- A promised page count is wrong after a renderer change and nobody can see why. **`extent()` was
  left without the capability declaration**, so the weights it multiplies by came from nowhere
  traceable (§12.2a).
- A fact is corrected in two places out of three, and the third is the one an implementer reads.
  **§15.8's grep test was not wired into CI** — and this is the failure mode with the best track
  record in this document's own history.
