# Plan Fulfilment — the system's side of the contract

> The LLM generates content. **The system is answerable for the artifact matching
> the approved plan.**

Not a safety net on the model. The plan gate makes a promise to the reader —
*what gets written is what you just read* — and a promise nothing can falsify is
not a promise.

---

## 1. What was broken

A real run, `e197e066`, whose approved plan derived 6 partition members over 17
concepts:

```
produced   1 section  ("Union-Find & Undirected Connectivity" — unit 5 of 6)
absent     15 of 17 approved concepts
reported   success, in green, with a PDF
```

Nothing was truncated — `providers.py` raises on `finish_reason == "length"` and
it never fired. The model returned a well-formed document with six
`deliberate_omissions` and considered itself finished.

Three things were wrong, and only the first belongs to the model:

1. **Adherence.** One call, a 5,031-character brief, 17 concepts, ~19 pages. The
   model wrote one part and stopped. A stronger model fails this way less often —
   it does not stop failing this way.
2. **No check.** Nothing compared the document to the commitment. This is ours,
   and no model upgrade touches it.
3. **No evidence.** `repairs` was not recorded, so the run could not even be
   attributed after the fact.

---

## 2. The flow

### Terminology

```
CURRICULUM  →  MODULES  →  SECTIONS / CONTENT  →  REPRESENTATIONS  →  PDF
```

**`partition` (Architecture decision 9) divides the scope into MODULES, and each
module becomes its own PDF.** Sections inside a module are decision 10, planned
later when that module is prepared for generation.

The module count is derived from the educational scope — never fixed, and never
from page count. A cheat sheet on one subject derives one module; *"agentic AI
from scratch"* derives many. See [Curriculum-Modules.md](Curriculum-Modules.md).

Everything below is written per part, whatever the count, and reads `modules`
with a fallback to the legacy `units` of plans written before that layer existed.

```
approved plan
    ↓
units                       requirements(plan) — one work order per derived member
    ↓
generate each unit          its own concepts, depths and size; not the whole plan
    ↓
verify each unit            check_unit(order, section)
    ↓  (short? ask again, once, naming exactly what is missing)
assemble                    front matter from the plan, body from the units
    ↓
final completeness check    check_document(plan, document, reports)
    ↓
render
```

**Per unit, and the reason is not context size.** Each call is answerable for a
small, checkable promise. A model asked for one part either produces that part's
concepts or visibly does not; a model asked for a whole document can silently
deliver a fraction of it and nothing downstream can tell. This holds whether the
plan derived two members or twenty — the architecture does not care how many,
which is the point of driving it from `partition` rather than from a number.

**Each brief carries only its own unit.** The other units are not that call's
business, and including them is what let the model wander into writing a
different part than the one asked for.

**Front matter comes from the plan, not the model.** Title, assumed entry and
target capability were shown to the user and agreed. Asking a model to restate
them lets them drift from what was approved, for no gain.

**The heading is the plan's.** A renamed part is a part the completeness check
cannot find, so the model's heading is overwritten with the approved one.

---

## 3. What verification reports

`agent/fulfilment.py`, pure and model-free — so it cannot itself hallucinate a
pass. Per unit:

| Field | Answers |
|---|---|
| `generated` | was a section produced for this approved unit at all |
| `concepts_required` / `_covered` / `_missing` | which required concepts were covered |
| `treatments_anticipated` / `_produced` · `depths_required` | **observation only** — see below |
| `blocks` · `departures` · `words` | how much came back — observation |

And for the document: `units_approved`, `units_generated`, `units_missing`,
`concepts_missing`, `changed` (sections no unit asked for), `coverage`,
`problems`, and **`satisfied`**.

`satisfied` is false whenever `problems` is non-empty. It reaches the API at the
top level and the UI titles the panel *"Your document — incomplete"*. **A missing
unit cannot be reported as success.**

### What it does not claim, stated rather than implied

**Coverage means named, not taught.** A concept is covered if it appears in the
unit written for it. That reliably catches *omission* — the failure this exists
for. It does not certify the treatment is good, and the UI says so in as many
words rather than letting a percentage imply more than it knows.

**Treatment is not checked at all — deliberately.** Which treatment a concept
deserves depends on artifact type, purpose and subject together, and that has not
had its design pass. A rule written here now — *"work through must produce a
trace"* — would fix a taxonomy by accident, in the place it is hardest to notice
and hardest to undo.

So `treatments_anticipated`, `treatments_produced` and `depths_required` are
recorded per unit as **evidence for that pass**, and none of them can make a
document unsatisfied. `satisfied` depends on completeness alone: every derived
member written, every approved concept covered, nothing added that was not
approved.

---

## 4. Failure behaviour

| Situation | What happens |
|---|---|
| a unit comes back short on **concepts** | asked again once, with the missing concepts named; the better of the two attempts is kept |
| a unit fails outright (provider fault) | recorded as ungenerated; the other units still run |
| the document is incomplete | **produced, and reported as not satisfied** |
| no unit produced anything | hard failure, no artifact |

Producing an incomplete artifact rather than discarding it is deliberate: the
members that *did* come back are worth having, and the user can see exactly what
is missing. Discarding them would be a second, larger loss on top of the first.
What is forbidden is calling it success.

---

## 5. What this deliberately does not do

- **No model-specific tuning.** The baseline is established with the current free
  model first, so that a later comparison against a stronger one measures *model*
  quality against a fixed system — rather than confounding the two.
- **No parallelism.** Units run in sequence. Concurrency is an optimisation and
  this is a correctness change.
- **No re-planning.** If the model cannot deliver an approved unit, the answer is
  to say so, not to quietly renegotiate what was agreed.
- **No treatment taxonomy.** Recorded, never enforced, until it has been designed
  across artifact types, purposes and subjects.

---

## 6. What to measure next

With the contract enforced, the same plan can be run against a stronger model and
the two compared on the same instrument:

```
coverage                fraction of approved concepts covered
units_generated         of units_approved (however many were derived)
calls                   how many attempts the units needed
treatments_anticipated  what the plan expected — recorded, not required
treatments_produced     what the model actually reached for
depths_required         approved depths, for the later treatment pass
```

That separates system quality from model quality, which was impossible while a
one-sixth document could report success.
