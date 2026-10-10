# MyNotes V2

Turns a request like *"notes on transformers for an interview in two weeks"* into an
approved curriculum and a set of PDFs — where **what gets written is what you
approved.**

V2 is a rebuild. V1 works and is frozen as the measurement baseline; `design/` holds
the investigation that produced this design, the frozen contract, and the recorded
runs it was measured against.

---

## Start here

```bash
cd V2
make bootstrap        # installs uv, syncs the locked environment
make db               # local Postgres
cp .env.example .env  # then fill PROVIDER_API_KEY
make check            # lint, types, boundaries, tests
make run              # backend on :8000
```

The frontend is a **separate process in a separate terminal** — the browser calls the
backend directly, so no serverless timeout enters a 342-second plan turn:

```bash
npm --prefix client run dev     # :3000
```

PowerShell, if `make` is unavailable:

```powershell
uv sync --all-extras
uv run ruff check . ; uv run pyright ; uv run pytest
uv run python -m backend.app
```

---

## Layout

```
core/       pure domain logic. No I/O, no database, no provider, no HTTP.
ports/      Protocol definitions. No implementations.
agent/      everything that reasons with a model: prompts, intake, planning, generation
engine/     the renderer: templates, capability declaration, Chromium
backend/    API, orchestration, persistence, tasks, claims, the model gateway
obs/        structured events
design/     the frozen contract, the investigation, and the recorded runs
infra/      image and deploy
tests/      boundaries, unit, repo, protocol, concurrency, workflow, recovery, e2e
```

**Five packages, five boundaries, enforced by a test.** `tests/test_boundaries.py` is
an AST wall, not a convention:

- `core` imports nothing but `core` — which is what makes *"a pure function cannot
  reach a store"* mechanical rather than reviewed
- `engine` may not import `core.types` — it renders a document-shaped **mapping**, and
  that boundary is why a template fix costs a render (~3.4 s) instead of a generation
  (~323 s)
- only `backend/gateway` may import a provider SDK or an HTTP client — every model
  call goes through one path
- `agent` never touches persistence

A failing boundary test is an architectural regression, which is why CI runs it as its
own job.

---

## Where the design lives

| | |
|---|---|
| `design/frozen/Domain-Model.md` | what the objects are, and which judgments can be wrong independently |
| `design/frozen/Architecture.md` | components, and the measurements that chose them |
| `design/frozen/Technical-Design.md` | **the implementation contract** — identities, the claim protocol, schema, flows |
| `design/plans/Build-Plan.md` | the milestones, in the order we are building them |
| `design/plans/Implementation-Plan.md` | design→code mapping, table inventory, interfaces, Definition of Done |
| `design/investigations/` | the nine section investigations and the measured defect ledger |
| `design/evidence/` | the corpus, the harness, and the recorded runs — also the CI fixture |

**The design is frozen.** It changes only if implementation finds a contradiction that
makes the system unbuildable as specified — recorded as a named finding against a
named section, with the trace that proves it.

---

## Current state

Building **M0** — skeleton, import wall, identity kernel. See
`design/plans/Build-Plan.md` for the thirteen milestones and what each one makes
demoable.

| | |
|---|---|
| ✅ | repository layout, import wall, config, logging, `/health`, entry point |
| ⬜ | `core/identity` — canonical JSON and the three key constructions |
| ⬜ | M1 — a project with a conversation that survives a reload |

Running it today prints what it knows and what it does not:

```
  backend running   http://127.0.0.1:8000
  model             nvidia/nemotron-3-ultra-550b-a55b:free   (NO API KEY SET)
  renderer          not_built - engine arrives with M5
  database          not_built - pool arrives with M1
```

`/health` answers from **this** process on purpose: a check run in a terminal proves
nothing about a server started somewhere else, and that distinction cost V1 three
rounds of diagnosis.
