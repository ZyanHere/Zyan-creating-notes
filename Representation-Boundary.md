# Representation Boundary — Rev. 3 — FROZEN BASELINE

> **Frozen 2026-09-06.** This is the current working baseline. Do not extend it with
> further architecture. It is reopened by **an M1 implementation that contradicts it** —
> a measured result, not an argument. §13's open items stay open; they are not an
> invitation to keep designing.
>
> The instrument that can produce such a contradiction is M1 itself, now recording:
> the diagnosis alongside the realization that served it, unrendered blocks reported
> rather than dropped, and an overflow probe that measures against the paper. See the
> representation report in `backend/service.py`. What that instrument reports is the
> only admissible evidence against this document.

Where the LLM's educational decision stops and the engine's realization begins.

Rev. 1 worked eight cross-domain cases and proposed six families. Rev. 2 answered the
challenge to one of those merges; the challenge generalised into the governing rule of
§1. Rev. 3 settles the three items Rev. 2 left open — selection, the honesty table's
home, and document-level coherence — and admits a fifteenth decision.

Proposes no block types. Implements nothing.

---

## 0. What is actually broken

Not §13 of the Architecture. §13 is right, and already says most of this:

> Prose is the default carrier; every other representation is a departure licensed by a
> specific, nameable failure of prose. The diagnosis selects the representation.

Its `Licenses` column is already plural — *table / comparison matrix*, *graph, flow*,
*sequence, swimlane, timeline*. One intent, several realizations. The separation exists.

Three things are broken:

1. **`contracts.py` implements the right-hand column only.** The model names a
   realization (`kind: "table"`), the diagnosis that licensed it is discarded, and the
   engine never learns why it is drawing what it draws.
2. **The vocabulary was sized from one PDF, not from §13.** `StackDiagram` answers
   nothing §13 licenses; §13's topology licenses *graph, flow*. *Parallel state* and
   *perceptual referent* have no implementation at all.
3. **Nothing ever said what a renderer must be given.** That omission is what let a
   domain-shaped block list in, and it is what Rev. 2 closes.

---

## 1. The governing rule

Rev. 1 separated realization capabilities by what the renderer must know:

```
layout        geometry only            deterministic
notation      a notation engine        deterministic
computation   evaluate a function      deterministic
perception    world knowledge it lacks generative
```

That split is right but it was justified on the wrong axis. Determinism is not the point.
The point is what the reader ends up believing.

> **Assertion preservation — proposed LOCK.**
> A realization may present only propositions the specification asserts, and must
> present every proposition the specification marks as emphasis. Adding a proposition
> is a correctness failure, not a style choice.

This single rule does three jobs:

- It explains why layout, notation and computation are safe: their outputs are functions
  of asserted content, so preservation is *achievable* and statically checkable.
- It explains why perception is different in kind: E exists **precisely to add what the
  model could not specify**. It cannot satisfy the rule. That is its definition, not a
  defect to engineer away.
- It gives a test for whether two intents are the same — see §2 — which is what settles
  the containment/sequence question.

Correctness is a gate, not a criterion. Assertion preservation is how that gate reaches
the *figure*, which today it does not.

---

## 2. The distinctness test

Rev. 1 used one test: **can a single payload drive every realization the intent
licenses?** If not, the intent is two intents wearing a coat.

That test is necessary and not sufficient. The challenge to the containment/sequence
merge is correct, and it exposes the missing half:

> Both encode as nodes + typed edges. That is an implementation similarity. It does not
> make them the same semantic representation.

Right. Add a second test, which follows from §1:

**Test 1 — payload sufficiency.** One payload drives every licensed realization.
**Test 2 — assertion equivalence.** The realizations make the *same kind of claim* about
the data.

Two intents are the same family only if they pass **both**. Sharing a serialization while
failing Test 2 means sharing a *carrier*, not a contract.

### Containment and sequence fail Test 2

```
A contains B contains C          A → B → C
```

- **Containment asserts transitivity, and the geometry enforces it.** You cannot draw C
  inside B inside A without also drawing C inside A. The picture makes the claim whether
  or not you intended it — which is fine, because containment is transitive.
- **Sequence does not assert transitivity.** A precedes B and B precedes C does not license
  an arrow from A to C. Drawing one is a new proposition.

So the same carrier, rendered by the two geometries, makes different claims. They are
distinct specifications. **Do not merge them.** Rev. 1's merge is withdrawn.

### The finding generalises past the two cases raised

Once Test 2 is applied to relations properly, the edge label stops being cosmetic. It
determines which geometries can tell the truth:

| Relation | Honest realization | Dishonest, and why |
|---|---|---|
| `is-subset-of` | Euler/Venn nesting, indented layers | arrows — asserts process where there is none |
| `is-part-of` | tree, bracket, exploded view, treemap nesting | **Euler nesting** — asserts *is-a*: a wheel is not a car |
| `precedes` | arrows, numbered steps | nesting; **evenly-spaced timeline** — asserts equal intervals the payload never gave |
| `causes` | labelled arrows | arrows shared with `precedes` — collapses order into causation |
| `associates-with` | undirected graph, adjacency matrix | any arrow — asserts direction; any ordering |

Note rows 1 and 2: `is-subset-of` and `is-part-of` are both "nesting," and they need
**different** nesting conventions. Euler nesting reads *is-a*; treemap nesting reads
*part-of*. The same geometry, two readings.

**Consequence:** honesty is a property of the (relation, geometry, reading convention)
triple, not of the geometry alone. So a table of honest pairings has to exist somewhere,
and it is domain-free — `is-subset-of` behaves identically for AI/ML/DL, for Felidae ⊂
Carnivora, and for `int ⊂ number`. That table is the real deliverable of the relational
family, and it is what a renderer needs that nothing currently supplies.

---

## 3. Which families are genuinely distinct

Applying both tests to the eight cases and to §13:

| | Specification | Payload | Class |
|---|---|---|---|
| **A1** | Containment (`is-subset-of`) | entities + relation | layout |
| **A2** | Composition (`is-part-of`) | entities + relation | layout |
| **A3** | Order / process (`precedes`) | entities + relation, optional actor, optional state | layout |
| **A4** | Causation (`causes`) | entities + relation | layout |
| **A5** | Association (`associates-with`) | entities + relation | layout |
| **B** | Tabulation | items × dimensions → cells | layout |
| **C** | Formal notation | notation name + verbatim text | notation |
| **D** | Quantitative behaviour | data or function + domain | computation |
| **E** | Perceptual form | a natural-language brief | perception |
| **F1** | Stepped instance | ordered steps with state | layout |
| **F2** | Falsifier | a claim + the case that breaks it | layout |

**A1–A5 share a carrier and not a contract.** One wire shape, five specifications, five
rows of the honesty table. This is the corrected version of Rev. 1's over-merge: the
generality is real and lives in the carrier; the distinctness is real and lives in the
relation semantics. Neither five blocks nor one.

**F splits, by the same test that split A.** Rev. 1 put worked examples, traces,
counter-examples and check questions in one family. A worked example asserts *this is how
it goes*; a counter-example asserts *this is where your model breaks*. Different claims,
different payloads. F1 and F2.

**C is the one safe merge, and it is safe for a specific reason.** Code, a LaTeX
expression, `mhchem`, SMILES, a regex, a genetic sequence — every realization makes the
identical claim: *this is exactly this text, in this notation.* Test 2 passes trivially
because notation rendering asserts nothing beyond faithfulness. That is why the family
absorbs unlimited domain variety without gaining a single type.

**D's two constructors lower to one.** Explicit data points, or a function plus its
domain; the renderer evaluates the second into the first. Same claim — *this is the
relation's behaviour over this domain* — so one payload.

**B stands alone.** A table is formally a relation, but its axis semantics are what
license the table/matrix/small-multiples choice. Erase them into edges and the renderer
can no longer choose.

---

## 4. What the semantic representation output looks like

Shape, not schema. Nothing here names a table, a stack, a Venn or a flowchart.

```
representation
  diagnosis    which prose failure fired            §13's left column
  spec         which specification                  A1..A5 | B | C | D | E | F1 | F2
  payload      per specification, domain-free
  emphasis     what the reader must take from it    REQUIRED
  caption      optional
```

Three fields deserve argument.

**`diagnosis` is separate from `spec` and both are needed.** The diagnosis is *why a
departure from prose was licensed*; the spec is *what shape the departure has*. Keeping
only the spec is today's bug — the engine cannot tell whether the figure did its job.
Keeping only the diagnosis is insufficient — one diagnosis licenses several specs.

**`emphasis` is required, in every family.** For D it is obvious: an unannotated curve
answers no prose failure. It generalises — which contrast in the table, which path through
the graph, which lines of the listing, which part of the image must be accurate. Three
reasons it is not optional:

- Assertion preservation (§1) has two halves; emphasis is the half that says what may not
  be dropped.
- It is what a realization can be *checked against*, which is the only mechanical link
  back to the diagnosis.
- It is what makes the departure educational rather than decorative — the thing §13's
  "diagnose, then choose" was protecting.

**`payload` mentions no subject.** Domain enters as data — labels, units, notation
names — never as schema. `notation: "smiles"` is legal; `ChemistryBlock` is not. Domain
knowledge accumulates in a **renderer registry** keyed by notation, which grows without
the contract changing. An unregistered notation is an infeasibility report (§14
obligation), not a crash and not a silent fallback to monospace.

Chemistry, in full:

```
reaction equation    ->  C, notation "mhchem"
molecular structure  ->  C, notation "smiles"
glycolysis           ->  A3, nodes = metabolites, edges = enzymatic steps
titration curve      ->  D, function + emphasis on the equivalence point
```

Four representations, zero chemistry in the schema, two registry entries. This is the
test of the abstraction: if a proposal needs a new *type* for chemistry, it is wrong.

---

## 5. Deterministic versus generative

By §1, the line is not "does it vary between runs." It is **whether the reader can end up
believing something the model never asserted.**

| Class | Preservation | Failure mode | Checkable? |
|---|---|---|---|
| layout | achievable | dishonest geometry for the relation | yes — the §2 table |
| notation | achievable | unregistered notation | yes — registry lookup |
| computation | achievable | misleading scale, unstated interval | yes — from the payload |
| perception | **impossible by construction** | invented content | **no** |

The first three can fail preservation, but they fail it *statically and detectably* — an
evenly-spaced timeline over a payload with no durations is a checkable error, and so is
Euler nesting over `is-part-of`. That is a linter, not a research problem.

Perception is different in kind. Everything that makes the image useful is content the
model did not supply, so there is no specification to check the output against except the
brief — which is exactly the point of §6.

---

## 6. Perceptual form, verification, and correctness

### The asset test already decides this

Architecture §8, the asset test — **LOCKED**:

> **Does this need to be stable and correctable, or can the model supply it inline?**
>
> The model knows the concepts; what it does not do is produce a stable, complete,
> consistent decomposition on demand — ask twice, get two graphs, with no way to
> accumulate a correction. That, not knowledge, is what an asset is for.

Ask an image model twice and get two small intestines, with no way to accumulate a
correction. **Generated figures pass the asset test decisively.** They are not payload.

That is the answer to "how does image generation fit," and it needs no new mechanism:
a figure becomes a **shared asset** — identified, versioned, promoted through a gate,
correctable, and covered by the existing reconciliation obligation when it drifts under a
commitment. The inline-generation pipeline is the wrong shape for the same reason
inline concept graphs were.

### Verification checks the specification, not the truth

This is the limit that has to be stated plainly, because a review step is easy to
describe and hard to mean.

A verifier can check **spec conformance**: are the four required referents present, is
the stated section plane used, are the layers in the asserted order. It cannot check
**truth**: is this what a small intestine looks like. Vision-checking a generated image
is two unreliable systems agreeing, and their agreement is not evidence.

So verification narrows the gap; it does not close it. What remains must be *reported*,
not absorbed — which is §12 of the semantics: an omission that fails quietly is the
dangerous kind. A generated figure carries a different epistemic status from an asserted
one and the reader is owed that difference.

### Three routes, in order of defensibility

1. **Report the gap.** §13's own conclusion — *diagnosable and probably unservable; report
   the limitation rather than substitute a diagram that answers a different failure.*
   Costs two lines and is always available. This is the correct default today.
2. **Retrieve from a licensed source.** Moves correctness to an editorial problem, which
   is ordinary and solved. Also solves the anchor problem below. Recommended if
   perceptual documents matter commercially.
3. **Generate, verify, review.** A real research commitment, and a product fork: human
   review means a queue, an async job, and a second independent reason for M4's background
   execution to exist. Worth knowing that before choosing it, not after.

### Two constraints that argue for route 2

**Anchors do not exist until the image does.** Annotation is an overlay on a surface with
known coordinates. A generated surface has none, so labelling requires a second pass —
the generator returning anchors, or vision locating referents. A retrieved figure with a
known coordinate convention has this for free.

**Diagnosing E when A serves is itself an error.** The gut wall — mucosa, submucosa,
muscularis, serosa — is ordered adjacency: A2 or A3, no capability needed, fully
preserving. E is licensed only when *the spatial truth is the content*, and the diagnosis
should carry the burden of showing that a schematic will not serve. Most apparent E is A
in disguise, and the disguise is expensive.

---

## 7. What §13 needs

| §13 row | Verdict |
|---|---|
| cross-reference → table / matrix | **holds** — B |
| topology → graph, flow | **too narrow.** Splits into A1–A5. Containment is a topology failure and neither graph nor flow serves it |
| parallel state → sequence, swimlane, timeline | **not a separate failure.** An actor attribute on A3 |
| perceptual referent → image | **holds hardest.** The only unservable one. Keep "report, do not substitute"; add that its output is an asset |
| abstraction grounding → worked example, **or code** | **splits** — F1 and C. The "or" is doing illegitimate work |
| procedure execution → trace with state | **holds** — F1 |
| false comprehension → counter-example, failing case, exercise | **holds** — F2 |

Net: seven diagnoses licensing eleven specifications, with an honesty table binding
relation semantics to geometry. Rev. 1's "six families" was too few, and it was too few
for the reason the challenge identified.

---

## 8. The boundary

```
1  educational decision      which prose failure fired, and on what
   (LLM)                     §13's left column

2  semantic specification    spec + payload + emphasis
   (LLM)                     domain appears only as opaque strings

3  realization               template picks the form among those the
   (template + engine)       honesty table permits for this relation
                             engine executes via a capability
                             engine measures, challenges, reports infeasibility
```

Each layer already has a rule in the existing documents:

- Layer 1 is Architecture §13 — *the diagnosis selects the representation; the author does
  not choose freely.*
- Layer 3 is Semantics §2 — *a template may influence visual treatment and a general
  preference for graphical representation; it may not decide that a diagram belongs at a
  given point.* **Which** realization: the template's, bounded by the honesty table.
  **Whether**: the model's.
- The challenge edge exists: `layout feasibility ──challenge──→ representation`.

**The current build's error is layering, not vocabulary.** Naming `kind: "table"` *is*
choosing a realization, so the model does the template's job — a violation of a LOCKED
semantic, committed at the schema level.

---

## 9. Two traps

**Do not collapse to one generic representation.** A free-form payload validates nothing
and cannot be rendered. Generality comes from each payload being domain-free, not from
there being one payload.

**Do not key renderers on domain.** Metabolic pathways and a request lifecycle are both
A3; mitosis-vs-meiosis and Postgres-vs-MySQL are both B. Key on specification and each
realization is built once. Key on subject and the same flow diagram is built five times,
and the sixth subject is still missing.

---

## 10. Selection — nobody selects

The question "who picks among permitted realizations" assumes a picker. Worked against
cases, there isn't one. There is a **filter chain**, and each stage is held by whoever
holds the information that stage needs. Only the last stage ranks.

```
1  honesty        relation semantics -> permitted geometries      honesty table (§11)
2  structural     payload properties rule some out as false        engine, from payload
                  or inexpressible
3  preference     rank what survives                               template
4  feasibility    does the ranked choice fit and stay legible?     engine, by measurement
5  escalation     nothing survives -> the signal travels up        Architecture §4
```

**The model never appears in this chain.** It asserts relation, payload and emphasis, and
that is the whole of its say. This is what fixes today's layering violation.

### Stage 2 is the one nobody had

Two containment payloads, same specification A1, different admissible realizations —
and neither difference is visible to the honesty table or to the template.

**Nine-level taxonomy.** `Life ⊃ Domain ⊃ Kingdom ⊃ Phylum ⊃ Class ⊃ Order ⊃ Family ⊃
Genus ⊃ Species.` Euler nesting is *honest* — containment is exactly what it draws. It is
also useless: the innermost region is a fraction of a percent of the outer area and its
label cannot be set. Indented layers and outline survive. The disqualification is
legibility, not truth.

**Overlapping sets.** `supervised learning` and `deep learning` intersect, and neither
contains the other. Euler handles this for three sets and generally cannot for four or
more with all intersections — non-convex regions are required. Indented layers cannot
express overlap *at all*: rendering it would assert a nesting that does not hold, which
§1 forbids outright. Here the structural filter removes a realization for **falsity**,
not legibility.

So stage 2 splits into two rejections with different force: *inexpressible* (drop it) and
*false* (drop it, and it would have been a §1 violation). Both are computable from the
payload alone, before any page exists.

### The chain holds across families

**Tabulation.** *mitosis vs meiosis* × 6 dimensions: honesty permits table, matrix, small
multiples, cards; structural drops small multiples (two items make poor panels);
template prefers density; feasibility fits. At 8 items × 12 dimensions feasibility fails
on width, and the engine transposes — a layout act that adds no proposition, so it needs
no escalation. At 20 × 30 nothing fits and stage 5 fires.

**Quantitative.** A loss curve: linear and log axes are both honest; a **truncated y-axis
is not** — it asserts a magnitude of difference the data does not contain. That is an
honesty-table row for family D, not a taste question, and it belongs at stage 1.

**Notation.** Degenerate but coherent: stage 1 admits one renderer per notation, stage 3
still chooses inline versus displayed for a short expression, stage 4 checks line length.

**Perceptual form.** Stage 1 admits **nothing** — no realization of E preserves
assertions. The chain terminates at stage 5 and produces the report. §13's "diagnosable
and probably unservable" is not a special case bolted on; it falls out of the same
mechanism that picks a diagram.

### Stage 5 already exists

Architecture §4: *the signal travels up, and the upstream decision-holder
resolves it — by expanding, reducing, changing representation, or reporting
infeasibility.* "Changing representation" is a challenge back to the model, not a choice
made for it. Decision 14's edge is already drawn: `layout feasibility ──challenge──→
representation`.

---

## 11. The honesty table is an asset, and its frames are conventions

### It passes the asset test

Architecture §8, **LOCKED** — *does this need to be stable and correctable, or can the
model supply it inline?*

- **Stable:** required. Re-deriving "is Euler nesting honest for `is-part-of`?" per
  document yields inconsistent answers, and a wrong one is a silently false figure.
- **Correctable:** required. The treemap/Euler distinction in §2 is exactly the kind of
  correction that has to accumulate rather than be rediscovered.
- **Model-supplied:** no. The model already demonstrated the failure — it drew a stack
  for containment and then wrote a callout to undo the implication.

Asset. Same machinery as §8: versioned, read-only to projects, promoted through a gate.

### But it is keyed differently, and that is the new finding

§8's assets are keyed by **subject × frame** — jurisdictions, schools, standard versions,
sitting side by side with a project selecting one. The honesty table is keyed by neither.
It is domain-free by construction: `is-subset-of` behaves identically for AI ⊃ ML ⊃ DL,
for Felidae ⊂ Carnivora, and for `int ⊂ number`.

It does have frames. They are **reading conventions**, and they are real:

| Glyph | Convention | Reads as |
|---|---|---|
| nested boxes | UML | namespace containment |
| nested boxes | treemap | part-of, weighted by area |
| nested regions | Euler | set inclusion |
| arrow A→B | flowchart | A precedes B |
| arrow A→B | **UML generalization** | **B is the base of A — the opposite direction** |
| arrow ↓ | chemistry | precipitate, not sequence |

The UML row is the decisive one: **the same glyph asserts opposite directions in two
conventions.** A single global honesty table is therefore wrong, and so is a per-subject
one — a software document and a biology document may share a convention, and two software
documents may not.

So: parallel frames, exactly as §8 line 363 describes them — *assets sit side by side, a
project selects one* — on a new axis. Convention, not subject.

**Who selects the convention: the template.** A template is a visual language, and a
reading convention is part of what a visual language is. The model's specification stays
convention-free — it asserts `is-part-of`, never "a nested box." Layering preserved.

### Drift changes meaning without changing assertions

This asset is unlike the others in one way worth recording before it is built.

Suppose the table is corrected: indented layers are found to read as *part-of* to the
intended audience, so `is-subset-of` loses that realization. Every committed document
that used it is now suspect — and **nothing in those documents changed.** The
assertions are identical; what shifted is what a reader takes from them.

The §14 reconciliation obligation covers asset drift under a commitment, and it applies
here. But every other asset's drift changes *what was said*. This one changes *what is
heard*. It is the first asset whose drift is invisible in a diff of the document, and the
reconciliation report is the only place it can surface.

### It spans every family, not just relational

Family D's truncated axis and family B's bar-chart-of-categoricals (implying magnitude
where the cells are nominal) are honesty rows too. The notation registry of §4 is a
second table of the same kind — domain knowledge as correctable data — keyed by notation
rather than relation. Separate tables, one asset class, one lifecycle.

---

## 12. Document-level coherence is decision 15 — it passes the admission rule

§16 asks whether Draft is one decision or two, and notes the cross-node coherence
problem. It is two, and the test is Architecture's own:

> Both survive the decision-admission rule separately: *"the order violates a
> dependency"* is a Section error with representation fine; *"that should have been a
> table"* is the reverse.

**A decision is distinct if it can fail alone.** Coherence can:

### The rising-abstraction chain

*biological neuron → artificial neuron → equations → code* = **E → A2 → C → C**. Four
specifications of one concept at increasing abstraction. Each is individually correct,
correctly diagnosed, correctly realized — and the document still fails when the diagram
labels its inputs `x₁…xₙ`, the equation writes `aᵢ`, and the code calls them `inputs`.
Three symbol systems for one referent. The whole point of showing four views is that the
reader can map between them, and nothing local can see that the mapping is broken.

Every other decision correct; document wrong. Admitted.

### It fails in both directions independently

- **Coherence fails, representation fine:** the neuron chain above.
- **Representation fails, coherence fine:** a stack drawn for containment in a
  single-figure document. One bad realization, nothing to be incoherent with.

Independent both ways, which is what the rule requires.

### What it owns — and what it must not

| Owns | Example |
|---|---|
| symbol and term consistency across representations of one concept | the neuron chain |
| representation mix | twenty sections that each open with a table; every table individually licensed, collectively unread |
| term collision across sections | *gradient* introduced as a concentration difference in a biology section and as a derivative in a maths section — each correct, together a trap |
| emphasis budget | three figures each marked "the key idea"; the document then has none |
| cross-representation reference | "as Figure 1 showed" surviving a realization change |

Must not own: the correctness of any single block, scope, or sectioning. Without that
boundary it becomes a fix-everything pass and stops being a decision.

### It needs a challenge edge, mirroring 14

Decision 14 challenges representation on **geometry**, per element. Decision 15 challenges
representation on **coherence**, across elements. They can conflict concretely: the engine
transposes a wide table for fit (a legitimate stage-4 act) and thereby breaks the parallel
structure of three sibling tables that a reader was meant to scan the same way.

```
layout feasibility  ──challenge──→  representation      decision 14, exists
document coherence  ──challenge──→  representation      decision 15, proposed
```

Same shape, different evidence. And like every other decision here, 15 is the LLM's,
consuming engine measurements as evidence — the pattern `agent/__init__.py` already
states: *if a decision needs a measurement from `engine/`, the backend takes that
measurement and passes it in.*

### It must be conditional on extent

A one-section cheatsheet has nothing to cohere. Making the pass unconditional buys
latency and cost for documents that cannot fail. The trigger is document extent and the
number of representations sharing a referent — both known before the pass runs.

---

## 13. What remains open

- **Is the relation list closed?** A1–A5 came from eight cases. `constrains`, `refines`,
  `contradicts` are plausible and untested. Treat as open, the way §16 treats the
  fourteen decisions.
- **How many conventions are there, and who authors the first one?** §11 establishes that
  frames exist and that templates select them. It does not size the set, and a convention
  is editorial work, not model output.
- **Stage 3's ranking is unspecified.** §2 gives the template a general preference for
  graphical representation. It does not order Euler against indented layers when both
  survive stages 1 and 2.
- **Threshold calibration**, inherited from §16 and now per-specification: how large must
  a relation set be before a diagram beats prose? Still no principled line.
- **Does decision 15 run once or to fixpoint?** It challenges representation; a changed
  representation can break a different coherence property. Bounded like §4's
  reconsideration bound, presumably, and with the same unfixed value.
