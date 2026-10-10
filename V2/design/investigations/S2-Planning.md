# §2 — Planning

A deep read of one section. **No design, no domain model, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**Two corrections to earlier documents, both in V1's favour:**

- **Extent is not model-guessed.** `derive_extent` computes it deterministically from
  depth constants. A4 is a **miscalibrated constant**, not a judgment failure — the
  cheapest fix in the whole ledger, and I overstated it as needing "density feedback."
- **Feasibility is not a model opinion either.** `derive_feasibility` is code, and its
  docstring says so: *"the model says what the content needs, code says what we can
  serve."* Which makes A1 **worse** than stated: approval discards a *computed fact*.

And one reassignment: **Q1 (job) moved to §1**, where `job` is produced.

---

## 1. What planning actually is

**Responsibility.** Turn a situation into a curriculum a user can read, correct and
approve: what exists in this subject, what is in play, what is covered and how deeply,
what is cut and at what cost, how it divides into modules, and in what order.

**Starts** when the user reaches the planning step (`proceed()` — deliberately not
automatic, per §1's latency requirement). **Ends** at a plan object the gate can show.

**This is where the product's value lives.** `Product-Semantics.md` §1 assigns
coverage, depth allocation and structure to the **system**, not the user — that
assignment is the entire product thesis.

---

## 2. What exists today

### Eight decisions, two model calls, two deterministic derivations

`[OBSERVED]` Persisted decision kinds: `interpret_situation` (§1), `intake_strategy`
(§1), then **`derive_structure`, `relevance`, `scope`, `partition`, `traversal`,
`consequence`**.

They resolve in **two calls**:

```python
derive(situation)          -> Landscape{ derive_structure, relevance }
plan(situation, landscape) -> PlanBody{ traversal, consequence, scope, partition }
```

Plus two functions that are **not model calls at all**:
`derive_extent(scope, partition)` and `derive_feasibility(scope)`.

**The grouping is honest about itself** `[OBSERVED]` — `PlanBody`'s docstring:

> *"Split from the landscape for a runtime reason … **six decisions in one response
> truncated — the model emitted `derive_structure` and stopped.** Only scope+partition
> are architecturally joint (Architecture §4); the grouping around them is ours. Four
> separate records either way, which is what a correction targets."*

So **truncation has already forced one architectural split**, and A5 shows it is still
happening at `derive`. The same failure, twice, one of them already paid for.

`Landscape`'s rationale is different and stronger: *"relevance must judge every concept
the same pass derived."* That one is genuinely joint.

### The models

| Decision | Shape | Notable |
|---|---|---|
| `derive_structure` | `Structure{concepts[], …}`; `Concept` carries `family` | Landscape breadth lives here |
| `relevance` | `Relevance{judgements[]}` — *"Every derived concept judged"* | `unjudged` was **0 in every record** `[MEASURED]` |
| `scope` | `covered[]` of `Covered{concept, depth, why, anticipates}` + `cut[]` (**names only**) | `anticipates` is a `ProseFailure` from Architecture §13's seven |
| `consequence` | `exclusions[]` of `Exclusion{topic, consequence, when_to_learn}` | Semantics §12's three parts; has a dedup validator |
| `partition` | `modules[]` of `Module{title, covers, why_here, capability}` **+ legacy `units[]`** | *"Becomes its own PDF"*; `capability` is the module test |
| `traversal` | `sequence[]` of **module titles** + `why` | String-keyed |

### Extent, computed

`[OBSERVED]`
```python
_DEPTH_PAGES   = {"mention": 0.15, "explain": 0.5, "work through": 1.0}
_DEPTH_MINUTES = {"mention": 2,    "explain": 8,   "work through": 20}
pages = Σ  _DEPTH_PAGES[depth] × weight(anticipates)
```
With the Architecture §11 rule written into the comment: *"extent is derived per part
and summed. **Never capacity divided by the number of parts.**"*

### Feasibility, computed

`[OBSERVED]` `shortfalls(scope.covered)` — for each concept whose `anticipates` names a
prose failure this build cannot serve, a `Shortfall`. *"Returned so the plan can say so
before it is approved."*

### Validators — and this is the section's central fact

`[OBSERVED]` `agent/plan.py` contains **exactly three** validators:

1. `Situation.stated` — accept legacy bare strings
2. `Consequence.exclusions` — dedup by topic
3. `Partition._one_shape_or_the_other` — at least one module *or* unit

**None of them is a cross-decision check.** Five relationships between these decisions
are pure arithmetic, and **zero are enforced:**

| Relationship | Checked? | Defect when violated |
|---|---|---|
| `partition.covers ⊆ scope.covered` | **no** | **A2 phantoms** |
| `traversal.sequence` == `partition.modules` titles | **no** | ordering silently references a missing module |
| `scope.cut ⊆ consequence.exclusions` topics | **no** | a concept cut with no stated consequence — violates Semantics §12's *mark the gap* |
| `scope.covered ⊆ relevance.in_play` | **no** | covering something relevance excluded |
| `relevance` judged every `derive_structure` concept | **no** (holds in practice) | a concept neither in nor out |

---

## 3. Problems

### Measured

**A1 — approval passes an undeliverable plan.** `[MEASURED]` `serves_everything:
False` in **6 of 8 plans**; 5 of those reached approval and **all 5 were approved**.
`perceptual-referent` ×5, `parallel-state` ×4 (*"No realization exists"*).

**Sharper than previously stated:** the shortfall list is produced by
`derive_feasibility`, which is **code**. This is not a model hedging — it is a
deterministic fact, computed before approval, and discarded by the gate.

**A2 — phantoms.** `[MEASURED, 1 of 1 opportunity]` 42 concepts − 6 cut = 36 in scope;
`concepts_per_module` sums to **40**. Approved.

**A2 and A4 compound, which I had not noticed.** `[OBSERVED]` `derive_extent` builds
`by_concept` from `scope.covered` and then does
`[by_concept[name] for name in covers if name in by_concept]` — so **phantom concepts
are silently skipped and contribute zero pages.** A plan that over-claims coverage
therefore *under-states* extent by exactly the over-claim.

**A4 — extent under by ~3×, and it is a constant.** `[MEASURED, n=1]` Module 1 held
**5 concepts** and produced **14 pages / 3,477 words** — about **2.8 pages per
concept**. The table's most generous value is `work through: 1.0`.

`[INFERENCE]` So the fix is three numbers and a calibration run, not an architecture.
The direction is consistent: **the plan promises a shorter document than it produces**,
which is the worse direction — a user approves against a budget the artifact then
blows.

**A6 — unbacked capability clauses.** `[MEASURED]` 2 of 19 in the large plan; 0 in the
seven smaller ones, which carried 1–9 clauses.

**Q2 — over-scoping.** `[MEASURED, n=1]` 18 reference concepts → 42; two modules for
material the reference cuts as *senior level only* and *a different interview*.

**Q3 — leftovers-bucket module.** `[MEASURED, n=1]` 9 concepts; capability is three
unrelated clauses. The reference **predicted this exact shape** for its own module 6.

**Q4 — retrieval under-funded.** `[MEASURED, n=1]` 2 concepts inside a 7-concept
Memory module where the reference wants 3 distinct ones, and neither is query
reformulation or iterative retrieval.

**Q5 — depth not differentiated.** `[MEASURED, n=2]` contract-act **21 of 23 at `work
through`**, zero `mention`. git-commits 7 explain / 4 work-through, zero `mention`.

**Q6 — no section numbers for a numbered statute.** `[MEASURED]` Carried from §0; the
*consumer* is here — `derive_structure` invented a landscape where one should have been
read.

**A5 — `derive_v1` returns truncated JSON and loses the run.** `[MEASURED]` 2 of 10
cases, both after passing intake. The widest output in the system.

**B1 — high non-determinism, and now with a candidate mechanism.** `[MEASURED]`

| `agentic-ai-interview` | `subject` as interpret restated it | concepts |
|---|---|---|
| Sep 14 | `'agentic AI'` | **29** |
| Sep 26 | `'Agentic AI — core concepts, patterns, and frameworks for interview readiness'` | **42** |

Across all eight plans, landscape breadth tracks how richly `interpret` restated the
subject — `'Git commit messages'` → 11, `'Indian Contract Act 1872'` → 23,
the 11-word agentic restatement → 42.

`[INFERENCE, and this is new]` **B1's variance may originate in §1, not §2.** `subject`
is a free string that `interpret` rewrites, and `derive` receives the rewritten form.
A two-word subject and an eleven-word subject are different prompts. That is a
testable mechanism, and it reframes non-determinism as a **coupling** rather than a
property of derivation.

### Observed

**No cross-decision validation** — the table in §2. Five arithmetic relationships,
zero checks.

**`traversal` is string-keyed to module titles** and produced in the same call as
`partition`, with nothing reconciling them.

**`traversal` cannot be bound by a user statement.** `[MEASURED]` From §0/§1:
*"section wise"* → `depth_register`, and `traversal.why` then explained a **derived**
order: *"Follows the Act's logical architecture…"*

**`scope.cut` is names only.** `Consequence.exclusions` carries the three parts.
Nothing links them, so a cut concept can have no stated consequence — the *mark the
gap* move Semantics §12 defines.

**The legacy `Unit` shape is why Q8 has no home.** `[OBSERVED]` `Unit` is documented
as *"LEGACY: a section of a single document … These were never modules."* When the
curriculum layer arrived, `Module` was added **beside** `Unit` rather than *above* it —
so V1 has a word for "section of one document" and a word for "module," and no way to
express *sections inside a module*. `Partition.parts` treats them alike *"only for
arithmetic that does not care,"* with a warning: *"Anything that means 'this is a
separate PDF' must ask `modules` directly."*

**O6 — no memoization.** `[OBSERVED]` `inputs_hash` is written into the decision row
and never read. A correction re-derives from scratch.

**O8 — planning holds the HTTP request.** `[OBSERVED]` `def force_plan` is sync;
measured 342s, and 11,537s in one case.

### Strong inference

- **CC1 in its purest form.** Extent and feasibility are computed correctly, and one is
  reported without consequence while the other is discarded. The model's judgments
  (`job`, `capability`, `anticipates`) are recorded and unchecked. **The section's
  defects are almost entirely "computed and not depended on."**
- **The two-call split was forced by a defect, not chosen by design.** That is worth
  knowing before treating the current boundary as intentional.
- **Q2/Q3/Q4/Q5 are all downstream of `job` and `subject`** — both §1 outputs, both
  free text. `[INFERENCE]` Over-scoping follows a job read as `construct`; breadth
  follows a rich `subject`. Planning may be faithfully executing bad inputs.

### Unknown

- Does a supplied section list improve `derive_structure` or add noise? `[UNKNOWN]`
- Is subject-richness **causal** for breadth, or correlated? `[UNKNOWN]` — testable by
  pinning the subject string across trials.
- What *are* the right depth-page constants? `[UNKNOWN]` — one calibration point
  exists (2.8 pages/concept, mixed depths).
- Are five decisions the right decomposition, or does `partition` want splitting
  (grouping vs. capability-writing)? `[UNKNOWN]`
- Would per-decision calls fix A5, or just multiply the failure surface? `[UNKNOWN]`

---

## 4. The key architectural question

**Not "are the five decisions right." It is: what makes a plan *a plan* rather than six
JSON objects in a bag?**

The evidence says V1 has the decisions and not the **relationships**:

```
derive_structure ──judged by──► relevance ──in play──► scope ──covered──► partition
                                                        │                    │
                                                    cut │                    │ titles
                                                        ▼                    ▼
                                                  consequence            traversal
```

Every arrow on that diagram is a **constraint**. V1 stores the six boxes and enforces
none of the arrows. A2 is one missing arrow; the cut↔consequence gap is another;
traversal↔partition is a third.

**Two properties that follow** `[INFERENCE]`:

1. **A plan can be internally contradictory and still be structurally valid** — which
   is A1 and A2 stated as one thing.
2. **A correction cannot be checked.** The router reports `claimed` vs `actual`, but
   with no invariants, "the plan changed as claimed" cannot be distinguished from "the
   plan changed and broke a relationship." `generate-01`'s correction reduced phantoms
   7→4 — **incidentally**, while answering a content complaint. Nothing noticed either
   the repair or the four that remained.

---

## 5. Where planning starts and ends

**Current** `[OBSERVED]`: starts at `proceed()`, ends at a plan object. Extent and
feasibility are appended by code. Approval (§3) is separate.

**Boundaries worth questioning** `[INFERENCE]`:

- **`derive_structure` may not belong here.** It answers *"what exists in this
  subject"* — situation-independent, per Architecture §8's shared-asset argument
  (composition keyed by subject × frame). Everything after it is situation-dependent.
  V1 re-derives the landscape per project, which is why the same subject yields 29 and
  42 concepts on two days.
- **`consequence` is about what was cut, so it is scope's shadow** — grouping it with
  traversal/partition is the runtime split, not a semantic one.
- **The §1/§2 boundary leaks.** Planning's two most consequential inputs (`job`,
  `subject`) are free strings written by intake and never validated on arrival.

---

## 6. What planning actually produces

Three kinds of thing in one object, mirroring §1's finding:

| | Content | Nature |
|---|---|---|
| **Model judgments** | concepts, families, relevance, depths, `anticipates`, module grouping, `capability`, ordering, consequences | genuinely irreducible |
| **Computed facts** | `extent`, `feasibility` | already deterministic, already correct in kind |
| **Unenforced relationships** | the five arrows | **absent** |

`[INFERENCE]` The middle row is the encouraging part: V1 already demonstrates that the
deterministic layer works and is cheap. The two functions that compute rather than ask
are also the two whose *output nobody acts on* — so the evidence for determinism here is
about **feasibility of mechanism**, not about it having been useful yet.

---

## 7. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| A concept relevance excluded but scope covers | accepted | unchecked |
| A module covering a cut concept | accepted | **A2** |
| A cut concept with no consequence | accepted | violates Semantics §12 |
| `traversal` naming a non-existent module | accepted | unchecked |
| Partition with one module | valid and correct | **P3** — the floor held `[MEASURED]` |
| Partition with legacy `units` | accepted, arithmetic-compatible | Q8's cause |
| Every concept unservable | `serves_everything: False`, plan proceeds | **A1** |
| `derive` output truncated | run dies | **A5** |
| Extent exceeds a stated capacity | *unknown* — `capacity` was `null` in every record `[MEASURED]` | the negotiation path Architecture §11 describes has **never executed** |

That last row deserves flagging: **capacity-based negotiation is entirely untested.**
No record carries a stated capacity, so the mechanism that makes extent matter has
never run.

---

## 8. Constraints and cross-section effects

**On §0** — `derive_structure` is the consumer of an ingested skeleton; `traversal` is
the consumer of a stated ordering. Both would change shape.

**On §1** — planning's inputs are free strings. A typed `job` (§1 option A) only
matters if planning branches on it; a typed `subject` may be what B1 actually needs.

**On §3** — approval can only gate on what planning computes. The shortfall list and
the phantom arithmetic already exist; **the gate is one boolean away.** Conversely,
corrections re-enter planning and are the only self-repair path.

**On §4** — `requirements(plan)` turns modules into generation orders, and
`curriculum.plan_for` scopes each. **A phantom concept can be handed to the generator**,
and `coverage: 1.0` would still report success.

**On §6** — `anticipates` is the *only* channel by which planning learns what the
renderer can draw. Change the renderer and this vocabulary changes.

**On §7** — five decision records per plan, plus commitments. `inputs_hash` exists for
reuse and has nowhere to be looked up.

**On §8** — the single longest synchronous operation in the product.

---

## 9. Solution directions — compared, not chosen

**A. Enforce the five relationships.** Validators or a checked assembly step.
*Delivers:* A2 outright, the cut↔consequence gap, traversal↔partition. *Cost:* very
small — this is arithmetic. *Does not deliver:* any quality finding.

**B. Recalibrate the depth constants.** Measure pages-per-concept-per-depth, set the
three numbers. *Delivers:* A4. *Cost:* one generation run per depth level.
*Caveat:* A2 must be fixed first or the measurement is polluted by skipped phantoms.

**C. Make feasibility and phantom-freedom approval preconditions.** *Delivers:* A1 —
and it is a §3 change consuming a §2 output that already exists. *Cost:* near zero.
*Risk:* a plan that cannot be approved needs a path forward, not a dead end.

**D. Bound `derive`'s output.** Chunk by family, stream, or split into two calls.
*Delivers:* A5. *Cost:* moderate. *Precedent:* the same defect already forced the
landscape/body split, so the mechanism is known to work.

**E. Pin `subject` and test breadth.** Hold the subject string constant across trials
and see whether concept count stabilises. *Delivers:* a mechanism for B1, or rules it
out. *Cost:* ~3 calls. **Highest information per call in this section.**

**F. Separate `derive_structure` from the situation-dependent decisions.** Toward
Architecture §8's shared asset. *Delivers:* stability, reuse, and a place for §0's
skeleton to live. *Cost:* the largest option here, and it opens asset versioning and
promotion.

**G. Give `job` and depth consequences.** Admissibility rules: `orient` forbids certain
depths; `execute a procedure` requires every step. *Delivers:* the only route to Q1,
Q2, Q5 that isn't prompt-tuning. *Cost:* moderate. *Effect:* `[UNKNOWN]`.

**H. Split `partition` into grouping and capability-writing.** The reference's
leftovers-bucket test is about whether *one sentence* describes the result — which is a
different judgment from which concepts belong together. *Delivers:* a possible route to
Q3. *Cost:* another decision. *Speculative.*

**The shape:** A, B and C are cheap, arithmetic, and fix three measured structural
defects between them. E is the cheapest experiment in the section. D has precedent. F
and G are real architecture. H is speculation.

---

## What remains genuinely open

1. **Is subject-richness causal for breadth?** Cheapest test, biggest reframe if true.
2. **What are the right depth constants?** One data point exists.
3. **Does a typed, consequential `job` reach Q2/Q5?** Shared with §1.
4. **Is `derive_structure` situation-independent** enough to be shared/cached?
5. **Is five the right decomposition** — and does `partition` want splitting?
6. **What should happen when a plan cannot be approved?** C has no answer yet.
7. **Capacity negotiation has never run.** Architecture §11's mechanism is untested.
