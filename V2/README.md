# myNotes — V1 baseline measurement

Read-only measurement of the frozen V1 prototype, which lives beside this
directory at `../V1`.

**V1 is the baseline. Nothing here modifies it.** The harness puts V1 on
`sys.path`, hands it an explicit store directory and an explicit output
directory, and drives it through the same calls `backend/api.py` makes.

Every record carries a **content hash of V1's source** (`baseline.source_hash`)
and whether it matches the pinned baseline. That is the freeze guard. It is a
content hash rather than `git status` because V1 and V2 now share one working
tree — a dirty tree says nothing about whether V1 itself moved. The pinned value
lives in `harness/baseline.py`:

```
807c8ec99a60d320e745e8ac208b8c7f690ebd273b3930f6680688d159cda116   38 files
```

Verified byte-identical (modulo CRLF, which the restructure introduced) to the
source at commit `1c8a1d7`, the commit the baseline was declared at.

`v1-orphan-approval-gate.patch` is a known V1 defect and its fix, **parked, not
applied**. Applying it changes V1's behaviour and invalidates the hash above.
The harness measures the defect instead.

The purpose is to turn *"things we noticed"* into *"things that happen at rate
N"* — because V1's own history shows single-run conclusions repeatedly misled
(module counts moved between runs, page counts varied, free-tier availability
changed). Nothing here proposes a fix. `V1 → run → measure → record`.

## Layout

```
corpus/
  cases.json            10 cases: request, believed situation, scripted intake
                        answers and corrections, what a good curriculum must do,
                        and what to watch for
  references/           3 hand-written good answers — the yardstick, and the
                        shape a V2 domain model must be able to represent
harness/
  baseline.py           finds V1, records which V1 (commit + dirty flag)
  providers.py          Counting (wraps the real provider, records cost/latency)
                        Stub    (canned answers, no model calls)
  observe.py            what we record about a run — all readings, no repairs
  run.py                the driver
runs/<name>/
  run.json              what was asked for
  records/<case>-t<n>.json   one record per trial, written as it completes
  store/                V1's FileStore for each trial (its own, not V1's out/)
  artifacts/            generated PDFs, when --phase generate
```

## Running

```bash
python -m harness.run --stub                    # no model calls; proves plumbing
python -m harness.run                           # all 10 cases, 1 trial, plan only
python -m harness.run --cases vlsi-underspecified --trials 3
python -m harness.run --phase generate --cases consensus-analogies
```

`V1_ROOT` overrides the V1 location. Provider selection is V1's own
(`OPENROUTER_API_KEY` etc. from V1's `.env`) — the harness chooses no model.

**Resume is the default.** A trial that already has a record is skipped, so a run
killed by a rate limit at case 7 keeps cases 1–6. `--force` redoes them.
A trial that fails is recorded as a failure and the run continues.

### What a run costs

Measured from stub runs, per trial, `--phase plan`:

| | calls |
|---|---|
| interpret | 1 |
| ask (only if the decider named an axis) | 0–1 |
| each scripted intake answer (re-reads: interpret + ask) | 1–2 each |
| derive | 1 |
| plan | 1 |
| each correction | 1 |
| **typical total** | **4–7** |

So **10 cases × 1 trial ≈ 50 calls** — one full day of the OpenRouter free
budget (50/day, account-wide across every `:free` model). Three trials is three
days. `--phase generate` adds roughly one call per concept in the generated
module, plus a Chromium render, for the six cases that request generation.

Start with one trial across all ten. Repeat trials matter most for the cases
where variance is the question (`vlsi-underspecified`, `ml-weekend-conflict`).

## What is recorded

Per trial: the interpreted situation · every axis reading with its strength,
materiality and whether it was asked · questions written and their options · the
derived concept landscape with dependency edges and families · relevance
exclusions · scope with depth and `anticipates` distributions · the module
partition with per-module capability · V1's own coherence and capability-support
diagnostics · extent · feasibility shortfalls · every correction with what the
router claimed vs what actually changed · approval outcome · per-module
generation with fulfilment, treatments anticipated vs produced, and the
representation report · model, provider, per-call latency and tokens · failures
with tracebacks.

Three readings are computed **here**, because V1 does not compute them:

- **orphans / phantoms** — concepts approved and belonging to no module, and the
  mirror. Found by code reading; measured rather than fixed, because V1 is frozen.
- **duplicate_coverage** — a concept claimed by two modules.
- **slug_collisions** — two module titles naming the same PDF file, computed with
  V1's own `slugify` so it reports what V1 would actually do.

## Rules

- Do not modify V1 to improve a number. The point is what V1 does.
- Do not analyse `--stub` runs. They carry `"stub": true` and their plans are
  nonsense; they exist to prove the harness, not V1.
- Do not promote a single observed failure to a V2 requirement. That is what the
  repeated trials are for.
- A record with `baseline.matches_baseline: false` is not baseline data.
