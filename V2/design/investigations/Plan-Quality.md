# Plan Quality — turning "this plan is shit" into something measurable

Structural correctness (`V1-Measured-Issues.md`) asks *is the plan self-consistent
and deliverable?* This asks a different question: **is it a good curriculum?** A plan
can pass every structural check and still be bad.

**Sources.** The 3 hand-written references in `corpus/references/` and the generated
plans already on disk for those same 3 cases. No new model calls.

| case | reference | generated plan available |
|---|---|---|
| `agentic-ai-interview` | 139 lines | 5 modules (Sep 14) · **8 modules (Sep 26)** |
| `contract-act-authority` | 114 lines | 9 modules (Sep 25) |
| `git-commits-narrow` | 95 lines | 1 module (Sep 14) |

Each reference ends with a "what this is testing" section, so the quality definition
below is largely **extracted from them**, not invented here.

---

## 1. What the references say makes a plan good

Thirteen properties, each named by at least one reference.

1. **The job is read correctly.** `orient` ≠ `construct` ≠ `retrieve/rehearse`. The
   agentic reference is explicit: *"The learner will be talking about agents, not
   shipping one… 'Architect a multi-tool production agent' is the wrong promise for an
   orienting document, however impressive it sounds."*
2. **Target capability decomposes into sub-capabilities, and those select the
   concepts.** `TARGET → C1…C7 → concepts`. The agentic reference calls this *"the part
   V1 has no representation for."*
3. **Every capability clause is cashable** — some concept in the module can answer it.
   *"C4 promising 'design iterative retrieval loops with query reformulation' over a
   scope holding one concept called RAG for Agents is a cheque the scope cannot cash."*
4. **A module is one capability sentence a reader could act on** — not three stapled
   together. The leftovers-bucket test: *"the test is whether a single sentence
   describes what the reader can do afterwards."*
5. **Partition floor: small stays one.** *"Length is not a reason to split."* Part 1 of
   a chain has no capability that stands alone.
6. **Depth is differentiated, and attaches to the capability clause it serves** — not
   uniform across concepts.
7. **Cuts carry consequences** and are first-class, not omissions.
8. **Granularity rule:** if the learner must tell two things apart, they are two
   concepts. *"As one node it can never be divided later, because there is nothing there
   to divide."*
9. **Sections are not modules.** The git-commits reference lists **6 sections inside
   one module**.
10. **Structure can be read rather than derived** — an external authority owning
    terminology, ordering and coverage.
11. **A stated constraint can bind traversal specifically** — "section wise".
12. **Zero internal dependency is sometimes correct.** *"A dependency-count rule would
    flag this module as incoherent, and would be wrong."*
13. **Out-of-scope corrections are deferred, not absorbed.** *"Absorbing it is worse
    than deferring it, because the user believes it was handled."*

---

## 2. What the comparison actually shows

### Failures

**Q1 — The job is misread in all three cases.** V1 recorded `job: construct` for
every one. References: agentic = **orient**, contract-act = **retrieve/rehearse**,
git-commits = construct. **2 of 3 wrong**, and both wrong the same direction — toward
*build it* instead of *talk about it / recall it*.

This is the root defect, because it cascades. With `job: construct`, agentic's target
became *"Explain agent architectures… trace execution… answer follow-ups on memory,
evaluation, and deployment trade-offs"* — and the scope grew to match.

**Q2 — Over-scoping follows from Q1.** The agentic reference cuts, with consequence:
multi-agent orchestration (*senior level only*), fine-tuning, production deployment and
observability (*a different interview*). V1 gave **multi-agent a whole 5-concept
module** and **deployment another 3-concept module**. Concepts went 18 (reference) → 42.

**Q3 — The predicted leftovers bucket appeared.** The reference warns module 6 is *"the
module most at risk of becoming a leftovers bucket… safety, observability, cost and
deployment thrown together because they are all 'advanced' is the failure shape."*

V1's **module 7, "Other Frameworks & Evaluation"** — 9 concepts — mixes Semantic
Kernel, OpenAI Assistants, LlamaIndex, AutoGPT/BabyAGI, AgentBench, WebShop, ALFWorld,
τ-bench and LLM-as-Judge. Its capability is three unrelated clauses: *position the
secondary frameworks* + *explain what AutoGPT got wrong* + *select an evaluation
approach*. It fails the single-sentence test exactly as predicted.

**Q4 — Retrieval is still under-funded.** The reference dedicates module 4 to it
(retrieval basics · query reformulation · iterative retrieval) and notes drily that this
is *"the module V1 funded with one concept."* V1 now folds it into a 7-concept Memory
module as `Memory Retrieval & RAG for Agents` + `RAG vs Agents Distinction`. Still no
query reformulation, still no iterative retrieval as distinct concepts.

**Q5 — Depth is not differentiated.** `contract-act`: **21 of 23 concepts at `work
through`**, 2 at `explain`, zero at `mention`. The reference wants free consent and
remedies at work-through, contingent contracts at explain, preliminary definitions at
mention-but-present. `git-commits`: 7 explain / 4 work-through, **no `mention` at all**,
where the reference assigns mention to imperative mood and trailers.

**Q6 — No section numbers for a numbered statute.** The contract-act reference's whole
point: *"Sections 1–75 exist, in an order, with names… A missing section is a fact, not
a judgment."* V1's plan contains **no section reference anywhere** — `Preliminary &
Definitions`, not `ss. 1–2`. Coverage stays unverifiable against anything external.

**Q7 — Intake over-asks as well as under-asks.** `git-commits`: the reference says
*"the honest intake here asks zero or one question… an axis whose answer would not
change the plan is not a question, however unknown it is."* V1 wrote **4 questions**
and flagged **7 weak axes**. That sits beside A3 in the structural ledger, where three
cases asked **zero** on a known-material guess. Both failure directions are real.

**Q8 — Sections are unrepresentable.** `git-commits` produced 11 concepts → 11 sections.
The reference specifies 6 named sections over 7 concepts. V1 has no section decision,
so a correct answer is not expressible.

### Passes — worth recording, because they were feared

**P1 — Terminology survived.** The contract-act reference's worry — *"a landscape that
produces 'Agreement validity factors' has renamed the thing the exam will use"* — did
not happen. V1 produced `Free Consent — Coercion`, `Undue Influence`, `Fraud`,
`Misrepresentation`, `Mistake`, `Quasi-Contracts`, `Bailment — Pledge & Lien`,
`Indemnity`, `Guarantee`, `Agency`. The Act's own words.

**P2 — Frameworks named separately.** LangGraph, CrewAI, AutoGen as distinct concepts,
plus legacy LangChain agents as contrast. The granularity rule held where the reference
most wanted it.

**P3 — The partition floor held.** `git-commits` → exactly 1 module, unprompted. That
is the thing the reference exists to test.

**P4 — The out-of-scope correction was deferred, not absorbed.** *"make it dark themed
with orange accents"* → `out_of_scope: "Theme and colour choices … are presentation
decisions owned by the demo/rendering stage, not the plan"`, `landed: false`,
`claimed: []`, `actual: []`. Exactly the behaviour the reference asked for.

---

## 3. The dimensions, and how each can be judged

Twelve checks. **Deterministic** means code can decide it given a machine-readable
expectation. **Judge** means it needs a model.

| # | Dimension | How | Needs |
|---|---|---|---|
| D1 | **Job label** matches the reference | compare enum | **Deterministic** — expected job in the case file |
| D2 | **Required concepts present** (reference's "must be in play" list) | fuzzy name match | **Deterministic** — requires a required-concepts list |
| D3 | **Forbidden concepts absent** (reference's cuts) | fuzzy name match | **Deterministic** — requires a cut list |
| D4 | **Module count** within the reference's range | integer compare | **Deterministic** — but weak on its own (see B1 variance) |
| D5 | **Depth differentiated** — not all one value; `mention` used where expected | distribution check | **Deterministic** |
| D6 | **Capability clauses backed by concepts** | V1 already computes `capability_unbacked` | **Deterministic — exists today** |
| D7 | **Cuts carry a consequence** (non-empty, names what is lost and when to learn it) | field presence + length | **Deterministic** for presence; **Judge** for honesty |
| D8 | **Coverage against an external authority** (statute sections, syllabus items) | set difference | **Deterministic — but needs the source**, which V1 cannot ingest |
| D9 | **Stated traversal constraint honoured** ("section wise") | ordering compare against authority | **Deterministic** given D8's source |
| D10 | **Module is one capability, not a bucket** | the leftovers-bucket test | **Judge** — this is the Q3 defect and no counter can catch it |
| D11 | **Granularity correct** — should X be two concepts? | — | **Judge** |
| D12 | **Depth appropriate for purpose**, ordering pedagogically sound | — | **Judge** |

**Six of twelve are deterministic**, and D6 already runs today. The expensive ones are
D10–D12, which are exactly the "this plan is shit" feeling — coherence, granularity and
judgment.

**The load-bearing insight:** the single worst defect (Q1, job misread, 2 of 3) is
**D1 — a one-line enum comparison.** The most consequential quality failure in the set
is the cheapest thing to measure, and it cascades into Q2, Q5 and the leftovers bucket.

---

## 4. Are the references sufficient? No — six gaps

**G1 — Coverage: 3 references for 10 cases.** Seven cases have no yardstick at all:
`transformers-deep`, `french-revolution-exam`, `vlsi-underspecified`,
`dsa-graphs-interview`, `heart-anatomy-visual`, `consensus-analogies`,
`ml-weekend-conflict`. Two of those (`heart-anatomy`, `consensus-analogies`) are the
visual and analogy cases — the ones carrying the most representation shortfalls.

**G2 — One reference is itself incomplete, and V1 beat it.** The contract-act
reference's structure table runs **ss. 1–75**. The Indian Contract Act runs to **s. 238**
— indemnity and guarantee, bailment and pledge, agency. V1 produced modules for all of
them (7, 8, 9); the reference has none.

So on coverage V1 is **more complete than its own yardstick**, and its 9 modules vs the
reference's 6 is partly explained by the reference stopping early rather than by V1
over-partitioning. **A reference that is wrong cannot score anything.** This one needs
extending before it is used as a measure.

**G3 — The references are prose, not data.** Every comparison in §2 I did by hand,
reading 348 lines and eyeballing module lists. Nothing in `corpus/` holds expected job,
required concepts, forbidden concepts, expected depth assignments or module-count range
as fields. D1–D5 and D8–D9 are all mechanically checkable **and none of them can run**
until the expectations exist as structured values.

**G4 — No rubric or weights.** Q1 (job misread) cascades into three other failures;
D4 (module count off by two) may not matter at all. Right now every dimension would
score equally, which would rank a plan with the right job and one extra module below a
plan with the wrong job and a lucky count.

**G5 — Variance makes single comparisons uninterpretable.** `agentic-ai-interview`
produced 5 modules and 29 concepts on Sep 14, then 8 and 42 on Sep 26. A one-shot score
against a reference cannot separate *"the planner is wrong"* from *"the planner is
noisy."* Quality measurement needs n>1 per case — which collides directly with 50
calls/day.

**G6 — Two dimensions score V1 as failing by construction.** D8/D9 need an ingested
source, and Q8 needs a section decision. V1 has neither, so these always fail with the
same reading. They are **architecture findings, already recorded** — scoring them
repeatedly produces no new information.

---

## 5. The definition, stated plainly

**A plan is good when:**

> the job is read correctly; the target capability decomposes into sub-capabilities and
> those select the concepts; every capability clause is answerable by a concept present
> in its module; each module is one thing a reader could afterwards do; depth varies with
> what each concept is for; what was cut says what that costs; and where an external
> authority exists, terminology, ordering and coverage come from it rather than from the
> model.

**Measured against that, V1's plans fail on job (2/3), on scope discipline, on module
coherence, on depth differentiation, and on external authority — and pass on
terminology, granularity-where-it-matters, partition floor, and correction routing.**

"Shit" was mostly **Q1 → Q2 → Q3**: one wrong enum at the top, a scope inflated to match
it, and a bucket module at the end to hold the overflow.

---

## 6. What this does not decide

Whether the fix is a better prompt, a capability-decomposition representation, a judge
in the loop, or an operation-based planner. Also untouched: whether the generated
*documents* are good — only plans were compared, and document quality has no reference
at all.
