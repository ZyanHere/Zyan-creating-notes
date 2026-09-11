# Architecture — Rev. 2

**4 Sep 2026 · downstream of `Product-Semantics.md` (Rev. 3)**

Web version: https://claude.ai/code/artifact/de99cd5c-c7a8-46f9-807e-b98430bfdc2f

This document records **architecture only**: what judgments exist, when they run, where they commit, and what a correction costs. It makes no educational claims. Where it needs one, it cites the semantics.

> **Rev. 2 is not Rev. 1 corrected.** Rev. 1 had one boundary rule doing four jobs, which produced a decision taxonomy presented as an execution pipeline. This revision separates four structures that were merged, and is organised around them. The list of stages in Rev. 1 §4 no longer exists in that form.

---

## 0. How to read this

| | meaning |
|---|---|
| **LOCKED** | Derived from a locked semantic claim, or survived a named attack in the appendices. A proposal must defeat the derivation or the test. |
| **WORKING MODEL** | Best current explanation. Used as a default; expected to change. |
| **OPEN** | Deliberately unsolved. |

Nothing here is locked because it is elegant. Three patterns were considered and partly rejected on evidence — a single generation call (§3), a canonical-state-plus-actions model (§12), and Rev. 1's own linear pipeline (Appendix C). All three rejections are recorded rather than assumed.

**Altitude.** Decision decomposition, execution topology, commitment, state and invalidation. No storage design, no schema, no framework, no prompt design, no agent topology. Those remain downstream, for the same reason the semantics kept architecture downstream of vocabulary.

### What changed from Rev. 1

| Rev. 1 claim | Status now | Broken by |
|---|---|---|
| One pipeline, nine stages | **Replaced** by four structures (§2) | Appendix C |
| Composition is one stage | Split: ingestion (conditional) vs derivation | C |
| Projection is one stage | Split: relevance · traversal · consequence | C |
| Structure then Treatment | Jointly resolved execution unit | C |
| Render is terminal | Split: configuration vs layout feasibility | prior review |
| "Node identity is the primary key" | **Wrong.** Four-level identity (§9) | B1 |
| Verification is not a stage | Reframed: a gate on the lifecycle structure (§6) | prior review |
| "One round, fixed tiebreak" | Replaced by the challenge principle (§5) | prior review |
| Composition keyed by subject | **Wrong.** Subject × frame (§8) | B5 |
| Verification results keyed to coverage | **Wrong.** Coverage + assumed entry (§6) | B3 |
| Every transition gets the full protocol | **Over-claimed.** Gates have an admission rule (§6) | C |

---

## 1. The thesis — LOCKED

> **The architecture makes no educational decisions. It decides what gets decided, when it runs, where it commits, and what a correction costs.**

The product's premise is that the LLM is the educational decision-maker: for each piece of knowledge it reasons about what communicates it best. A structure like this one *looks* like a rules engine and must not become one.

The resolution: **a decision is not a rule. A decision is one judgment, made by the model, separated out because it can be wrong on its own.** The architecture chooses the seams and supplies the evidence. It never supplies the answer.

---

## 2. Four structures — LOCKED

The central claim of this revision.

```
DECISION TAXONOMY    what judgments exist
                     admission: can it be SEPARATELY CORRECTABLE?

EXECUTION TOPOLOGY   when and how those judgments run
                     admission: must they RESOLVE JOINTLY under a shared constraint?

LIFECYCLE            where a result becomes committed
                     admission: does anything EXTERNALLY RELY on it?

INVALIDATION         what goes stale when a judgment changes
                     keyed to DECISIONS, never to execution units
```

**Four different admission rules.** Rev. 1 had one and used it for all four, which is why its stage list simultaneously over-merged (Projection bundled three separately-correctable judgments) and over-split (Structure and Treatment cannot be finalised apart).

Nothing guarantees the four structures have the same shape, and in the tested cases they demonstrably do not.

### How they interact without collapsing — LOCKED

Three rules keep them separate, and each one prevents a specific failure.

**Execution coupling is not dependency coupling.** Two decisions sharing an execution unit are not thereby dependent. Structure and Treatment resolve jointly; a treatment change invalidates the sectioning **only if the sectioning actually depended on it**. Collapse this and every correction invalidates its whole unit, and the cost model — the reason the architecture exists — is wrong.

**Gates sit on results, not on positions.** A lifecycle gate is admitted by external reliance (§6), not by where something falls in the topology. Some decisions run early and are gated; others run late and are not.

**Invalidation traverses the decision graph.** Execution topology is a *scheduling* fact. It never appears in an invalidation edge.

---

## 3. Decision taxonomy

### The decisions — WORKING MODEL

Fourteen currently. **The count is not the finding**; the classification is. Rev. 1's nine were what backend development happened to require.

| | Decision | Applies |
|---|---|---|
| 0 | **Intake strategy** — what to ask next | universal · see below |
| 1 | **Situation interpretation** — purpose, entry, target, capacity | universal |
| 2 | **Frame selection** — jurisdiction, school, standard, version | **conditional** — multi-frame subjects only |
| 3 | **Source ingestion** — read an authoritative structure | **conditional** — only where source material exists |
| 4 | **Structure derivation** — what concepts exist, what is built from what | universal |
| 5 | **Relevance** — what is in play for this situation | universal · **source varies** |
| 6 | **Traversal** — teachable order | universal |
| 7 | **Consequence** — what omitting each thing costs | universal |
| 8 | **Scope** — depth allocation and the cut | universal · budget moves conditional on capacity |
| 9 | **Partition** — how in-scope material divides | universal · may resolve to one member |
| 10 | **Section** — documents, sections, presentation order | universal |
| 11 | **Representation** — which prose-failure applies (§13) | universal |
| 12 | **Draft** — the content | universal |
| 13 | **Render configuration** — template, visual vocabulary, packaging | universal |
| 14 | **Layout feasibility** — does the treatment survive the page | universal |

### Conditionality is a first-class property — LOCKED

> **Source ingestion must not imply that every request has an ingestion phase.**

Backend development has no authoritative source: there is no document that says what backend development *is*. The Indian Contract Act is a numbered statute — a primary source that is **read, not derived**. Different operation, different failure modes, no convergence condition, no promotion question.

Three kinds of conditionality, and they are not the same:

```
CONDITIONAL ON SUBJECT     ingestion · frame selection
                           present only when the subject has sources or frames

CONDITIONAL ON SOURCE      relevance is DERIVED for backend,
                           GIVEN for a syllabus — same decision, different evidence

CONDITIONAL ON SITUATION   budget moves fire only when capacity is stated
                           and exceeded (§11)
```

**Relevance is the important one.** It is universal as a decision and variable in where its evidence comes from. Treating "supplied by an authority" as a different decision would double the taxonomy; treating it as the same decision with a different source keeps the invalidation edges intact.

### Two things that are not decisions — LOCKED

**Intake strategy** is listed as decision 0 because it is a genuine judgment and can be wrong. But it is the only one whose output is *evidence* rather than a derived claim about the artifact, and it belongs to a loop rather than to the artifact's derivation. Everything downstream consumes its *product*, never the decision itself.

**Verification is not a decision.** It produces no claim that another decision consumes as input. It belongs to the lifecycle structure (§6), where it is first-class. Rev. 1 said "not a stage" while having only one structure to say it in, which read as "not important" and would lead to under-building it.

---

## 4. Execution topology

### The admission rule — LOCKED

> **Decisions belong in one execution unit when they must resolve jointly under a shared constraint** — neither can be finalised without the other's value.

This is a different question from separate correctability, and it produces a different answer.

### The topology — WORKING MODEL

```
intake loop                              iterated · terminates on sufficiency
        ↓
situation interpretation
        ↓
frame selection                          conditional
        ↓
ingest sources    ∥    derive structure  parallel · ingestion conditional
        ↓
relevance                                derived, or supplied by authority
        ↓
traversal         ∥    consequence       parallel · independent evidence
        ↓
scope  +  partition                      JOINT
        ↓
   ┌────┴────┬─────────┐                 fan-out, per member
   ▼         ▼         ▼
section + representation                 JOINT
        ↓
      draft
   └────┬────┴─────────┘
        ▼
render configuration → layout feasibility
```

Three things Rev. 1's line could not express: **parallelism** (traversal and consequence share no evidence), **joint resolution**, and **conditional presence**.

### What "joint" means, precisely — LOCKED

`+` is not vagueness. It is a defined arrangement, and it must preserve both facts about its members — separately correctable, jointly resolvable.

> A **joint execution unit** produces its member decisions within one resolution against a shared constraint, and emits **one decision record per member decision**, each carrying which of its siblings actually constrained it.
>
> Re-deriving one member **re-enters the unit with the others pinned** as constraints.

That answers the four questions directly:

| | |
|---|---|
| One model call, or iterative exchange? | Either. Not architecturally significant — the constraint is that neither is *finalised* before the other. |
| Joint plan or separate records? | **Separate records, always.** This is what keeps invalidation at decision level (§7). |
| Can one be recomputed alone? | Yes — by re-entering the unit with the sibling pinned. |
| Does changing one invalidate the other? | **Only if that record says it constrained it.** Recorded per resolution, never assumed from the unit. |

### The two joint units, and their shared constraints — LOCKED

**Section + Representation** share the sectioning choice itself. Five sub-doctrines across four dimensions: the comparison table is either the payload — one section built round it — or a summary after five subsections. You cannot choose the sectioning without knowing the representation, and you cannot choose the representation without knowing whether it is payload or summary. For comparison-heavy material this is the normal case, not an exception.

**Scope + Partition** share capacity and the completion conditions. Under capacity pressure, what to cut depends on what members exist, because dropping a leaf *member* is a scope move at member granularity. The cut and the boundaries are mutually determining.

Both survive the decision-admission rule separately: *"the order violates a dependency"* is a Section error with representation fine; *"that should have been a table"* is the reverse.

### Why Rev. 1 missed this — LOCKED

Backend development is mechanism-heavy, so dependency order does most of the sectioning for you, and Section→Representation *looked* sequential. Appendix C is the standing record of that, because the failure is not obvious and a future revision could regress into it silently.

### Downstream challenge, not downstream ownership — LOCKED

Replaces Rev. 1's "one round, fixed tiebreak," which was an operational parameter wearing the clothes of a principle.

> **Downstream work may challenge an upstream assumption. It never owns the upstream decision.**

Section reveals that derived extent exceeds capacity; it does not set scope. Representation reveals that a table obliges thirty cells; it does not expand coverage. In both cases the signal travels up, and the upstream decision-holder resolves it — by expanding, reducing, changing representation, or reporting infeasibility (§14).

A bound on reconsideration cycles is still required — a principle without one is an unbounded loop in production — but it is an **operational parameter, deliberately unfixed here**.

---

## 5. Lifecycle

### The admission rule for gates — WORKING MODEL

Stated positively, as the counterpart to §3's rule for decisions.

> **A lifecycle gate exists where a result becomes externally relied upon:** a user approves it, another project consumes it, or an error in it becomes materially more expensive to correct once downstream work has proceeded.

Three sources of reliance, and they are independent.

| Gate | Reliance |
|---|---|
| **Plan** — situation interpretation, scope, partition, order, extent, exclusions | user approval |
| **Demo** — treatment policy | user approval |
| **Draft** — correctness | cost asymmetry; a wrong legal claim shipped is not recoverable by editing |
| **Layout** | cost asymmetry; cheap now, expensive after packaging |
| **Promotion** into a shared asset | other projects consume it (§8) |

**Not gated:** traversal, consequence, derived relevance, render configuration. Internal, cheap to redo, nothing relies on them. Rev. 1's claim that every transition takes the full protocol was over-claimed.

### The protocol — WORKING MODEL

```
derive → candidate → verify → commit
                          └── reject, routed to a decision (§7)
```

### Four states, not two — LOCKED

```
candidate     derived, not yet through its gate
committed     through its gate; relied upon
superseded    committed under a premise that has since moved — still valid as delivered
dirty         derived from something that changed, never committed
```

**Superseded is the one Rev. 1 lacked**, and it is load-bearing. When a learner switches from "build things" to "interview prep," the already-committed databases member is not wrong and may be reusable unchanged. Collapsing it into *dirty* rebuilds work nobody asked to rebuild.

### Commitments are self-describing — LOCKED

> A commitment is a **standalone snapshot**, not a set of pointers into shared state. It carries the concept names, the exclusions and their stated reasons as its own content, and *links* to asset ids for re-derivation.

Forced by B1. The user approved a *meaning* — "covers caching, excludes distributed caching, here is why" — not a node id. Store it as pointers and asset drift silently changes what was approved, which §12 of the semantics forbids.

This is also the resolution of an internal contradiction in Rev. 1: §10 separated committed from live derivations, and §9 then gave them one storage discipline.

### Commitment is per-member and ordered — LOCKED

Forced by B3. Member 1 commits standalone; member 5 commits only given committed 1–4 — because §10's partition rule makes assumed entry a function of predecessors. **One relation, two uses:** the predecessor relation that governs partition legality also governs commitment order.

---

## 6. Verification

Belongs to the lifecycle structure. Not a decision (§3), and not merely routing (Rev. 1's under-framing).

### It splits in two — LOCKED

§4 of the semantics locked that sufficiency and efficiency are only partially verifiable, and that verification is "a reader model, not an assertion suite."

```
MECHANICAL   cheap · deterministic · always on
             connectivity — nothing referenced before it is defined
             nothing below entry · nothing beyond target
             every table cell filled
             every marked gap carries its consequence and its when-to-learn

JUDGMENT     expensive · sampled · a simulated reader at the stated entry point
             can this reader FOLLOW it     structural sufficiency
             can this reader ACT on it     practical sufficiency
```

### The correctness gate — LOCKED

§4 of the semantics locked correctness as a gate, not a criterion — architecturally, exactly a gate on a state transition rather than a score. Its budget is allocated by **consequence severity**, which decision 7 already computed. Same signal, second use.

### Results are keyed to coverage **and** assumed entry — LOCKED

Rev. 1 said coverage alone. B3 breaks that: members 5–6 were verified against a reader who has completed member 4. If member 4 fails, their passes were earned against a false premise even though their content is untouched.

> A predecessor change invalidates a successor's verification result even when nothing in the successor changed.

### A check that cannot name a decision is not actionable — LOCKED

It should not be written. Verification's output is a verdict plus a target in the decision graph.

---

## 7. Invalidation topology

**Keyed to decisions. Never to execution units.** This is the rule that makes the four-structure separation pay.

### Execution coupling ≠ dependency coupling — LOCKED

Section and Representation share a unit. Changing the representation of one node invalidates the sectioning **only when that decision record says the sectioning depended on it**. Promoting a table from summary to payload does; adding a worked example inside an existing section does not.

Consequently the joint resolution must **record which sibling constrained which**. Decision records are not only provenance — they carry dependency edges that could not be known in advance.

### The dependency graph — WORKING MODEL

```
situation ────────→ frame · relevance · traversal · consequence · scope · representation
frame ────────────→ structure derivation · relevance
ingestion ────────→ structure derivation · relevance
structure ────────→ relevance · traversal · consequence
relevance ────────→ traversal · consequence · scope
traversal ────────→ scope · section
consequence ──────→ scope · verification budget
scope ────────────→ partition
partition ────────→ section · representation · commitment order
section ↔ representation      recorded per resolution, never assumed
representation ───→ draft
draft ────────────→ render configuration
render config ────→ layout feasibility
layout feasibility ──challenge──→ representation
```

**The line that matters most is still the first, in what it omits:** a situation change does not invalidate structure derivation. "Actually I'm advanced" re-projects; it does not rebuild the subject. That seam is what makes the product economically viable, and it exists because §10 of the semantics is locked.

### Invalidate ≠ regenerate — LOCKED

Invalidation produces **dirty state that persists**. It does not schedule a model call. Corrections accumulate, regeneration costs money, the user may change their mind again, and some rebuilds need approval first.

### In-flight work — LOCKED

A derivation whose inputs changed mid-flight stores its result under a hash nobody will look up again. Cancel it or let it finish; correctness does not depend on which. This falls out of the memoisation choice in §12 and is the strongest evidence for it.

### Corrections enter through resolution, not through the pipeline — LOCKED

```
user feedback → intent resolution → meaning classification (§8) → target decision
              → invalidate dependent region → dirty → re-derivation plan → gate
```

A correction is not a stage. It is a routing operation over the decision graph.

---

## 8. Assets

### Composition is keyed by subject × frame — LOCKED

Rev. 1 said subject. B5 breaks it: *"a contract requires consideration"* is true in common law and false in civil law; the money→inflation mechanism differs by school; DSM-IV and DSM-5 disagree about subtype relations. These are **constitutive relations that vary** — not by learner situation, but by jurisdiction, school, or standard version.

```
parallel frames        jurisdictions — assets sit side by side, a project selects one
disagreement as
  content              teaching that two schools disagree needs a `contested_by`
                       relation IN the asset
authority versions     DSM-IV vs DSM-5 — a frame indexed by time
```

Backend development has exactly one frame, which is why the key looked like "subject."

**Frame selection is the first situational input that binds composition itself**, and it enlarges the semantics' open external-authority question: *"the Indian Contract Act"* does not merely supply coverage — it selects the frame.

### Relations are typed; the vocabulary is open — LOCKED

"HTTP runs on TCP," "an ORM emits SQL," "an index is implemented as a B-tree" are three relations, not one. Enumerating the vocabulary now would repeat the error §15 exists to prevent — and had Rev. 1's single edge type been locked, B5 would have broken §8 outright rather than only its key.

### What is stable, and what is projected — LOCKED

| stable — a property of the subject × frame | projected — a property of the traversal |
|---|---|
| concepts exist | prerequisite order |
| typed constitutive relations | difficulty *for this learner* |
| dense regions | centrality |
| names and aliases | presentation order |
| | module cuts |
| | omission consequence |
| | granularity — the resolution the graph is read at |

**Test that established it (A1).** Does TCP come before HTTP? Absent for a first application, usually present for a bottom-up syllabus, conditional for interviews. An edge cannot be present and absent for the same subject, so two relations were merged: **constitutive** (a fact about the subject) and **traversal** (a fact about a projection).

> §10 of the semantics locks that the situation projects *consequence* onto the graph. It also projects *prerequisite*. The projection does more work than §10 credits it with.

### The asset test — LOCKED

> **Does this need to be stable and correctable, or can the model supply it inline?**

The model knows the concepts; what it does not do is produce a stable, complete, consistent decomposition on demand — ask twice, get two graphs, with no way to accumulate a correction. That, not knowledge, is what an asset is for.

Run the test on the four candidates from Rev. 1:

| Candidate | Verdict |
|---|---|
| **Composition** | **asset today.** Fails to be stable when model-supplied. |
| **Conventions** — syllabi, certification requirements | **not an asset — an authority.** A syllabus is a document the user supplies, not model knowledge. See the semantics' open question. |
| **Misconceptions** | model-supplied for now. Becomes an asset when we want it correctable. |
| **Treatment patterns** | **OPEN.** No data, no representation of effectiveness, no evidence it generalises across subject, level, job and purpose. |

### Exploration reads; it never writes — LOCKED

Rev. 1's "Composition and Projection are a fixpoint" named a mathematical property and called it an answer, while contradicting its own promotion rule.

```
shared asset (read-only)  +  situation
            ↓
   project-local exploration
            ↓
   candidate graph  ─────→  relevance · traversal · consequence
            ↓
   discovered candidates ──→ promotion proposal (gated, §5)
```

**Convergence:** the frontier stops producing candidates that relevance rates in play. It terminates because the candidate set grows monotonically against a fixed situation. A hard expansion limit is a safety net, not the stopping condition.

### Promotion requires a situation-free adjudicator — LOCKED

Additions merge trivially. **Retypes conflict** — two projects can disagree about an existing edge's type. That disagreement is modelling imprecision, not situational variance, so §8's stable/projected split survives; but somebody must adjudicate, and it cannot be a project.

> Every decision in §3 is situation-conditioned by construction. Promotion review is the only operation that must **not** be — which makes it a different kind of actor from anything else in the architecture.

### Assets evolve; commitments reconcile — LOCKED

v7→v12 does not only add. It **splits**, **merges**, and **retypes**, and no id discipline survives all three. Pinning a project forever defeats the return visit that justifies persistence at all; re-projecting silently violates §12 of the semantics.

Because commitments are self-describing snapshots (§5), drift produces a **reconciliation report** — *"two concepts you excluded were split; one you covered was merged"* — rather than silent semantic change.

---

## 9. Identity — LOCKED

Rev. 1 said composition node ids are the primary key for everything. That is wrong: one concept appears in several members, at several resolutions, in several roles.

```
asset version      which subject × frame snapshot
concept id         a node in that asset
instance id        this concept, at this resolution, in this project
placement id       where it sits — member, section, and in what role
block id           the realised passage
decision record    the judgment that produced any of the above
```

Each structure keys to a different level: scope and relevance to **instances**, section and representation to **placements**, draft to **blocks**, verification to **placements plus their entry premise**, invalidation to **decision records**.

Split and merge break concept-id continuity by construction, which is why §8 requires reconciliation rather than an id-stability promise that cannot be kept.

---

## 10. Partition

Survived both rounds of attack unchanged.

### Legality — LOCKED

> A partition is legal iff every member is complete by its own job's completion condition, given the assumed entry its predecessors supply, and the union covers the target.

No coupling metric, no threshold. This is the same test as set-versus-pile: partition legality and set validity are one rule. And the predecessor relation it defines also governs commitment order (§5).

### Necessity — LOCKED

**A job change forces a boundary.** §6 of the semantics locked that the five jobs have different completion conditions; a document that is 60% construct and 40% look-up is complete by neither standard.

Tested against a hard case: a construct document ending in a syntax appendix is two artifacts in one file — and the rule correctly predicts the appendix should be indexed for retrieval rather than ordered pedagogically.

**Known dependency:** if "practice" is a sixth job, every chapter with exercises becomes a two-artifact set, which is absurd. This assumes exercises are a *representation* — failure mode 7 (§13) — not a job.

### Not a reason to partition — LOCKED

**Length.** Splitting a tight chain for size yields "Part 1 / Part 2," which is packaging, not a set. A set member is complete on its own terms; Part 1 of a chain is a document with an interior cut — broken rather than compressed.

### Granularity — WORKING MODEL

> A member should correspond to a capability the learner would exercise on its own.

Purpose-relative, as §5 of the semantics requires. It makes *"why is caching a separate module?"* answerable rather than a matter of taste.

### Three boundaries — LOCKED

```
SCOPE       what is in at all
PARTITION   how in-scope material divides
PACKAGING   how artifacts become files      — render configuration
```

A proposed fourth, *curriculum boundary*, dies: "what domain are we covering" is the scope decision under another name. **Artifact boundaries and file boundaries are not the same thing.**

---

## 11. Capacity, extent, and budget — LOCKED

From the semantics at Rev. 3: **capacity** is an optional user constraint; **extent** is derived and reported. Budget pressure is the gap.

```
derive extent per member from its own situation → sum → report
        no stated capacity        →  build it; report the scale
        stated capacity exceeded  →  the budget-pressure moves apply
```

Never `capacity ÷ members`. Sizes emerge from what each capability requires.

**Reporting scale is an obligation.** The semantics locked that the system must speak when the target does not fit; the inverse holds when the plan is far larger than the learner expects.

**Not derived:** whether the budget-pressure transformations lift from the concept graph to the member graph. Structurally analogous, but a member is not a concept node. See §16.

---

## 12. Mutation — WORKING MODEL

A canonical-state-plus-actions model was evaluated and partly rejected on one structural difference: there, `apply(state, action)` is pure, cheap, total and deterministic because the workspace is *authored* state. Almost all of ours is **derived** — expensive, non-deterministic, and capable of regressing.

The surviving requirement is not "actions are the only mutation language." It is:

> Every meaningful change must be explicit, attributable, and invalidate only the work that actually depends on it.

Two mechanisms satisfy it, not one.

```
STRUCTURAL   pure · cheap · deterministic · fully unit-testable
             set_capacity · drop_member · reorder · set_template

DERIVATION   expensive · non-deterministic · can fail · can regress
             not a recorded command but a recorded RESULT:
             inputs hash + model + prompt version + params → output
             memoisation, not a command log
```

**User intents compile down.** The user must never hand-edit composition nodes; §1 of the semantics forbids pushing subject design onto the learner. But they do say *"you missed distributed caching."* One engine, two vocabularies.

**Reproducibility, in the only form available.** The model cannot be made deterministic. Recording each derivation's inputs makes state **replayable without re-running anything** — enough for debugging, diffing and evaluation.

### The seven state categories — WORKING MODEL

| | Category | Rule |
|---|---|---|
| 1 | **Testimony** — raw utterances, explicit user decisions | never derived; permanent; the only thing derived from nothing |
| 2 | **Shared assets** | cross-project; read-only to projects; promoted through a gate |
| 3 | **Committed derivations** | self-describing snapshots; superseded rather than silently changed |
| 4 | **Live derivations** | freely recomputable; memoised by input hash |
| 5 | **Decision records** | small, structured, carry dependency edges; highest provenance value |
| 6 | **Bulk output** | large, regenerable, lowest historical value |
| 7 | **Commitments** | events; they change the mutability of what precedes them |

**Testimony is state, not input.** Every downstream decision is an *interpretation* of what the user said; when it is wrong, the original words are needed to reinterpret.

**Rejections are evidence.** *"Why isn't X in here?"* is among the likeliest user questions. Discard what exploration considered and dropped and it cannot be answered.

**Provenance value runs inverse to volume.** The most valuable retained thing is the smallest — which prose-failure fired on which node and why. That is the evidence §4 of the semantics needs to ever learn which treatments work.

**Persistence is justified by the return visit.** A one-shot project would keep its artifacts and discard the rest.

---

## 13. Representation sizes the visual vocabulary — WORKING MODEL

§14 of the semantics blocked architecture on Q2. This is the unblock.

**Prose is the default carrier; every other representation is a departure licensed by a specific, nameable failure of prose.** The diagnosis selects the representation — the author does not choose freely. That is what prevents decoration.

| Prose failure | Diagnostic | Licenses |
|---|---|---|
| **cross-reference** | can you name both axes? | table / comparison matrix |
| **topology** | must the reader repeatedly reconnect distant parts? | graph, flow |
| **parallel state** | do two actors evolve at once? | sequence, swimlane, timeline |
| **perceptual referent** | is the thing itself spatial or visual? | image |
| **abstraction grounding** | can they restate it but not recognise or produce it? | worked example, code |
| **procedure execution** | can they read it but not run it? | trace with state shown |
| **false comprehension** | is it easy to accept while holding a wrong model? | counter-example, failing case, exercise |

**Perceptual referent is diagnosable and probably unservable.** If we cannot produce anatomical figures, the correct response is to report the limitation — infeasibility must be reported — not to substitute a diagram that answers a different failure.

**The diagnostic runs at more than one granularity.** A recap figure is topology failure at *document* scale.

**Mix is a document-level property**, which is an argument for a document-level pass that decision 11 does not currently have. See §16.

---

## 14. Obligations — LOCKED

Not features. Consequences of locked semantics, requiring first-class paths rather than error handling.

| Behaviour | Forced by |
|---|---|
| Report infeasibility — artifact type cannot be honoured | §1 of the semantics |
| Report derived extent — including when far larger than expected | §11 |
| Report deliberate omissions — boundary, consequence, when to learn it | §12 of the semantics |
| Propose a smaller target — when the compression floor does not fit | §9 of the semantics |
| Report reconciliation — what asset drift changed under a commitment | §8 |
| **Defend a scope decision** — the user is wrong and complying damages the artifact | **no semantic home yet** |

The last has no semantic backing and is a gap, not a design. **The deliberate-omission report is where scope judgment becomes visible** — if that is a differentiator, this is the surface on which a user sees it.

---

## 15. What this document does not contain

No storage design, schema, database, framework, prompt design, agent topology, queueing, concurrency model, or deployment shape.

An elaborate schema is earned by a settled vocabulary. Ours is not settled: Q4 is half-open, three questions were added to the semantics at Rev. 3, and a sixth job would change §10.

> **Copy the shape, not the depth.** The shape is what makes an architecture production-grade. The schema is what makes it premature.

---

## 16. Open questions

```
—    the decision taxonomy is fourteen because of two tested subjects.
     A third subject class — a craft skill, a language, a body of
     practice with no source and no frame — may add or remove.
     Do not treat the list as closed.

—    granularity: the composition asset must be readable at several
     resolutions. How a graph supports that without becoming two
     graphs is unresolved.

—    external authorities: a syllabus supplies relevance AND selects a
     frame. What else can they constrain — depth, terminology,
     ordering, assessment expectations? Blocks the semantics' open
     question, and §8 now enlarges it.

—    defending scope: a real product behaviour with no semantic home.
     When is the right answer to a correction to refuse it?

—    do budget-pressure transformations lift from the concept graph to
     the member graph? NOT DERIVED.

—    which member absorbs the loss when a set exceeds capacity?
     A3 of the semantics selects the MOVE per member; it does not
     order members against each other.

—    is Draft one decision or two? Node-by-node generation has a
     cross-node coherence problem mirroring the representation-mix
     problem in §13. A document-level pass would be decision 15.

—    the reconsideration bound (§4) is deliberately unfixed. It must
     exist; its value is an operational parameter.

—    promotion adjudication: §8 establishes the adjudicator must be
     situation-free. It does not say what one is.

—    threshold calibration in §13: cross-reference must fire on
     5 items × 6 dimensions and not on two items on one dimension.
     No principled line yet.

—    a frame that changes mid-flight — a student who discovers their
     syllabus follows a different standard than assumed. Untested.
```

---

# Appendix A — structural tests

### A1 — Composition and traversal are different relations

One subject, three projects: **backend development**, for a first application · for interviews · for a university syllabus.

`TCP → HTTP` is absent for the first, usually present for the third, conditional for the second. An edge cannot be present and absent for the same subject, so two relations were merged (§8).

Confirmed on further pairs: `transactions → isolation levels` is both; `SQL → ORM` is constitutive always and traversal only for interviews; `B-tree → index` is constitutive always and irrelevant for a first application.

**Independent confirmation:** every property that varied across the three projects turned out to be projection, and the constitutive relations never contradicted each other — only the selection, the resolution and the order changed.

### A2 — The monolith is defeated by correctability

A single generation call has a real advantage — perfect context, nothing lost at seams. Q5 defeats it: "change the colour" must not regenerate the scope, and a monolith can only regenerate. Verifiability and reuse are supporting arguments; this one is close to decisive alone.

Its advantage yields the governing rule: **every seam loses context, so separate only where a rule in §2 forces it.**

### A3 — Partition reproduces four intuitions from two rules

| | jobs | standalone capabilities | result |
|---|---|---|---|
| SVM cheatsheet | 1 | 1 | one artifact |
| Deep-learning foundations, overlong | 1 | 1 | **one artifact, two files** |
| Backend development | many | many | a set |
| Deep learning | many | many | a set |

No page counts anywhere. Row 2 is the discriminating one: length alone does not create an artifact.

### A4 — One correction, seven meanings

"You missed distributed caching" resolves to seven faults across five decisions, of which two are promotable and one requires refusing the correction.

| | Meaning | Fault in |
|---|---|---|
| 1 | not in the graph at all | **structure derivation** — promotable |
| 2 | present, rated not in play | relevance |
| 3 | in play, cut for capacity | scope — possibly correct, badly communicated |
| 4 | covered under an unrecognised name | aliases — promotable |
| 5 | too shallow to register | depth allocation |
| 6 | their target is not what we inferred | **situation** |
| 7 | genuinely out of scope; the user is wrong | nothing — §14 |

The structure/relevance split earns its keep here for a reason unrelated to caching: it distinguishes *we did not know about it* from *we knew and judged it not in play*. Merged, those are indistinguishable — and they are different bugs with different fixes.

---

# Appendix B — state evolution tests

Five cases chosen to stress time, concurrency, partial failure and subject disagreement. **No abstraction broke at the root; four keys and one cardinality did.**

### B1 — Asset evolution across project time

Project commits at asset v7; asset reaches v12; user returns months later. v7→v12 **splits** (`caching` → local + distributed), **merges** (`sessions` + `cookies`), and **retypes** edges. No id promise survives all three.

Pinning defeats the return visit that justifies persistence at all. Re-projecting violates §12 of the semantics. **Result:** commitments must be self-describing snapshots (§5), and drift produces reconciliation (§8), not silent change. Rev. 1's "node identity is the primary key" is false.

### B2 — Correction during generation

Six members: 1–2 committed, 3 drafting, 4 verifying, 5–6 queued. The user changes purpose.

In-flight work is already handled — memo keys make an abandoned derivation harmless (§7). What broke is the **state model**: members 1–2 are committed *and* their premise moved. **Result:** four states, with `superseded` distinct from `dirty` (§5).

### B3 — Partial verification failure

Member 4 fails; the rest pass. But §10's corollary makes assumed entry a function of predecessors, so members 5–6 were verified against a reader who completed member 4. Their passes were earned against a false premise.

**Result:** verification results are keyed to coverage **and** assumed entry (§6); commitment is per-member but ordered by partition's own predecessor relation (§5).

### B4 — Concurrent discovery and promotion

Two projects discover different missing concepts; a third proposes retyping an existing edge. Additions merge; **retypes conflict.**

The threat to §8 — that a contested relation means constitutive relations are situational — does not land: "an ORM emits SQL" is a fact about ORMs, not about a learner. Disagreement is modelling imprecision. **Result:** §8 survives; promotion requires a **situation-free adjudicator**, which is a kind of actor nothing else in the architecture is.

### B5 — Contested or evolving subject structure

Common law vs civil law on consideration; monetarist vs post-Keynesian on inflation; DSM-IV vs DSM-5 on subtypes. Constitutive relations that vary — not by learner situation, but by jurisdiction, school, or version.

**Result:** §8 survives; **its key does not.** Composition is keyed by subject × frame. Note that had Rev. 1's single constitutive edge type been locked, this case would have broken §8 outright rather than only its key.

---

# Appendix C — the pipeline test

> **Standing warning.** Rev. 1's linear pipeline was an artifact of testing on backend development, which is unusually mechanism-heavy. Any future revision that reintroduces a single sequential stage list must first defeat this case. It is preserved for that reason.

**Case:** *"I need to learn the Indian Contract Act for my university exam in six weeks."* Traced from request to delivery without forcing it through Rev. 1's stages. The subject **names its own frame** in the first four words.

### C1 — Composition is two operations, and one is not a derivation

The Act has three structures, not one graph at three resolutions:

```
STATUTORY   §§1–238, chaptered, numbered, authoritative — a SOURCE DOCUMENT
DOCTRINAL   offer · acceptance · consideration · capacity · free consent
            does NOT follow section order — consideration is §2(d) and §25
CASE LAW    which judgments interpret which sections, and which bind
```

The statutory structure is **ingested, not derived**: no judgment about what exists, no convergence condition, no promotion question. Backend has no source document, so ingestion and derivation collapsed into one box.

### C2 — Projection fails the decision-admission rule

Four outputs with **different evidence sources**: relevance is *given by the syllabus*; traversal comes from doctrine; difficulty and consequence from the learner. And they are separately correctable — *"§230 isn't on our syllabus"* / *"you taught privity before consideration"* / *"you treated mistake as low-consequence"* are three bugs with three fixes.

By §3's own rule that is not one decision. Execution consequence the single box hid: relevance resolves first, after which traversal and consequence **run in parallel**.

### C3 — Section and Representation are jointly resolved

*Free consent* — coercion, undue influence, fraud, misrepresentation, mistake: five sub-doctrines across four dimensions. Representation diagnoses cross-reference failure and proposes a table. Section asks: five subsections, or one section built round the table?

**Same decision.** You cannot section it without knowing the representation, nor choose the representation without knowing whether it is payload or summary. For comparison-heavy material this is the normal case.

They remain separately correctable, which is what forces §4's joint-unit definition rather than a merge.

### C4 — The lifecycle protocol is not universal

Nobody approves a traversal order; it is internal and cheap to redo. Scope is approved. A draft asserting law incorrectly is not recoverable by editing. Three different answers in one project — which forces the positive admission rule for gates in §5.

### C5 — What survived

**Representation → Draft is genuinely sequential.** Representation decides *that* a worked example is needed; Draft decides *which case*, knowing what reads well.

**Partition survives**, and A3's rules reproduce the right answer: construct the doctrines, retrieve sections and cases for the exam, look up a section reference — three jobs, therefore a set.

### C6 — The rule Rev. 1 was missing

```
DECISION ADMISSION    distinct when SEPARATELY CORRECTABLE
EXECUTION BOUNDARY    one unit when they must RESOLVE JOINTLY
```

Two criteria, two structures, and nothing guarantees they agree. Section and Representation are separately correctable *and* jointly resolvable; so are Scope and Partition. Backend hid this because dependency order does most of the sectioning for you when the material is mechanism-heavy.
