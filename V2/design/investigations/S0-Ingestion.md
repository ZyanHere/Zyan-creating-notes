# §0 — Ingestion / External Sources

A deep read of one section. **No design, no domain model, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

---

## 1. What "ingestion" means for MyNotes

Not "let users upload files." Concretely, from the specs:

**`Foundation.md` §3 (LOCKED)** `[OBSERVED]`:

> *"A real request rarely has one source of truth, and the sources will disagree.
> 'Notes for B.Tech 5th-semester Operating Systems' may involve a university
> syllabus, the professor's slides, a textbook, previous-year papers, and the
> student's own notes. **For this product's core users that is the normal case, not
> an edge case.**"*

So the product's founding user base — semester exams, GATE, university subjects —
is the population for whom this matters most. That is a product claim, already locked,
not something to re-derive.

**But it is conditional, and the spec says so.** `[OBSERVED]` `System-Design.md` §3:

> *"Retrieval is conditional — INVARIANT … present for a statute or syllabus, absent
> for backend development, which has no authoritative source. **Retrieval is a branch,
> not a spine.** A project with no sources never touches it."*

The gating concept is **`Foundation.md` §3.2's three scope-authority tiers**, and this
is the most useful thing in the section:

| Tier | Example | Scope is |
|---|---|---|
| **Documented** | syllabus, exam blueprint, certification outline | *given and verifiable* |
| **Consensus** | SDE interviews, standard ML interviews | known by a community, recoverable |
| **Asserted** | "roadmap to Senior SDE" | the model's own judgment — *"weakest tier, must be labelled"* |

**In our own corpus** `[MEASURED]`: `contract-act-authority` is **documented**.
`agentic-ai-interview`, `dsa-graphs-interview`, `ml-weekend-conflict` are
**consensus**. `git-commits-narrow`, `transformers-deep`, `consensus-analogies` are
**asserted**. `french-revolution-exam`, `heart-anatomy-visual`, `vlsi-underspecified`
are documented-in-principle (a class-9 syllabus, a NEET syllabus, a university
scheme) but **no document was supplied**.

So: **1 of 10 cases has a real authority in play, and 3 more would if the user
brought one.** That is the honest size of the problem — not marginal, not dominant.

**What ingestion is *for*, stated once:** to give the system something outside its own
output to check the plan against. Everything else follows from that.

---

## 2. What exists today

### Specified, in detail

`[OBSERVED]` The design work is **done and locked**; only the code is missing.

**`Foundation.md` §3.1 — claim-specific authority, LOCKED.** Four independent scores
plus recency:

```
source.authority = { scope, factual, terminology, assessment }
source.recency   = published_at
```

With a profile table: a syllabus is **high** on scope and **low** on factual; a
textbook is the reverse; professor slides are **high** on terminology; past papers are
**high** on assessment. *"A conflict is resolved by asking which kind of claim is
this?, then consulting the source that scores highest on that dimension — never by
ranking documents wholesale. Ties break on recency."* And §10 explicitly kills the
alternative: *"~~A single `authority_tier` per source~~ — Authority is claim-specific."*

**`Foundation.md` §3.3 — the Knowledge and Source layer**: source chunks
(retrievable), extracted terminology, syllabus→topic mappings, canonical diagrams,
verified content fragments, prior approved Specs. *"Accumulated from usage and
uploads, not hand-curated per domain."*

**`System-Design.md` §6 — two conditional decision signatures:**
```
select_frame(subject, situation, candidates) -> Frame | None      # conditional
ingest_sources(sources)                      -> SourceStructure   # conditional
derive_structure(subject, frame, frontier)   -> CandidateGraph
```
Note the third line: **`derive_structure` already takes a `frame`.** The spec places
frame selection and ingestion *before* derivation.

**`System-Design.md` §9** — `POST /projects/:id/sources   multipart   [conditional]`.

**`System-Design.md` invariant 8** — *"A commitment pins its whole derivation
environment … model, prompt version, taxonomy version, asset version, **source
versions**."* So ingestion must produce a version identity.

**`System-Design.md` §7** — a named reliability class: *"**source-grounded** — as
reliable as the source; claim checked against a cited authority; **the only class that
can support a legal or medical claim**."*

**`Build-Spec.md` §1** — conditional decisions as applicability branches:
```
def ingest_sources(env: Envelope) -> SourceStructure | NotApplicable | Infeasible
```
> *"The invariant is that a conditional capability is **never silently skipped** — not
> that it always throws. A subject can *have* authoritative sources that a
> *particular artifact* does not require."*

Plus named tests: `test_conditional.py::test_not_applicable_is_a_recorded_output`,
`::test_unsupported_surfaces_in_plan`.

### Implemented

**Nothing.** `[OBSERVED]` A search across `agent/*.py` and `backend/*.py` for
`class Source`, `authority`, `Frame`, `frame` returns **zero matches**. `select_frame`
and `ingest_sources` return zero matches anywhere. No upload endpoint, no
`UploadFile`, no `source` field, no `syllabus` handling.

### Specified but absent — the gap, precisely

Every artefact in the previous subsection. Fifteen decision kinds are specified;
**eight are implemented** (the persisted kinds are `interpret_situation`,
`intake_strategy`, `derive_structure`, `relevance`, `scope`, `partition`, `traversal`,
`consequence`). `select_frame` and `ingest_sources` are not among them — and
**`Build-Spec.md` §1 claims all fifteen are implemented.** `[OBSERVED]` The spec is
wrong about its own status.

### Where source information can currently enter

One path only, and it is not a source path. `[OBSERVED]`

Free text in an utterance → `interpret_situation` → `StatedConstraint(text, axis)` →
attributed to **one of eight axes**: `subject`, `purpose`, `entry_point`,
`target_capability`, `capacity`, `depth_register`, `artifact_type`, `template`.

**None of those axes is about a source, a document, or an ordering.**
`Product-Semantics.md` has no source axis, and its §13 lists this as OPEN
— see §4 below.

### What downstream currently assumes

`[OBSERVED]` That the model's own knowledge is the only source.
`agent/fulfilment.py:covers()` is normalized substring matching of a concept name
against generated text. The artifact is checked against the plan; **the plan is
checked against nothing.**

---

## 3. Problems the absence creates

### Measured

**Q6 — external-authority structure unrepresented.** `[MEASURED, n=1 of 1
opportunity]` The contract-act plan contains no section reference anywhere:
`Preliminary & Definitions`, not `ss. 1–2`.

**NEW — a stated traversal constraint was bound to the wrong axis.**
`[MEASURED, n=1]` This is the finding the benchmark could not expose, because the
harness records axis attributions and nothing compares them to a reference.

The user said **"section wise."** The reference calls it *"a stated constraint on
traversal, and it outranks any pedagogical ordering the planner would otherwise
prefer."* V1 recorded:

```
stated      : ['indian contract act 1872', 'for my law semester', 'section wise']
stated_axes : ['subject', 'purpose', 'depth_register']
```

**"section wise" → `depth_register`** — an axis that is `askable=False` and
*"biasing, not binding"* by locked policy. It also leaked into `artifact_type` as free
text (*"structured section-wise study notes"*), where it likewise binds nothing.

And `traversal` then produced a **derived** ordering, its own justification saying so:

> *"Follows the Act's **logical architecture**: formation prerequisites first, then
> vitiating factors that attack formation, then legality filters…"*

That is a pedagogical ordering with a pedagogical rationale, for a request that asked
for the statute's own. The decision exists (`traversal`); there is simply **no channel
by which a user statement can bind it.**

**Q5 is adjacent.** `[MEASURED, n=2]` The contract-act reference wants depth
concentrated *"where problem questions concentrate"* — that is **assessment
authority**, which only past papers can supply. V1 put 21 of 23 concepts at
`work through`.

**P1 — terminology survived without a source.** `[MEASURED]` V1 produced the Act's own
words unaided. So terminology authority is **valuable but not the urgent gap** — the
model already knows a well-known statute's vocabulary.

### Observed

- **No path exists to report "I should be reading a source and cannot."** `[OBSERVED]`
  Specified as `Infeasible`; absent.
- **The Asserted tier is never labelled.** `[OBSERVED]` Foundation: *"must be
  labelled, and the first thing a user should review."* Nothing labels it. A user
  cannot tell a scope derived from a syllabus from one the model invented.
- **Model-sourced content is not marked.** `[OBSERVED]` Foundation §3.1 requires it.
- **The §0→§1 dependency is unimplemented.** `[OBSERVED]` Foundation §3.2: *"Intake
  derives from this. Documented scope → do not ask for a syllabus. No documented scope
  → the syllabus is required and must be requested."* Intake has no such rule and no
  axis to hang it on.

### Strong inference

- **CC3 is caused here.** Verification is self-referential because there is no
  external referent to be non-self-referential *against*. Ingestion is the only stage
  that could change that.
- **The `source_grounded` reliability class is unreachable**, so the correctness gate
  that `Product-Semantics` LOCKS is unenforced for law, medicine and anything
  syllabus-bound.
- **Absence is silent, which is the expensive kind.** A plan for a documented subject
  and a plan for an asserted one are indistinguishable in the output. The user
  approving a 9-module contract-law curriculum has no signal that no statute was read.

### Unknown

- Would ingestion actually improve plans? `[UNKNOWN]` — never tested. It is plausible
  that a section list fixes Q6 and *worsens* Q1 by adding context noise.
- Does the four-score authority model survive contact with real documents? `[UNKNOWN]`
  It has never scored a real file.
- What fraction of real users would supply a source at all? `[UNKNOWN]`

---

## 4. What a source should be able to constrain

`Product-Semantics.md` §13 states this as **the open question**, in these words
`[OBSERVED]`:

> *"…can constrain the plan independently of the system's own projection — §1
> currently lists coverage as always system-decided. **Open on two counts: whether this
> is a new binding axis or a target stated by reference to a document, and what each
> kind of authority can actually constrain** (coverage, depth, terminology, ordering,
> assessment expectations, required capabilities)."*

So the question is live by design. Here is what the evidence supports, candidate by
candidate.

| Candidate | Verdict | Basis |
|---|---|---|
| **Coverage / scope** | **Strongest yes** | Foundation §3.2: documented scope is *"given and verifiable."* Q6: *"a missing section is a fact, not a judgment"* `[OBSERVED spec + MEASURED]` |
| **Ordering / traversal** | **Yes, and newly evidenced** | `traversal` is already a decision; "section wise" had nowhere to bind `[MEASURED]` |
| **Terminology** | Yes in principle, **low urgency** | Foundation §3.1 profile table; but P1 shows the model managed unaided `[OBSERVED + MEASURED]` |
| **Assessment structure / weightage** | Yes, and it reaches depth | Foundation: past papers score **high** on assessment. The reference derives depth from where problem questions concentrate `[OBSERVED]` |
| **Facts** | Yes, but entangled with §4 | The `source_grounded` class exists precisely for this `[OBSERVED]` |
| **Definitions** | Subset of terminology | `[INFERENCE]` |
| **Learning objectives** | Possibly — and it is interesting | Many syllabi state them. That would bind `target_capability`, an axis the user currently states themselves `[INFERENCE]` |
| **Depth (directly)** | **No** | Semantics §1 LOCKS depth *allocation* as system-decided. A source should reach depth **only through assessment weightage**, never set it `[INFERENCE from locked semantics]` |

### The distinction you asked for, and the spec already makes it

*"The source contains this"* ≠ *"the system should treat this as authoritative."*

**Foundation §3.1's profile table is exactly this distinction encoded.** A textbook
*contains* a chapter list — which is scope information — and scores **low** on scope
authority. A syllabus contains statements of fact and scores **low** on factual
authority. `[OBSERVED]`

So the architecture already separates the two, and the practical consequence is:
**ingestion must extract more than it is allowed to bind.** A parsed syllabus yields
scope, ordering, terminology and objectives; only some of those are authoritative from
that document. `[INFERENCE]`

One genuinely unresolved half: **is a source a new axis, or a target stated by
reference?** Evidence leans toward *neither is sufficient alone* `[INFERENCE]` — "here
is my syllabus" is a **binding constraint on coverage and ordering** (axis-like), while
"prepare me for GATE 2026" is a **target stated by reference to a document the user
does not possess** (reference-like, and needs the system to know what GATE 2026 is).
Those are different mechanisms.

---

## 5. Where ingestion sits

### What the spec already decides

`[OBSERVED]` `derive_structure(subject, frame, frontier)` takes a frame, and
`select_frame` precedes it. So the spec places frame selection and ingestion
**before derivation** — eagerly.

### The two shapes, and a third

**(a) Eager — `user → upload → ingest → plan`**
- *For:* derive gets the skeleton before inventing one, which is precisely Q6's fix.
  Scope becomes checkable at plan time. `traversal` can be bound.
- *Against:* the user must have the file at intake, processing cost is paid before any
  value is visible, and it is paid even when the artifact would not have needed it —
  the case Build-Spec §1 explicitly calls out.

**(b) Lazy — `user → plan → read the source when needed`**
- *For:* pays only for what is used; a source can arrive mid-conversation.
- *Against:* derive would have to run twice, or run against a landscape it must later
  reconcile — which is asset-drift reconciliation, the most expensive machinery in
  Architecture §8. And Q6 is a *derive-time* defect; lazy reading cannot fix it.

**(c) Two-phase** `[INFERENCE — mine, not the spec's]`
The two uses have different shapes and different costs:

| Use | Needs | Cost |
|---|---|---|
| scope · ordering · objectives | the document's **skeleton**: ordered, addressable units | small, once |
| facts · quotes · grounding | **passages** with locations, searchable | large, ongoing |

So: **eager structural read, lazy content read.** Scope and traversal get their
skeleton before derive; grounding retrieves passages only when a claim needs one. This
is not a compromise between (a) and (b) — it is the observation that they are two
different capabilities that the word "ingestion" conflates.

---

## 6. What "ingested" actually means

Reasoned from what downstream would consume, not from a generic pipeline.

**Required for the structural use — small:**
- **An ordered list of addressable units** — section numbers, chapter names, syllabus
  items. Ordered, because ordering is the constraint. Addressable, because *"a missing
  section is a fact"* only if you can name it.
- **The source's own terms for those units** — `Free Consent` not `Agreement validity
  factors`.
- **A version identity** — System-Design invariant 8 requires commitments to pin
  source versions. Without it, a re-read silently changes what was approved against.
- **An authority profile** — the four scores. Derived how is open: declared by the
  user, inferred from the document, or asked.

**Required only for grounding — large:**
- Retrievable passages with **locations** precise enough to cite. Foundation §3.3 says
  "source chunks (retrievable)"; the `source_grounded` class needs *"a cited
  authority."*

**Probably needed:**
- **Raw bytes retained** `[INFERENCE]` — by the same argument that made delivered PDF
  bytes an artifact: a re-extraction is not the thing that was read.
- **Per-unit weightage** where derivable (past papers → frequency) — this is the only
  route by which a source legitimately reaches depth.

**Probably not needed, and worth saying so:**
- Embeddings / a vector index for the structural use. An ordered list of ~10–75
  section names is a list, not a retrieval problem. `[INFERENCE]`
- A "structured outline" beyond the ordered unit list — the extra nesting buys nothing
  that scope and traversal can consume.

**The load-bearing conclusion:** the cheap half of ingestion delivers Q6, ordering,
and terminology. The expensive half delivers factual grounding. **Conflating them is
what makes ingestion look like a large project.** `[INFERENCE]`

---

## 7. When a source is absent

Build-Spec already types three outcomes `[OBSERVED]`:
`SourceStructure | NotApplicable | Infeasible`, under the invariant that *"a
conditional capability is never silently skipped."*

Mapped to the states you named, plus one more:

| State | What it means | What planning should know |
|---|---|---|
| **No source provided, none needed** | consensus or asserted tier | `NotApplicable` — recorded, and **the tier labelled** so the user sees scope is asserted |
| **No source provided, one is needed** | documented tier, nothing supplied | Foundation §3.2: *"the syllabus is required and must be requested"* — this is an **intake** obligation, and V1 has no axis for it |
| **Source exists, not processed** | upload pending or extraction failed | `Infeasible` — plan may proceed, but scope is unverified and must say so |
| **Unknown whether an authority exists** | the system has not determined the tier | **The actual V1 state for all 10 cases.** Tier is never computed, so this state is invisible |

The fourth row is the real finding. The reference asks it directly: *"Is there any
path by which the system could say 'I should be reading the statute and I cannot'?"*
**Answer: specified as `Infeasible`, and there is no path, because nothing ever asks
the tier question.** `[OBSERVED]`

---

## 8. What makes this ingestion rather than "more context"

Three capabilities, none of which dumping text into a prompt provides.

**1. Checkability.** Q6's sentence is the whole argument: *"A missing section is a
fact, not a judgment — unlike a missing concept in a derived landscape."* Text in
context gives the **model** more to read. An ingested unit list gives the **system**
something to compare a plan against. That is the only thing that converts CC3
(verification is self-referential) into verification against an external referent.
`[OBSERVED + INFERENCE]`

**2. Binding, not influencing.** *"Section wise"* in a prompt is a suggestion the
model weighs. A traversal constraint bound to an authority **outranks** the planner's
own preference. The measured failure in §3 is exactly the difference: the constraint
was present in the text, read correctly as a phrase, and bound to nothing.

**3. Attribution.** The `source_grounded` reliability class requires knowing *which
claim came from where*. A prompt-stuffed document produces text whose provenance is
unrecoverable — and Foundation requires model-sourced content to be *marked as such*,
which is impossible if everything arrives through one channel. `[OBSERVED]`

**Stated as a test:** if the only thing ingestion changes is what the model reads,
it has failed. It must change what the **system can refuse**.

---

## 9. Constraints and cross-section effects

**On §1 Intake** — the largest. A new binding channel (axis or stated-by-reference);
Foundation §3.2's ask/don't-ask rule, which requires the tier to be known *during*
intake; a file-upload surface in a conversational UI; authority profiles either
declared, inferred, or asked.

**On §2 Planning** — `derive_structure` gains a `frame` parameter it does not have;
scope becomes externally checkable; `traversal` becomes bindable; `relevance` gains
documented grounds for exclusion; assessment weightage becomes a legitimate input to
depth allocation.

**On §4 Generation** — grounding and citation; the `source_grounded` class; marking
model-sourced content.

**On §7 Storage** — source bytes, extracted structure, and **version identity**;
commitments must pin source versions (invariant 8); *"a shared composition asset built
from private sources is a real disclosure risk"* (System-Design §12).

**On §8 Deployment** — PDF/DOCX extraction is **another native dependency**, and
`Runtime-Dependencies.md` exists because the last one cost three rounds of diagnosis;
upload size limits; processing time moved out of the request path; egress if sources
arrive by URL.

**Not relevant to MyNotes, and worth excluding:** a general document-search product,
OCR of handwriting, multi-user source sharing (before auth exists), and real-time
source updates.

---

## 10. Solution directions — compared, not chosen

**A. Structural-only ingestion.** Extract an ordered, addressable unit list plus the
source's terms. No chunking, no retrieval, no grounding.
*Delivers:* Q6, ordering, terminology, checkable coverage. *Leaves:* factual grounding
untouched. *Cost:* small. *Risk:* extraction quality on real PDFs `[UNKNOWN]`.

**B. Structural + passage retrieval.** A, plus chunked searchable passages for
grounding and citation.
*Delivers:* everything specified, including `source_grounded`. *Cost:* the largest
option, and it lands a native dependency plus an index in §7/§8.

**C. User-typed structure.** The user pastes the syllabus or section list as text; no
file parsing at all.
*Delivers:* most of A. *Cost:* near zero. *Risk:* asks work of the user, which cuts
against the product thesis — though **pasting a syllabus is not the same as designing
a curriculum**, so the thesis may not actually object. `[INFERENCE]`

**D. No ingestion; declare the tier honestly.** Compute documented/consensus/asserted,
label it, and say plainly when scope is asserted.
*Delivers:* the labelling obligation Foundation already requires, and the fourth state
in §7. *Delivers nothing on checkability.* *Cost:* near zero. **This is the honest
baseline and the thing to beat** — it is also the only option that is strictly
required by an already-locked spec.

**E. Reference-by-name, no document.** For well-known authorities (the Indian Contract
Act, a GATE syllabus), ask the model for the unit list, then treat *that* as the
skeleton to check against.
*Delivers:* Q6's mechanism without any file handling. *Risk:* the referent is
model-generated, so it is not genuinely external — it converts a judgment into a
*fixed* judgment, which is weaker than a fact but stronger than nothing.
P1 is mild evidence it would work for famous statutes. `[INFERENCE]`

**F. Tier-first dispatch.** Determine the tier, then choose the cheapest sufficient
mechanism per project: asserted → D, consensus → D or E, documented-with-file → A or
B, documented-without-file → request it (§1).
*Delivers:* matches cost to need, and it is the shape `Build-Spec` §1's applicability
branch already implies. *Cost:* requires the tier decision to exist, which nothing
currently computes.

**What I am not doing here:** choosing. But the comparison has a clear structure —
**D is required by spec and nearly free; E is the cheapest thing that could deliver
Q6; B is the only one that reaches factual grounding; and F is the frame the others
sit inside.**

---

## What remains genuinely open after this investigation

1. **Axis or stated-by-reference?** Product-Semantics §13's first count. Evidence
   leans to *both mechanisms, for different situations* — not settled.
2. **Does a supplied skeleton improve plans, or add noise?** `[UNKNOWN]`, and it is
   testable cheaply: hand `derive` a section list for contract-act and compare against
   the reference. One case, a few calls.
3. **Who assigns authority scores?** Declared, inferred, or asked — no evidence.
4. **Extraction quality on real files.** `[UNKNOWN]` and it decides A vs C.
5. **Is the four-score model right?** Locked in Foundation, never tested against a real
   document. Worth flagging that a LOCKED decision here has zero implementation
   evidence behind it.
