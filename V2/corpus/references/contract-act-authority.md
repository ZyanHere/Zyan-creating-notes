# Reference — Indian Contract Act, 1872

**Request:** *"i need to study the indian contract act 1872 for my law semester, section wise"*

Hand-written. This is the case that breaks assumptions which look entirely
reasonable under a coding workload, and it is here because **the subject has an
authority and the system does not.**

---

## 1. What makes this case different

For backend development there is no document that says what backend development
*is*, so deriving a concept landscape from the model's own knowledge is the only
available operation. The Indian Contract Act is a **numbered statute**. Its
structure is not derived — it is **read**. Sections 1–75 exist, in an order, with
names, and that order is the thing the learner said they want.

Three consequences a domain model has to be able to express:

1. **Terminology is not the model's to choose.** The Act says *"free consent"*,
   *"voidable"*, *"coercion"*, *"undue influence"*. A landscape that produces
   "Agreement validity factors" has renamed the thing the exam will use.
2. **Ordering has an external authority.** *"Section wise"* is a stated
   constraint on traversal, and it outranks any pedagogical ordering the planner
   would otherwise prefer.
3. **Coverage is checkable against something outside the model.** A missing
   section is a fact, not a judgment — unlike a missing concept in a derived
   landscape.

V1 has no representation for any of this. `derive_structure` will invent a
landscape, and nothing in the system can say *"this one should have been read."*

## 2. The situation, read correctly

| Axis | Reading | Binding? |
|---|---|---|
| subject | Indian Contract Act, 1872 | stated |
| job | **retrieve / rehearse** for an exam, with problem application | inferred |
| purpose | Law semester examination | stated |
| entry_point | Law student, first contract-law exposure | inferred |
| target_capability | State the provisions and apply them to problem questions | inferred |
| constraint | **"section wise"** — binds traversal | **stated** |

## 3. Capability decomposition

```
TARGET: answer a contract law paper — theory questions and problem questions

├── C1  State what makes an agreement an enforceable contract
├── C2  Identify, on a fact pattern, which element is missing
├── C3  Distinguish void from voidable, and say who may avoid
├── C4  Apply the consent provisions to a problem question
└── C5  State the remedies available and how damages are measured
```

C2 and C4 are why this cannot be pure recall: a law paper gives a fact pattern
and asks which provision bites. That is application, and it needs worked problem
questions — not a summary of each section.

## 4. Structure — read, not derived

Grouped by the Act's own scheme, keeping its section numbers and its words:

| Group | Sections | Concepts (the Act's terms) |
|---|---|---|
| Preliminary | 1–2 | Proposal · acceptance · promise · agreement · contract · void · voidable |
| Formation | 3–9 | Communication · revocation · absolute and unqualified acceptance |
| Consideration | 10, 23–25 | Lawful consideration · exceptions to "no consideration, no contract" |
| Capacity | 11–12 | Minor · unsound mind · disqualified persons |
| Free consent | 13–22 | Coercion · undue influence · fraud · misrepresentation · mistake |
| Void agreements | 26–30 | Restraint of marriage, trade, legal proceedings · wagering |
| Contingent contracts | 31–36 | — |
| Performance | 37–67 | Who must perform · time and place · reciprocal promises · appropriation |
| Discharge | 62–67 | Novation · rescission · alteration |
| Breach and remedies | 73–75 | Damages · remoteness · quantum meruit |

**Note what is *not* happening here:** no concept was invented, no section was
renamed, and the grouping is the Act's own, not a pedagogical one.

## 5. Modules

Six, following the statute:

1. **Formation** (ss. 1–10) — *State when a proposal becomes a promise and a promise becomes a contract.*
2. **Consideration** (ss. 2(d), 23–25) — *State the consideration requirement and its statutory exceptions.*
3. **Capacity** (ss. 11–12) — *Determine whether a party could contract, and state the effect where they could not.*
4. **Free consent** (ss. 13–22) — *Identify which vitiating factor a fact pattern discloses, and state the remedy.*
5. **Void agreements and contingent contracts** (ss. 26–36) — *Recognise agreements the Act declares void, and say why.*
6. **Performance, discharge and remedies** (ss. 37–75) — *State how a contract is performed or discharged, and measure damages on breach.*

*Traversal:* the Act's own order. Not negotiable — it is a stated constraint,
and it is also how the exam is set and how the textbook is organised.

**Depth:** free consent and remedies get `work through` — those are where problem
questions concentrate. Contingent contracts get `explain`. Preliminary
definitions get `mention` but must be *present*, because the later sections are
written in their terms.

## 6. What this reference is testing

- Can the domain model express **"this structure was read, not derived"** — a
  source with authority over terminology and ordering?
- Can it express a **stated constraint binding traversal** specifically, rather
  than generically?
- Is there any path by which the system could say *"I should be reading the
  statute and I cannot"* — i.e. report the absence of a source it needs?
- Does the correction in this case (*"the ordering should follow the act's own
  sections, not your grouping"*) route to **traversal**, or get mistaken for a
  partition fault? They are different decisions and only one of them fixes it.
- Can coverage be checked against an **external** list of sections rather than
  against the model's own earlier output? Everything V1 verifies is
  self-referential — it checks the artifact against the plan, and the plan
  against nothing.
