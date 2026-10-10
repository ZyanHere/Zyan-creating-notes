# Pre-Implementation Decisions

Three decisions settled before any code beyond `core/identity`. **No frozen document is modified.**
`Build-Plan.md`'s milestone list is updated, which is a plan and not frozen.

---

# D1 · DBOS Transact — decision and timing

## You were right about the timing, and my M6 recommendation was wrong

The challenge is correct and worth stating as a principle: **a spike whose purpose is to inform a
decision must happen before the decision, not after the implementation.** Spiking at M6 means either
throwing away tested concurrency code, or — far more likely — sunk-cost bias keeping it. I put the
spike at M6 because that is where the Task layer appears in the plan, which is the wrong reason.

And the spike needs **none of our code.** It needs Postgres and a scratch script. There is no
dependency forcing it late.

## What I verified since the landscape review

All three questions I previously listed as blockers are now answered from documentation.

| Question | Answer | Source |
|---|---|---|
| **Can DBOS coexist with our schema?** | **Yes.** It keeps system tables in its own schema, renameable via the `dbos_system_schema` config key, with its own migration ledger at `dbos.dbos_migrations`. Critically, `migrations: False` makes a process **verify** the schema instead of altering it — intended for *"a deployment that migrates out of band"* or a role without DDL | [system tables](https://docs.dbos.dev/explanations/system-tables), [configuration](https://docs.dbos.dev/python/reference/configuration) |
| **Does it provide fencing?** | **Functionally yes, by a different mechanism.** `workflow_status.owner_xid` — *"The ownership token of the execution currently running this workflow, used to detect concurrent executions. Null when no execution owns the workflow."* Plus `executor_id` and `recovery_attempts` | [system tables](https://docs.dbos.dev/explanations/system-tables) |
| **Python 3.14?** | **Yes.** `requires-python = ">=3.10"`, classifiers list 3.10–3.14 | [pyproject.toml](https://github.com/dbos-inc/dbos-transact-py/blob/main/pyproject.toml) |

**So the gates are not the question any more.** The question has moved, and become sharper.

## The real question, which I had not identified

Our §7.3a `PUBLISH` is **one transaction** containing the claim CAS *and* the result metadata rows.
That atomicity is the fix for Rev. 7's worst bug — a claim saying *"done"* with no version row.

If DBOS owns step-completion as *its own* transaction in *its own* schema, then a step checkpoint and
our publication are **two transactions**, and a crash between them reopens exactly the window we
closed:

```
DBOS: "step 3 complete"  committed
our PUBLISH              rolled back
→ the workflow will never retry step 3, and the result does not exist
```

**But there is a version where this is strictly better than what we have.** DBOS's whole mechanism is
database checkpointing — *"each step ends with a DB transaction storing state."* If its system tables
live in the **same Postgres database** as ours, a DBOS transaction step can include our publication
writes, and the step checkpoint and the publication become **genuinely atomic**. That is a stronger
guarantee than our design currently has, because today the Task's progress record and the publication
are separate.

So the spike is not *"does DBOS work."* It is **"can a DBOS step checkpoint and our PUBLISH commit in
one transaction?"** That one question decides everything else.

## Decision: **C — spike first**, and it is the next architectural action

Not M6. **Immediately after `core/identity`, and before M1's `0001_init.sql`** — because if DBOS is
adopted, the first migration must account for a second schema in the same database, and retrofitting
that is a migration rather than an edit.

```
M0  core/identity  ────►  D1 SPIKE  ────►  M1  schema + auth + conversation
                          (half a day)      (migration shape depends on the outcome)
```

### The spike, specified

**Setup:** a scratch Postgres (`docker compose up postgres`), `uv add dbos`, one file, no MyNotes code.

**Six questions, in priority order. Question 1 is the gate; if it fails, stop.**

| # | Question | How to answer it | Pass means |
|---|---|---|---|
| **1** | Can a DBOS step checkpoint and an arbitrary application write commit in **one** transaction, in the same database? | declare a workflow with a transaction step that inserts into a `public.probe` table; kill the process mid-step; assert either both or neither landed | our `PUBLISH` can be a DBOS transaction step |
| **2** | Does `owner_xid` actually fence a **zombie**? | start a workflow, suspend the process (`SIGSTOP`), let another executor recover it, resume the first and let it try to complete | a stale owner's completion is rejected |
| **3** | Is our per-kind `task_key` expressible as the workflow id? | `SetWorkflowID(task_key(...))`, then start twice | second start is a no-op — exactly-once |
| **4** | Is `incomplete` with **per-member progress** expressible? | a workflow fanning out to 5 children where 1 fails; resume | the 4 successes are not re-run and the 1 failure is identifiable |
| **5** | Can resume grant a **fresh budget**? | resume a workflow and observe whether per-attempt state can be reset while cumulative state persists | our §8.8 semantics survive |
| **6** | Do DBOS **queues** give us concurrency + rate limiting? | a queue with `concurrency=2`, submit 8 | exactly 2 run concurrently |

### Pre-committed decision rule — written now, so the spike cannot end in *"interesting"*

```
ADOPT (full)      Q1 passes AND Q2 passes AND Q4 passes
                  → DBOS replaces work/{states,lease,lifecycle,coordinator}.py
                  → our PUBLISH becomes a DBOS transaction step — STRONGER than today
                  → the Claim protocol, MemoIndex, SharedDerivation and RECONCILE stay ours

ADOPT (partial)   Q1 fails BUT Q6 passes
                  → keep our Task layer; use DBOS QUEUES for provider concurrency and
                    rate limiting, replacing gateway/slots.py and part of §8.6a
                  → this is a real middle option and I would have missed it

REJECT            Q1 fails AND Q6 fails, or Q2 fails
                  → keep ours. Record the finding in this file and move on without
                    revisiting. Q2 failing is disqualifying: a lease without real
                    fencing is unsafe for our R2 timeline, and that is not negotiable
```

**Timebox: half a day.** If Q1 is unanswerable in that time, that is itself a reject — a mechanism we
cannot establish in half a day is not a mechanism we should put in the correctness kernel.

## What would be replaced, and what stays ours — regardless of outcome

| | Full adopt | Partial | Reject |
|---|---|---|---|
| Task state machine, lease, epoch, heartbeat | **DBOS** | ours | ours |
| orphan sweep / recovery on restart | **DBOS** | ours | ours |
| cancel / resume | **DBOS** `DBOSClient` + our budget rules | ours | ours |
| provider concurrency + rate limit | **DBOS queues** | **DBOS queues** | ours |
| Task identity (`task_key`) | **ours**, as the workflow id | ours | ours |
| **Claim protocol** (content-addressed, fencing, publication) | **ours** | ours | ours |
| `MemoIndex`, `SharedDerivation`, `RECONCILE` | **ours** | ours | ours |
| `CallLedger`, `UserQuotaBucket`, Task budget | **ours** | ours | ours |
| every `core/` function | **ours** | ours | ours |

**The Claim protocol survives every outcome**, and that is the point worth holding onto: DBOS
checkpoints by *position within one workflow*; our claims address by *content across all workflows and
all projects*. §5.7a's memo reuse, §4.2a's cross-project sharing and §7.3c's `RECONCILE` are not
expressible as workflow checkpoints. That is the design's actual intellectual content and no engine
provides it.

---

# D2 · Authentication — your instinct is right, and the design already requires it

## Not a deferral question. A boundary-placement question.

Your concern is correct and the cost asymmetry is stark:

```
establish the boundary now      ~150 lines, one adapter, one dependency
retrofit it later               every handler, every store call, every test fixture
```

**And more importantly: the frozen design already requires a principal.** TD §13.4 — *"a Task is
readable and cancellable only by its project's owner."* §4.2 — `Project.user_id`, `Commitment.approved_by`.
§13.1 — *"every read path takes `(user_id, project_id)` and filters on both."*

So the design assumes an authenticated identity exists and simply does not specify the **mechanism**.
Building that mechanism at M1 is **implementing the frozen design, not amending it.** There is no
conflict to resolve.

What §13 actually defers is *production* auth: registration, OIDC, password reset, roles. Those stay
deferred.

## Evaluating your proposal rather than agreeing with it

| Option | Verdict |
|---|---|
| **hardcoded dev user + opaque session token, server-side** | **Recommended.** See below |
| hardcoded dev user + **JWT** | **Rejected.** Current guidance for first-party single-backend apps is explicit: *"for session tokens specifically, opaque tokens with server-side state are often the better choice"*, because *"revocation is not real-time without a check against a revocation list, which negates much of the point of JWTs."* A denylist is a session store with extra steps |
| in-memory session dict | Rejected — re-login on every reload, and it never exercises revocation, which is one of the two things the boundary exists to get right |
| signed stateless cookie, no store | Rejected for the same reason: logout becomes a lie |
| **dev adapter behind a port** | **Adopted — this is the architecturally important half**, orthogonal to the token mechanism |
| OAuth/OIDC now | Rejected — premature, and gated on U6 |

Sources: [JWT vs opaque tokens 2026](https://guptadeepak.com/jwt-vs-opaque-tokens-api-authentication-2026/),
[stop defaulting to JWTs](https://reptile.haus/journal/stop-defaulting-to-jwts-choosing-the-right-session-architecture-in-2026/),
[session management](https://identitysecurity.tech/paths/session-management/),
[token lifetimes](https://guptadeepak.com/ciam-compass/guides/token-lifetime-best-practices/).

**One nuance worth knowing:** the 2026 default for *distributed, multi-service* systems is hybrid —
short-lived JWT access tokens plus opaque refresh tokens. That is the right answer when validating a
token must not require a database round trip across services. We have **one backend and one database
we already query on every request**, so the JWT half buys nothing and costs revocation.

## The minimal implementation

```
ports/auth.py
    Principal          frozen dataclass: user_id, display_name, issued_at
    Authenticator      Protocol: verify(credentials) -> Principal | None
    SessionStore       Protocol: create(principal) -> token
                                 resolve(token) -> Principal | None
                                 revoke(token) -> None

backend/auth/dev.py        DevAuthenticator — ONE account, from config.
                           Refuses to construct when APP_ENV != "local" unless
                           DEV_AUTH_ALLOWED=1 is set explicitly.
backend/auth/session.py    opaque token: secrets.token_urlsafe(32)
                           stored hashed (sha256) — a leaked DB must not yield live tokens
backend/api/deps.py        current_principal() — the FastAPI dependency. The ONLY place a
                           request becomes an identity.

store/pg/sessions.py       Session: token_hash PK · user_id · created_at · expires_at ·
                           last_seen_at.  The 21st table — infrastructure state, same class
                           as Task, collectable on expiry.
```

**Transport: `httpOnly`, `Secure`, `SameSite=Lax` cookie.** Not an `Authorization` header.

- a cookie the browser cannot read survives XSS; a token in JS does not
- our frontend is first-party, so there is no third-party-cookie problem
- `localhost:3000` → `localhost:8000` are different *origins* but the same *site*, so `Lax` works —
  with `allow_credentials=True` and an **explicit** origin list in CORS (never `*`, which browsers
  refuse alongside credentials). Our `config.Server.cors_origins` is already explicit

**The three endpoints:**

```
POST /auth/login     {username, password} → sets the cookie, returns {display_name}
POST /auth/logout    revokes the session server-side, clears the cookie
GET  /auth/me        → Principal, or 401
```

## What makes this swappable rather than throwaway

Production auth replaces **one file**: `backend/auth/dev.py` becomes `backend/auth/oidc.py`. The
`Authenticator` Protocol, the `SessionStore`, the dependency, and every call site are unchanged —
because none of them knows how a credential was verified.

That is the entire point, and it is why the port matters more than the token format.

## Authorization, which is the half that is easy to forget

Authentication answers *who*. **Authorization is what the design actually requires**, and it is a
one-line discipline enforced by a test:

```
every project-scoped repository method takes a Principal (or user_id) and filters on it.
no handler reads a project by id alone.
```

Two tests at M1, both named in the frozen design's spirit:

```
test_unauthenticated_request_is_refused         every project route → 401
test_cannot_read_another_users_project          user A's token, user B's project → 404 (not 403)
```

**404, not 403** — deliberately. A 403 confirms the resource exists, which is an enumeration oracle.

## What is explicitly NOT built

No user table, no registration, no password reset, no email, no OAuth provider, no roles, no billing,
no enterprise IAM. One account, from config, refusing to exist outside local without an explicit flag.

**And one thing I would add that you did not ask for, because it is nearly free:** note in
`0001_init.sql` that every project-scoped table carries `user_id` **so Postgres row-level security
remains possible later.** Do not enable RLS. Just do not design it out — retrofitting RLS onto a schema
is painful, and designing so it stays available costs a comment.

---

# D3 · Milestone sequence — auth moves into M1

**Yes.** And your framing is the better one: *"log in → create project → have a conversation"* is a
more honest first demo than pretending an identity exists.

I considered giving auth its own milestone and rejected it: the demo would be *"you can log in and do
nothing,"* which is a worse milestone than either half. It is ~150 lines and belongs with the first
thing it protects.

## Updated sequence

```
M0   Skeleton · import wall · identity kernel                      ← in progress
D1   DBOS SPIKE — half a day, gates M1's migration shape           ← NEXT, after core/identity
M1   Dev authentication + project + conversation                   ← renamed, auth folded in
M2   First real model call (MODEL_CALL + CallLedger + trace id)
M3   Multi-turn conversation
M4   Real intake + evals-as-CI-fixture
M5   Renderer proof + capability declaration
M6   Planning + Task system   ← shape decided by D1, not discovered during it
M7   Plan revision
M8   Approval
M9   Generation (claims + memo + fencing)
M10  The real PDF
M11  Export
M12  Hardening
M13  Evidence
```

**Only two things changed:** D1 inserted as a gate before M1, and M1 gained auth. M2–M13 are
untouched.

### M1 restated in the seven-question format

**User-visible capability** — open MyNotes, log in with the development account, create a project, send
messages, reload, the transcript is still there and belongs to you.

**Components** — `client` · `backend/{auth,api}` · `ports/auth.py` · `store/pg` · Postgres.

**Foundations introduced** — `core/types` · the **authentication boundary** (`Principal`,
`Authenticator`, `SessionStore`) · opaque session tokens, hashed at rest · `Utterance` append-only with
`ord` slot-bump and `request_id` + fingerprint · **authorization on every project-scoped read** ·
`0001_init.sql` with immutability grants and an RLS-compatibility note.

**Implemented** — `core/types/*`; `ports/auth.py`; `backend/auth/{dev,session}.py`;
`backend/api/{deps,auth,conversation}.py`; `store/pg/{sessions,decisions}.py`; `0001_init.sql`; the
client's login and conversation views.

**Demo** — visit the app unauthenticated → redirected to login. Log in as the dev account. Create a
project, type three messages, reload: all there. Log out: the session is gone server-side, and the old
cookie is refused.

**Tests** —
`test_unauthenticated_request_is_refused` ·
`test_cannot_read_another_users_project` (→ 404) ·
`test_logout_revokes_server_side` (the token fails after logout, proving the store is authoritative) ·
`test_session_token_is_hashed_at_rest` (the raw token never appears in the DB) ·
`test_dev_authenticator_refuses_outside_local` ·
`test_intake_retry_does_not_double_append` ·
`test_request_id_mismatch_returns_409` ·
`test_concurrent_appends_get_distinct_ord` ·
utterances are immutable by privilege.

**NOT yet** — any model call, registration, OAuth, roles, password reset, email, RLS enforcement.

---

# D4 · The methodology rule, recorded

Adopted as a standing rule for this project. It now applies to every technology recommendation I make
here.

```
Problem
   ↓  what are we actually solving
Technology category
   ↓  what is this KIND of thing called — the step that was missing
Current ecosystem
   ↓  mature · modern · emerging, with maturity stated
Tradeoff analysis
   ↓  including operational cost and lock-in
Recommendation
   ↓
Explicitly document what was rejected and why
```

**The commitments inside it:**

- You should never need to know a technology's name before I consider it.
- If something is relevant and we do not need it: *"This exists. It solves X. We do not need it
  because Y."*
- If it could become relevant: **a trigger**, not a date.
- If you should learn it regardless of whether MyNotes uses it, I say so.

`Learning-Map.md` is the first product of this rule.

---

# D5 · The development platform is Linux, via WSL2

Not a preference. Found by running the quality gates for the first time, which is what the first run of
a gate is for.

## The finding

`psycopg` **cannot import on the Windows dev machine.** Smart App Control is Enforced
(`VerifiedAndReputablePolicyState = 1`), and it blocks low-reputation unsigned binaries:

| | |
|---|---|
| `pydantic_core` · `httptools` · `watchfiles` · `websockets` · `playwright` | load fine |
| **`psycopg`** — `_psycopg.pyd` | **blocked** |
| `hypothesis` — `_native.pyd` | **blocked** |

Prevalence, not correctness: the widely-downloaded wheels are reputation-trusted and the rest are not.
`psycopg` is a hard dependency, so this is the entire store layer — M1, every claim operation, and
**D1's spike**, which needs a real Postgres within half a day.

`hypothesis` is worse than it looks: pytest loads its plugin through entry points, so *installing* it
fails every test in the suite, including tests that never mention it. It is backed out of
`pyproject.toml` with that reason recorded, and goes back in with the first property test.

## Decision: WSL2, and it was already on the path

| Option | Verdict |
|---|---|
| **WSL2 + Ubuntu** | **Adopted.** |
| Turn Smart App Control off | Rejected. **Irreversible** — re-enabling needs a Windows reinstall — and it still leaves no Postgres and no Docker, so the database problem survives it. |
| Native Postgres + `psycopg[pool]` against a signed `libpq` | Rejected as the narrow fix. Solves `psycopg` and nothing else: `hypothesis` stays blocked, `docker-compose.yml` stays unusable, and the next low-prevalence wheel hits the same wall. |

The argument that decided it is that **WSL2 was already assumed by this repository.** `docker-compose.yml`
and `make db` require Docker, and Docker Desktop on Windows 11 Home requires WSL2. So WSL2 was never the
extra step — the Windows-native toolchain was.

Three things fall out of it, all of them improvements:

- **The dev platform now matches CI** (`runs-on: ubuntu-latest`) **and production.** The claim protocol's
  correctness *is* database atomicity, and the renderer's measured footprint is a Linux number. A dev
  environment that differs from both was a latent source of findings that reproduce in only one place.
- **Docker Desktop is not needed.** `docker-compose.yml` is a plain `postgres:17` — password `postgres`,
  database `mynotes_v2`, port 5432, no extensions. Postgres 17 from the PGDG apt repository is
  equivalent and ~2 GB lighter. The compose file stays: it still pins the version for anyone who has
  Docker, and the pin matters (`ON CONFLICT ... DO UPDATE ... WHERE`, and NULL-distinctness in UNIQUE).
- **`uv.lock` survives.** uv resolves for all platforms in one lockfile, so the lock is reused as-is.
  Only `.venv` is platform-specific and gets rebuilt.

The frontend stays on Windows. WSL2 forwards `localhost`, so `npm run dev` reaches the backend on
`localhost:8000` with no change — which is exactly the process boundary the design already chose.

## Runbook

```
#  Windows, in an ADMIN PowerShell — needs a reboot
wsl --install

#  then, inside Ubuntu
curl -LsSf https://astral.sh/uv/install.sh | sh

sudo apt install -y curl ca-certificates
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
     --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  | sudo tee /etc/apt/sources.list.d/pgdg.list
sudo apt update && sudo apt install -y postgresql-17

sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres'"
sudo -u postgres createdb mynotes_v2

cd /mnt/d/myNotes/V2
uv sync --frozen --all-extras
make check
```

`DB_URL=postgresql://postgres:postgres@localhost:5432/mynotes_v2` — the same string CI uses, which is
the point.

## What the first gate run found, recorded because the reasons matter more than the diffs

Seventeen findings. Three were real.

- **`pytest-asyncio` — our own upper bound was the defect.** The 0.x line calls
  `asyncio.get_event_loop_policy()`, deprecated in 3.14, and `filterwarnings = ["error"]` turned that
  into a failure in *every* test. The pin `<1` excluded the 1.x line that fixes it. Bumped to
  `>=1.0,<2`. The alternative was weakening the warning policy, which would have hidden this instead of
  surfacing it on day one. Async itself is not in question — TD §4: *"Task workers: async coroutines,
  one per leased Task."*
- **`find_spec`, not `try: import`.** Both of pyright's complaints were about probing modules that do
  not exist until M1 (`backend.api.asgi`) and M5 (`engine.capability.version`). We never wanted the
  symbols — only *"does this module exist."* `app.py` hands uvicorn a string and uvicorn does its own
  importing; `health.py` already guarded with `getattr(..., None)`, so it was half static and half
  dynamic. Both now use `importlib.util.find_spec`, with **zero suppressions**. pyright was right and
  the code was dishonest about what it was doing.
- **`# fmt: off` on `FORBIDDEN`.** The one place the formatter was overruled. One string per line turns
  a 40-line grid into 100, and that table is where the architecture is legible or nowhere.

Of the seven `PLC0415` deferred-import findings, four were sloppiness and were hoisted to module scope;
three were genuine optional-dependency probes. A rule that splits 4/3 on first contact is a rule worth
keeping.

---

# Next coding task

**Unchanged: `core/identity`.** None of D1–D5 changes it — it has no dependency on the Task layer, on
auth, on the schema, or on anything Smart App Control blocked. It is pure functions over strings.

```
core/identity/{canonical,envelope,task_key,claim_key,member,content,fingerprint}.py
tests/test_boundaries.py            already written, and it bites
tests/unit/test_identity.py         the §15.2 golden table, both directions
tests/unit/test_identity_props.py   Hypothesis properties — needs D5's environment
```

D5 orders these but does not block the first two: the golden table runs anywhere, and the property
tests are the half that needs Linux. Writing the module on Windows and the properties after is a
worse split than doing both in the environment they will live in, so **D5 first** — it is one command
and a reboot, against the alternative of touching `core/identity` twice.

**Then D1's spike, before M1's migration.** That ordering is the one real change the earlier review
produced, and it exists so the Task layer's shape is a *decision* rather than a discovery. The spike
needs a real Postgres, so it depends on D5 outright.

## Current state of M0

```
skeleton                 done — 39 files, 6 packages, CI, Makefile, config, ports/clock, obs/log
import wall              done — 9 tests passing, verified to fail on an injected `import httpx`
lint · format · types    GREEN for the first time (ruff 0.17, pyright 1.1.414 strict, 0 errors)
uv.lock                  generated, 1213 lines, cross-platform
identity kernel          NOT STARTED  ← the task
dev environment          D5 pending — admin `wsl --install` and a reboot
```
