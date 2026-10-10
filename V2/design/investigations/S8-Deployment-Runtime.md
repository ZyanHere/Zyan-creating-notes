# §8 — Deployment and Runtime

A deep read of one section. **No design, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**The section with no artefacts.** There is no Dockerfile, no deploy config, no CI, and
no container. What exists is a well-made local dev entry point and a set of runtime
behaviours that were correct for a laptop and are the binding constraints on everything
else.

---

## 1. What this section actually is

**Responsibility.** Run the backend somewhere a user can reach, keep long work alive,
and make the prerequisites visible before they cost anything.

**Starts** at process launch. **Ends** at a served response — and, in practice, at the
question *"what does this cost to run?"*, which every earlier section defers to here.

---

## 2. What exists today

### The entry point

`[OBSERVED]` `backend/app.py`. Deliberate and documented:

- `timeout_keep_alive = 900`, with the reason: *"A plan turn is one or two model calls
  and runs for minutes. Uvicorn's default of 5 seconds closes the connection underneath
  it, and the browser reports the result as 'Failed to fetch' — a network error for what
  was really a working server still thinking. **This is not a tuning knob.**"*
- A port-in-use check, because *"Uvicorn's own message for this is 'only one usage of
  each socket address is normally permitted', which is true and unhelpful."*
- A startup banner printing the **resolved model** and **renderer status** — *"'nothing
  happens when I click' has twice turned out to be the model, and knowing which one is
  the first thing worth checking."*
- `os.chdir(ROOT)` before any import, because `out/` is working-directory-relative.
- `--reload` off by default, warning that *"saving a file will kill any turn in
  progress."*

### `/health`

`[OBSERVED]` Returns `{status, renderer: browser_status()}`, and the docstring states
the principle that cost three rounds of diagnosis:

> *"The answer that matters is the one **this process** computes: a check run in a
> terminal proves nothing about a server started from somewhere else."*

### Background work

`[OBSERVED]` `backend/jobs.py`, and it is honest about its scope:

> *"**Not a job queue.** No persistence, no retries, no fan-out, no worker pool …
> What is here is the smallest thing that lets a browser watch a long call: a thread, a
> status, and a result. When M4 arrives this is replaced, not extended."*
>
> *"One deliberate consequence: a restart loses running jobs. Finished ones survive,
> because their artifact is on disk and the file is the record — so the failure mode is
> 'you have to press it again', never 'it silently half-happened'."*

Idempotent by key: *"a double-click on Generate must not spend two model calls."*
`generate_module` calls `JOBS.forget(key)` then `JOBS.start(key, …)`; `forget` only
removes non-running jobs and `start` returns an existing running one, so the double-click
case is correct.

### Concurrency shape

`[OBSERVED]` Endpoints are `def`, not `async def` — so FastAPI runs them in its
threadpool and the event loop stays free. `render_pdf` uses `playwright.sync_api`.
Generation runs on a `daemon=True` thread per module.

### Provider resilience

`[OBSERVED]` `agent/providers.py`: `TIMEOUT = httpx.Timeout(600.0, connect=15.0)`,
`_TRANSIENT_ATTEMPTS = 3`, linear backoff `_TRANSIENT_BACKOFF * (attempt + 1)`.
Named exceptions: `ProviderUnavailable` (retries exhausted), `ProviderRefused` (4xx),
`NoProviderConfigured`, `OutputTruncated` — all mapped by `_guard` to 503/502 rather than
escaping as 500s with a traceback.

### What is absent

`[OBSERVED]` No Dockerfile. No `render.yaml`/`fly.toml`/`vercel.json`. No CI. No auth —
`USER = "local"`. CORS hardcoded to `http://localhost:3000` and `http://127.0.0.1:3000`.
No graceful shutdown or drain.

---

## 3. Problems

### Observed

**A single model call can burn ~30 minutes before failing.** `[OBSERVED + MEASURED]`
600s timeout × 3 attempts, plus linear backoff. That is the mechanism behind
`contract-act-authority`'s **11,537 seconds** — 3.2 hours across 4 calls, ending in
`getaddrinfo failed`. The retry is correct in principle and its *cost* is unbounded from
the caller's point of view: nothing above it can say *"give up after N minutes."*

`[INFERENCE]` Backoff is linear with **no jitter**, so concurrent callers hitting the
same overloaded provider retry in lockstep.

**Unbounded threads, each able to launch Chromium.** `[OBSERVED]` One daemon thread per
module generation, no pool, no semaphore. Each calls `render_pdf`, which launches a fresh
browser. **N concurrent generations = N Chromium processes.**

**`Jobs._jobs` grows for the life of the process.** `[OBSERVED]` A finished job is
evicted only when the **same key** is started again (`forget` immediately precedes
`start`). A module generated once and never regenerated leaves its `Job` — with its
`GenerateResult` and, on failure, a full traceback string — in the dict forever. Modest
per entry, unbounded in count.

**A restart loses running jobs.** `[OBSERVED]` Deliberate, documented, and the failure
mode is the right one. It is still the reason a 323-second generation cannot survive a
deploy.

**Planning holds the HTTP request.** `[OBSERVED + MEASURED]` `force_plan` is sync;
measured 342s. `jobs.py` solves exactly this shape and only generation uses it.
`/generate`'s own docstring admits the pattern: *"Synchronous through M3 … until M4 moves
this to background execution."*

**Everything is synchronous (CC4).** `[OBSERVED]` Agent, engine and service. This is why
§4's ~4× parallelism win is invisible as an option — the code shape forbids it, and
`sync_playwright` anchors it in the renderer.

**No auth, one shared provider key.** `[OBSERVED]` A public URL lets anyone spend the
quota and generate arbitrary content on the account.

**CORS is hardcoded to localhost.** `[OBSERVED]` Correct for dev; one env var from being
deployable.

**Chromium is the deployment floor.** `[OBSERVED]` ~700 MB across two builds, absent
after `pip install`, and invisible until the last step of a paid generation.
`Runtime-Dependencies.md` exists because that cost three rounds of diagnosis, and it
records the sandbox case where every shell check reported success while the server
correctly reported the browser missing.

**Fonts and egress change output rather than failing.** `[OBSERVED]` Three of four
templates fetch `fonts.googleapis.com`; `networkidle` waits them out; fallbacks change
pagination. `Runtime-Dependencies.md` §5 prescribes pinning a font set in the image —
there is no image.

**Ephemeral disk wipes everything.** `[INFERENCE]` Project state, artifacts and the
retained Document JSON all live under `out/`.

### Measured

**The free tier dominates every measurement.** `[MEASURED]` Across two baseline attempts:
**7 network failures** (`getaddrinfo failed`, 502 `Service temporarily overloaded`,
`WinError 10054`) and **2 model-output failures**. 4 of 10 cases never produced a plan for
reasons unrelated to V1.

`[INFERENCE]` So the deployment question and the measurement question are the same
question: **a stable provider is a prerequisite for measuring anything else**, and it is a
spending decision rather than an engineering one.

### Passes worth recording

`[OBSERVED]`

- **The browser check runs before the model call**, in `service.generate`, *"because the
  model call between the two takes minutes and is billed, and its output is not persisted
  until after the render succeeds."*
- **The check is narrow on purpose** — it refuses only on *absent*, never on a failed
  trial launch, because *"it must never be the reason a healthy run does not happen."*
- **Provider errors are typed and mapped**, not leaked as 500s.
- **`/health` answers from the process that renders.**
- **Job idempotency by key** — a double-click costs nothing.
- **The banner prints what actually matters** for the two most common confusions.

### Strong inference

- **The deployment blocker is the process model, not Chromium.** Browser-per-render **+**
  unbounded threads **+** 512 MB is the fatal combination. Fix any one and it survives.
- **This section is where every other section's deferred cost lands.** §2's 342s, §4's
  323s and §6's browser all become one number here, and that number is unmeasured.
- **The honest framing is not "how do we deploy V1" but "what would V1 cost to run."**
  Nothing in the repository answers that.

### Unknown — and these gate the most

- **Peak RSS of one render.** `[UNKNOWN]` The single most consequential unmeasured number
  in the product.
- **Concurrent render ceiling.** `[UNKNOWN]`
- **Steady-state memory of the process** after N generations, given the job dict.
  `[UNKNOWN]`
- **What a real deployment costs** on a paid provider per module. `[UNKNOWN]` — we have
  token counts (≈57k in / 32k out per module) but have never priced them.
- **Is the deployment a portfolio link or a product?** `[UNKNOWN]` and it changes the auth,
  storage and quota answers entirely.

---

## 4. The key architectural question

**What is the unit of deployment, and what is the unit of work?**

V1 answers *"one process, one thread per job"* — and three separate constraints push
against that `[INFERENCE]`:

| Constraint | Wants |
|---|---|
| Chromium's footprint | a bounded number of concurrent renders |
| A 323s generation | work that survives a restart |
| A 342s plan turn | work that is not in the request path |

All three are the **same** requirement wearing three hats: **durable, bounded background
work**. `jobs.py` provides one of the three (out of the request path), for one of the two
long operations, and says so.

**The second question is the memory one, and it is narrower than it looks.** The renderer
is the only heavy component, and §6 established that only *one* of its four measurements
genuinely needs a browser. So the deployment question decomposes:

1. Does a pooled browser fit the target instance? → measurement
2. If not, is a non-browser renderer possible? → §6's question
3. If not, is a separate render service acceptable? → an architecture choice

**Nothing can be decided before (1)**, and (1) needs no model calls.

---

## 5. Where this section starts and ends

**Current** `[OBSERVED]`: one uvicorn process; the frontend is separate and always was;
`agent/` and `engine/` are libraries this process imports — *"There is nothing else to
run."*

**Boundaries worth questioning** `[INFERENCE]`:

- **The renderer's co-location is the live question.** In-process makes the browser's
  lifetime the request's and puts 700 MB in the backend image.
- **The job runner is explicitly a placeholder** — *"When M4 arrives this is replaced, not
  extended."* That sentence is a design instruction, not a caveat.
- **The frontend boundary is settled and good.** `lib/api.ts` uses `NEXT_PUBLIC_API`, so
  the browser calls the backend directly and no serverless timeout enters the path.

---

## 6. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| Chromium absent | refused before the model call, with the install command | well-made |
| Chromium present, broken | render attempted | deliberate |
| Provider unreachable | 3 attempts × 600s, then `ProviderUnavailable` → 502 | **up to ~30 min per call** |
| Restart during generation | job lost; *"you have to press it again"* | deliberate |
| Restart during planning | the HTTP request dies; no job to resume | **worse than generation** |
| Double-click Generate | idempotent by key | correct |
| N concurrent generations | N threads, N Chromium processes | `[UNKNOWN]` ceiling |
| Long-lived process | `_jobs` accumulates finished entries | slow growth |
| Port in use | a clear sentence and an alternative command | correct |
| Wrong working directory | `chdir(ROOT)` in `app.py` | mitigated |
| Public URL | anyone spends the quota | no auth |
| Disk wiped | everything gone | no persistence layer |

---

## 7. What makes this section valuable

`[OBSERVED]` Four things that only come from operating the thing:

1. **The prerequisite check is placed before the expensive call**, not where it would
   naturally be caught.
2. **`/health` is authoritative** because it answers from the rendering process.
3. **Failures are typed and readable** — 503/502 with a sentence, never a traceback in a
   UI.
4. **The banner answers the two questions that actually get asked**: which model, and can
   it render.

And `jobs.py` is the best-documented placeholder in the repo: it states its scope, its one
deliberate consequence, and its own replacement condition.

---

## 8. Constraints and cross-section effects

**On §2** — planning must move to the job runner before it can survive a deploy or a
reload.

**On §4** — parallel units multiply against render concurrency; the sync codebase is the
obstacle, and `sync_playwright` is where it is anchored.

**On §6** — the deployment floor *is* the renderer. Pooling, replacing, or extracting it
are all deployment decisions before they are rendering decisions.

**On §7** — ephemeral disk forces a persistence decision; artifacts want object storage
and state wants a database, and the shape of §7 currently assumes neither.

**On §0** — PDF/DOCX extraction would be **another native dependency**, and
`Runtime-Dependencies.md` exists because the last one was undocumented and invisible until
the final step. Its §6 states the rule: *"Adding a runtime prerequisite means adding a row
here in the same change."*

**On measurement** — a stable provider is a prerequisite for measuring §2's variance,
§4's parallelism, and quality against the references. **§8 gates the research programme,
not just the product.**

---

## 9. Solution directions — compared, not chosen

**A. Measure the renderer.** Peak RSS, launch share, concurrent ceiling, against the saved
document JSON. *Delivers:* the four unknowns that gate every option in §6 and §8.
*Cost:* **zero model calls.** Not optional.

**B. Bound concurrency.** A semaphore around render, or a worker with a fixed size.
*Delivers:* the memory ceiling becomes predictable rather than a function of user
behaviour. *Cost:* small.

**C. Pool the browser.** Build-Spec §8's own answer. *Delivers:* launch cost and most of
the footprint. *Cost:* the engine stops being a pure function.

**D. Move planning onto the job runner.** *Delivers:* removes the last long synchronous
request; makes reload/timeout survivable. *Cost:* small — the pattern is written and
working for generation.

**E. Durable jobs.** Replace the in-process dict, as `jobs.py` instructs.
*Delivers:* work survives restarts; enables retries and fan-out. *Cost:* needs §7's
storage decision first.

**F. A Playwright base image with pinned fonts.** `Runtime-Dependencies.md` §5 specifies
it, including the version-matching rule and the `PLAYWRIGHT_BROWSERS_PATH` trap.
*Delivers:* reproducible rendering and a deployable artifact. *Cost:* small — it is
already written as a recipe.

**G. Env-driven CORS + an access gate.** *Delivers:* deployable without giving the quota
away. *Cost:* trivial. *Note:* a shared code is not auth, and should not be described as
auth.

**H. A paid provider for the measurement programme.** *Delivers:* every other measurement
becomes possible. *Cost:* money, and it is the only item here that is not an engineering
decision.

**I. Extract the renderer as a service.** *Delivers:* Chromium out of the backend image,
a warm browser, independent scaling. *Cost:* a deployment unit and a network hop.

**J. Async the hot path.** *Delivers:* §4's parallelism and a coherent concurrency story.
*Cost:* the largest here — `sync_playwright` and every provider call.

**The shape:** **A first** — it is free and it gates B, C, F and I. D and G are small and
unlock deploying at all. F is already written and just needs to exist as a file. E waits
on §7. H is a spending decision that gates the research. J is the real architecture and
should follow a decision about the renderer, not precede it.

---

## What remains genuinely open

1. **Peak RSS of one render.** Everything in this section waits on it.
2. **Portfolio link or product?** Changes auth, storage, retention and quota.
3. **Renderer co-located, pooled, or extracted?**
4. **Durable job substrate** — and it depends on §7.
5. **Is there an acceptable total wait?** 600s × 3 attempts has no caller-side bound.
6. **What does a module cost on a paid provider?** Never priced, and it decides H.
