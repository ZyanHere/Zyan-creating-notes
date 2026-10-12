# MyNotes V2 — Build Plan

**Supersedes the *staging* of `Implementation-Plan.md`. Does not supersede its content.** That
document remains the engineering reference for the design→code mapping (§4), the database inventory
(§5), the canonical interfaces (§6) and the Definition of Done (§9). This document replaces only
**the order in which that material is built**.

> **DESIGN FROZEN:** `Domain-Model.md` Rev. 4.1, `Architecture.md` Rev. 5, `Technical-Design.md`
> Rev. 11. No revision was made for this task. Nothing below changes what the architecture *is* —
> only when each part of it comes into existence.

---

# 1. Assessment: product-first vs bottom-up

## 1.1 The diagnosis is right, and it is not merely a communication problem

A build order whose first six milestones are `identity → schema → claims → tasks → gateway →
admission` produces no product signal for a long stretch. That is a real project risk, and worse than
"hard to follow": **losing the thread about why a mechanism exists is how you build machinery nobody
needed.** This project's own history is the evidence — V1 shipped three mechanisms built to
specification and left unwired (`inputs_hash` written never read, `freshness` declared never set,
`feasibility` computed never gated). Each was built because the design said so, not because a feature
demanded it.

So I accept the premise. A plan that cannot answer *"what can I show you now?"* at every step is a bad
plan even when every phase is individually correct.

## 1.2 Where the proposed approach is wrong or dangerous

Five places. The first three matter.

### (a) The claim/memo protocol is **not** deferrable the way the proposal assumes — this is the big one

The proposal says: *"Basic conversation → simple LLM call may be enough. Parallel generation of many
modules → now Tasks / Claims / idempotency become necessary."*

That instinct is usually right and is wrong here, for a specific reason. TD §9.5:

> *"S12 makes an incomplete Document not a Document. V1 could not afford that rule because resuming
> re-spent all five calls; here it costs the missing sections only. **The mechanism is what makes the
> invariant affordable.**"*

The memo is **not a scaling optimisation. It is a semantic precondition.** Build generation without
it and you necessarily build V1's semantics — a partial document reported as *"doesn't match what was
approved"*, or a full re-spend on retry. Adding the memo afterwards then changes:

```
the Document rule            whole-or-nothing ← only affordable with the memo
the Task state machine       `incomplete` becomes a real, resumable state
the generation loop          fan-out, per-section claims, keep-better
every test asserting the old behaviour
```

That is not *"introduce the mechanism when the feature needs it."* That is **rewriting the feature**.

**Correction:** claims + memo land **in the same milestone as generation** (M9), not after it. The
proposal's *trigger* is right — generation is where they are needed — but they are a precondition of
that milestone, not a follow-up to it.

### (b) *"A simple LLM call may be enough"* would recreate TD §8.6b's worst finding

If "simple" means a direct provider call bypassing `MODEL_CALL`, that is precisely the defect Rev. 11
found and fixed: synchronous intake had its own path to the provider and therefore passed no
admission, entered no ledger, and counted against no quota. A second provider path is the thing the
design centralised away.

**Correction — and it costs nothing:** `MODEL_CALL` exists from the **first** model call, with its
admission steps as **no-ops**. The *shape* is right from day one; the *policies* arrive when traffic
justifies them. This is the general principle this plan runs on (§1.4).

### (c) Auth at milestone 2 is the proposal committing the exact sin it diagnoses

The proposal's complaint is premature infrastructure. Then it places auth second — before there is
anything to protect, and before **U6** (*"portfolio link or product?"*) is answered. TD §13's position
is that T1 needs an **access gate**, and *"a shared code is not auth and must not be described as
auth."* Real auth — users, sessions, ownership checks — is needed when there is a second user, which
may never happen for a portfolio deployment.

**Correction:** `user_id` lives in the schema from M1 (V1 already does this: `USER = "local"`, *"one
column to change"*). An access gate arrives with the first public deployment. Real auth arrives when
U6 is answered, not before.

### (d) `artifact-library` and `guardrails-evals` are not components the frozen design has

**Templates belong to the renderer**, and the reason is specific: `render_environment` — including
`template_content_hash` — is *"captured in the engine, not passed in"*, because otherwise System
Design invariant 10 is unenforceable (TD §12.1). Lifting templates into a sibling component breaks
that capture. They stay at `engine/templates/`.

**Guardrails already exist and are already placed.** `Integrity`, `validate_blocks`, the honesty
check and the X1 guard *are* the guardrails — they live in `core/compute` and `engine/checks`. A
`guardrails/` package would either duplicate them or move `Integrity` out of `core`, breaking the
`dom`-purity rule the import wall enforces.

**Evals are genuinely separate and genuinely absent from the design.** The measurement programme —
`V2/runs/`, the harness, the reference plans — is not application code and should not live in the
application tree. That one earns a top-level directory.

### (e) Rendering at position 11 is too late, and the design says why

Not a judgment call — a dependency. `extent` and `feasibility` both read the **capability
declaration** (TD §12.2a, §12.2), and planning calls both. So the declaration must exist before
planning, and it belongs with the renderer.

It is also the cheapest possible de-risking: the renderer is **testable with zero model calls**
against the saved `V2/runs/generate-01` document, and it is the **deployment floor** (241 MB/render,
1.4 s launch, the measured numbers the whole scaling model rests on). Discovering at milestone 11 that
it does not fit the target instance would invalidate ten milestones of assumptions.

**Correction:** a renderer milestone before planning (M5), which *produces* the capability declaration
that M6 consumes.

## 1.3 What bottom-up gets right and must survive

| | Why it is forced |
|---|---|
| **identity before schema** | every uniqueness constraint is *over* identity columns. Retrofitting `envelope` is a migration of nearly every table — and identity is a pure function, a day's work. There is no reason to defer it |
| **Postgres from day one** | TD/§7's diagnosis: `inputs_hash`, `freshness` and `feasibility` are unwired *for the same reason* — a JSON blob cannot give per-decision addressability. Starting on files blocks all three behind a migration |
| **import walls at M0** | V1's own comment: *"Written at M1, when there are three packages to keep apart, rather than at M8 when the damage is already done."* Free at the start, expensive later |
| **immutability enforced, not documented** | TD §4.4 says *"by revoking `UPDATE`/`DELETE`, not by convention."* Retrofitting means code that mutates already exists, and that code is the bug |
| **admission before the Gateway is complete** | `MODEL_CALL` steps ①–② *are* admission. Not a sequencing preference |

## 1.4 The synthesis: a product spine, a small kernel, and *shape now, policy later*

```
PRODUCT SPINE          vertical milestones, each runnable and demoable
                       ordered to match TD §9's own flow order
KERNEL (M0)            the few things that cannot be retrofitted without rework
SHAPE NOW, POLICY LATER  canonical primitives exist from first use; their
                       policies start as no-ops and tighten when traffic justifies
```

**The third line is the reconciliation**, and it is what makes the other two compatible:

| Primitive | Exists from | Policy at first | Tightened at |
|---|---|---|---|
| `MODEL_CALL` | M2, the first call | admission steps are no-ops | M12 |
| `CallLedger` | M2 | full — accounting is cheap and **irreplaceable**, you cannot reconstruct history you did not record | — |
| `envelope` column | with its table | computed and written | used for reuse at M6 |
| `Claim` table + `step()` | **M9** | full — it is a semantic precondition there (§1.2a) | — |
| `UserQuotaBucket` / `calls_admitted` | M12 | — | — |
| `RECONCILE`, orphan sweep, GC units | M12 | — | — |

Note the asymmetry between the two halves of accounting, because it is deliberate: **accounting is
early and admission is late.** A ledger row costs one insert and answers *"why did this project cost
46 calls?"* — a question you cannot answer retroactively. Admission needs real traffic to tune and
protects against a risk that does not exist with one user.

## 1.5 Scored comparison, honestly

| | Bottom-up | Product-first (as proposed) | **This plan** |
|---|---|---|---|
| correctness | highest — kernel proven before use | **at risk** — §1.2a would be built twice | high — kernel is M0 + M9 |
| development speed | slow to first demo | fastest early, then rework | fast, with two forced detours (M0, M5) |
| understanding progress | **poor** | best | best — every milestone demos |
| debugging | easiest — primitives tested in isolation | hardest early | good — walls + ledger from M2 |
| architectural integrity | highest | **at risk** — §1.2b, §1.2d | high — shape-now keeps boundaries |
| premature infrastructure | **high risk** — admission/quota before traffic | low, except auth (§1.2c) | low |
| rewrite risk | lowest | **high at generation** | low |

**The dominant risk in bottom-up is building unneeded machinery. The dominant risk in pure
product-first is rewriting generation.** This plan accepts two small detours (M0's kernel, M5's
renderer) to remove the second risk without reintroducing the first.

---

# 2. Top-level architecture: services vs packages

## 2.1 Recommendation — one repository, packages, two processes

```
mynotes-v2/
├── client/            Next.js — the ONLY UI.  Separate process (dev server / Vercel)
├── core/              PACKAGE · dom — pure, no I/O.  Imported by all, imports none
├── agent/             PACKAGE · all LLM behaviour: prompts, intake, planning, routing, generation
├── engine/            PACKAGE · the renderer + templates + capability declaration
├── backend/           PACKAGE · API, orchestration, persistence, tasks, claims, gateway
├── evals/             NOT application code — the measurement programme and references
└── infra/             Dockerfile, migrations runner, deploy config
```

**Two processes at T0/T1**, which is what the design specifies (TD §3.1: *"T0 and T1 are one OS
process"* plus the separate frontend). One repository.

## 2.2 Verdict on each proposed component

| Proposed | Verdict | Reason |
|---|---|---|
| `client/` | **separate process, day one** | Already true in V1 and the one deployment decision V1 got right: `NEXT_PUBLIC_API` means the browser calls the backend directly, so **no serverless timeout enters the path** |
| `backend/` | **package; the main process** | — |
| `agent/` | **package, not a service** | A service adds a network hop and a deployment unit for zero benefit at T1. V1's three-package split with import walls already works |
| `renderer/` → `engine/` | **package now; separate unit at T2** | TD §H gives the *numeric* condition: `render slots needed > min((mem − 65 MB)/240 MB, vCPU)`, or bulk re-render becomes real. Split on the measurement, not on the diagram |
| `artifact-library/` | **does not exist** | Templates live in `engine/templates/`. `template_content_hash` is captured *in the engine* or invariant 10 is unenforceable (§1.2d) |
| `guardrails-evals/` | **split in two, and only one exists as a directory** | Runtime guardrails are already `core/compute` + `engine/checks`. **Evals** become `evals/`, outside the app |
| `core/` | **package, exactly as proposed** | And the proposal's framing is right: deterministic, immutable, no LLM, no DB, no HTTP. The import wall makes it true rather than aspirational |
| `infra/` | **directory** | — |

## 2.3 The import wall (M0, non-negotiable)

Modelled on V1's working `tests/test_boundaries.py`:

```
core     → may import nothing but core           (this is what makes dom purity mechanical)
agent    → core, ports.  NOT psycopg, NOT engine, NOT backend.store
engine   → core.identity only.  NOT core.types (duck-typed mappings), NOT httpx/socket
backend  → anything.  It coordinates — that is its job
ONLY backend.gateway may import a provider SDK or httpx
```

Two of these encode design decisions rather than tidiness:

- **`engine` may not import `core.types`.** A duck-typed mapping is what lets a template fix cost a
  render (~3.4 s) instead of a generation (~323 s).
- **Only the gateway reaches a provider.** TD §15.8's Rev. 11 addition, with its own stated limit: an
  import wall bounds Python imports, never a subprocess's network — Chromium's font fetching is
  handled separately by pinning fonts and dropping `networkidle`.

---

# 3. What must exist before product work (and what must not)

## 3.1 The M0 kernel — genuinely cannot be retrofitted

| | Why it cannot wait |
|---|---|
| repository layout + packages | — |
| **import walls** | free now, expensive after the first violation |
| config (env-driven), structured logging, `/health` | `/health` must answer **from the process that renders** — V1's lesson that cost three rounds of diagnosis |
| Postgres connection + migration runner | §1.3 |
| **`core/identity`** — canonical JSON, the three key constructions, member encoding, content hashes | every uniqueness constraint is over its output |
| **immutability grants** in the first migration | TD §4.4 — enforced, not documented |
| `Clock` port | so every later lease/expiry test injects time instead of sleeping |
| CI running pytest | — |

## 3.2 Deferred, with the trigger named

| | Deferred until |
|---|---|
| Tasks | M6 — planning is 342 s and cannot hold a request |
| Claims + memo | M9 — generation fans out; and §1.2a makes it a precondition there |
| admission, quotas, provider slots | M12 — needs real traffic to tune; protects against a risk that does not exist with one user |
| `RECONCILE`, orphan sweep, GC | M12 — recovery paths for failures that only occur in operation |
| real auth | when **U6** is answered |
| object storage | M10 — the first artifact that must survive a restart |
| T2 render split | when §H's numeric condition fires |

---

# 4. Machinery → feature mapping

`feature → the problem the feature creates → the mechanism that solves it → when`

| Feature | Problem it creates | Mechanism | Milestone |
|---|---|---|---|
| first real model call | a call fails in ten distinguishable ways; *"nothing happens when I click"* has twice been the model | `MODEL_CALL` shape · failure classification · `CallLedger` | **M2** |
| multi-turn conversation | a network retry must not append a second utterance | `request_id` + fingerprint · `Project.next_ord` slot bump | **M3** |
| real intake | the whole transcript is re-read each turn; readings must carry confidence | `situation`/`job` envelopes · `sufficiency` as pure policy | **M4** |
| any PDF at all | the renderer is the deployment floor and the capability declaration is read by planning | `engine/*` · both declaration tables · `renderer_build` nesting | **M5** |
| planning | 6 calls / 342 s cannot hold an HTTP request; a timeout loses all of it | **Task system** — durable, leased, epoch-fenced, resumable | **M6** |
| plan revision | re-deriving everything costs 342 s; untargeted decisions must survive | `DecisionVersion` + `DependencyEdge` + `stale()` · `RoutingResult` | **M7** |
| approval | the plan must be refusable, and what was approved must be pinned | `Commitment` + members · `Integrity` · `approved_extent` · `template_policy` | **M8** |
| **generation fan-out** | N concurrent section calls; a partial failure must not re-spend the successes | **`Claim` · `MemoIndex` · the memo envelope · `step()` · epoch fencing** | **M9** |
| regenerate after a correction | the same module under a new commitment is a new production event | per-kind Task idempotency keys | **M9** |
| rendering the real document | one artifact per (document, environment); Chromium memory is the ceiling | render claim · bounded slots · `ArtifactIndex` | **M10** |
| export | a zip must contain what the commitment approved, and be byte-identical | commitment-scoped resolution · canonical zip | **M11** |
| a public URL | one tenant drains the shared quota | admission: `calls_admitted` · `UserQuotaBucket` · provider slots | **M12** |
| operating it | claim loss, orphaned tasks, crash windows, growth | `RECONCILE` · orphan sweep · GC unit rule · the §17 event set | **M12** |
| cross-project reuse | two projects derive the same structure | `step_shared` + `ATTACH` + `SharedDerivation` | **M12** (envelope recorded from M6, so switching it on needs no migration) |

**Note the two places this deliberately diverges from "introduce when needed":** the `CallLedger` at
M2 (you cannot reconstruct unrecorded history) and the claim protocol at M9 **with** generation rather
than after it (§1.2a).

---

# 5. Guardrails vs evals

They are different in kind, live in different places, and arrive at different times.

### Runtime guardrails — already in the design, no new component

| Guardrail | Where | Arrives |
|---|---|---|
| span verification (a reading's support must be a real quote) | `agent/` intake | M4 |
| `sufficiency` policy — ask only what changes the plan | `core/policy/sufficiency.py` | M4 |
| honesty table — no dishonest (relation, geometry, convention) triple | `engine/checks.py` | M5 |
| `unrendered` reporting — a block kind never silently vanishes | `engine/checks.py` | M5 |
| **`Integrity`** — the only automatic refusal in the system | `core/compute/integrity.py` | M8 |
| `validate_blocks` — every `StructuralClaim` carries a Licence; the X1 guard | `core/document/validate.py` | M9 |
| approved-shortfall rule — a disclosed-unservable need becomes a `Reference` | `core/document/validate.py` | M9 |
| failure classification — ten classes, retriable vs terminal | `backend/gateway/classify.py` | M2 |

All of these are **pure functions in `core` or `engine`**. None is a service. Creating a `guardrails/`
package would move `Integrity` out of `core` and break the purity the import wall enforces.

### Offline evals — a real new directory, and it already has content

```
evals/
├── references/      the hand-written reference plans the corpus is judged against
├── corpus/          the 10 cases
├── harness/         the runner that produced V2/runs/
└── runs/            recorded outputs — ALSO the CI fixture (TD §15.7's stub gateway)
```

**Arrives at M4**, in a minimal form, and for a reason beyond measurement: the recorded runs are what
let CI test every workflow **without a provider and without a quota** — the direct answer to CC6
(*"free-tier reliability contaminates every measurement"*). So the eval harness pays for itself as test
infrastructure long before it is used to judge plan quality.

Full plan-quality evaluation (the 12 dimensions, the reference comparison) is a **post-M12** research
activity, gated on U7 (*what does a project cost on a paid provider?*) — it needs stable, repeatable
runs, which the free tier cannot give.

---

# 6. The build plan — thirteen milestones

Every milestone answers the seven questions. Every milestone leaves a **runnable, demoable system**.

---

## M0 · Skeleton, walls, and the identity kernel

**User-visible capability** — none. This is the one milestone with no product outcome, and it is
deliberately the only one.
**Components** — all packages created empty; `core/identity` real.
**Foundations introduced** — layout · import walls · config · structured logging · `health()` ·
`Clock` port · CI · **`core/identity`**.
**Implemented** — `core/identity/{canonical,envelope,task_key,claim_key,member,content,fingerprint}.py`;
`tests/test_boundaries.py` with the full FORBIDDEN table.
**Demo** — `python -m backend.app` prints the banner (resolved model, renderer and database status),
`health()` answers in-process, a deliberately-injected bad import fails CI.
**Tests** — the §15.2 golden identity table **in both directions**;
`test_three_key_constructions_are_disjoint`; `test_canonical_json_stable`; boundary test fails on an
injected violation.
**NOT yet** — any model call, any domain type beyond what identity hashes, Tasks, Claims, the Gateway,
**anything touching Postgres**, and the HTTP surface (`health()` is a function here; the ASGI app that
serves it at `/health` arrives with M1).

> **Corrected.** This milestone previously claimed `0001_init.sql`, the Postgres pool, the migration
> runner and the immutability grants. All four moved to **M1**, where the rest of the schema already
> lived. They cannot be here: **D1 exists to gate the shape of M1's migration**, and a spike cannot gate
> a migration that M0 has already written. `backend/api/health.py` had independently settled the same
> question — it returns *"pool arrives with M1"*, and the banner prints it.

### State

```
layout · config · structured logging · Clock port · health()      DONE
import wall                    DONE - 9 tests, verified to fail on an injected import
core/identity                  DONE - 9 files, 983 lines, Rev. 12 found while writing it
golden identity table          DONE - 85 inclusion + 461 exclusion assertions, 13 kinds
lint · format · types          GREEN - ruff 0.17, pyright 1.1.414 strict, 0 errors
pytest                         114 passing
uv.lock                        generated, cross-platform, committed
CI                             executed - see the run referenced in the commit
```

**The exclusion half is generated, not listed.** `INCLUDED` comes from `SPECS[kind]` and `EXCLUDED`
is every other field in the test context, so each of the 13 kinds is asserted to ignore every one of
the 42 project facts it does not read, rather than the handful §15.2 names. A hand-written exclusion list would need extending
every time the context grows, which is the drift §5.11 exists to prevent.

**Carried forward out of M0, both deliberate:**

| | |
|---|---|
| Hypothesis property tests | Its compiled `_native` extension is blocked by Smart App Control on the dev machine, and pytest loads its plugin through entry points so merely installing it fails the whole suite. The 461-assertion sweep covers determinism and exclusion; what is missing is shrinking and the unicode edge-case corpus. Lands when the environment can load it. |
| `test_brief_hash_matches_renderer` (§15.2) | Needs `BriefInputs` and the brief renderer — `core/types` (M1) and the engine (M5). Until it exists the memo envelope's honesty rests on one `BriefInputs` value having two consumers rather than on a test, which is recorded in the test file so it is not forgotten. |

---

## D1 · DBOS spike — a gate, not a milestone

**Half a day, after `core/identity` and before M1's migration.** See
`Pre-Implementation-Decisions.md` §D1 for the six questions and the pre-committed decision rule.

**Why it sits here rather than at M6:** a spike whose purpose is to inform a decision must precede the
implementation, not follow it. And M1 writes `0001_init.sql` — if DBOS is adopted it keeps its own
schema in the same database, and retrofitting that is a migration rather than an edit.

**Outcome gates:** the shape of M1's migration, and whether `work/` is written at M6 at all. The Claim
protocol survives every outcome.

---

## M1 · Log in, create a project, have a conversation

**User-visible capability** — open MyNotes, **log in with the development account**, create a project,
send messages, reload: the transcript is there and it belongs to you.
**Components** — `client` · `backend/{auth,api}` · `ports/auth.py` · `store/pg` · Postgres.
**Foundations** — `core/types` · **the authentication boundary** (`Principal`, `Authenticator`,
`SessionStore`) · opaque session tokens, hashed at rest, in an httpOnly cookie ·
**authorization on every project-scoped read** · `Utterance` append-only with `ord` slot-bump and
`request_id` + fingerprint · `0001_init.sql` with immutability grants and an RLS-compatibility note ·
**the Postgres pool** · **the migration runner** · **the ASGI app** — the last three inherited from M0,
which could not hold them (see the correction note under M0).
**Implemented** — `core/types/*`; `ports/auth.py`; `backend/auth/{dev,session}.py`;
`backend/api/{deps,auth,conversation}.py`; `backend/api/asgi.py`; `backend/store/pg/pool.py`;
`backend/store/migrate.py`; `store/pg/{sessions,decisions}.py`; `0001_init.sql`; the client's login and
conversation views.

**Those three module paths are already fixed by code that exists.** `Makefile`'s `migrate` target runs
`python -m backend.store.migrate` and says *"runner arrives with M1"*; `backend/app.py` probes for
`backend.api.asgi` and prints *"arrives with M1"*; `backend/api/health.py` reports *"pool arrives with
M1."* The plan is being corrected to match three places that already agreed with each other.
**Demo** — visit unauthenticated → login. Log in as the dev account. Create a project, type three
messages, reload: all there. Log out: the session is gone **server-side** and the old cookie is refused.
**Tests** — `test_unauthenticated_request_is_refused` ·
`test_cannot_read_another_users_project` (→ **404**, not 403 — a 403 confirms existence) ·
`test_logout_revokes_server_side` · `test_session_token_is_hashed_at_rest` ·
`test_dev_authenticator_refuses_outside_local` · `test_intake_retry_does_not_double_append` ·
`test_request_id_mismatch_returns_409` · `test_concurrent_appends_get_distinct_ord` ·
utterances are immutable by privilege.
**NOT yet** — any model call, registration, OAuth, roles, password reset, email, RLS enforcement.

**Why auth is here and not deferred:** the frozen design already *requires* a principal — TD §13.4
(*"a Task is readable and cancellable only by its project's owner"*), §4.2's `user_id` and
`approved_by`, §13.1's *"every read path takes `(user_id, project_id)`"*. It specifies no **mechanism**.
Building the mechanism now is implementing the design; retrofitting it later would thread an identity
boundary through every handler and every store call. See `Pre-Implementation-Decisions.md` §D2.

---

## M2 · The system talks to a model

**User-visible capability** — send a message, get a real model reply. The full vertical works:
`client → backend → agent → provider → backend → client`.
**Components** — `client` · `backend.gateway` · `agent`.
**Foundations** — **`MODEL_CALL` with its final shape** (admission steps as no-ops) · the provider
adapter · attempt deadline · failure classification (all ten classes) · full jitter ·
**`CallLedger`**.
**Implemented** — `ports/gateway.py`; `backend/gateway/{model_call,classify,budget,providers}.py`;
`store/pg/ledger.py`; a trivial `agent/echo.py` prompt.
**Demo** — *"Hi"* → a real reply. Kill the network mid-call → a typed, readable error, not a
traceback. `SELECT * FROM call_ledger` shows the call, its tokens and its outcome.
**Tests** — `test_429_is_retried` · `test_400_is_terminal` ·
`test_task_budget_exhaustion_is_distinguishable` · `test_failed_call_is_in_the_ledger` ·
**`test_provider_boundary_is_mechanically_exclusive`** (the import wall) · a stub-gateway path exists
for CI.
**NOT yet** — admission, quotas, provider slots, Tasks, Claims. The gateway's steps ①–③ are present
and return *admit*.

**Why `MODEL_CALL` in full shape now:** a second path to a provider is exactly TD §8.6b's Rev. 11
finding. Getting the shape right costs nothing today and cannot be retrofitted cheaply.

---

## M3 · A real multi-turn conversation

**User-visible capability**
```
User: Hi
Agent: Hello.
User: I want notes on Transformers.
Agent: What is your current experience level?
```
**Components** — `client` · `backend` · `agent`.
**Foundations** — the whole transcript as a model input · the `situation` envelope **computed and
recorded** (not yet used for reuse) · `DecisionVersion` with its envelope column.
**Implemented** — `agent/interpret.py`; `store/pg/decisions.py` version writes;
`backend/flows/intake.py` in its simplest form (interpret, no sufficiency yet).
**Demo** — a coherent multi-turn exchange; the `decision_version` table shows one `situation` row per
turn with a distinct envelope.
**Tests** — a turn writes exactly one version; the envelope changes when the transcript grows and
**not** when an excluded field changes.
**NOT yet** — sufficiency, questions chosen by policy, `job`, `scope_tier`, `frame`.

---

## M4 · Real intake

**User-visible capability** — the system asks only questions that would change the plan, two to four
concrete options each, and stops when it has enough.
```
request → interpret → ask → answer → ask → intake complete
```
**Components** — `client` · `backend` · `agent` · `core/policy` · **`evals/`**.
**Foundations** — `sufficiency` as a pure policy · `job` as its own decision · `scope_tier` and
`frame` (content-addressed, per-subject) · span verification · the eval harness as a **CI fixture**.
**Implemented** — `core/policy/sufficiency.py`; `agent/{ask,classify}.py`;
`flows/intake.py` in its final §9.1 order — **situation and job first, then tier and frame**, because
both read situation readings; `evals/{corpus,harness,runs}`.
**Demo** — a bare *"notes on Transformers"* reaches `ready` in one turn of questions, with each axis's
strength and evidence visible in the response.
**Tests** — `test_frame_reads_situation_readings` (only reachable if situation precedes frame) ·
sufficiency gate is `askable ∧ weak ∧ material` · intake meets its 30 s budget against the stub ·
the stub gateway replays `evals/runs/` so the suite needs no provider.
**NOT yet** — planning, templates, Tasks.

---

## M5 · A PDF from a document — the renderer, proven early

**User-visible capability** — a real PDF, rendered from the **saved** `generate-01` document. Not yet
from a generated one.
**Components** — `engine` · `backend`.
**Foundations** — `merge` (pure Jinja) · the three merge-time checks · bounded Chromium slots · the
two layout probes · **both capability-declaration tables** · `renderer_build` / `render_env_hash` /
`capability_decl_version` as **nested** hashes.
**Implemented** — `engine/{merge,checks,print}.py`; `engine/capability/*`; `engine/templates/`.
**Demo** — `POST /render` with the saved document JSON returns a PDF. `/health` reports renderer
status. A template whose relation mapping is dishonest is **refused at merge time**.
**Tests** — `test_honesty_table_enforced` · `test_realization_paired_in_source_order` ·
`test_unrendered_kind_reported` · `test_no_margin_argument` · `test_viewport_is_a4` ·
`test_no_network_at_render` · peak RSS and slot count measured **on the target instance** (closes
**U3** with a number).
**NOT yet** — `ArtifactIndex`, the render claim, object storage, export.

**Why here and not at position 11:** `extent` and `feasibility` both read the capability declaration
(§12.2a) and M6 calls both — so this is a **dependency**, not prudence. It is also the cheapest
de-risking available: zero model calls, and it produces the measured numbers the whole scaling model
rests on.

---

## M6 · Planning

**User-visible capability** — intake completes, and the system proposes a curriculum: modules, their
capabilities, what is covered, what is cut and at what cost, how long it will be.
**Components** — `client` · `backend` · `agent` · `core/compute` · `engine/capability`.
**Foundations** — **the Task system** (states, `task_key` per kind, lease, epoch fencing, heartbeat,
cancel, resume, orphan sweep) · `structure` / `projection` / `scope` / `partition` / `sections` /
`ordering` · `extent` and `feasibility` as pure compute.
**Implemented** — `work/{states,lease,lifecycle,coordinator}.py`; `agent/plan.py`;
`core/compute/{extent,feasibility}.py`; `flows/planning.py`; the client's plan view and task-status
polling.
**Demo** — click *Plan*, watch a task progress, see a curriculum with per-module page estimates and
disclosed shortfalls. Restart the backend mid-plan → the task resumes.
**Tests** — `test_regenerate_under_same_commitment_is_idempotent` · `test_resume_incomplete_task` ·
`test_double_resume_is_a_noop` · `test_cancel_on_terminal_task_is_rejected` ·
`test_completion_wins_tie_with_cancel` · orphan sweep re-leases an abandoned task ·
`test_derive_prompt_bump_yields_a_new_plan_task`.
**NOT yet** — Claims (Task-level idempotency is sufficient here: one Task per key, and a plan Task
does not fan out) · cross-project structure sharing (the envelope is recorded, sharing is switched on
at M12) · correction · approval.

---

## M7 · Plan revision

**User-visible capability** — *"drop the deployment module"*, *"you've missed evaluation"* — and only
the affected decisions change.
**Components** — `client` · `backend` · `agent`.
**Foundations** — `DependencyEdge` · `stale()` as a graph walk over **monotonic sequences** ·
`RoutingResult` · targeted version writes · the `reusable` vs `stale` distinction.
**Implemented** — `agent/revise.py`; `flows/correction.py`; `store/pg/routing.py`; the client's
correction input and a *what changed / what is now stale* panel.
**Demo** — correct a plan; the response shows the reading, what was claimed, what actually changed,
and what is now stale. A `job` correction visibly **reuses** the structure.
**Tests** — `test_job_correction_stales_downstream_not_structure` · `test_prompt_bump_is_not_stale` ·
`test_ordering_is_sequence_not_wallclock` · `test_version_row_never_without_edges`.
**NOT yet** — approval, generation.

---

## M8 · Approval — the gate

**User-visible capability** — a plan can be **refused**, with the reason and the decisions implicated;
and once approved, exactly what was approved is pinned.
**Components** — `client` · `backend` · `core/compute` · `engine/capability`.
**Foundations** — `Integrity` (the only automatic refusal) · `Commitment` + per-member rows ·
`environment_hash` in commitment identity · `approved_extent` pinned · `template_policy` ·
`disclosed` shortfalls recorded.
**Implemented** — `core/compute/integrity.py`; `core/policy/template.py`; `flows/approval.py`;
`store/pg/commitments.py`; the client's approve button with a refusal panel.
**Demo** — approve a clean plan. Then construct a phantom and watch approval **refuse**, naming
*both* `scope` and `partition` as implicated. Edit a template's CSS and re-approve → a **new**
commitment, because the pinned environment changed.
**Tests** — one test per runtime invariant (S1, S2, S2b, S3, S4, S5, S12) and an *inexpressibility*
test per construction-enforced one (S6–S14) · `test_stale_blocks_approval_when_integrity_is_clean` ·
`test_reapproval_after_template_edit_is_a_new_commitment` ·
`test_double_click_approve_is_one_commitment` · `test_approved_extent_survives_recalibration`.
**NOT yet** — generation.

---

## M9 · Generation — **the claim milestone**

**User-visible capability** — an approved plan becomes written content, section by section, and a
failure part-way costs only the missing sections.
**Components** — `client` · `backend` · `agent` · `core/document`.
**Foundations** — **`Claim` table · `claim_key` · the five operations · `step()` / `step_shared()` ·
`PUBLISH` as one transaction · `MemoIndex` + the memo envelope · epoch fencing · `ATTACH` ·
`ATTACH_PROVENANCE` · `Document` + `DocumentConstruction` + `DocumentProvenance`** · per-kind Task
idempotency including `{commitment_id, module_id}`.
**Implemented** — `claim/*` in full; `agent/generate.py`; `core/document/{builder,validate}.py`;
`flows/{generation,document}.py`; the client's per-section progress.
**Demo** — generate a module; watch sections complete in parallel. **Kill the worker after three of
five** and resume: exactly two calls, visible in the ledger. Cancel mid-run and resume later: the
same. Approve a correction and regenerate: unchanged sections are reused.
**Tests** — the whole concurrency suite: `test_two_workers_one_envelope` (16 threads → one call) ·
`test_fencing_rejects_slow_worker` (R2) · `test_takeover_race` · `test_committed_is_write_once` ·
`test_heartbeat_detects_fencing` · `test_content_addressed_payload_prevents_overwrite` ·
`test_publish_is_atomic` · `test_fenced_publish_writes_nothing` ·
`test_generation_resume_costs_the_remainder` · `test_incomplete_writes_no_document` ·
`test_identical_content_is_one_document` · `test_document_provenance_attaches_on_hit` ·
`test_no_workflow_restates_the_claim_branches`. **Lease expiry injected via the `Clock`, never
slept.**
**NOT yet** — artifacts, export, admission, `RECONCILE`.

**Why claims land here and not later:** TD §9.5 — *"V1 could not afford that rule because resuming
re-spent all five calls; here it costs the missing sections only. The mechanism is what makes the
invariant affordable."* Building generation without the memo builds V1's semantics, which then have
to be replaced (§1.2a).

---

## M10 · The real PDF

**User-visible capability** — the generated document becomes a downloadable PDF, and the same
document under a different template is a sibling, not a replacement.
**Components** — `backend` · `engine` · object storage.
**Foundations** — the render claim · `ArtifactIndex` with `UNIQUE (document_id, render_env_hash)` ·
`capability_decl_version` recorded on the artifact · content-addressed object storage · signed-URL
delivery.
**Implemented** — `flows/render.py` via `step("render", …)`; `store/pg/artifacts.py`;
`store/objects/{local,s3}.py`; `api/delivery.py`.
**Demo** — intake → plan → approve → generate → **download the PDF**. The first complete product
path. Re-render after a template fix: ~3.4 s, not another generation.
**Tests** — `test_render_claim_prevents_duplicate_artifacts` ·
`test_one_artifact_per_document_environment` · `test_render_claim_loss_does_not_re_render` ·
artifact delivery survives a provider outage.
**NOT yet** — export, admission, recovery.

---

## M11 · Export

**User-visible capability** — download the whole curriculum as one zip, in the approved order.
**Components** — `backend` · object storage.
**Foundations** — commitment-scoped artifact resolution · `export_hash` as both task key and object
path · the canonical zip · the refuse/inform rules.
**Implemented** — `flows/export.py`; `api/delivery.py` export route.
**Demo** — export a multi-module curriculum; modules are ordered as the plan decided, not
alphabetically. Export an incomplete curriculum → a refusal naming the unrendered modules.
**Tests** — `test_export_uses_commitment_documents` ·
`test_export_task_key_changes_with_artifact_set` · `test_export_refuses_when_a_module_is_unrendered` ·
`test_export_refuses_unsatisfiable_pin` · `test_export_reports_newer_plan_without_refusing` ·
**`test_export_zip_is_byte_deterministic`** (two builds, different processes) ·
`test_export_has_no_claim_row`.
**NOT yet** — admission, recovery, sharing.

---

## M12 · Hardening — make it survivable and shareable

**User-visible capability** — the system can be given a URL without being drained; it survives
crashes, restarts and worker loss; and a second project on the same subject costs less.
**Components** — all.
**Foundations** — admission (`calls_admitted` CAS · `UserQuotaBucket` upsert · FIFO provider slots) ·
`RECONCILE` + `FIND_RESULT` wired into `step()` · orphan sweep · GC with the unit rule and reverse
deletion order · `step_shared` + `SharedDerivation` + source extraction · the §17 event set · access
gate · env CORS · T1 image with pinned fonts.
**Implemented** — `work/admission.py`; `gateway/slots.py`; `claim/{find,reconcile}.py`;
`flows/extraction.py`; `store/gc.py`; `obs/*`; `infra/`.
**Demo** — hammer the API past the cap → refusals with a quota reason, not provider 429s. Delete a
claim row → the next run reconciles with **zero** model calls. Two projects on one subject → one
structure derivation.
**Tests** — `test_budget_is_enforced_under_concurrency` · `test_cold_quota_bucket_admits` ·
`test_provider_cap_holds_across_both_origins` · `test_provider_slot_is_released_on_failure` ·
`test_claim_loss_costs_at_most_one_call` · `test_memo_gc_cannot_produce_a_false_hit` ·
`test_routing_gc_retires_its_claim` · `test_second_project_reuses_shared_derivation` ·
`test_shared_derivation_does_not_leak_staleness` ·
`test_late_old_extractor_cannot_regress_the_source` · the full `recovery/` suite.
**NOT yet** — real auth (gated on **U6**) · T2 render split (gated on §H's numeric condition) · full
plan-quality evaluation (gated on **U7**).

---

## M13 · Evidence — close the Definition of Done

**User-visible capability** — none new. This milestone produces the **evidence** that the system is
done.
**Implemented** — the E2E suite; the §17 observability questions answered from data; p95 intake
latency recorded on the target provider (**not one sample**); the concurrent-generation benchmark
(closes **U4**, confirming or replacing the `~4–5×` claim).
**Demo** — one command runs intake → plan → correct → approve → generate → render → export against
the stub gateway, and the provenance chain walks back from the artifact to the originating
`Utterance`.
**Tests** — `Implementation-Plan.md` §9's Definition of Done, in full, with evidence per line.
**Exit** — every box ticked with evidence, not with code existing.

---

# 7. Where the frozen machinery lands

| TD machinery | TD § | Milestone | Why there |
|---|---|---|---|
| canonical JSON, `envelope`, `task_key`, `claim_key`, member encoding | §5.1, §5.11a, §5.12, §5.12a | **M0** | every uniqueness constraint is over its output |
| immutability by privilege | §4.4 | **M0** | retrofitting means the mutating code already exists |
| import walls | §15.8 | **M0** | free now, expensive later |
| `core/types`, closed vocabularies | §4.1 | **M1** | — |
| `Utterance` append-only, `request_id`, fingerprint | §4.2, §18.3 | **M1** | the first thing a retry can double |
| `MODEL_CALL` shape, failure classes, jitter, deadline | §8.5, §8.6, §8.6b | **M2** | one provider path from the first call |
| `CallLedger` | §8.8a | **M2** | unrecorded history cannot be reconstructed |
| `DecisionVersion` + envelope column | §4.2, §5.4–§5.9a | **M3** | recorded now, used for reuse at M6 |
| `sufficiency`, span verification, `job`, `scope_tier`, `frame` | §9.1, §5.9a, §6 | **M4** | — |
| eval harness as CI fixture | §15.7 | **M4** | CI must not need a provider |
| `merge`, three merge-time checks, probes, slots | §12.3–§12.5 | **M5** | zero model calls; de-risks the floor |
| capability declaration, both tables, nested hashes | §12.1, §12.2 | **M5** | planning reads it (§12.2a) |
| **Task** states, lease, epoch, cancel, resume, sweep | §8.1–§8.5, §8.7, §8.8 | **M6** | 342 s cannot hold a request |
| the six planning decisions | §9.2 | **M6** | — |
| `extent`, `feasibility` | §12.2a | **M6** | — |
| `DependencyEdge`, `stale()`, sequences | §10.2, §10.2a | **M7** | correction is the first thing that makes a version old |
| `RoutingResult` | §4.2, §9.3 | **M7** | — |
| `Integrity`, `Commitment` + members, `environment_hash`, `approved_extent` | §9.4, §9.4a, §E5 | **M8** | approval is the first refusal |
| **`Claim`, the five operations, `step()`, `PUBLISH`, fencing** | §7.1–§7.3b | **M9** | §1.2a — a semantic precondition of generation |
| `MemoIndex` + memo envelope | §4.2, §5.7a | **M9** | same |
| `Document`, `DocumentConstruction`, `DocumentProvenance`, `ATTACH_PROVENANCE` | §4.2, §5.8, §9.6, §9.6a | **M9** | — |
| `validate_blocks`, approved-shortfall rule, X1 | §9.6, §9.7 | **M9** | the first blocks to validate |
| `ArtifactIndex`, render claim, object storage, signed URLs | §4.2, §9.8, §13.3 | **M10** | the first artifact to keep |
| export resolution, canonical zip | §9.9, §9.9a | **M11** | needs artifacts |
| admission: `calls_admitted`, `UserQuotaBucket`, provider slots | §8.6a, §8.6b ③ | **M12** | needs traffic to tune |
| `FIND_RESULT`, `RECONCILE` | §7.3c | **M12** | a recovery path for an operational failure |
| GC unit rule, reverse deletion order | §10.6, §10.6a | **M12** | nothing to collect before this |
| `step_shared`, `SharedDerivation`, `ATTACH` | §4.2a, §7.3b | **M12** | the envelope is recorded from M6, so no migration |
| source extraction, computed state | §9.8a, §9.8b | **M12** | conditional capability; 1 of 10 corpus cases |
| the §17 event set | §17 | **M12** | — |
| Definition of Done | Impl-Plan §9 | **M13** | — |

**Nothing is dropped.** Every item in `Implementation-Plan.md` §4–§6 appears above with a milestone.

---

# 8. First concrete coding task

**Unchanged from `Implementation-Plan.md` §10 — the reordering does not move it.**

> ## `core/identity` + the import wall
>
> `core/identity/{canonical,envelope,task_key,claim_key,member,content,fingerprint}.py`, plus
> `tests/test_boundaries.py` with the full FORBIDDEN table and `tests/unit/test_identity.py` carrying
> the §15.2 golden table.

**Why it survives the re-ordering.** It is the only module with zero dependencies — no database, no
provider, no browser. Every uniqueness constraint in the schema is over its output, so it is upstream
of M1's first table. And it is where **U1 — which the design calls *"the first thing to get wrong"*** —
is either closed or is not.

**Acceptance criteria** (all from the frozen design):

1. Canonical JSON — UTF-8, keys sorted by code point, no insignificant whitespace, NFC-normalised
   strings, **integers only**.
2. Three constructions, **provably disjoint**: `envelope(kind, member, inputs, env)`,
   `task_key(kind, inputs)`, `claim_key(domain, identity)` — each with its `"domain"`/kind
   discriminator, 128-bit output, `v: 1`.
3. `member` is never null — `""` is the root sentinel, in the payload and later in the column.
4. **The golden table, both directions, and the exclusion half is the bar**: `structure` must not
   change on `entry_point` or `project_id`; `memo` must not change on `commitment_id`, a sibling
   section, `capacity` or `depth_register`; `document` must not change on `commitment_id`; `frame`
   **must** change on sources and purpose and **must not** on `entry_point`.
5. `test_three_key_constructions_are_disjoint` passes.
6. The import wall exists and bites — verify by adding `import httpx` to a `core` module, watching CI
   fail, and removing it.

**Out of scope:** any table, any flow, any model call, `BriefInputs`' field list (it needs `core/types`,
which is M1's work).

**Done when** the golden table covers every kind in TD §5.10, disjointness passes, and the boundary
test fails on an injected violation.

**Then M1**, which is the first milestone with something to show: a project, a conversation, and a
transcript that survives a reload.
