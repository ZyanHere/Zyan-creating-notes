# Plan Gate Milestone — BUILD PLAN, FOR VERIFICATION

Agent, backend and frontend for one loop:

```
request → interpretation + questions → proposed plan → correction → revised plan → … → approved plan
```

Stops at approval. No demo, no template selection, no render, no PDF.

Nothing in here is built yet except the agent prototype in §7, which **diverges from
the recorded taxonomy** and is the first thing to verify.

---

## 1. What this milestone is for

The primary success criterion is behavioural, not structural:

> A human can have this conversation with the system and converge on an approved plan.

Everything below is the minimum that makes that testable and keeps it from having to
be rebuilt at M4. Where a choice is between "correct" and "smaller", this document
picks smaller and says so.

**In scope:** eight decisions as *records* — five plan, two supporting upstream,
one interaction (§2) — the questions loop, natural-
language correction routing, revision, approval, and the commitment. A web UI a
non-technical person can actually use.

**Explicitly out:** demo generation, template selection, rendering, PDFs, members,
jobs, async execution, verification classes, the invalidation closure walk, decision
versioning, promotion, shared assets.

---

## 2. Three classes of decision

The prototype invented six decision names, four of which do not exist in the system.
`decision_kind` (Build-Spec §3) is already written, migrated and CI-tested. But the
rename is the smaller half of the correction: the decisions this milestone touches
are not all the same *kind of thing*, and flattening them is what produced the
mistaken idea that two of them could be absorbed.

### Plan decisions — the user approves these

Shown as sections of the plan; carried in the commitment snapshot.

| Shown as | Decision | `decision_kind` |
|---|---|---|
| what we read your request as | 1 Situation interpretation | `interpret_situation` |
| what's covered, how deep | 8 Scope | `scope` |
| what's left out, and what it costs | 7 Consequence | `consequence` |
| the order of the units | 6 Traversal | `traversal` |
| the units | 9 Partition | `partition` |

### Supporting upstream decisions — recorded, not shown as sections

Architecture §3 lists these as **universal decisions in their own right**. They are
not absorbed into scope and this plan does not treat them as if they were. What
distinguishes them is only that they have no natural plan section: the user reads
their *consequences* through scope and exclusions rather than reading them directly.

| Decision | `decision_kind` | Visible as |
|---|---|---|
| 4 Structure derivation — what concepts exist, what is built from what | `derive_structure` | which concepts are available to cover at all |
| 5 Relevance — what is in play for this situation | `relevance` | why a concept earns or loses its place |

They get rows like any other decision. The reason is routing, and it is concrete:

```
"you've completely missed X"        → derive_structure   (X was never in the graph)
"X isn't relevant for me"           → relevance          (X is known, wrongly in play)
"go deeper on X"                    → scope              (X is in play, wrongly cut)
```

Three different faults with three different repairs. Route all of them to `scope`
and the first is unfixable — scope can only cut or keep what relevance handed it,
so a concept that was never derived cannot be restored by any change to scope.
Recording them costs two rows and one prompt section; not recording them means
knowingly misrouting a correction, which Presentation-Boundary §5 already argues is
worse than deferring one.

### Interaction decisions — govern the conversation, not the artifact

| Decision | `decision_kind` |
|---|---|
| 0 Intake strategy — what to ask next | `intake_strategy` |

Architecture §3 is explicit that decision 0 is the odd one: a genuine judgment that
can be wrong, whose output is *evidence* rather than a claim about the artifact, and
which belongs to a loop rather than to the derivation. Everything downstream consumes
its product, never the decision itself. It is recorded because asking well is exactly
what this milestone tests — and it is not in the commitment snapshot, because the
user approves a plan, not a question.

### And one thing that is not a decision

**`extent` is derived from scope**, and Architecture §14 makes *reporting* it an
obligation rather than a field the model fills in. The prototype lets the model write
"about two pages" freely with nothing behind it. Extent is computed from the scope
and partition that were actually agreed, and displayed.

`exclusions` likewise is not its own decision — it is the output of `consequence`.

## 3. Decisions are rows, not fields

The prototype holds one `Plan` object and compares it before and after. That works
in memory and cannot survive contact with the rest of the system, because targeted
correction is defined over decision *records*:

```
decision(project_id, kind, status, freshness, inputs_hash, output jsonb, …)
```

So:

- Each of the eight writes **one row**, `status='candidate'`, `output` = its own JSONB.
- The `Plan` the user sees is a **projection** over the current rows, assembled for
  display. It is not stored as a plan.
- A correction updates only the rows it routed to. Untouched rows keep their id, and
  the diff is free rather than computed.
- Approval writes `commitment(kind='plan', snapshot, decision_ids, decision_ids_hash)`.

**What approval commits.** `decision_ids` names every decision the plan rests on,
including `derive_structure` and `relevance` — the user approved a meaning that
depends on them, and if one drifts later the approval rested on a derivation they
never saw. `intake_strategy` is excluded: it is an interaction decision, not part
of the artifact's derivation. The `snapshot` carries the plan projection only.

**`snapshot` still stands alone.** System Design §4: the user approved a *meaning*.
The snapshot carries the concepts, the exclusions and their stated reasons as its own
content; `decision_ids` are links for re-derivation, never the substance. Both are
stored — that is not redundancy, it is the point.

**Idempotent approval falls out.** `decision_ids_hash` makes re-committing an
identical set identity rather than a second commitment, which holds across retries,
clients and users without an idempotency key (System Design §5, invariant 1).

**Deferred deliberately:** `dependency` rows, the `freshness='stale'` closure walk,
and the memo key (`inputs_hash` is written but never read). Correction at this
milestone re-derives what it routes to and does not chase what depends on it. That
is a real limitation and §9 names the correction class it fails on.

---

## 4. Agent layer

Two calls to propose, one to revise. Decisions are grouped by what genuinely
resolves together, never by what is convenient.

```
understand(utterances)       → interpret_situation · derive_structure · relevance
plan(understanding)          → scope · consequence · traversal · partition
                               · intake_strategy
revise(state, correction)    → routing + revised outputs for the routed decisions only
```

**Why `understand` is one call and not three.** Situation, structure and relevance are
distinct decisions with distinct rows and distinct correction targets — but deriving
the concept graph and judging what is in play for *this* learner are one act of
reading. Splitting them into three calls on the current provider costs three round
trips and three chances at a 502 for no gained seam. They are still **three rows**,
which is what routing needs.

**Why `plan` is one call.** Architecture §4 makes scope, partition and traversal
jointly resolved; splitting them invents seams the architecture says are not there.
`intake_strategy` rides with them because "what should I ask next" is a judgment about
the plan just produced — it needs the whole thing in context, and a third round trip
buys no seam and one more chance at a 502. Five rows.

**What `revise` may return.** The router names the affected set — it is not a lookup
table. A capacity change ("four days") plausibly moves scope and extent, and may also
move partition, traversal or consequence; whether it does is a judgment about *this*
plan, not a rule. The examples in this document are illustrative of the routing
*classes*, never of a fixed mapping. What the loop enforces is only that the model
declares the set it changed and that the declaration is checked against what actually
changed.

**Prompts.** `plan_v1` and `plan_revise_v1` exist and are close; both need editing
for the renamed decisions. `intake_v1` is new.

**Rules the prompts must keep** (all locked, all already written into the drafts):

- Semantics §3 — silence is the system's decision. `interpret_situation` separates
  what the user *stated* from what was *inferred*, and the inferred list is shown on
  every turn. A decision the user cannot see is one they cannot correct.
- A question is asked only where two plausible answers give materially different
  plans, carries what would differ, and carries the default it proceeds with.
  Questions never block.
- Semantics §12 — an exclusion has three parts or it is a hole.
- `revise` routes before it revises, and refuses corrections belonging to a later
  gate (`out_of_scope`) rather than approximating them with a plan change.

**Validation.** Pydantic is authoritative; one repair attempt on failure, as
`generate.py` already does.

---

## 5. Backend layer

### Database

Run `migrations/0001_init.sql` **as it stands**. It is written, ordered and CI-tested;
partially applying it to save four unused tables is how migration order rots.

Used this milestone: `project`, `utterance`, `decision`, `commitment`.
Present and unused: `member`, `job`, `artifact_version`, `dependency`,
`verification`, `set_status`. The nullable FKs on `decision` and `commitment` already
permit this.

`utterance` is append-only testimony: every user message including corrections, in
order. It is the transcript, and it is what a later `intake_strategy` reads.

### Service

```python
create_project(text)                  -> Project        # + first utterance
propose(project_id)                   -> PlanView       # runs interpret, plan, next_question
add_utterance(project_id, text)       -> PlanView       # correction: routes, revises
approve(project_id, decision_ids)     -> Commitment     # idempotent
get_plan(project_id)                  -> PlanView
```

`PlanView` is the projection of §3 plus the open questions, the routing record of the
last turn, and the derived extent. It is a read model, never stored.

### HTTP

From System Design §9's candidate surface, unchanged where it already says the right
thing:

```
POST   /projects                       { text }              → project_id
POST   /projects/:id/utterances        { text }              → PlanView
GET    /projects/:id/plan                                    → PlanView
POST   /projects/:id/plan/approve      { decision_ids }      → Commitment  [GATE]
GET    /projects/:id                                         → project + transcript
```

`GET /projects/:id/intake` is folded into `PlanView.questions`; a separate endpoint
implies questions are a phase, and they are a field of the current state.

**Synchronous.** A turn is 20–60s on the current provider. §9's job queue arrives at
M4 with a reason; adding it now is infrastructure ahead of need. The frontend must
therefore tolerate a slow POST — see §6.

---

## 6. Frontend layer

Next.js 16 / React 19 / Tailwind 4 / TypeScript — the stack from commit `e98cb59`,
recoverable from git. That commit's dashboard shell is reusable.

> **Corrected 2026-09-08.** This previously said `TemplateCard` must not come back,
> citing an internal-templates rule that has since been withdrawn — Semantics §1 and §2
> LOCKED have the user selecting a template. A selection control belongs here. Its shape
> is worked in [Design-Library.md](Design-Library.md) (deferred), not recovered from
> `e98cb59`: the user picks by looking at a rendered exemplar, not by reading a name.

### Screens

**1. New project.** One text box, one button. No dropdowns, no level selector, no
subject picker. Every one of those is a decision the system is supposed to make and
show as inferred.

**2. The plan.** One page, the whole plan visible, in this order:

```
  READ AS               what we understood — subject, job, for whom, what you'll be able to do
  YOU SAID              stated constraints, verbatim
  WE DECIDED            the inferred list          ← visually equal to YOU SAID, never collapsed
  OPEN                  questions, each with what it changes and the default
  COVERS                scope, each with why it earns its place
  DELIBERATELY NOT      exclusions, each with consequence and when-to-learn
  UNITS                 partition, each with why these belong together
  ORDER                 traversal, one or two sentences
  EXTENT                derived, with what drives it
```

`WE DECIDED` is the screen's reason for existing. If it renders as a muted footnote
the product silently decides for the user and §3's lock is cosmetic.

**3. Correction.** A free text box under the plan: *"Anything wrong? Say it however
you like."* No structured correction UI — no per-section edit buttons, no field-level
forms. The system classifies; the user writes English. That is the thing being
tested, and a form would test something else.

**4. After a correction.** Before the revised plan, show what happened:

```
  read as:      one sentence
  changed:      scope, extent
  unchanged:    situation, partition, order, exclusions
  deferred:     "black with yellow accents" — appearance, decided at the demo stage
```

Changed decisions are marked in the plan itself. **Deferred is not an error state** —
it is the system correctly declining a well-formed request that belongs to a gate
that does not exist yet, and it should read that way.

**5. Approve.** One button, disabled while a turn is in flight. On approval: a
confirmation showing the committed plan and an explicit *"the next stage would build
a sample page — not yet available."* No dead-end.

### States that must be handled

- **In flight, 20–60s.** Show the request being worked on, not a spinner alone. The
  user must not be able to send a second correction concurrently.
- **Turn failed.** Provider 502s are routine on the current tier and cost a whole
  conversation if mishandled. Prior corrections stay applied; the failed one is not.
  Offer retry.
- **Model returned nothing routable.** `targets` empty and `out_of_scope` null means
  the correction was not understood. Say so and ask them to rephrase — never silently
  return an unchanged plan.

---

## 7. What exists, and what is wrong with it

| File | State |
|---|---|
| [agent/plan.py](agent/plan.py) | prototype — **wrong decision names**, `extent` as a decision, questions not recorded |
| [agent/prompts/plan_v1.md](agent/prompts/plan_v1.md) | close; edit for renamed decisions |
| [agent/prompts/plan_revise_v1.md](agent/prompts/plan_revise_v1.md) | close; routing table needs the real names |
| [backend/planning.py](backend/planning.py) | in-memory + JSON files; replace with the service in §5 |
| [plan_cli.py](plan_cli.py) | keep as a harness — a UI-free way to exercise the loop |
| [tests/test_planning.py](tests/test_planning.py) | 10 tests, stub provider; the properties survive the rename |

The prototype ran a real three-turn conversation to approval, so the loop's shape is
evidenced. What it does not evidence is anything about persistence or routing to
decision records, because it has neither.

---

## 8. Verification — how you check this milestone is done

Behavioural, in order of what would make me abandon the design:

1. **A stranger converges.** Someone who has not read these documents opens the app,
   types a request, and reaches an approved plan they agree with. If they cannot
   tell what the system decided for them, §3 has failed regardless of the code.
2. **A correction changes only what it routed to.** The property is agreement
   between the declared set and the actual set — not a fixed mapping from phrases to
   decisions. "Cut it to four days" is a capacity change: it will move scope and the
   derived extent, and it may well move partition, traversal or consequence too. That
   is the router's judgment about this plan. What is verified is that whatever it
   declared is what changed, and that nothing else moved silently.
3. **Upstream corrections reach upstream decisions.** "You've missed X entirely"
   routes to `derive_structure`, not to `scope`. Scope can only cut or keep what it
   was handed, so a misroute here is unfixable by any later correction.
4. **Presentation is deferred, not absorbed.** "Make it black with yellow accents"
   leaves every plan decision untouched and says which stage owns it.
5. **A misunderstanding is visible in one turn.** `read as:` is wrong → the user sees
   it immediately, not three turns later.
6. **Approval is idempotent.** Double-submit yields one commitment.
7. **The commitment stands alone.** Read the snapshot with the decision table dropped
   and it still says what was agreed.

Instrumented, per turn, for the same reason M1 has a representation report:

- `claimed` vs `actual` decisions changed — drift reported, never repaired
- corrections whose routing was empty and not deferred (understanding failures)
- turns to approval, and tokens per turn

---

## 9. Decide before building

- **`derive_structure` / `relevance` are recorded as decisions** (§2) and derived in
  one call with `interpret_situation` (§4). Settled, not open.
- **One plan per project, or competing plans?** System Design §9 flags this open.
  Recommendation: one. Revision supersedes.
- **Partial approval?** §9 flags it. Recommendation: no — approve the set or correct
  it. `decision_ids_hash` assumes whole-set approval.
- **Does a correction after approval reopen the gate,** or start a new commitment
  chain via `superseded_by`? The column exists. Recommendation: defer — this
  milestone ends at first approval.
- **Auth.** `project.user_id` is `NOT NULL`. Single hardcoded user for now, or real
  accounts? Recommendation: hardcode; it is one column to change.
- **Does the frontend show decision ids at all?** Approval posts them. Recommendation:
  no — the UI sends what it was given and never displays them.
