# MyNotes V2 — Domain Model

**Rev. 4.1 — FROZEN.** Derived from the nine section investigations. Four review findings
applied in Rev. 4, two further inconsistencies found while checking them; **Rev. 4.1 adds
CF-8, found while deriving `Architecture.md`, and reclassifies OR-1 / OQ-3 as
non-blocking.** See §7 and §8.

**Not in this document:** architecture, APIs, schema, storage, jobs, prompts,
implementation, renderer, deployment. The renderer is **infrastructure outside the
domain**.

---

## 0. What this model is for

Across §1–§7 of the investigations, one pattern appears seven times:

> **V1 records judgments as free-form fields that nothing downstream depends on or
> checks.**

`job` is a string nothing branches on (Q1) · `feasibility` is computed and gates nothing
(A1) · `partition.covers` is never checked against `scope.covered` (A2) ·
`capability_unbacked` is computed and ignored (A6) · `diagnosis` is optional (A7) ·
`inputs_hash` is written and never read · `freshness` is declared and never set.

The model's job is **making relationships between judgments explicit and checkable.** V1
does this correctly in exactly one place — §5's guard, which compares `diagnosis` against
`realizes` and **raises**.

---

## 1. Three kinds of data, and who may refuse

| | What it is | Recomputable? |
|---|---|---|
| **Authoritative** | testimony, sources, approvals, delivered bytes | **no** — loss is loss |
| **Derived** | readings, structure, scope, curriculum decisions, document content | yes, at model cost |
| **Computed** | integrity, extent, feasibility, fulfilment, status, freshness, supersession | yes, deterministically, free |

**Three distinct acts, which Rev. 1 collapsed into the word "gate":**

**Automatic refusal** — the system declines without asking. Permitted **only** on a
deterministic check. The check may read derived fields freely; it may not itself be a
judgment.

**Human approval** — the user accepts or corrects derived decisions. **This is the
product.**

**Disclosure** — the system states something it will not refuse on, because it is a
trade-off the user can weigh rather than an error they cannot act on.

A1's defect is not that V1 gated on the wrong thing. It is that a deterministic fact was
computed and **neither refused on nor disclosed**.

---

## 2. Classification of every named concept

Complete, so architecture never has to guess whether something has identity. *(Review #2.)*

### Entities — identity, independently referenced, independently correctable

| | Identity | Owned by |
|---|---|---|
| `Project` | assigned | — |
| `Utterance` | assigned + ordinal | `Project` |
| `Source` | assigned + version | `Project` |
| `Decision` | `(project, kind, member?)` | `Project` |
| `DecisionVersion` | assigned, immutable | `Decision` |
| `Commitment` | assigned | `Project` |
| `Concept` | **assigned, with aliases** — not its name | `SubjectStructure` |
| `Module` | **assigned, not positional** — see CF-6 | a `partition` `DecisionVersion` |
| `Section` | assigned | a `sections` `DecisionVersion` |
| `Document` | content identity | `Module` |
| `Artifact` | content identity | `Document` |

`SubjectStructure`, `Projection` and `Scope` are **entities only in the sense that each is
the subject of its own `Decision`** — their identity is the decision's. Where this document
names them, read "the output of that decision's current version."

### Value objects — no identity; defined by their values, replaced rather than edited

`AxisReading` · `EvidenceSpan` (utterance ordinal + verbatim quote) · `Constraint` ·
`SubjectRef` · `Relation` (typed, directed, between two `Concept`s) · `Coverage` · `Cut` ·
`Ordering` · `Block` and its kinds · `Licence` · `Authority`

### Classifications — closed vocabularies

`Job` (5) · `Depth` (3) · `Strength` (4) · `Materiality` (3) · `RelationType` (5) ·
`ProseFailure` (7 + escape) · `ScopeTier` (3) · **`Target`** (what a `Constraint` may bind)

### Payloads of a `DecisionVersion` — **not objects with identity**

- **`Situation`** — the output payload of the `situation` decision: `{AxisReading per axis}`
  + `{Constraint}` + `SubjectRef`. **It has no identity of its own**; its identity is the
  version's. V1 treats it as a thing, which is why correcting one axis rewrites all of them.
- **`Job`** — the output payload of its **own** `Decision` (CF-2), because it can
  independently be wrong (measured 2 of 3) and must be independently correctable.

### Collective terms — **not objects at all**

- **`Curriculum`** — a convenient name for `{Module*} + Ordering`, which are outputs of two
  different decisions. Treating it as an object is how V1's `Partition` ended up holding
  both `modules` and legacy `units` in one place.
- **`Content`** — the `Block`s a `Document` carries. Not an entity. A partially-generated
  document is **process state**, not a domain object.

---

## 3. The layers

### Layer 1 — Evidence (authoritative)

**`Utterance`** — append-only, never edited, never derived. Authoritative as a **record of
what was said**, not as truth: what was said may be mistaken, self-contradictory, or a
change of mind. Authoritative about **provenance**; silent about fact. That is what lets a
`Constraint` cite an `EvidenceSpan` and remain a *reading*.

**`Source`** — external material, **optional**. Carries `Authority`: **claim-specific
standing** (Foundation §3.1, LOCKED) — independent scores for *scope*, *factual*,
*terminology*, *assessment*, plus recency. §0's point: **what a source contains is not what
it is authoritative for.**

**`ScopeTier`** — `documented | consensus | asserted`, a property of *subject × situation*.
It decides whether a source is **needed**. `asserted` must be visible (Foundation: *"the
first thing a user should review"*). V1 never computes it, which is why *"no source
exists"* and *"we never asked"* are indistinguishable.

### Layer 2 — Situation

**`AxisReading`** — one per axis: `value`, `strength`, `evidence` (`EvidenceSpan`s),
`materiality` (**three-valued**, resolving A8), `would_differ`.

**Readings travel with their confidence.** V1 hands planning the values and keeps confidence
elsewhere — so a plan built on a *guessed* entry point is indistinguishable from one built
on a *stated* one, for the axis the agentic reference calls *"not recoverable by any later
decision."*

**`Job`** — closed set of five (Product-Semantics §6, LOCKED), its own `Decision`.

**`Constraint`** — what the user said, and what it binds:
`Target ∈ axes ∪ { ordering, source, representation-preference }`. V1 binds to axes only,
which is why `"section wise"` landed on `depth_register`.

**`SubjectRef`** — identity plus frame, **not a prose restatement**. §2 measured breadth
tracking phrasing: `'agentic AI'` → 29 concepts; the 11-word restatement → 42.

### Layer 3 — Subject knowledge

**`SubjectStructure`** — `Concept`s and typed `Relation`s, keyed by **subject × frame**
(Architecture §8).

**`Projection`** — what is in play, with grounds.

```
Projection.judged = SubjectStructure.concepts              equality          S3
Projection.judged = in_play  ⊎  out_of_play                total, disjoint   S2b
```

### Layer 4 — The plan

**`Coverage`** — per in-play concept: `depth` and **`RepresentationNeed`** — which failure of
prose this concept's content is expected to hit. V1's `anticipates`, which §4 found **never
reaches the writer**.

**`Cut`** — `{concept, consequence, when_to_learn}` as **one value object**. V1 has
`scope.cut` (names only) and `consequence.exclusions` (the three parts) as two unlinked
lists, so a concept can be cut with no stated cost. As one object, that is
**inexpressible**.

```
Projection.in_play = Scope.covered  ⊎  Scope.cut            total, disjoint   S2
```

**`Module`** — title, `capability`, covered concepts, `why_here`. The test for modulehood is
`capability`: *"something the learner would exercise on its own."*

```
Scope.covered = ⊎ Module.covers          exact AND DISJOINT                  S1
```

**Module membership is exclusive.** *(Review #1 — Rev. 3's `⋃` contradicted its own prose.)*
Three pieces of evidence decide it rather than taste:

- `derive_extent` sums pages per module over its concepts. A concept in two modules
  **double-counts**, so the arithmetic already assumes exclusivity.
- V1's harness measures `duplicate_coverage` as a **defect class** (0 in all 11 records),
  which presumes duplicates are unwanted.
- One module becomes one document. Two documents both answerable for teaching a concept
  means the reader meets it twice and **neither module owns it** — and `capability` is
  precisely a claim of ownership.

*Covering* is being answerable for teaching. A module may freely **reference** a concept it
does not cover; that is prose, not coverage.

**`Section`** — resolving Q8. Ordered, named, covering one *or more* concepts, inside a
module. **A planning decision** — see Layer 5 for how a Document realizes it.

```
⋃ Section.covers = Module.covers         total; exclusivity OPEN (OR-1)       S4
```

**Why modules and sections differ**, since the asymmetry is deliberate: across modules,
duplication means two separate documents each claiming to teach the same thing. Within a
module, revisiting a concept in a later section is ordinary pedagogy, and `redundancy` is a
candidate dimension in Product-Semantics. Different situations, different rules.

**`Ordering`** — one per level (modules; sections within a module). References **member
identities**, not title strings, and carries a **basis**:
`derived-pedagogical | bound-by-constraint`. §0 measured `traversal.why` explaining *"the
Act's logical architecture"* for a request that said *"section wise."*

### Layer 5 — Document (renderer-independent)

**`Document`** — the complete, renderable, **engine-independent** whole for one module:
plan-derived front matter (`title`, `assumed_entry`, `target_capability`, marked gaps), and
the `Block`s for each of the module's committed sections, in order.

The evidence: V1 has this object, `engine/` is **test-forbidden from importing `agent`**
(verified in `tests/test_boundaries.py`), and the Document is persisted deliberately —
*"A template fix should not cost another generation."*

**`Document` realizes the planned sections; it does not redefine them.** *(Review #3.)* One
`Section` concept, not two:

- `Section` (plan) owns **identity, name, order, and which concepts it covers.**
- `Document` owns **the `Block`s**, addressed by section identity.

So blocks belong to the **Document**, not to the Section. Rev. 3 said *"a `Section` holds its
`Block`s"*, which put generated content on a planning object — and would have made the
planned section change every time the module was regenerated.

A Document is **immutable once complete**, and there may be **many per module over time**;
each references the sections of the `Commitment` it was generated against.

| | Owns | Does not own |
|---|---|---|
| `Section` (plan) | identity, name, order, covered concepts | any content |
| `Block` | what is said, and what kind of saying it is | where it sits |
| `Document` | all blocks, per section, plus front matter | how any of it looks |
| `Artifact` | bytes, pagination, resolved fonts, the engine | what it says |

### Blocks

**`Prose`** — the carrier. Every other block is a departure from it.

**`StructuralClaim`**:

> A block in which **the structural relationship among its parts is itself part of what is
> said.** Rearranging it changes the claim.

V1's words: *"Order is meaning, not layout."* `AI contains ML` and `input precedes hidden`
are different statements; drawing them identically asserts the wrong one. `Callout` is
exempt because *"it asserts no shape, order, containment or magnitude."*
Falsifiability-by-geometry is a **consequence** of the definition, and a useful test.
Ordinary prose makes claims too — what it cannot do is make a claim *by its arrangement*.

Carries a `RelationType` and ordered entities, and **never names a geometry**.

**`Presentation`** — formats without structural meaning: code, list, chips, headings.
*Open: `Table` — OR-2.*

**`Reference`** — names something it cannot show. V1's `Callout` with `realizes = False`, and
the only legal answer to a `perceptual-referent` need.

**`Licence`** — required on every `StructuralClaim`. A7 measured 6 of 36 departures with
none, because the field is optional and the guard fires only when present. **Vocabulary
stays open** for §5's reason: an enum *"would make the one interesting reading impossible: a
model that needed a failure the taxonomy does not list."* Seven named plus
`unlisted:<name>` — **required, with an escape.**

### `RepresentationNeed` and `Licence` — same vocabulary, different concepts

| | `RepresentationNeed` | `Licence` |
|---|---|---|
| attaches to | a **concept**, in `Coverage` | a **block**, in `Document` |
| says | *prose alone will not carry this* | *this departure exists because of this* |
| tense | prediction, content unwritten | justification, content written |
| cardinality | **one per concept** | **one per departing block; many per concept** |

Related by a **comparison** (`TreatmentAgreement`), not by identity. §4's finding is that V1
records both sides and never compares them.

### Layer 6 — Decisions, commitment, artifact

**`Decision`** — a slot for a judgment that can independently be wrong and be corrected,
identified by `(project, kind, member?)`.

**`DecisionVersion`** — one resolution. **Immutable.** Carries the output payload, the inputs
it was resolved against, its **recorded dependencies**, and its derivation environment
(model, prompt version, taxonomy version, source versions, structure version).

**`status`, `freshness` and `supersession` are computed relations, not fields:**

```
committed(v)   ⟺  some Commitment names v
stale(v)       ⟺  a recorded dependency of v has a newer version
superseded(d)  ⟺  a later Document exists for the same Module
superseded(a)  ⟺  a later Artifact exists for the same (Document, template)
```

*(Review #4 — Rev. 3 had an immutable `Artifact` with a `superseded_by` pointer, which would
require mutating it when a successor appears.)* Supersession needs no field and no new
object: it is a **computed relation**, the same pattern as `status` and `freshness`. Nothing
is written to the old artifact — which is the whole point of it being immutable, and what
makes *"my March document"* answerable.

**Rev. 4.1 — CF-8, found while deriving the architecture.** Rev. 4 keyed artifact
supersession on the **`Module`**, which contradicted this layer's own sentence *"the same
Document under a different template is a different artifact"*: rendering one document in a
second template would have marked the first superseded, when the two are **alternatives, not
successors**. Corrected to two relations at the levels where each question is actually asked
— *is this the current content?* (Document) and *is this the current rendering of that
content in that template?* (Artifact).

The artifact key is `(Document, template)` and deliberately **not** the full render
environment: a re-render after an engine or font upgrade **does** supersede its predecessor,
whereas a different template does not.

**`Commitment`** — **one per approval act.** Names the exact `DecisionVersion`s in force,
keyed by member where the decision is per-member (Architecture §5: *per-member and
ordered*). V1's counts decision *kinds*: `decision_count` was **exactly 7 in every record**,
for plans of 1 to 9 modules.

**`Artifact`** — bytes, **identified by content, immutable**: document identity + render
environment + bytes. §7's worst finding: V1 addresses a module's PDF by `slugify(title)`, so
a rename orphans it and a regeneration overwrites it. Many artifacts per Document — the same
Document under a different template is a different artifact.

---

## 4. Entity / relationship diagram

```
 AUTHORITATIVE
  Project ─┬─► Utterance*        append-only · authoritative as RECORD, not as truth
           ├─► Source*           optional · Authority per claim kind · versioned
           └─► Commitment*       1 per approval act · names exact DecisionVersions,
                                 keyed by member where the decision is per-member

 DECISIONS            every judgment below is a Decision, resolved as immutable
                      DecisionVersions.  Payloads have NO identity of their own.
  Decision(project, kind, member?) ──1:N──► DecisionVersion   immutable · deps recorded

   kind = situation   payload: {AxisReading + EvidenceSpan*} + {Constraint} + SubjectRef
   kind = job         payload: Job                                   own decision, CF-2
   kind = structure   payload: SubjectStructure{ Concept*, Relation* }   subject × frame
   kind = projection  payload: judged = SubjectStructure.concepts            S3  equality
                               judged = in_play ⊎ out_of_play                S2b total
   kind = scope       payload: in_play = covered ⊎ cut                       S2  total
                               Coverage{depth, RepresentationNeed}  1 per concept
                               Cut{concept, consequence, when_to_learn}
   kind = partition   payload: Module*   covered = ⊎ Module.covers           S1  DISJOINT
                               Module identity ASSIGNED, not positional      CF-6
   kind = sections    payload: Section*  ⋃ Section.covers = Module.covers    S4  total
                               exclusivity OPEN — OR-1
   kind = ordering    payload: Ordering  one per level · over identities · basis

 RENDERER-INDEPENDENT
  Module ──1:N over time──► Document      immutable when complete
                             ├─ front matter, from the plan
                             └─ Block* per committed Section, in order        (Review #3)
                                Block ∈ { Prose | StructuralClaim(+Licence)
                                        | Presentation | Reference }
       │
       ▼   ── INFRASTRUCTURE BOUNDARY: domain asks "can you serve this need?"; infra answers
       │
  Document ──1:N──► Artifact     bytes · content-addressed · immutable
                                 supersession is COMPUTED, never stored      (Review #4)
                                 keyed (Document, template), NOT Module      (CF-8)

 COMPUTED (functions, never fields)
  Integrity · Extent · Feasibility · Fulfilment · PromiseBacking · TreatmentAgreement
  status(v) · freshness(v) · superseded(a)
```

**The accounting chain — nothing may silently disappear:**

```
SubjectStructure.concepts = judged = in_play ⊎ out_of_play
                                    in_play = covered ⊎ cut
                                              covered = ⊎ Module.covers     ← disjoint
                                                        = ⋃ Section.covers
                                                          each Section ≥1 Block
```

Every concept that exists is judged; every judged one is in or out; every in-play one is
covered or cut-with-consequence; every covered one belongs to **exactly one** module and at
least one section; every section has content.

---

## 5. Invariants

### S — Structural (set membership and identity; mechanically decidable)

| # | Rule | Closes |
|---|---|---|
| **S1** | `Scope.covered = ⊎ Module.covers` — exact **and disjoint** | **A2**, duplicate coverage, Review #1 |
| **S2** | `Projection.in_play = Scope.covered ⊎ Scope.cut` — total, disjoint | silent omission |
| **S2b** | `Projection.judged = in_play ⊎ out_of_play` — total, disjoint | silent omission |
| **S3** | `Projection.judged = SubjectStructure.concepts` — equality | §2 |
| **S4** | `⋃ Section.covers = Module.covers` — total (exclusivity open, OR-1) | **Q8** |
| **S5** | `Ordering` is a bijection over member identities, one per level | §2 |
| **S6** | Every `StructuralClaim` carries a `Licence` | **A7** |
| **S7** | Every `Cut` carries a consequence and a when-to-learn | §2 |
| **S8** | `Job` is one of the five | **Q1** |
| **S9** | An `Artifact` is identified by content, never by a title | §7 |
| **S10** | A `Commitment` names exact `DecisionVersion`s, keyed by member | **B2** |
| **S11** | `Utterance` is append-only | V1 holds this |
| **S12** | Every `Section` has ≥1 `Block` in a Document; every `Module` ≥1 `Section` | silent omission |
| **S13** | A `DecisionVersion` is immutable | CF-5 |
| **S14** | `Module` and `Section` identity is **assigned, not positional** | **NEW — CF-6** |

### M — Semantic (require judgment; heuristic or judged, never arithmetic)

| # | Rule | How it can be checked |
|---|---|---|
| **M1** | Every `capability` clause is answerable by a concept in its module (**A6**) | heuristic today — V1's term-matching over semicolon-split clauses produced noise; a judge later |
| **M2** | A `Constraint` is honoured by the reading of the target it binds (§0) | partly structural (did the target change?), partly semantic |
| **M3** | A `Licence` is the failure the block actually answers | **not mechanically checkable** — §5: *"a model that labels the same block `topology` draws exactly the same false figure and passes"* |
| **M4** | `Fulfilment` means the content teaches the concept | V1 checks *mention* by substring; truth needs a `Source` or a judge |

### C — Computed (deterministic; never authored)

| # | Rule | Closes |
|---|---|---|
| **C1** | `Extent` is computed from calibrated density, never authored | **A4** |
| **C2** | `Feasibility` is computed from `RepresentationNeed` against what infrastructure declares | **A1** |
| **C3** | `Integrity` is the conjunction of S1–S7, S12, S14 | — |
| **C4** | `status`, `freshness` and `supersession` are computed, never stored | CF-5, Review #4 |

### H — Human approval and refusal

| # | Rule | Closes |
|---|---|---|
| **H1** | An `Integrity` violation **refuses approval automatically**, naming the decision that must change | **A1**, **A2** |
| **H2** | A `Feasibility` shortfall is **disclosed, never refused** | **A1** |
| **H3** | An `asserted` `ScopeTier` is disclosed | §0 |
| **H4** | Approval is over derived decisions, and is the only gate entitled to weigh judgment | §1 |
| **H5** | The system refuses automatically **only** on a deterministic check | §5's guard, generalised |

### X — Exemption

**X1** — a `perceptual-referent` `Licence` admits no realization; the only legal forms are a
`Reference` carrying that licence, or a corrected licence. **V1's guard implements this and
should be kept verbatim** — the one working instance of H5, and honest that it catches
self-contradiction only, never misdiagnosis (M3).

---

## 6. Lifecycle and state

**Principle: process state never becomes state of a domain object.**

| Transition | Object that changes | Version created | Must stay immutable |
|---|---|---|---|
| **intake** | `Utterance` appended | new versions of `situation` and `job` | all prior utterances and versions |
| **correction** | `Utterance` appended | new versions of **only the targeted** decisions | untargeted versions; all prior versions |
| **planning** | — | new versions of structure / projection / scope / partition / sections / ordering | everything before |
| **approval** | `Commitment` created | none | **every decision version** — `committed` is computed, not a mutation |
| **generation** | *nothing in the domain* | — | — |
| **document** | `Document` created **whole** | one per (module × generation) | the Document, forever |
| **artifact** | `Artifact` created **whole** | one per (document × render environment) | the Artifact, forever |
| **delivery** | *nothing* — an **event** | — | the Artifact |
| **supersession** | **nothing** — a computed relation | the successor already exists | the superseded artifact, untouched |

**Not domain state:** generation running / failed / retried, job identity, provider
attempts, render attempts.

**Decision status, as a computed view:**

```
                 current            stale
 candidate       candidate          dirty
 committed       committed          superseded
```

Invalidation produces `stale`, **never regeneration**: corrections accumulate, regeneration
is expensive, and the user may change their mind again.

**The plan gate** resolves §3's three coexisting readings in favour of the product sentence
— *what gets written is what you approved* — the **contract** reading:

- **Integrity violations are errors.** Refuse automatically and **name the decision that
  must change**, because *"placing a stranded concept would be a partition decision, and
  this layer must not make one."*
- **Feasibility shortfalls are trade-offs.** Disclose in the plan; let the user approve
  knowingly.

---

## 7. Consistency findings

### From this pass

| # | Finding | Resolution |
|---|---|---|
| **CF-6** | **`Module` and `Section` identity was never stated, and V1 uses position.** `_job_key(project_id, index)` keys generation by **index**, so a correction that re-partitions silently re-points "module 3" at different content — and `ml-weekend` went 5 modules → 3 in one correction. Per-member commitment (S10) and `Module → Document` are both meaningless without stable identity | **S14** — identity is assigned, not positional |
| **CF-7** | The `⊎` / `⋃` asymmetry between modules and sections was asserted, not justified | Justified in Layer 4: across modules, duplication means two documents each claiming ownership, and `capability` *is* an ownership claim; within a module, revisiting is ordinary pedagogy. **Strengthened while deriving the architecture:** the arithmetic reason is that `derive_extent` sums pages **per module**, so a shared concept double-counts — and extent is never computed per section, so section overlap breaks no arithmetic. That is why S1 must be disjoint and S4 need not be |
| **CF-8** | `superseded(a)` was keyed on the **`Module`**, contradicting *"the same Document under a different template is a different artifact"* — a second template would have superseded the first | Split into `superseded(d)` over Documents of a Module and `superseded(a)` over Artifacts of a **`(Document, template)`**. See Layer 6. Found while deriving the architecture, which is the intended way for this kind of error to surface |

### Carried from Rev. 3

**CF-1** `Content` is not an entity · **CF-2** `Job` is its own Decision ·
**CF-3** S2b and S12 closed the last silent-disappearance holes ·
**CF-4** `Module → Document` and `Document → Artifact` are both 1:N ·
**CF-5** `status`/`freshness` are computed, not fields

### Re-run of the four checks

**Entity completeness** — every transition in §6 is expressible with no unstated object.
`Situation` and `Job` are payloads; `Curriculum` and `Content` are collective terms;
supersession needed no object at all.

**Relationship consistency** — diagram, prose and invariants now agree on every cardinality
and every set relation. Review #1 was the last surviving instance of the Rev. 1 error class
(`⋃` in the invariant, "exactly one" in the prose); I checked each remaining relation
individually rather than by inspection.

**Invariant completeness** — the accounting chain closes with S1's disjointness, S2, S2b,
S3, S4 and S12. S14 closes identity. Semantic rules are separated from structural ones and
none is presented as arithmetic. No hypothesis appears in the invariant tables.

**Lifecycle consistency** — no process state remains on a domain object: `generating` is
gone (Rev. 2), `status`/`freshness` are computed (Rev. 3), and `superseded_by` is now
computed too (Rev. 4). Every transition names what is created and what must not change.

---

## 8. Open questions and hypotheses

### ~~Required before architecture~~ — reassessed in `Architecture.md` §0

Rev. 4 listed both as blocking. Having derived the architecture, **that was too strong on
both counts**, for specific reasons rather than convenience:

| | | Status |
|---|---|---|
| **OR-1** | May a concept belong to more than one `Section` in a module? | **Does not block.** Architecture consumes **totality** only (S4), which is what lets generation fan out per section and still guarantee the module's coverage. The block-addressing half was already settled by Review #3 — blocks belong to the `Document`, addressed by section identity. Exclusivity is a **plan-quality** question, measurable against the `redundancy` dimension |
| **OQ-3** | Is a source a **new axis** or a **target stated by reference**? | **Does not block.** Both mechanisms are already expressible here: `Constraint.Target` admits `source`, and `Source` is an authoritative entity with claim-specific `Authority`. A supplied syllabus and *"prepare me for GATE 2026"* both route through **source resolution** + **constraint binding**. What is open is intake's question vocabulary — a product decision |

### Can be deferred to architecture

| | | Why deferrable |
|---|---|---|
| **HY-3** | Is `SubjectStructure` stable enough to share across projects? | The domain already permits it (keyed subject × frame); whether V2 *does* is storage and versioning |
| **OQ-2** | What are the calibrated density constants? | `Extent` is computed either way. One data point: ~2.8 pages/concept vs V1's 1.0 |
| **HY-4** | Is subject phrasing causal for landscape breadth? | `SubjectRef` already removes free-text restatement |
| **OR-2** | Is `Table` a `Presentation` or a `StructuralClaim`? | Decides whether `Table` needs a `Licence`. A comparison table and a lookup table are different claims with one form, and the five jobs distinguish *retrieve* from *look up* on that basis |

### Genuinely optional

| | | |
|---|---|---|
| **HY-1** | Does `Job` constrain admissible depths and licences? | **An experiment, not a rule.** The only non-prompt route to Q1→Q2→Q5; §1 and §2 both recorded its effect as unpredictable. `Job`'s *membership* is S8 |
| **HY-2** | Does a supplied structural skeleton improve plans or add noise? | Testable on contract-act against the reference for a few calls |
| **OQ-1** | Where does factual correctness live? | `Fulfilment` verifies mention (M4). Nothing closes this without `Source`, and the product ships without it today |

---

## 9. Outside the domain

- **The renderer.** The domain states a `RepresentationNeed` and a `StructuralClaim`'s
  relation; infrastructure answers *can I serve this* and *which geometry tells this
  relation's truth*. §6 found V1's split already right for relations — and that three of
  four templates violate the honesty table by drawing `is-subset-of` and `precedes`
  identically. **An infrastructure defect, not a domain one.**
- **Storage, jobs, providers, transport, pagination, fonts.**
- **The capability declaration** — what this build can draw. Belongs with the renderer, is
  *read* by `Feasibility`. V1 keeps it in `agent/treatment.py`, the wrong side of the line.

---

## 10. Freeze assessment

**Rev. 4.1 — FROZEN.** One contradiction (CF-8) was found while deriving the architecture and
corrected in place; one justification (CF-7) was strengthened. Neither changes the shape of
the model. OR-1 and OQ-3 are reclassified as non-blocking above, with reasons.

*Original Rev. 4 assessment, retained:*

**Internally consistent. Ready to freeze once OR-1 and OQ-3 are answered.**

Four passes have now been run against this model. Rev. 2 corrected twelve findings, Rev. 3
five, Rev. 4 four raised plus two found while checking them — and the residue is shrinking
in kind, not just in count: Rev. 2's were conceptual (a missing entity, a wrong gating
rule), Rev. 4's were notational (`⋃` vs `⊎`, where blocks live, whether a pointer is a
field).

**Nothing remains that changes the shape of the model.** The two blocking questions are
product decisions answerable from the references and your own judgment, not from further
measurement:

- **OR-1** — section exclusivity. The evidence supports totality and is silent on
  uniqueness.
- **OQ-3** — source as axis or stated reference. Product-Semantics has it open on two
  counts and §0 concluded *both mechanisms, for different situations*.

Everything else is deferrable, or an experiment that should stay labelled as one.
