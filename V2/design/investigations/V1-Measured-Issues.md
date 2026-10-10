# V1 Measured Issues

What measurement — not reading code, not remembering — established about frozen V1.

**Sources.** Only what is on disk:

- `runs/baseline-01` — 10 records, 6 complete
- `runs/generate-01` — 1 record, the only end-to-end run (plan → approve → PDF)
- `runs/*/store/*-t1/*.json` — V1's own persisted decisions, which carry fields the
  observer drops
- `corpus/references/` — 3 hand-written references, the yardstick for §B

V1 at source hash `807c8ec99a60`, model `nvidia/nemotron-3-ultra-550b-a55b:free`
throughout.

**This is not `V1/Issue-Ledger.md`.** That was compiled from conversation history —
things we noticed while building. This contains only what a recorded run demonstrates.
Where they disagree, this one wins.

`Plan-Quality.md` holds the long working for §B and §D — the thirteen properties
extracted from the references, and the reference-by-reference comparison. **This ledger
supersedes it** where the two differ.

**Method rules, learned the hard way.**

- **Exclude `runs/stub` from every glob.** Its `would_differ` values are literally
  `"nothing, this is a stub"`. It silently contaminated one pass during this analysis.
- **Read record fields by name, never by column position.** A positional misread turned
  `cut` values into a fictional slug-collision finding (see §F).
- **Sample sizes are stated on every finding and are small.** Eight plans, **one**
  generation, three references. Several findings are n=1 and say so. Nothing here is a
  rate.

---

## §A — Structural defects

Things V1 *does*, not things the provider did to it.

### A1 — Approval passes a plan that admits it cannot be delivered

**Issue.** Every plan computes feasibility and records which concepts it cannot
realize. `approve()` ignores the report completely.

**Evidence.** `serves_everything: False` in **6 of 8 plans**. Five of those six reached
approval; **all five were approved** (the sixth, `contract-act`, died at `correct`
before approval). Two failure kinds:

- `perceptual-referent` — "The system cannot draw this" — **5 plans**
- `parallel-state` — "**No realization exists**" for the licensed forms
  (`sequence · swimlane · timeline`) — **4 plans**

Concrete: `heart-anatomy-visual`, a case explicitly about visual learning, flagged
*Pericardium and heart position*, *External heart features and sulci*, *Right atrium
internal anatomy*. Approved. `generate-01` flagged *Observability & Tracing* as
undrawable and *Streaming & Async Execution* as having no realization. Approved.

**Why it matters.** The plan gate is the product's central promise — *what gets written
is what you approved*. The user approves a document containing anatomy diagrams the
system has already determined it cannot draw. The information is computed, recorded,
and reaches no one.

**V2 requirement: YES.** Strongest in the set.

### A2 — Modules promise concepts that scope excluded (phantoms)

**Issue.** Relevance cuts a concept; a module still lists it as covered; approval
accepts the contradiction.

**Evidence.** `generate-01`: **7 phantoms before corrections, 4 after** —
`AutoGPT / BabyAGI`, `LlamaIndex Agents`, `OpenAI Assistants API / Agents SDK`,
`Semantic Kernel`. Arithmetic confirms: 42 concepts − 6 cut = 36 in scope, while
`concepts_per_module` sums to **40**. `approved: true`.

Observed in the only plan where relevance cut *and* partitioning produced many
modules — **1 of 1 opportunity**, not 1 of 8.

**Downstream.** `curriculum.plan_for(snapshot, index)` scopes generation from the
module, so a generator can be handed a concept the plan excluded — and `coverage: 1.0`
would still report success.

**The parked patch does not fix this.** `v1-orphan-approval-gate.patch` gates on
*orphans* — approved concepts in no module — and **orphans were 0 in all 11 records**.
This is the mirror defect.

**V2 requirement: YES.**

### A3 — STRUCK

~~"Intake declares sufficient while holding a known-guessed material axis."~~

**Retracted.** The three cases cited — `contract-act` and `transformers-deep`
(`capacity`), `vlsi-underspecified` (`depth_register`) — involve axes that are
`askable=False` **by locked policy** (`V1/agent/sufficiency.py:115–133`). Capacity's
recorded reason is that asking is itself the error:

> *"deriving the plan and reporting its extent is what CAUSES a capacity to be stated.
> Asking upfront asks for a number the learner cannot honestly give."*

Not a defect. Correct behaviour.

**Evidence preserved, because it matters elsewhere.** The intake mechanism is genuinely
reasoning about materiality, and **V1 persists the justification**. Recovered from
`decision[*].output.sufficiency.axes[*].would_differ` in the per-trial stores:
**88 of 88 readings populated, median 188 characters, minimum 110, zero empty.** They
are concrete, not generic — e.g. for `git-commits` / `entry_point`:

> *"Beginner needs git basics (staging, history) explained; experienced dev needs only
> conventions, examples, and tooling."*

The residual question is threshold calibration, recorded as **B8**.

### A4 — Extent is badly under-estimated

**Issue.** The page estimate the user approves against does not match what generation
produces.

**Evidence.** `generate-01`: plan promised **~36 pages / ~11 hours** for 8 modules.
Module 1 — the *smallest*, 5 of 40 concepts — produced **14 pages**, 3,477 words. At
that density 40 concepts is well over 100 pages.

**n=1** for the comparison. The arithmetic is not marginal.

**Why it matters.** Extent is the only quantity connecting a plan to the user's
capacity, and Architecture §11 rests capacity negotiation on it.

**V2 requirement: YES**, with one measurement setting direction, not magnitude.

### A5 — `derive_structure` returns unparseable JSON and loses the run

**Evidence.** 2 of 10 cases on 2026-09-25 — `transformers-deep`,
`dsa-graphs-interview` — both *"produced invalid output twice for derive_v1 … Invalid
JSON: EOF whil…"*. Both had passed intake. Both lost everything.

**Why it matters.** `derive` is the widest output in the pipeline. This is the model
completing and being malformed — not a network fault.

**V2 requirement: YES** — as *bounded output*, not a bigger retry.

### A6 — Capability promises are not fully backed by concepts

**Evidence.** `generate-01`: `capability_clauses: 19`, **`capability_unbacked: 2`**.
Zero in the 7 earlier plans, which carried 1–9 clauses. First appearance at 19.

**V2 requirement: WEAK YES.** Real but small, and only visible once plans got large.

### A7 — Representation departures escape without a licence

**Evidence.** `generate-01`, module 1: `departures: 36`, **`undiagnosed: 6`**,
`unlisted: 0`, `unrendered: 0`, `scale: 1.0`, `clean: false`. 30 pairs correctly
licensed.

**Why it matters.** `Representation-Boundary` (FROZEN) requires every departure to name
its licence. 17% don't, and the PDF renders anyway.

**V2 requirement: YES**, and cheap — the check exists and simply does not block.

### A8 — Persisted intake collapses the materiality enum to a boolean

**Issue.** `AxisReading.materiality ∈ {changes_the_plan, changes_details, no_effect}`
is reduced to `material: bool` before storage
(`material = reading.materiality == "changes_the_plan"`).

**Evidence.** No store in any run contains the three-valued field; only the derived
boolean survives. Confirmed by search across all non-stub stores.

**Why it matters.** `changes_details` and `no_effect` become indistinguishable after
the fact, so the middle value — the one that would justify *not* asking about a weak
axis — cannot be audited. Small, definite, V1's own data-model loss.

**V2 requirement: YES**, trivially.

---

## §B — Plan-quality defects

A plan can pass every structural check in §A and still be a bad curriculum. Measured
against the 3 hand-written references, on the 3 cases that have one.

### Q1 — The job is misclassified

**Evidence.** V1 recorded `job: construct` for all three cases. References:
`agentic-ai` = **orient**, `contract-act` = **retrieve/rehearse**, `git-commits` =
construct. **2 of 3 wrong**, both toward *build it* rather than *talk about it / recall
it*. **n=3.**

**Why it matters.** It is the root defect, because it cascades — Q2 and Q3 are both
downstream of it. The agentic reference is explicit: *"the learner will be talking
about agents, not shipping one … 'Architect a multi-tool production agent' is the wrong
promise for an orienting document, however impressive it sounds."*

### Q2 — Over-scoping follows from Q1

**Evidence.** The agentic reference cuts, with consequence: multi-agent orchestration
(*senior level only*), fine-tuning, production deployment and observability (*a
different interview*). V1 gave **multi-agent a 5-concept module** and **deployment
another 3-concept module**. Concepts: **18 (reference) → 42 (V1)**. **n=1 case.**

### Q3 — Leftovers-bucket modules

**Evidence.** The reference warns its module 6 is *"the module most at risk of becoming
a leftovers bucket … safety, observability, cost and deployment thrown together because
they are all 'advanced' is the failure shape."*

V1's **module 7, "Other Frameworks & Evaluation"** — 9 concepts — mixes Semantic
Kernel, OpenAI Assistants, LlamaIndex, AutoGPT/BabyAGI, AgentBench, WebShop, ALFWorld,
τ-bench and LLM-as-Judge. Its capability is three unrelated clauses: *position the
secondary frameworks* + *explain what AutoGPT got wrong* + *select an evaluation
approach*. It fails the reference's single-sentence test. **n=1 case — and the failure
shape was predicted in advance.**

### Q4 — Important capabilities under-funded

**Evidence.** The reference dedicates module 4 to retrieval — *retrieval basics ·
query reformulation · iterative retrieval*, three concepts — and notes drily that this
is *"the module V1 funded with one concept."*

V1 now folds it into a 7-concept Memory module as **two** concepts, `Memory Retrieval &
RAG for Agents` and `RAG vs Agents Distinction`. **Neither is query reformulation or
iterative retrieval.** **n=1 case.**

### Q5 — Depth is not differentiated

**Evidence.** `contract-act`: **21 of 23 concepts at `work through`**, 2 at `explain`,
**zero `mention`** — where the reference wants free consent and remedies at
work-through, contingent contracts at explain, and preliminary definitions at
mention-but-present. `git-commits`: 7 explain / 4 work-through, **zero `mention`**,
where the reference assigns mention to imperative mood and trailers. **n=2 cases.**

### Q6 — External-authority structure is unrepresented

**Evidence.** The contract-act reference's whole point: *"Sections 1–75 exist, in an
order, with names … A missing section is a fact, not a judgment."* V1's plan contains
**no section reference anywhere** — `Preliminary & Definitions`, not `ss. 1–2`.
Coverage stays unverifiable against anything external. **n=1 of 1 opportunity** — it is
the only corpus case with an authoritative source.

### Q8 — Sections are not represented independently of modules

**Evidence.** `git-commits`: 11 concepts → **11 sections**. The reference specifies
**6 named sections over 7 concepts**.

**Architectural, not statistical.** V1 has no section decision — sections are
one-per-concept by construction — so the correct answer is *inexpressible*, not merely
unachieved. **n=1 case, but the cause is structural.**

---

## §C — Variability and uncertainty

Not defects. Things the measurements show are unstable or unexplained, and which
therefore cannot yet become requirements.

### B1 — The planner is highly non-deterministic

Same request, same frozen V1, same model:

| `agentic-ai-interview` | Sep 14 | Sep 26 |
|---|---|---|
| concepts | 29 | **42** |
| edges | 38 | 60 |
| roots | 1 | **5** |
| modules | **5** | **8** |
| relevance cut | 0 | 6 |
| phantoms | 0 | **4** |

`ml-weekend-conflict`, stated precisely as two separate facts:

- **Cross-run:** 1 module / 32 concepts (Sep 14) vs 5 modules / 26 concepts
  (Sep 25, pre-correction)
- **Within-run:** one correction moved it **5 modules → 3**, and cut 11 → 13

**Consequence.** Every single-run number in this ledger is one sample. Variance sits in
the *planner* and moves the landscape itself, so "how many concepts does this subject
have" is not a stable quantity in V1.

**Explicitly open, and deliberately not resolved here:** whether V2 needs
**determinism**, or only **stability in what it promises**. That is a product decision.

### B2 — `decision_count` is always exactly 7

Every approval in every record. Plans ranged from **1 to 9 modules**. A per-member
ordered commitment (Architecture §5) should not be constant. Most likely it counts
decision *kinds* — unverified. Flagged, not diagnosed.

### B3 — Partitioning looks reasonable, but the evidence is weak

Module counts across 8 plans: **9, 8, 5, 3, 1, 1, 1, 1**. They track breadth in the
right direction — `git-commits-narrow` (11 concepts) got 1, `contract-act` (a semester
syllabus) got 9. But B1 shows breadth itself is unstable, and the same case produced 1
and 5. *"Partitioning works"* is **not established** — only that it is not stuck at 1.

### B4 — Three modules with no internal dependency

`modules_with_no_internal_dependency`: 3 (`contract-act`), 3 (`generate-01`),
1 (`agentic-ai` base), 0 elsewhere. May be a correct grouping of independent items or
an arbitrary bucket — the diagnostic cannot tell them apart.

The agentic reference confirms both readings are real: *"Zero internal dependency is
correct here — the frameworks are not built on each other, and that is exactly what
makes the comparison possible. A dependency-count rule would flag this module as
incoherent, and would be wrong."*

### B5 — Depth allocation is unexplained

`contract-act` assigned `work through` to 21 of 23 concepts for a university exam;
`french-revolution-exam` assigned `explain` to 16 of 17. Both exam cases, near-opposite
allocations. Related to Q5, but no basis here for calling either *wrong*.

### B6 — The free tier dominates, and it is not V1

Failures across both baseline attempts: **7 network** (`getaddrinfo failed`,
502 `Service temporarily overloaded`, `WinError 10054`) and **2 model-output** (A5).
`contract-act-authority` burned **11,537s** — 3.2 hours — on 4 calls and still failed
on local DNS.

A measurement-programme problem, not a product defect. It also means every rate here is
unreliable: 4 of 10 cases never produced a plan for reasons unrelated to V1.

### B7 — The harness loses data on retry, and undercounts cost

`dsa-graphs-interview` had a partial record with a plan (43 concepts, 1 module). The
retry failed *earlier* and **overwrote it** — retry is unconditional overwrite.

Separately, a record's `cost` counts only the plan phase: `v1_service.generate` calls
`select_provider()` itself and bypasses the counting wrapper. `generate-01`'s true cost
was **11 calls**, not the 6 that `cost.model_calls` reports.

### B8 — Intake threshold calibration (reclassified from a defect)

**What is certain.** The materiality filter has **never once suppressed a question**:
*weak + askable + `material=False`* occurs **0 times in 88 readings**. The only four
askable `material=False` cases are all `artifact_type`, and all were already *stated or
inferred* — so materiality was moot there anyway.

**What is equally certain.** It is not a rubber stamp: 88/88 `would_differ` values are
populated and concrete (A3), and the model *does* discriminate elsewhere — 26 of 88
readings are not `changes_the_plan`.

**So this is a threshold difference, not a broken mechanism.** The model's bar is
*"emphasis or inclusion would differ"*; the reference's is *"would move scope, depth or
partition meaningfully."* The enum has exactly the right middle value for the gap —
`changes_details` — but A8 means its use cannot be audited.

**And the reference is contestable on the axis that matters most.** It asserts entry
point would not move scope for `git-commits`, while the model answers *"beginner needs
git basics (staging, history) explained; experienced dev needs only conventions"* —
which describes a real scope change. The reference quietly assumes its own answer
(*"Uses git daily; commits are messy"*).

**Evidence:** one contestable reference judgment against one defensible model judgment,
on one case. **Not a defect.**

---

## §D — The plan-quality model

Twelve candidate dimensions, extracted from the references. **Not a scoring system** —
no weights, no thresholds, no aggregate.

| # | Dimension | Class |
|---|---|---|
| D1 | Job label matches | **Deterministic** |
| D2 | Required concepts present | **Deterministic** |
| D3 | Forbidden concepts absent (the reference's cuts) | **Deterministic** |
| D4 | Module count within range | **Deterministic** (weak alone — see B1) |
| D5 | Depth differentiated; `mention` used where expected | **Deterministic** |
| D6 | Capability clauses backed by concepts | **Deterministic — runs today** (A6) |
| D7 | Cuts carry a consequence | **Hybrid** — presence deterministic, honesty judged |
| D8 | Coverage against an external authority | **Requires external structured authority** |
| D9 | Stated traversal constraint honoured | **Requires external structured authority** |
| D10 | Module is one capability, not a bucket | **LLM-judged** |
| D11 | Concept granularity correct | **LLM-judged** |
| D12 | Depth appropriate for purpose; ordering sound | **LLM-judged** |

**Six deterministic, three judged, two need an authority, one hybrid.**

**The asymmetry worth recording:** the worst measured defect (Q1, job misclassified,
2 of 3) is checked by **D1 — a one-line enum comparison.** The most consequential
quality failure is the cheapest thing to measure, and it cascades into Q2 and Q3.

---

## §E — Benchmark and measurement gaps

- **G1 — Coverage.** Only **3 of 10** cases have references. The seven without include
  `heart-anatomy-visual` and `consensus-analogies` — the visual and analogy cases,
  which carry the most representation shortfalls.
- **G2 — One reference is itself incomplete.** The contract-act reference's structure
  table runs **ss. 1–75**; the Act runs to **s. 238**. V1 produced modules for
  indemnity, guarantee, bailment, pledge and agency; the reference has none. **On
  coverage V1 beat its own yardstick**, and its 9 modules vs the reference's 6 is partly
  the reference stopping early. A reference that is wrong cannot score anything.
- **G3 — References are prose, not data.** Nothing in `corpus/` holds expected job,
  required concepts, forbidden concepts, expected depths or module-count range as
  fields. D1–D5 and D8–D9 are mechanically checkable and **none can run** until the
  expectations exist as structured values. Every comparison in §B was done by hand.
- **G4 — No rubric or weights.** Q1 cascades into three other failures; D4 off by two
  may not matter. Every dimension currently scores equally.
- **G5 — Variance defeats one-shot scoring.** B1 means a single comparison cannot
  separate *"the planner is wrong"* from *"the planner is noisy."* Quality measurement
  needs n>1 per case, which collides with 50 calls/day.
- **G6 — Two dimensions fail by construction.** D8/D9 need an ingested source and Q8
  needs a section decision; V1 has neither, so they always fail identically. Repeating
  them yields no new information.
- **G7 — The harness drops `would_differ`.** V1 emits it in `to_json`;
  `harness/observe.py:66–77` does not copy it. It is recoverable from the stores, but
  invisible in the records — which nearly produced a false "never populated" finding.

---

## §F — Disproved, and confirmed-correct

### F.1 Disproved / no evidence

| Claim | Verdict |
|---|---|
| **"V1 collapses to 1 module"** | **Disproved.** 9, 8, 5, 3, 1, 1, 1, 1. The 1-module cases are narrow requests. |
| **"Slug collisions are real — 5 and 12"** | **Disproved, and it was an analysis error.** `slug_collisions: 0` in all 11 records; the numbers were `cut` values misread off a positional table. |
| **"Relevance never cuts anything"** | **Disproved.** 13 (`ml-weekend`) and 6 (`generate-01`). Zero in the other six — it cuts when the situation gives grounds. |
| **"Orphans are a live defect"** | **No evidence.** 0 in all 11 records. The parked patch was written from code reading; its mirror (A2) is what actually occurs. |
| **"Duplicate coverage"** | **No evidence.** 0 in all 11 records. |
| **"The generator silently omits approved content"** | **Not reproduced.** `satisfied: true`, `coverage: 1.0`, `concepts_missing: []`, `units_missing: []`, `problems: []`, `repairs: 0`. **n=1** — but the prime suspect did not appear. |
| **"Intake is merely procedural"** | **Disproved.** 88/88 `would_differ` populated, median 188 chars, concrete alternatives with named consequences. See A3 and B8. |

### F.2 Behaviours the references feared and V1 got right

Recorded so they are not re-litigated.

- **Terminology preserved.** The contract-act reference feared *"a landscape that
  produces 'Agreement validity factors' has renamed the thing the exam will use."* V1
  produced `Free Consent — Coercion`, `Undue Influence`, `Fraud`, `Misrepresentation`,
  `Mistake`, `Quasi-Contracts`, `Bailment — Pledge & Lien`, `Indemnity`, `Guarantee`,
  `Agency` — the Act's own words.
- **Framework granularity held.** LangGraph, CrewAI and AutoGen as separate concepts,
  plus legacy LangChain agents as contrast — exactly where the reference's granularity
  rule most mattered.
- **The partition floor held.** `git-commits` → **exactly 1 module**, unprompted. That
  is the thing its reference exists to test.
- **An out-of-scope correction was deferred, not absorbed.** *"make it dark themed with
  orange accents"* → `out_of_scope: "Theme and colour choices … are presentation
  decisions owned by the demo/rendering stage, not the plan"`, `landed: false`,
  `claimed: []`, `actual: []`.

---

## §G — Conclusion

**Measurement moved the problem upstream.**

The suspected failure was generation — a generator dropping approved content. The one
end-to-end run shows the generator honouring its contract exactly, and the *plan it was
handed* being the broken artifact.

**V1 can produce a plan that is both internally inconsistent and pedagogically wrong,
and approve it.**

- **Inconsistent** — it admits it cannot draw what it promised (A1, 6 of 8) and lists
  concepts its own scope excluded (A2), and gates on neither.
- **Pedagogically wrong** — it misreads the job (Q1, 2 of 3), inflates scope to match
  (Q2), and parks the overflow in a bucket module (Q3).

"This plan is shit" decomposes to **one wrong enum at the top, a scope inflated to
match it, and a leftovers module holding what is left over.**

**What V2 does not need to fix, on current evidence:** orphans, duplicate coverage,
slug collisions, generator omission, and intake's willingness to reason about
materiality.

**What cannot be decided from these records:** whether the planner's non-determinism
(B1) is a defect or a property to be managed, and whether intake's materiality
threshold (B8) is miscalibrated or the reference is. Both need evidence that does not
exist yet.

**No V2 architecture is proposed here, deliberately.**
