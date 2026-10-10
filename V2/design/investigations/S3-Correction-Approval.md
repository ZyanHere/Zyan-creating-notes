# §3 — Correction and Approval

A deep read of one section. **No design, no domain model, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**A correction to `V1-Measured-Issues.md` up front.** A2 states: *"The parked patch
does not fix this. `v1-orphan-approval-gate.patch` gates on orphans … This is the
mirror defect, and the patch leaves it untouched."*

**That is wrong.** The patch handles **both**. Its own docstring:

> *"`phantoms` is the same fault mirrored: a module names a concept that `scope` does
> not carry, so `plan_for` drops it while the module still lists it to the reader as
> something it covers."*

The `Unassigned` dataclass it introduces carries `orphans` **and** `phantoms`, and
`unassigned()` computes both. A2's ledger entry needs amending.

---

## 1. What this section actually is

**Two responsibilities that V1 treats as one stage and that are not the same thing:**

- **Correction** — take a sentence of plain English, work out which decision it is
  about, and revise exactly that decision. Repeatable, any number of times.
- **Approval** — freeze a set of decisions as the thing the system is now answerable
  for.

**Starts** when a plan exists. **Correction ends** when the user stops correcting.
**Approval ends** the planning phase and begins §4.

**Why the gate exists at all** — it is the product's central promise: *the plan is a
gate, not a loading screen. What gets written is what you approved.*

---

## 2. What exists today

### Approval

`[OBSERVED]` `backend/planning.py:approve()` — 30 lines, and the whole of it:

```python
current   = store.current_decisions(project_id)
committed = [current[k] for k in PLAN_DECISIONS + UPSTREAM_DECISIONS if k in current]
ids       = [d.id for d in committed]
hash_     = commit_hash(ids)

existing  = store.commitment_by_hash(project_id, hash_)
if existing is not None: return existing          # idempotent

for decision in committed: decision.status = "committed"; store.put_decision(decision)
return store.add_commitment(Commitment(..., snapshot=..., decision_ids=ids,
                                       decision_environment={...}, approved_by=USER))
```

**There is no `if` in this function except the idempotency check, and no `raise` at
all.** `[OBSERVED]` Approval cannot refuse.

**What it commits** — 7 decision kinds: `PLAN_DECISIONS` (`interpret_situation`,
`scope`, `consequence`, `traversal`, `partition`) + `UPSTREAM_DECISIONS`
(`derive_structure`, `relevance`). `intake_strategy` is excluded deliberately —
*"it governs the conversation, not the artifact."*

The upstream two are included with a stated reason: *"the user approved a meaning that
depends on them, and if one drifts later the approval rested on a derivation they never
saw."*

**Idempotency is real and well-made** `[OBSERVED]` — keyed on `commit_hash(ids)`, so
re-approving an identical decision set returns the existing commitment rather than
creating a second one.

### Correction

`[OBSERVED]` `agent/plan.py:revise()` → `PROMPT_REVISE = "plan_revise_v2"`. The prompt
receives **all current decisions as JSON** plus the correction text. The model returns
a `Routing`:

```python
targets:       list[DecisionKind]   # what this correction actually changes
out_of_scope:  str | None           # set when it belongs to a later gate
reading:       str                  # what it was understood to mean
# plus a full replacement object for any of the 8 decisions, or null
```

`revised()` returns only the non-null ones. The docstring is precise about what
`targets` is: *"the router's judgment about **this** plan, not a lookup from phrases to
decisions."*

**Corrections write `status="candidate"`, `freshness="current"`** — so correcting after
approval creates new candidates beside the committed set, and re-approving mints a new
commitment under a new hash. `[OBSERVED]`

### What is observed per correction

`[OBSERVED]` The harness records `said`, `reading`, `claimed`, `actual`,
`unclaimed_drift`, `claimed_but_unchanged`, `out_of_scope`, `not_understood`, `landed`.
So V1 already distinguishes *what the router said it would change* from *what changed*.

### The 2×2 exists in the data model

`[OBSERVED]` `Decision.status: candidate | committed` and
`Decision.freshness: current | stale` — System Design Rev. 4's status×freshness
separation, faithfully implemented as two independent axes.

---

## 3. Problems

### Measured

**A1 — the gate gates nothing.** `[MEASURED]` `serves_everything: False` in 6 of 8
plans; 5 reached approval and all 5 were approved. And now confirmed at code level:
`approve()` has no refusal path.

**A2 — phantoms pass the gate.** `[MEASURED]` 40 module-claimed concepts against 36 in
scope. `approved: true`.

**B2 — `decision_count` is always exactly 7, and this is now explained rather than
flagged.** `[MEASURED + OBSERVED]` `PLAN_DECISIONS` (5) + `UPSTREAM_DECISIONS` (2) = 7.
It counts **decision kinds**, not modules or members. Architecture §5 says commitment
is *"per-member and ordered"* — V1's commitment is **per-plan and unordered**. Not a
bug in the code; a gap between the code and the locked architecture.

**Corrections work, and are the only self-repair path in the system.** `[MEASURED, n=2]`
`ml-weekend`: 5 modules → 3, cut 11 → 13. `generate-01`: phantoms 7 → 4.

**But the phantom repair was incidental.** `[MEASURED + INFERENCE]` The correction was
a content complaint — *"you've missed evaluation entirely"* — and its `reading` says it
wanted *"the three cut benchmarks (WebShop, ALFWorld, τ-bench) restored."* Restoring
them to `scope` reduced the scope/partition mismatch because `partition` already claimed
them. **Nothing noticed the repair, and nothing noticed the four that remained.**

**P4 — out-of-scope routing is correct.** `[MEASURED]` *"make it dark themed with orange
accents"* → `out_of_scope: "Theme and colour choices … are presentation decisions owned
by the demo/rendering stage, not the plan"`, `landed: false`, `claimed: []`,
`actual: []`.

### Observed

**A correction replaces whole decision objects with no cross-check.** `[OBSERVED]` The
router returns a complete new `Scope` or `Partition`. Nothing validates the new object
against the decisions that did **not** change. So a correction can create or repair a
relationship violation arbitrarily — which is exactly what both measured corrections
did, in opposite directions, unnoticed.

**The parked patch's docstring names the mechanism better than anything we had
written.** `[OBSERVED]` Worth quoting in full because it is the clearest statement of
CC2 in the repository:

> *"A correction adds a concept to `scope` without placing it in a module. The plan page
> shows it — `compose.ts` surfaces it under 'Also covered' — and the user approves it.
> `derive_extent` counts its pages into the size they agreed to. Then `modules()` reads
> `partition.modules` and nothing else, so the concept is in no module, no module is
> answerable for it, and `check_document` — which runs per module against that module's
> narrowed plan — never sees it to report it missing. **Every surface reports satisfied
> and the concept is simply not in the artifact.**"*

So **corrections are the mechanism that creates orphans**, and the plan page actively
displays the stranded concept as covered.

**Corrections can revise `interpret_situation`.** `[OBSERVED]` `Routing` carries a
`Situation` field. So the situation is revisable after intake "ends," through a
different prompt (`plan_revise_v2`) with different rules from `interpret_v1`. §1's
boundary question — *does intake end?* — is answered here: **no, it just changes
channel.**

**`freshness` is never set to `stale`.** `[OBSERVED]` One write, `freshness="current"`.
The invalidation axis is declared in the data model and never exercised. So *"invalidate
≠ regenerate"* — the locked distinction the architecture spent a full stress test on —
has no implementation.

**`decision_environment` is partial.** `[OBSERVED]` It records `prompt_versions` and
`models`. System-Design invariant 8 requires *"model, prompt version, **taxonomy
version**, asset version, **source versions**."* Two of five.

**Third instance of the same pattern.** `[OBSERVED]` `inputs_hash` written, never read.
`freshness` declared, never set. `feasibility` computed, never gated. Three mechanisms
built to specification and left unwired.

### Strong inference

- **A1 is a one-boolean change and the hardest question in the section is what happens
  next.** The information already exists, deterministically, before approval. What is
  missing is not a check — it is an answer to *"and then what?"* A plan that cannot be
  approved needs a route forward, and refusing is not one.
- **Correction is doing two jobs.** It revises the *situation* (an intake concern) and
  revises *decisions* (a planning concern), through one prompt with one routing model.
  The out-of-scope branch shows a third job — deferring to a later gate.
- **The gate's promise and the gate's implementation have diverged.** The product
  sentence is *"what gets written is what you approved."* What is enforced is *"a
  commitment names the decisions that existed when you clicked."*

### Unknown

- **Why did Lexo remove its approval gate?** `[UNKNOWN]` W7: `PlanApprovalTool` bound to
  no agent, capture functions never called, state fields vestigial, config flags
  retained, and **no post-mortem comment** in a codebase whose comments are otherwise an
  incident log. The removal is evidence about a *different object* — theirs gated task
  execution, ours gates deliverable scope — but the absence of a recorded reason is the
  most uncomfortable fact in this section.
- Does a user who cannot approve a plan correct it, or abandon the project? `[UNKNOWN]`
- Is per-member commitment (Architecture §5) actually needed before multi-module
  regeneration? `[UNKNOWN]`

---

## 4. The key architectural question

**What must be true for a plan to be approvable?**

V1's answer is *"a plan exists."* Every other answer requires deciding what approval
*means*, and there are three candidate readings, which the evidence does not separate:

| Reading | Approval asserts | Consequence |
|---|---|---|
| **Receipt** | "the user saw this" | V1's current behaviour; gating would be wrong |
| **Contract** | "the system is answerable for producing this" | feasibility and internal consistency become preconditions |
| **Commitment point** | "this version is now the historical reference" | versioning and supersession matter; refusal is irrelevant |

`[INFERENCE]` The product sentence — *what gets written is what you approved* — is the
**contract** reading. The implementation is the **receipt** reading. The data model
(`status × freshness`, `commit_hash`, `snapshot`) is built for the **commitment point**
reading.

Three readings, one function, and the divergence explains A1 more usefully than
"nobody added a check."

**And a second-order question the patch exposes:** if approval refuses a plan holding a
stranded concept, **who places it?** The patch is explicit that it must not:

> *"Reported, never repaired. Placing a stranded concept would be a partition decision,
> and this layer must not make one."*

So refusing implies routing back to §2 for a re-partition — which means the gate needs a
**repair path**, not just a predicate.

---

## 5. Where this section starts and ends

**Current** `[OBSERVED]`: correction and approval are both post-plan, pre-generation,
and correction may run any number of times, including after approval (new candidates
beside committed decisions).

**Boundaries worth questioning** `[INFERENCE]`:

- **Correction is not one stage.** Situation revision belongs with §1; decision revision
  belongs with §2; deferral (`out_of_scope`) belongs to whichever later gate owns it.
  V1 fuses all three because the *user-facing act* is one sentence — but the user-facing
  act and the architectural boundary need not coincide.
- **Approval may not be a stage at all.** It is a state transition on a decision set. It
  has no model call, runs in **0.04s** `[MEASURED]`, and produces no content.
- **Is there a second gate?** Architecture had a demo-page approval in the original
  flow. V1 has none — generation runs straight from the commitment.

---

## 6. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| Re-approve identical decisions | returns the existing commitment | correct, and well-made |
| Approve an infeasible plan | approved | **A1** |
| Approve a plan with phantoms | approved | **A2** |
| Approve a plan with orphans | approved | the patch's target; **0 observed** `[MEASURED]` |
| Correct after approval | new candidates beside committed; re-approval mints a new commitment | works; **no supersession recorded** |
| A decision drifts under a commitment | nothing happens — `freshness` never goes stale | the reconciliation path Architecture B1 defines is absent |
| Correction the router cannot place | `not_understood` recorded | observed `false` in every record `[MEASURED]` |
| Correction belonging to a later gate | `out_of_scope`, `landed: false` | **P4** — correct |
| Router claims a change that did not happen | `claimed_but_unchanged` recorded | empty in every record `[MEASURED]` |

Two rows are notable for being **never exercised**: `not_understood` and
`claimed_but_unchanged` were false/empty in all 11 records. Either the router is
reliable, or one correction per case is too few to find out. `[UNKNOWN]`

---

## 7. What makes this section valuable rather than a confirm button

`[OBSERVED]` Three things V1 already does that a confirm dialog does not:

1. **It routes rather than regenerates.** A correction targets named decisions and
   revises only those — so *"I don't need deployment"* does not re-derive the landscape.
2. **It records intent against effect.** `claimed` vs `actual` vs `unclaimed_drift` means
   a correction that silently changed something else is *visible in principle*.
3. **It refuses politely.** `out_of_scope` names which stage owns the request instead of
   absorbing it — and the reference is explicit that absorbing is worse: *"the user
   believes it was handled."*

**The gap:** all three produce records that nothing consumes. `unclaimed_drift` is
computed and no one is told. That is CC1 again, in the one stage whose whole job is to
be trustworthy.

---

## 8. Constraints and cross-section effects

**On §1** — corrections are a second situation-revision channel with different rules.
Any change to the situation's shape must be honoured by two prompts, not one.

**On §2** — approval can only gate on what planning computes. Feasibility and the
phantom arithmetic already exist. Conversely, a refusal needs somewhere to send the
plan back to, so §2 needs a re-partition entry point that is not a full re-plan.

**On §4** — the commitment snapshot is generation's brief. `curriculum.plan_for` narrows
it per module, which is where a phantom gets silently dropped and an orphan silently
disappears. **Every §3 weakness is a §4 input.**

**On §7** — commitments, decision status, and `decision_environment` all live here.
Invariant 8's missing three fields are a storage-shape question. And with no
supersession, the history of a corrected-then-re-approved plan is a list of commitments
with no stated relationship.

**On §8** — the cheapest stage in the product. 0.04s, no model call. Anything added here
is nearly free in latency terms.

---

## 9. Solution directions — compared, not chosen

**A. Make approval a predicate over what §2 already computes.** Refuse on
`serves_everything: False`, phantoms, orphans, unbacked capability clauses.
*Delivers:* A1, A2. *Cost:* near zero — the patch is already written and covers both
halves. *Blocked on:* the repair path (§4 below).

**B. Surface rather than refuse.** Show shortfalls and stranded concepts **in the plan
the user reads**, and let them approve with eyes open. *Delivers:* the honesty
obligation without a dead end. *Cost:* frontend plus a plan-view field. *Risk:* it is
the receipt reading, and *"what gets written is what you approved"* becomes *"what you
approved was known to be undeliverable."*

**C. Both — refuse on contradiction, surface on incapability.** Internal inconsistency
(phantoms, orphans, traversal mismatch) is an **error** the user cannot act on. A
representation shortfall is a **trade-off** they can. *Delivers:* A1 and A2 with a
coherent story about who decides what. *Cost:* small. *`[INFERENCE]` this is where the
evidence points, and I am naming it as a direction rather than a decision.*

**D. Split correction into its three jobs.** Situation revision → §1's mechanism;
decision revision → §2's; deferral → the owning gate. *Delivers:* one set of rules per
concern instead of two prompts that can disagree. *Cost:* moderate; it is a decomposition,
not a rewrite.

**E. Validate a revision against the decisions it did not touch.** After `revised()`,
re-check the five §2 relationships. *Delivers:* stops corrections creating orphans —
which the patch's docstring identifies as **the** orphan mechanism. *Cost:* small, and
it is the same check as A.

**F. Wire up `freshness` and supersession.** Mark dependents stale when a decision
changes; relate commitments. *Delivers:* Architecture §7's invalidation model.
*Cost:* the largest here. *Question:* is it needed before regeneration of an
already-generated module is a real user action?

**G. Make commitment per-member.** Architecture §5. *Delivers:* the gap B2 exposes.
*Needed when:* modules are approved or regenerated individually.

**H. Leave it.** *Argument for:* it is the cheapest stage, corrections demonstrably
work, and Lexo deleted theirs. *Argument against:* A1 is the highest-severity measured
defect in the system and its fix costs almost nothing.

**The shape:** A/C/E are cheap and address the two worst structural defects, and E is
the one that stops the defect **recurring**. D is a decomposition worth doing whenever
§1 and §2 are touched. F and G are real architecture that should wait for a user action
that needs them. B is a genuine product alternative, not a lesser version of A.

---

## What remains genuinely open

1. **Which of the three readings is approval?** Receipt, contract, or commitment point.
   Everything else in this section follows from that.
2. **What happens to a plan that cannot be approved?** A predicate without a repair path
   is a dead end.
3. **Why did Lexo remove theirs?** The only external evidence we have, and it is
   unexplained.
4. **Should correction stay one act?** One user sentence, three architectural concerns.
5. **Is the router reliable?** `not_understood` and `claimed_but_unchanged` are empty
   in all 11 records — reliability or insufficient sampling, unknown.
6. **When does invalidation become necessary?** `freshness` exists and is inert.
