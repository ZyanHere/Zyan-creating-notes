# §1 — Intake

A deep read of one section. **No design, no domain model, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**One correction to the Pipeline Map up front.** It filed **Q1 (job
misclassified)** under §2 Planning, noting it "partly originates here." That is
wrong. `job` is a field on `Situation`, produced by `interpret_situation`, which is
an **intake** decision. Q1 belongs to §1 entirely, and §4 below is about it.

---

## 1. What intake actually is

**Responsibility.** Turn what the user said into a situation the rest of the system
can plan against, and decide whether anything must be asked before planning starts.

**Starts** at the first user message. **Ends** when `sufficiency.verdict ==
"sufficient"` or the loop exhausts — at which point `state` becomes `ready` and
`proceed()` may run.

**What makes it hard, stated in the product thesis** `[OBSERVED]`
`Product-Semantics.md` §1: *"The user can specify preferences and constraints. They
cannot reliably specify the knowledge structure, coverage, sequencing, or treatment
they need — that would require already understanding the subject."*

So intake is not a form. It is the stage that must extract binding constraints from
ordinary language, **decide what is worth asking**, and hand planning a situation —
without asking the user to do the system's job.

---

## 2. What exists today

`[OBSERVED]` This is the most complete stage in V1, and the only one whose design is
fully realised in code.

**The split, and the latency it bought.** `backend/planning.py:_read()` runs
`interpret` → `decide` → `ask` **only if** `sufficiency.asking` is non-empty.
`create()` and `answer()` never plan. Measured: first useful question **102.6s →
17.7s**. `[MEASURED]`

**Policy is code, judgment is the model's** — `agent/sufficiency.py`, 602 lines, and
its docstring states the division explicitly. The policy table cites the locked claim
behind each axis:

| Axis | askable | blocking | priority | Recorded reason |
|---|---|---|---|---|
| `subject` | ✓ | ✓ | 0 | *"nothing exists to plan without it"* |
| `purpose` | ✓ | — | 1 | *"Semantics §5 LOCKED — purpose is the arbiter"* |
| `entry_point` | ✓ | — | 2 | *"assuming wrongly is not recoverable by any later decision"* |
| `artifact_type` | ✓ | — | 3 | *"long notes vs short notes … materially different plans"* |
| `target_capability` | ✓ | — | 4 | *"the target may not exist yet and that is a legitimate state"* |
| `capacity` | **✗** | — | 90 | *"Asking upfront asks for a number the learner cannot honestly give"* |
| `depth_register` | **✗** | — | 91 | *"biasing, not binding. A default is always defensible"* |
| `template` | **✗** | — | 93 | *"Presentation-Boundary rule 1 — internal. Users never select one"* |

**The gate** (`sufficiency.py:358`): `askable AND weak AND material`, in priority
order, capped by `DEFAULT_BUDGET = 4` — set to the number of askable axes *"so a
genuinely bare request can be resolved in ONE turn rather than several — fewest
conversational turns is the goal, not fewest questions."* Anything over budget is
**recorded as over-budget, not dropped**.

**Subject is a prerequisite, not a budget competitor** — resolved first and alone,
returning `verdict: needs_subject`.

**Span verification.** A reading's support must be a real quote from a real utterance
(`_verify`), must discriminate (`_discriminating` — a quote supporting every reading
equally is refused), and must not deny its own reading (`_supports`, negation-aware).
Unverifiable support is discarded, which **demotes the reading to a guess**.

**Two exits.** `sufficiency` decides when to stop; plus `improved()` — if no axis
strengthened, asking again cannot help. Bounded by `MAX_INTAKE_ROUNDS`.

**Questions are objective, not open** `[OBSERVED]` `ask_v1.md`: *"The learner cannot
reliably specify their entry point or target … They can recognise their own situation
when it is put in front of them."* Two to four concrete options, each of which must
produce a materially different plan, with a worked bad/good example. `default_label`
names what happens if they skip — *"a question is an offer to correct early, never a
blocker."*

**Output.** `Situation(subject, job, entry_point, purpose, target_capability,
capacity, stated[], inferred[])` plus the `intake_strategy` decision carrying every
axis verdict with `strength`, `material`, `would_differ`, `askable`, `asked`, `reason`.

---

## 3. Problems

### Measured

**Q1 — job misclassified, 2 of 3.** `[MEASURED, n=3]` `construct` for all three
cases; references say **orient** / **retrieve-rehearse** / construct. Root of Q2 and
Q3. **Produced here.** See §4.

**Job values actually produced across 8 plans:** `[MEASURED]`

```
6x 'construct'      2x 'retrieve'      0x 'orient'
```

**`orient` was never selected once** — and it is the correct answer for the interview
case, which is the single most common request shape this product exists for.

**B8 — the materiality filter has never fired.** `[MEASURED]` *weak + askable +
`material=False`* occurs **0 times in 88 readings**. The four core askable axes are
marked material **11 of 11**. The only four askable `material=False` cases are all
`artifact_type`, and all were already *stated or inferred*, so materiality was moot.

**But it is not a rubber stamp.** `[MEASURED]` 88/88 `would_differ` populated, median
188 chars, minimum 110, concrete: *"Beginner needs git basics (staging, history)
explained; experienced dev needs only conventions, examples, and tooling."*

**Q7 — over-asking, and the reference is contestable.** `[MEASURED, n=1]`
`git-commits` wrote **4 questions** and flagged **7 weak axes** where the reference
says 0–1. But the model's `entry_point` answer describes a real scope difference,
while the reference quietly assumes its own (*"Uses git daily; commits are messy"*).

**A8 — the materiality enum collapses to a boolean before storage.** `[OBSERVED]`
`material = reading.materiality == "changes_the_plan"`. `changes_details` — the value
that would justify *not* asking — becomes indistinguishable from `no_effect`.

**An answer was discarded because nothing was asked.** `[MEASURED]` `agentic-ai`
baseline: `intake_turns: 0`, `intake_answers_unused: 1`. Intake declared `ready` on
the first message, so the follow-up (*"i can code but i've never built an agent"*) was
never consumed. In the `generate-01` run the same case took 1 turn and used it. **Same
case, same input, different intake behaviour.**

**Small models fail span verification entirely.** `[MEASURED]` `gemma-4-26b`,
`nex-n2.5-mini`, `lfm-2.5-2.6b`: `verified=0`, every axis falls to `guessed`, and the
whole flow collapses to `needs_subject`. **The mechanism's correctness is
model-capability-dependent** — a strictness that is a feature on a strong model is a
denial of service on a weak one.

### Observed

**The `job` vocabulary in code contradicts the locked semantics.** `[OBSERVED]` This
is the sharpest finding in the section.

`agent/plan.py:101`:
```python
job: str = Field(description="orient · construct · retrieve · rehearse.")
```

`Product-Semantics.md` §6 locks **five** jobs, derived through discriminating tests:

| Locked job | In the field description? |
|---|---|
| Construct understanding | ✓ `construct` |
| Orient in a landscape | ✓ `orient` |
| Retrieve known material | ✓ `retrieve` |
| **Look up while working** | **absent** |
| **Execute a procedure** | **absent** |
| — | `rehearse` — **not one of the five** |

`rehearse` was a *candidate that was merged away* during Q1's derivation. So the field
offers a value the semantics rejected, and **cannot express two jobs the semantics
locked** — including *execute a procedure*, whose completion condition (*"every step
present and verifiable"*) is the strictest in the table.

**And it is a free `str`.** No `Literal`, no enum, no validator. Any string passes.

**No code branches on `job`.** `[OBSERVED]` Zero matches for `["job"]`, `.job`,
`get("job")` across `agent/`, `backend/`, `engine/`. It *does* reach the model —
`derive(situation)` and `plan(situation, landscape)` serialise the whole Situation into
the prompt — so it influences **by suggestion**. Nothing deterministic depends on its
value. **That is why it can be wrong in 2 of 3 cases and nothing notices.**

**`artifact_type` is binding by semantics and is not a Situation field.** `[OBSERVED]`
`Product-Semantics.md` §1: *"binding unless infeasible, and infeasibility must be
reported."* `Situation` has no `artifact_type`. It exists as a sufficiency axis
reading, and reaches planning only as either a `StatedConstraint` (if the user said it
and the model attributed it) or a free-text line in `inferred[]` — e.g. contract-act's
*"artifact_type: structured section-wise study notes"*. A binding axis arrives as
unstructured prose. `[MEASURED]`

**The axis table's derivation is unimplemented.** `[OBSERVED]` It says *"Document job
— derived from artifact type, never chosen."* In code `job` is a peer field the model
fills freely, and `artifact_type` is not in the same object. The stated derivation does
not exist.

**No axis for a traversal constraint** — `"section wise"` bound to `depth_register`.
Carried from §0; the *defect* is here, in the axis vocabulary.

**The whole transcript is re-interpreted every turn.** `[OBSERVED]`
`interpret(transcript: str)`. Measured 1–2 calls per answer.

### Strong inference

- **Q1 is an instance of CC1, not a model failure.** A free string with no consumer
  and a vocabulary that contradicts its own spec is a field that *cannot* be reliably
  right. Improving the prompt treats the symptom.
- **B8's explanation follows from the same cause.** If nothing depends on materiality,
  nothing corrects a threshold that drifts high. The mechanism is well-built and
  unexercised.
- **The axis set may be incomplete rather than miscalibrated.** Eight axes, none for
  source/authority (§0) and none for traversal. A constraint with no axis is absorbed
  into the nearest one, which is how *"section wise"* became a depth register.

### Unknown

- Is the threshold miscalibrated, or is the reference wrong? `[UNKNOWN]` — needs
  per-axis reference judgments on more than one case.
- Would a typed `job` with consequences fix Q1? `[UNKNOWN]` — the central open
  question of this section.
- Does re-interpreting the transcript cost anything measurable next to the model call?
  `[UNKNOWN]`
- Why did intake engage on one run of `agentic-ai` and not another? `[UNKNOWN]` —
  B1 non-determinism reaching intake.

---

## 4. The key architectural question: what does intake *produce*?

Not "what does it ask." The output is where the defects are.

`Situation` currently mixes three kinds of thing in one flat object `[INFERENCE]`:

| | Field | Nature |
|---|---|---|
| **Read from the user** | `subject`, `entry_point`, `purpose`, `target_capability`, `capacity` | evidence-backed readings, each with strength and spans **recorded elsewhere** |
| **Classified by the system** | `job` | a *decision* drawn from a closed vocabulary — and typed as free text |
| **Provenance** | `stated[]`, `inferred[]` | why the rest of it says what it says |

The consequences of that flattening are all measured:

- `job` gets the same treatment as a free-text reading, so its vocabulary drifted from
  the locked five and nothing validates it.
- `artifact_type` — binding — didn't make it into the object at all.
- The strength/materiality/`would_differ` record lives in a *separate* decision
  (`intake_strategy`), so the situation planning receives is **stripped of how
  confident any of it was**. A plan derived from a guessed entry point looks identical
  to one derived from a stated entry point.

That last point is the one I would want to test first `[INFERENCE]`: the agentic
reference says a wrong `entry_point` is *"not recoverable by any later decision — if
the landscape is built assuming API fluency, API foundations are never in the graph."*
V1 records that entry point's strength faithfully and then hands planning a bare
string.

**The distinction worth preserving** (and the §0 parallel is exact): *"what the user
said"* ≠ *"what the system concluded"* ≠ *"how sure it is."* V1 has all three and
serialises them as one blob.

---

## 5. Where intake starts and ends

**Current boundary** `[OBSERVED]`: ends at `sufficient` or exhaustion; planning is a
separate user-triggered step (`proceed()`), which is what the latency work
established — *"derive/plan are not called until the user explicitly reaches the
planning stage."*

**That boundary is sound and I would not reopen it.** `[INFERENCE]` It is the only
reason first-question latency is 17.7s.

**Two boundary questions that are genuinely open:**

**(a) Does intake end, or does it stay open?** Foundation §3.2 requires intake to ask
for a syllabus when scope is undocumented — which means intake needs a fact (the
tier) that only §0/§2 can establish. And corrections (§3) are *demonstrably* a second
intake channel: `ml-weekend`'s correction re-partitioned the plan, and `generate-01`'s
correction changed scope. `[MEASURED]` So the situation is revised after intake
"ends," through a different mechanism, with a different prompt.

**(b) Is `improved()` the right exhaustion test?** It stops when no axis
*strengthened*. A user answer that *weakens* a reading — genuinely useful information
— would read as no progress. `[INFERENCE, untested]`

---

## 6. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| No subject | `verdict: needs_subject`, asks subject alone | Correct `[OBSERVED]` |
| Weak material axis, askable | asked within budget | Correct |
| Weak material axis, over budget | recorded as `over_budget`, *"becomes visible in the plan as an assumption"* | `over_budget` was **empty in all 11 records** — never exercised `[MEASURED]` |
| Weak material axis, **not askable** | proceeds on the guess | Policy-correct (A3 struck) — but **is the guess surfaced?** `inferred[]` carries free text; nothing marks it as *material and guessed* `[OBSERVED]` |
| User answers something never asked | discarded | Measured once: `intake_answers_unused: 1` |
| Model cannot verify any span | every axis → `guessed` → `needs_subject` | Denial of service on weak models `[MEASURED]` |
| User skips a question | `default_label` applies | Correct by design |

The row that matters: **a material guess is not visibly a material guess.** Policy
forbids asking about capacity — correctly — but Foundation §3.1's companion rule
(*"content sourced that way must be marked as such"*) has no equivalent for axes.

---

## 7. What makes intake useful rather than a form

V1 already gets this right, and it is worth recording so a redesign does not lose it.

**Three capabilities a questionnaire does not have** `[OBSERVED]`:

1. **It asks only what changes the plan.** The gate is `material`, not `unknown`. The
   rule the git-commits reference states — *"an axis whose answer would not change the
   plan is not a question, however unknown it is"* — is the policy the code implements,
   even if B8 shows the threshold never bites.
2. **It asks recognisably, not abstractly.** Two to four options, each a different
   document, with concrete implications — *"skips roughly four pages"*, never *"more
   advanced."* This is the thesis made operational: the user recognises their situation
   rather than specifying it.
3. **It records why.** Every axis carries strength, spans, materiality, `would_differ`,
   and a human-readable reason. That record is what made A3 strikeable and B8
   diagnosable. **Almost no other stage in V1 is auditable this way.**

**The gap between that and being useful:** the record exists and **nothing consumes
it.** Planning gets the values, not the confidence. Same shape as CC1.

---

## 8. Constraints and cross-section effects

**On §0** — Foundation §3.2's ask/don't-ask rule needs the scope tier *during* intake.
So either intake learns the tier (a new capability) or §0 runs first (a reordering).
A source is also a *stated constraint* with no axis to bind to.

**On §2 Planning** — the whole situation JSON is the derive prompt's input, so
**every intake defect is a planning input defect**. `entry_point` is
unrecoverable-if-wrong. A typed `job` would be the first thing planning could branch
on deterministically.

**On §3 Correction** — corrections are a second situation-revision channel with a
separate prompt (`plan_revise_v2`). Whether that duplication is right is open.

**On §4 Generation** — `_unit_brief` iterates `situation["stated"]`, so stated
constraints reach generation directly. A misattributed constraint (*"section wise"* →
`depth_register`) therefore misleads two stages, not one.

**On §7 Storage** — A8: persist the enum, not the boolean. `would_differ` is already
persisted and is good.

**On §8 Deployment** — intake is the latency-sensitive path and the only stage with a
product-level latency requirement. It is also the cheapest stage: 1–2 calls per turn
against derive's one large one.

---

## 9. Solution directions — compared, not chosen

**A. Type the closed vocabularies.** `job` becomes a `Literal` over the locked five;
`artifact_type` becomes a Situation field. *Delivers:* makes Q1's failure mode
impossible to express, and makes the missing two jobs expressible. *Cost:* near zero.
*Does not deliver:* correctness — a `Literal` can still hold the wrong member.

**B. Give `job` consequences.** Downstream admissibility rules — if `job = orient`,
certain depths and treatments become inadmissible; if `execute a procedure`, *"every
step present and verifiable."* *Delivers:* the thing that makes a label matter, and
makes Q1 detectable. *Cost:* requires §2 to have something to check against. **This is
the option whose effect is genuinely `[UNKNOWN]`** and the most valuable to test.

**C. Carry confidence into planning.** Hand derive the axis verdicts, not just the
values, so a guessed `entry_point` is visibly guessed downstream. *Delivers:* the
`inferred`-marking obligation Foundation already states. *Cost:* small. *Risk:* more
prompt content on the stage that already truncates (A5).

**D. Extend the axis set.** Add whatever `"section wise"` and a supplied syllabus
should bind to. *Delivers:* §0's traversal finding. *Cost:* small, but it is a
semantics change — Product-Semantics §13 has it open on two counts.

**E. Recalibrate materiality.** Use `changes_details`; persist the enum; possibly let
the *reference set* define the threshold rather than the model. *Delivers:* B8.
*Blocked by:* only one case has a reference judgment, and it is contestable.

**F. Leave intake alone.** It is the best-built stage, its latency requirement is met,
and its defects are all *output-shape* defects that could be fixed at the §1/§2
boundary instead. *Delivers:* focus. *Ignores:* that Q1 — the root quality defect —
is produced here.

**The comparison has a clear shape:** A is nearly free and strictly good. B is the one
that would actually fix Q1 and the one we cannot predict. C and D are small and
depend on decisions in §2 and §0 respectively. E is blocked on evidence. F is the
honest null option, and A1's lesson argues against it — *"computed and depended on by
nothing"* is exactly what this stage does with its own best work.

---

## What remains genuinely open

1. **Does a typed, consequential `job` fix Q1?** The section's central unknown.
2. **Is the axis set complete?** Source and traversal have no home.
3. **Should the situation carry confidence, or only values?**
4. **Does intake end?** Corrections revise the situation through a different path.
5. **Is `improved()` right** when an answer legitimately weakens a reading?
6. **Materiality threshold** — unresolvable until more references exist.
