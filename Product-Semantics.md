# Product Semantics — Rev. 2

**4 Sep 2026 · supersedes the thesis sections of `Foundation.md` (Rev. 4)**

Web version: https://claude.ai/code/artifact/c9d25647-eaaa-48e6-b9e6-b492a7275d1e

This document records **product semantics only**. No architecture, no schema, no engine.

That separation is deliberate and it is the correction that produced this document. The previous attempt sized an architecture against a single benchmark PDF before the vocabulary was known, and every decision downstream came out too small — eight block types, one figure archetype, one template. The vocabulary is settled here first.

> **Changes in Rev. 2.** §2 is new: artifact type, template and learning situation are three separate layers, and *document job* was wrongly listed in §1 as something the user picks. §7 is new: the candidate artifact types. Purpose is no longer categorical. Everything else is unchanged.

---

## 0. How to read this

Every claim carries one of three statuses.

| | meaning |
|---|---|
| **LOCKED** | Stress-tested against concrete cases. A future proposal must defeat the test that established it, not merely disagree with it. The tests are in the appendix. |
| **WORKING MODEL** | The best current explanation. Used as a default; expected to change. |
| **OPEN** | Deliberately unsolved. Not an oversight. |

Nothing is locked because it sounds right. Each locked item names the case that forced it.

---

## 1. Where the product starts — LOCKED

> The product starts from the learner's **situation**, not from a requested document format.

The user can specify preferences and constraints. They cannot reliably specify the knowledge structure, coverage, sequencing, or treatment they need — that would require already understanding the subject.

This is a narrower claim than "the user cannot specify anything," and deliberately so. A user *can* say "I want interview questions" or "ten pages." The claim is that they shouldn't have to design the educational artifact.

### The situation, decomposed — LOCKED

Mixing these axes is what made the earlier taxonomy incoherent. They are separate.

| Axis | Set by | Force |
|---|---|---|
| Subject | user | binding |
| **Purpose** — what they must be able to do afterwards | user | binding; arbitrates every trade-off |
| Entry point — current capability relative to the subject | user | binding |
| Target capability | user, often implied by purpose | binding |
| Budget — time or pages | user | hard limit |
| Depth **register** — survey / working / rigorous | user | biasing |
| **Artifact type** — see §2 and §7 | user | binding unless infeasible, and infeasibility must be **reported** |
| **Template** — see §2 | user | biasing; constrains presentation only |
| | | |
| **Document job** — derived from artifact type, never chosen | **system** | |
| Coverage — what is in, what is out | **system** | |
| Depth **allocation** — which concepts get depth | **system** | |
| Structure — documents, sections, order | **system** | |
| Representation — prose, table, figure, example, code, exercise | **system** | |
| Set relations — how artifacts depend on each other | **system** | |

Two splits carry weight:

**Depth splits in two.** Register is a user preference; allocation is a system decision. Conflating them made "shallow but broad" look impossible. A user asking for rigorous notes is not asking for equal rigour everywhere — the system still decides where rigour is worth spending.

**Representation, not "block."** *Block* is implementation language. At product level the question is what the best representation of this knowledge is, and the candidates are prose, comparison, example, question, code, diagram, table, sequence, exercise.

### The artifact teaches; the product is not a tutor — LOCKED

The product produces artifacts that teach. It does not conduct an interactive teaching relationship. This bound keeps the product from drifting into tutoring.

---

## 2. The three layers

### The separation — LOCKED

```
1  ARTIFACT TYPE       what the user asks to have generated
                       long notes · Q&A · cheatsheet · flashcards …

2  TEMPLATE            how that artifact is visually structured
                       standard · diagram-supported · table-heavy · minimal academic …

3  LEARNING SITUATION  what the learner actually needs
                       topic · purpose · entry point · target · budget · depth
```

Collapsing these produced the incoherent original list, in which *Q&A* (an artifact type), *research-level* (a depth register) and *diagram-heavy* (a template) sat as peers. A user selects:

```
Artifact: Long notes
Template: Diagram-heavy
```

never `Artifact: Diagram-heavy notes`.

### Artifact type is a preset over a job — WORKING MODEL

Nobody picks "retrieve known material" off a menu. They pick **flashcards**.

> An **artifact type** is a named preset over (**job** × a few fixed coordinates). The job is what the system reasons with; the artifact type is what the user picks.

Like camera modes: *Portrait* and *Sports* are not different cameras, they are recognisable presets over aperture, shutter and ISO. Nobody wants to set aperture; everybody understands Portrait.

```
Long notes    →  construct · generous budget · present
Short notes   →  construct · tight budget · present
Flashcards    →  retrieve · atomic units · withheld
Q&A           →  retrieve · explanatory units · withheld
Cheatsheet    →  look up · intent-keyed
```

**Correction to Rev. 1:** §1's table listed *document job* as a user-set axis. That was wrong. The user picks an artifact type; **the system derives the job.**

This also explains why *long notes* and *short notes* can both be legitimate menu items while resolving to one job. They are two presets over construct that differ in budget, and both are names people recognise.

### A template constrains presentation, never content — LOCKED

A template may influence visual density, layout, visual treatment, and a general preference for graphical representation. It may **not** decide that a diagram belongs at a given point.

> **Long notes + diagram-heavy** must not insert meaningless diagrams. Where a diagram actually improves understanding remains a content decision (§8).

```
human digestion       naturally carries many diagrams
constitutional law    naturally carries very few
agentic AI            needs them at specific conceptual points only
```

The user should not have to know this, and should not have to request each diagram individually.

This follows from two already-locked claims — *silence is freedom* (§3) and *a representation earns its place by communicative value* (§8) — so it is locked by derivation rather than by a separate test.

**Templates are per-artifact-type sets, not a global list.** A cheatsheet's templates (standard reference, table-heavy, visual, formula-focused) are not long notes' templates (compact standard, visual summary, high-density revision). What varies, and how many exist, is **OPEN**.

### Reconstructing the situation

A request may begin from an artifact choice. That does not stop the system reasoning about the situation.

```
"Generate long notes on Agentic AI."

known    topic · artifact type · job · rough budget
unknown  entry point · purpose · target capability
```

**Purpose is not categorical — LOCKED.** Exam, interview and project are not the set. *"I've learned frontend and backend; Agentic AI is my next skill"* is a complete and valid purpose — upskilling — and forcing it into a bucket would distort the whole downstream chain.

**The target may not exist yet, and that is a legitimate state — LOCKED.** "Explore before deciding" is a real answer. The situation is something the system reconstructs and negotiates, not a form the user fills. A useful follow-up is *what do you want to be able to do with this afterwards* — with "I don't know yet" as an accepted answer that the product helps resolve.

**Ask only what materially changes the artifact — WORKING MODEL.**

> Extract everything the request already implies. Ask only questions whose answers would materially change the artifact.

For *"generate long notes on Agentic AI"*: entry point and target capability genuinely change the output, so those are worth one question. Nothing else on the axis table is.

---

## 3. Silence is freedom — LOCKED

> Anything the user did not mention is the system's decision, not a prohibition.

Not asking for diagrams does not mean no diagrams. Not mentioning tables does not forbid tables. Only stated constraints bind — and a stated negative ("no diagrams") binds as strongly as a stated positive.

---

## 4. What "good" means

### Correctness is a gate, not a criterion — LOCKED

A document that is wrong is not a worse document; it is not a document. Correctness does not trade against the criteria below — it disqualifies.

Correctness does not require every statement to come from an external source. It requires the final claim to be trustworthy enough for its use. How that is achieved is an implementation question.

### The three criteria — LOCKED

> A document is good when it gives this reader the **minimum sufficient treatment** to reach the target capability from their entry point:
> **sufficient** to actually get there, **efficient** in not spending attention on what does not contribute, **effective** in choosing treatments that work for this purpose.

"Shortest" was rejected as the objective. It optimises a proxy and would delete examples, intuition, reinforcement and visual explanation — the treatments that often make an artifact longer *and* substantially more effective.

### Sufficiency and efficiency are partially verifiable — LOCKED

Not fully checkable, and this matters for how verification must be built.

- **Sufficiency** — coverage of required capabilities is checkable. *Whether the treatment is enough for this reader to acquire the capability* is judgment.
- **Efficiency** — obvious waste is detectable (material below the entry point, beyond the target). Subtler waste is judgment: three explanations where one would work; a tangent that technically relates.

Verification is therefore a reader model, not an assertion suite.

### Effectiveness — WORKING MODEL

Effectiveness comes from three things, not one:

```
known-good treatment patterns
        +
matching to purpose and reader
        +
eventual evidence / feedback
```

The defensible form is *a system that knows which treatment tends to work for which learning situation* — not "a library of learning patterns." A pattern that works well in one situation may be poor in another; the matching is the substance.

---

## 5. Purpose is the arbiter — LOCKED

Where budget forces a choice between more explanation, more examples, more coverage or more practice, there is no universally correct allocation.

> **The same topic, budget and entry point can require different treatment depending on what the learner needs to be able to do.**

Established concretely: the same 5-page database document has its optimal budget strategy *reversed* between building and interview preparation. See Appendix A3.

---

## 6. The five document jobs

### Methodology — LOCKED

Categories are derived from what the reader is *doing with* the document, never from names.

> **Admission.** A distinct job exists when the reader is attempting a fundamentally different operation, producing a stable difference in the document's **unit**, **relation structure**, or **completion condition**.
>
> **Death.** A category dies when its identity is fully explained by existing jobs plus independent axes.

Two diagnostics support the admission rule but are not the definition:
- Changing depth cannot transform one job into another.
- Their sufficiency conditions have different shapes.

Prefer fewer real grammars to more plausible-sounding labels.

### The five — LOCKED (with one exception, below)

| Job | Reader operation | Unit | Relation structure | Completion condition |
|---|---|---|---|---|
| **Construct understanding** | build a model of how something works | a concept, developed | dependency graph | no gap in the chain |
| **Orient in a landscape** | build a map of what exists | a member + its placement | position within a set | no region missing |
| **Retrieve known material** | recover from internal memory | prompt → content | coverage of a source set | nothing needed is untriggered |
| **Look up while working** | locate in external memory | key → value | index: reachable from a held question | the things needed are present *and findable* |
| **Execute a procedure** | produce a result by steps | a step | strict sequence; state carries | every step present and verifiable |

Two further properties, derived rather than independent:

- **If incomplete:** construct and procedure **break**; orient, retrieve and look-up **degrade**. How strict sufficiency must be is a property of the job.
- **Redundancy changes sign:** deliberate reinforcement in construct; overlap is fine in retrieve; repetition is a *defect* in look-up.

### `Execute a procedure` is untested — OPEN

The other four survived a discriminating test. Procedure was never challenged against anything. It is in the table on plausibility, not on evidence.

It did contribute one independent finding: it needs a representation nothing else does — the **verification checkpoint** (*"you should now see X"*).

### `interaction` — discovered, unclassified — OPEN

Whether the answer is withheld (test) or adjacent (present) is a real parameter. It is **not** promoted to a peer of purpose, depth, budget and template, because it is not universally applicable: it is coherent for construct and retrieve, incoherent for look-up and orient.

Unresolved: is it a global input axis, a job-conditioned modifier, or a presentation mechanism? In a static document it behaves like layout, but it changes unit shape — a test prompt must be a well-formed question where a cue can be a bare label. Do not force it into an axis yet.

---

## 7. Candidate artifact types — OPEN

This is a **candidate list**, not a taxonomy. Nothing here has been through the mechanism test. It is organised by the job each resolves to, because that is what shows the structure.

| Job | Candidate artifact types |
|---|---|
| **construct** | Long notes · Short notes · One-page summary |
| **orient** | Landscape overview · Mind map / concept map \* · Comparison notes \* · Timeline notes \* |
| **retrieve** | Q&A · Flashcards · Question bank · Revision sheet |
| **look up** | Cheatsheet · Formula / reference sheet · Glossary |
| **execute a procedure** | Walkthrough / tutorial |
| **job unclear** | Problem set / worked exercises |

### Excluded, and why

| Excluded | Because it is |
|---|---|
| Research-level notes | a **depth register** — construct at rigorous. Nothing else distinguishes it. |
| Notes with diagrams · Diagram-heavy | a **template** |
| Fancy notes design | a **template** |

### Two things the list reveals

**`Execute a procedure` had no name.** Neither original list contained a walkthrough or tutorial, yet it is one of the five jobs and obviously a thing people want — *"set up a RAG pipeline, step by step."* The job model predicted a missing artifact type, which is mild evidence that the job model is doing real work.

**Problem set does not fit.** Worked exercises are not retrieval (the goal is skill, not recall), not construct (they do not explain), not procedure (there is no single result). This may be a **sixth job** — practice — or a representation that lives inside construct. A missing job is a larger error than a miscategorised artifact, so this is the higher-priority test.

### The three flagged candidates — OPEN

Mind map, comparison notes and timeline notes are each named after their **dominant representation**, which is the same category error that moved *diagram-heavy* to the template layer.

A template must not blindly dictate content. But "timeline notes" on calculus would force a nonsense timeline — exactly the failure that rule exists to prevent. Ask for a timeline and either the subject's relations are temporal, in which case orient produces one anyway, or they are not, in which case honouring the request produces something false.

Running the death rule on mind map: job = orient; presentation = single radial figure; completion condition = every concept connected, which *is* orient's condition. Fully explained by an existing job plus an existing axis, so it probably dies as an artifact type and lives as a presentation of orient.

Not asserted. The strongest argument for keeping it is that a mind map is a genuinely different *reading* experience, and that has not been tested.

---

## 8. Representation — LOCKED

> A representation earns its place when it communicates the intended idea **better than the alternatives** for this reader and this purpose.

Explicitly rejected: "a figure earns its place when the prose replacing it would be longer." Length is a proxy. A diagram can win even when the prose is shorter, because it makes a relationship instantly apprehensible.

**Comparison is a representation, not a job.** It appears wherever a difference matters. Its prominence in decision-oriented material is a fact about representation mix, not evidence of a distinct grammar.

---

## 9. Budget pressure

### Short notes are not a document kind — LOCKED

> "Short notes" is the **construct** job operating under a budget smaller than sufficiency wants.

Not *retrieve* — that is revision, and it differs by assumed entry: a revision sheet assumes prior exposure to *this specific material*, which is what licenses dropping every explanation and keeping only cues.

### Legal and illegal transformations — LOCKED

For **construct**, whose completion condition is connectivity:

```
LEGAL
  compress treatment          same concepts, less development
  remove genuine leaves       nothing downstream depends on them
  truncate the target         same start, stop earlier along the chain

ILLEGAL
  remove an interior node while claiming the same path
```

Not a heuristic — forced by the completion condition. A short document with a hole in the middle is not compressed, it is broken, and it fails differently from one that honestly stops earlier.

### Raising assumed entry is outside the sequence — LOCKED

Compressing, removing and truncating modify the **document**. Raising assumed entry modifies the **learner model**. A budget problem may not be solved by behaving as though the reader is someone else. It requires an explicit change to the stated learning situation.

### The sacrifice ordering — WORKING MODEL

One concrete case forced an inversion (Appendix A3):

```
generative target    (design, build, implement)
    needs depth per node   →   sacrifice breadth   →   truncate, remove leaves

recognition target   (discuss, evaluate, follow along)
    needs coverage         →   sacrifice depth     →   compress
```

Mechanism: compression is **not uniform damage**. It preferentially destroys the expensive treatments — worked examples, counter-examples, exercises — while definitions survive. Generative capability is built by examples. So compression attacks precisely what a generative target depends on.

Strong, but established on one situation. Not locked.

### The compression floor — WORKING MODEL; operational definition OPEN

> Compression may continue until the treatment no longer enables the intended learning transition for this reader and target.

Equivalently: the floor is where treatment stops supporting the *kind* of capability targeted. High for generative targets — one complete worked example is indivisible. Low for recognition targets — a definition plus a distinguishing feature may suffice.

**Open:** how to determine it operationally, rather than recognise it after the fact.

### When even the floor does not fit — LOCKED

The system must not silently pretend it delivered the original target. It must either state that the target does not fit the budget, or explicitly propose a smaller achievable target.

---

## 10. Omission consequence

The major new result of the Rev. 1 pass.

### It is a projection, not a node attribute — LOCKED

```
consequence(node | target, context)
```

Transactions are low-consequence for a single-user local notes app and extremely high-consequence for anything handling money. The dependency graph carries **structure**; the learning situation **projects consequence onto it**.

### Two independent importances — LOCKED

```
structural importance     if this node disappears, does the graph break?
consequence importance    if the learner never acquires it, what happens
                          when they attempt the target capability?
```

A node can be structurally optional and still severe to omit. Indexes and transactions are both leaves of the database dependency graph, and omitting them is not equally acceptable.

The property is **not** "safety-bearing." The same pattern appears in security, correctness, cost and compliance. *Omission consequence* is the general name.

### Candidate dimensions — WORKING MODEL

```
severity          how bad is the outcome
visibility        will the learner discover the gap
reversibility     can it be corrected once discovered
```

Illustrative shape, **not a literal formula**:

```
danger of omission  ≈  severity  ×  silence  ×  permanence
```

Any one of the three being favourable can rescue a node. The usable form:

> A node whose omission fails **loudly and reversibly** is a good omission candidate — reality supplies the lesson. A node whose omission fails **quietly** is not, because nothing will.

**Open:** whether these three are the right dimensions.

### Conditional consequence — OPEN

Some consequences depend on a decision the reader has not made yet. CSRF matters under cookie-based auth and is largely irrelevant under token auth. `consequence(node | target, context)` is therefore not always determined at planning time.

Current reading: where consequence is conditional on a downstream choice, the document owes the **condition** rather than the node. This is §12 again, so it may need no new machinery.

---

## 11. Structural vs practical sufficiency — LOCKED

```
structural sufficiency
    the knowledge structure required by the learning path is adequately connected
    → the reader can FOLLOW the document

practical sufficiency
    the learner can act toward the intended use without unacceptable omission
    consequences
    → the reader can ACT on it
```

### They fail independently — LOCKED

Both directions are real:

```
structurally complete, practically insufficient
    the 5-page database document with no transactions
    → understood correctly, still ships something unsafe

structurally incomplete, practically sufficient
    "always wrap writes in a transaction" with no isolation model
    → acts correctly without understanding why
```

The second cell is what most "best practices" documents are. So these are not a check and a stricter check — they are **different targets**.

### Which situations owe which — OPEN

Explicitly **not locked**: *"a recognition target owes structural only; a generative target owes practical."* Too broad. Some recognition material still needs practical safeguards; some generative learning happens in a deliberately safe environment where consequences differ.

---

## 12. The fifth budget move — mark the gap

### The mechanism — LOCKED

```
silent absence  →  explicitly named limitation  →  known boundary
```

Since **silence** is what makes omission dangerous, naming the boundary attacks exactly the dimension that made it so. It costs a line or two.

> *"This does not cover transactions. Concurrent writes to the schema you just designed can silently corrupt data. Cover it before this touches real users."*

Complete form: state the omitted boundary, its consequence, and when the reader must learn it.

### It does not make omission acceptable — LOCKED

> **Warning about a missing concept is not teaching the missing concept.**

Marking the gap is a fourth option in the budget strategy, not a licence:

```
teach the node
    or
omit the node
  + expose the boundary
  + state the consequence
  + state when the reader must learn it
```

Whether the second is acceptable still depends on the learning situation and the omission consequence. A high-severity, low-visibility, low-reversibility node may not be markable-and-omittable at all.

---

## 13. Open questions

```
Q2   what knowledge wants which representation?

Q4   when is one artifact insufficient, and what makes a set
     rather than a pile?

Q5   what decisions can the user correct, at what stage, and what does
     changing each one invalidate?
     ("change the colour" must not regenerate the scope;
      "you missed distributed caching" probably should)

—    problem set: a sixth job (practice), or a representation inside
     construct?                          HIGHEST PRIORITY — a missing job is
                                         a larger error than a miscategorised
                                         artifact

—    mind map, comparison notes, timeline notes: artifact types, or
     presentations of orient?

—    which templates exist per artifact type, and what varies between them?

—    interaction: global axis, job-conditioned modifier, or presentation?

—    compression floor: how is it operationally determined?

—    structural vs practical sufficiency: which situations owe which?

—    omission consequence: are severity, visibility and reversibility
     the right dimensions?

—    execute a procedure: never stress-tested. Is it real?
```

---

## 14. What this document deliberately does not contain

No architecture. No data model. No schema. No engine design. No block types, no template structure, no archetype library, no build plan.

Those are downstream of Q2 in particular — the archetype library cannot be sized until we know what knowledge wants visual representation. Sizing it earlier is the mistake this document exists to prevent.

---

## Appendix — the tests that did the work

A locked conclusion may be reopened by defeating its test, not by disagreeing with its conclusion.

### A1 — Orient survives as a distinct job

One subject, both jobs: **databases, for a backend developer.**

```
orient      relational · document · key-value · wide-column · graph ·
            time-series · vector — what each is for, where each sits

construct   storage engine · B-tree vs LSM · write-ahead log ·
            isolation levels · query planner · how an index is used
```

Deepening the orient document yields a *deeper survey*, never the construct document. Shallowing the construct document yields a vague account of B-trees, never the landscape.

**Mechanism:** depth operates *within* a unit; the job determines what the units are and how they relate. Construct's units are mechanisms related by dependency; orient's are members related by position.

**Independent confirmation:** sufficiency has different shapes — coverage over a set versus connectivity over a graph. They do not converge at any depth.

### A2 — Rehearse and recall are one job

If "test vs remind" were a job difference, the 2×2 it implies should have empty cells. It does not:

| | answer withheld | answer adjacent |
|---|---|---|
| drawn from **what will be asked** | interview Q&A | interview crib sheet |
| drawn from **what you studied** | flashcards | revision sheet |

All four are real artifacts. Both axes reduce to things already in the model — content source is determined by purpose; withholding is layout in a static document. The unit-shape difference (question vs bare label) is downstream of withholding, not independent of it.

**Result:** the pair merged into *retrieve known material*, and `interaction` was discovered.

### A3 — Purpose reverses the sacrifice ordering

Situation: beginner backend developer · databases · *design a simple application's database* · 5 pages. Full treatment is 15–20 pages, so a 3–4× squeeze.

| | what fits | what the reader can do |
|---|---|---|
| **A compress** | all 15 nodes at ~140 words | name every term; **design nothing** |
| **B remove leaves** | 8 nodes at ~280 words | explain the core; never seen a design |
| **C truncate** | 6 nodes at ~350 words **+ one full worked schema** | design a blog schema; no indexes, no transactions |

```
building        C > B > A
interview       A > B > C          reversed
```

For an interview the leaves *are* the material — replication, sharding, CAP, NoSQL is what gets asked. B deletes the highest-value content; C stops before anything interesting.

### A4 — Retrieve and look up are distinct

The developer's question is *"which method gives a default if the key is missing?"* — **they do not know the name.** So the document must provide a path from *intent* to *name*.

```
retrieve    the prompt is a CUE      works only because you encoded it
look up     the key is an ADDRESS    must be reachable from a question you hold
```

**Test:** re-index a revision sheet by intent and it does not become a cheatsheet — it becomes a badly incomplete one, because re-indexing cannot add what you never studied. The completion condition does not move under re-indexing.

### A5 — Omission consequence, across four domains

| node | domain | structural role | severity | visibility of the gap | reversibility | safe to omit? |
|---|---|---|---|---|---|---|
| password hashing | security | leaf | catastrophic | **none** — the app works | low once exposed | **never** |
| overfitting | correctness | leaf | high — conclusions wrong | **none** — the number looks great | high if caught | no |
| transactions | data | leaf | high | **none** | low | no |
| env config | deployment | near-interior | high | **total** — fails on first run | total | **yes** |
| indexes | performance | leaf | moderate | high — visibly slow | high | yes |
| schema shape at scale | data | interior | high | eventual | **low** | no |

**Env config** is the contrast case that earns *visibility* as an independent dimension: high severity, structurally near-interior, and still safe to omit — the reader hits it in five minutes and looks it up.

**Schema shape at scale** earns *reversibility* separately: it fails visibly, and is still not safe to omit, because by the time it is visible the fix means migrating live data.
