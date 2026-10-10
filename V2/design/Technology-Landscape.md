# Technology Landscape Review — MyNotes V2

**Researched October 2026.** Where a claim comes from a search rather than from the codebase, the
source is linked. Where I could not verify something, it says so and names the spike that would.

**This document changes no frozen design.** It ends with a recommendation, and that recommendation is
mostly *"keep what we have, for reasons we can now state."*

---

## 0. The bias you identified is real, and here is its shape

Your diagnosis is correct and worth making precise, because the correction is different from "read
more."

**Assistants over-recommend the tools with the most written about them.** LangChain, RAG and vector
databases dominate tutorial content, so they dominate what gets suggested. Durable execution,
content-addressed memoisation and admission control have far less tutorial volume and far more
production relevance to a system like yours. The imbalance is in the *training corpus*, not in the
engineering.

**A second bias worth knowing, because it will mislead you directly.** Searching *"LiteLLM
alternatives 2026"* returns pages mostly authored by gateway vendors ranking their own product first
— several of the top results for that query are published by a company that sells the gateway they
rank #1. That is not a reason to dismiss the content, but it is a reason to read benchmark claims
from vendors as marketing until reproduced. I have flagged these inline.

**Third, and the one that matters most here:** "newer" and "more capable" are different axes, and
"well-known" is a third. Your React analogy is apt but incomplete — the honest version is that in
2013 the *right* answer for many apps was still server-rendered HTML, and React's value was specific
and demonstrable. The test is not novelty; it is whether the tool solves a problem you actually have.

---

## 1. The vocabulary — the thing you were actually missing

This section exists because you cannot ask about a category whose name you do not know. These
distinctions are commonly blurred, including by assistants.

### Model and agent layer

| Term | What it actually is | Example |
|---|---|---|
| **Model SDK** | A typed client for one provider's HTTP API. No orchestration. | `anthropic`, `openai` |
| **Model gateway** | A proxy in front of *many* providers: routing, retries, rate limits, budgets, caching, observability. Infrastructure, not logic. | LiteLLM, Portkey, Cloudflare AI Gateway, OpenRouter |
| **Agent framework** | Opinionated runtime for loops, tools, and multi-agent delegation. Decides control flow for you. | OpenAI Agents SDK, Google ADK, CrewAI |
| **Typed agent library** | Structured model calls with validation, minimal control flow. | PydanticAI |
| **Graph/state-machine orchestration** | You declare nodes and edges; it runs them, checkpoints, resumes. | LangGraph |
| **Tool framework** | How a model invokes functions, and how results return. Often bundled into the above. | — |
| **Agent interoperability protocol** | Wire format so *different vendors'* agents and tools interoperate. | MCP (tools→agent), A2A (agent→agent) |

**The distinction that matters for you:** an agent framework decides *control flow*. Your frozen
design decides control flow itself — the nine `flows/` are explicit, not emergent — so you are not in
the market for one. That is a legitimate position, not a gap.

### Execution and state layer — the category you had never heard of

| Term | What it actually is | Guarantee |
|---|---|---|
| **Queue** | A buffer. Hand a message to a worker; maybe retry. | at-least-once delivery |
| **Scheduler** | Runs things at times. Cron. | fires, eventually |
| **Event log** | Append-only ordered record; consumers read at their own offset. | replay, ordering |
| **Workflow engine** | Executes a *multi-step graph*, tracks which step you are on, retries steps. | the graph completes |
| **Durable execution** | Your *function* survives process death. Completed steps are not re-run; the function resumes mid-body after a crash. | **effectively-once per step** |
| **Event sourcing** | State *is* the log of events; current state is a fold over it. | full history, auditability |
| **Transactional outbox** | Write business data and the "send this message" record in **one** transaction, so you cannot commit one without the other. | no dual-write bug |

**What durable execution actually solves**, in one sentence: *a function that calls a paid API,
crashes, and restarts must not pay twice.* Two implementation families exist — **journal-based
replay** (Temporal, Restate: re-run the function, serve completed steps from a journal) and
**database checkpointing** (DBOS, Inngest, Trigger.dev: each step ends in a DB transaction storing
its result) ([LabHub](https://labhub.hopto.org/blog/culture/2026-05-14-durable-execution-engines-2026-temporal-restate-inngest-trigger-dev-dbos-deep-dive-2026?lang=en),
[Kanopy](https://kanopylabs.com/blog/restate-vs-temporal-vs-dbos-durable-execution)).

**Hold that sentence against your system.** A generation Task makes five paid calls at ~65 s each. If
the worker dies after three, you must not pay for those three again. **That is the durable-execution
problem, exactly.** §4 deals with it properly.

### Consistency vocabulary

| Term | Meaning |
|---|---|
| **Idempotency key** | A caller-supplied id making a retry a no-op |
| **Optimistic concurrency / CAS** | `UPDATE … WHERE version = :observed` — your claim protocol's core |
| **Lease** | A time-bounded right to work on something |
| **Fencing token** | A monotonically increasing number proving your lease is still current. **A lease without a fencing token is not safe** |
| **At-least-once / at-most-once / effectively-once** | Delivered ≥1 / ≤1 / observable effect exactly once. True exactly-once across a network is impossible; effectively-once is what systems actually provide |
| **Saga / compensation** | A multi-step transaction you undo step-by-step, since you cannot roll back a sent email |
| **Content addressing** | Name a thing by the hash of its bytes. Makes writes idempotent and overwrites impossible |

Your design already uses five of these seven correctly. The two it does not use — sagas and event
sourcing — it does not need, and §12 says why.

---

## 2. Agent / LLM orchestration

**The problem we have:** turn a situation into structured decisions through a known, fixed sequence of
model calls, each validated against a schema.

**What we have:** `agent/` makes schema-constrained completions. Control flow lives in `flows/` as
explicit Python. No loop, no tool calling, no delegation.

| Option | Category | Maturity | Py/TS | Fits MyNotes? |
|---|---|---|---|---|
| **LangGraph** | graph orchestration + checkpointing | mature, the default for stateful workflows | both | **No** — it would own control flow we deliberately own, and its checkpointer competes with our claim protocol |
| **OpenAI Agents SDK** | agent framework | mature, OpenAI-leaning | both | No — tightly scoped assistants and delegation; we have neither |
| **Google ADK** | agent runtime, GCP-native | mature, batteries-included, debugging UI | Py/TS/Java/Go | No — we are not GCP-native and do not want an opinionated runtime |
| **PydanticAI** | **typed agent library** | mature; fastest median latency in one public comparison (2.2 s) | Python | **Worth evaluating** — see below |
| **Claude Agent SDK** | agent framework | current | both | No — same reason as OpenAI's |
| **Semantic Kernel / MS Agent Framework** | agent framework | mature, .NET-first heritage | Py/C# | No |
| **CrewAI, Agno, Strands, smolagents** | multi-agent frameworks | varied | Python | No — multi-agent is not our shape |

Sources: [LangChain's own framework survey](https://www.langchain.com/resources/ai-agent-frameworks),
[AWS Builder Center](https://builder.aws.com/content/3AzsgG6TreTO3uLRqpWNxfEyUhe/picking-an-ai-agent-framework-in-2026),
[open-techstack comparison](https://open-techstack.com/blog/langgraph-vs-openai-agents-sdk-vs-pydanticai-2026/).

### The one genuine candidate: PydanticAI

Not an agent framework in the control-flow sense — a **typed model-call library** from the Pydantic
team. You already depend on Pydantic v2 for `core/types`, and every model call in the design is
*"produce an object matching this schema."* That is PydanticAI's exact brief.

**What it would replace:** the hand-written request/parse/validate/repair cycle inside `agent/`.
Specifically V1's `_parse_or_repair` — *"gives the model its own validation error once"* — which is a
pattern PydanticAI implements as a built-in retry.

**What it must not touch:** `MODEL_CALL`. PydanticAI would sit *above* the gateway, not instead of it.
Admission, the ledger, provider slots and failure classification stay where the design puts them. If
adopting it means a second path to a provider, the answer is no.

**Verdict: evaluate at M2**, as a spike, with one acceptance test — *can it issue its request through
an injected client so `MODEL_CALL` remains the only provider path?* If yes, it removes real code. If
no, we keep ours and lose nothing.

---

## 3. Durable execution — the honest answer

### Yes, we have this problem

Five paid calls at ~65 s; a worker that dies after three must not pay for those three again. That is
textbook durable execution.

### And yes, we built a subset of an engine

Let me be blunt, because you asked me to be. **Our Task + Claim machinery is a hand-built,
Postgres-backed, checkpoint-style durable execution engine.** The public literature describes the
exact design we arrived at independently:

> *"Postgres can enforce idempotency through primary-key checkpoints and support crash recovery with
> leases."* …
> *"Lease duration presents a tradeoff: if too short, a slow-but-alive worker can have its work
> stolen; if too long, recovery after a crash is delayed."*
> — [opulion.dev](https://opulion.dev/ground-truth/durable-execution-idempotency-or-both)

That second sentence is our §7.5 R2 timeline, which is precisely why we added a fencing token. We did
not get this wrong. We re-derived it.

### The landscape

| Engine | Mechanism | Infrastructure | Python | Notes |
|---|---|---|---|---|
| **Temporal** | journal replay | **server cluster** | yes | The mature standard. Best for complex long-lived cross-service workflows. 50–200 ms invocation latency |
| **Restate** | journal replay | **single binary**, embedded storage | yes | Same guarantees, far less infrastructure. Single-digit-ms invocation, so viable on a request path. Virtual-object model from Orleans |
| **DBOS Transact** | **DB checkpointing in Postgres** | **none — it is a library** | **yes** | Best fit when Postgres is already the state you trust. Workflows, steps, durable queues, idempotency keys, concurrency limits, cron, recovery on restart |
| **Inngest** | DB checkpointing | hosted/SaaS | TS-first | Good DX, event-driven |
| **Trigger.dev** | DB checkpointing | hosted/SaaS | TS-first | Good DX |

Sources: [Kanopy Labs](https://kanopylabs.com/blog/restate-vs-temporal-vs-dbos-durable-execution),
[LabHub deep dive](https://labhub.hopto.org/blog/culture/2026-05-14-durable-execution-engines-2026-temporal-restate-inngest-trigger-dev-dbos-deep-dive-2026?lang=en),
[DBOS Transact repo](https://github.com/dbos-inc/dbos-transact-py).

### Where our design does something these do *not*

This is the part that saves the architecture, and it is a real distinction rather than a rationalisation.

```
DBOS / Temporal checkpoint by POSITION
    "workflow W, step 3 is done — on restart, skip it"
    scope: one workflow execution

Our claim protocol addresses by CONTENT
    "this exact derivation (envelope) is done — by ANY task, in ANY project, ever"
    scope: global, cross-project, cross-commitment
```

Three things in the frozen design depend on the second and are not expressible in the first:

- **§5.7a's memo envelope** — a correction to module 5 must not invalidate module 1's generated
  sections. That is content-keyed reuse across *different* Task executions. Position-based
  checkpointing cannot express it: those are two different workflows.
- **§4.2a's cross-project `SharedDerivation`** — two projects on the same subject derive the structure
  once. Different workflows, different tenants, one result.
- **§7.3c's `RECONCILE`** — reattach a lost claim to an existing result found by canonical identity.

So the honest summary: **we built two layers, and only one of them is a reimplementation.**

| Layer | What it is | Mature equivalent exists? |
|---|---|---|
| Task durability — lease, epoch, heartbeat, orphan sweep, resume, retry classification | durable execution | **Yes: DBOS Transact** |
| Claim protocol — content-addressed identity, single-flight, fencing, publication transaction, reconcile | **content-addressed memoisation** | **No** — this is domain-specific and the design's real intellectual content |

### Recommendation

**Keep both, and do one timeboxed spike.** Specifically:

- **Do not adopt Temporal.** A server cluster for a single-process app, with the design's own T1
  target at 512 MB, is unjustifiable. Revisit only at T3 with multiple workers *and* cross-service
  workflows — neither of which exists.
- **Do not adopt Restate or Inngest or Trigger.dev.** Restate is the most interesting technically
  (one binary, request-path latency), but it is still a second runtime and a second state store
  beside the Postgres we already need for domain truth.
- **Spike DBOS Transact at M6**, when the Task system is about to be written. Two hours, three
  questions:
  1. Can it coexist with our schema, or does it own the database? *(I could not verify this from the
     docs; it is the deciding question.)*
  2. Does it expose a **fencing token**, or only a lease? Our §7.5 R2 timeline is only safe with one,
     and the docs I fetched did not address fencing.
  3. Python 3.14 support?
- **If the spike passes:** DBOS replaces `work/{states,lease,lifecycle,coordinator}.py` — maybe 400
  lines of the most concurrency-sensitive code we would otherwise own and test ourselves. Our claim
  protocol stays, because DBOS does not do content addressing.
- **If it fails any of the three:** keep ours. It is already specified to a level most teams never
  reach, and §15.4's test suite is the evidence.

**What this costs if we never spike it:** we own and test lease/epoch/orphan-recovery code forever.
That is the trade, stated plainly. It is not free, and "we designed it carefully" is not the same as
"a team maintains it for us."

---

## 4. Agent interoperability — MCP and A2A

The protocol stack consolidated during 2026 rather than fragmenting. **MCP for tools, A2A for
agents** — and IBM's competing ACP merged *into* A2A in August 2025 instead of splitting the layer
([Linux Foundation](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year),
[state of standards](https://dev.to/alexmercedcoder/the-state-of-agentic-ai-standards-in-2026-mcp-a2a-webmcp-osi-and-the-protocol-stack-taking-3o2l)).

A2A reached **v1.0 with 150+ organisations and production deployments**, with integration across
Google, Microsoft and AWS. This is no longer speculative infrastructure.

### What MCP actually solves

A standard wire protocol so a model host can discover and call tools it was not built against.

```
MCP SERVER   exposes tools/resources/prompts over JSON-RPC (stdio or HTTP+SSE)
MCP CLIENT   lives in the host (Claude Desktop, an IDE, your agent) and calls them
```

Before MCP, every (host × tool) pair was bespoke. After it, a tool written once is callable by any
compliant host. **The value is N×M → N+M**, and it is only value when N or M is greater than one.

### Should MyNotes consume MCP tools?

**No, and it is not close.** The frozen design has no tool-calling loop: `agent/` makes
schema-constrained completions and `flows/` decides what happens next. There is nothing for a tool
server to plug into. Adding MCP inbound would mean first adding a tool loop — a design change with no
requirement behind it.

### Should MyNotes *expose* itself through MCP?

**This is the genuinely interesting question, and the answer is "later, and here is the trigger."**

A MyNotes MCP server would expose something like:

```
create_project(subject, purpose)      → project_id
get_plan(project_id)                  → the curriculum, shortfalls, approvability
approve(project_id)                   → commitment_id | refusal with decisions implicated
generate(commitment_id, module_id)    → task ref
get_artifact(module_id)               → the PDF
```

Then Claude, an IDE, or another agent could *drive* MyNotes as a tool. That is a real product
capability: *"plan my semester and put the PDFs in my notes folder."*

**Why not now:** every operation above is already an HTTP endpoint (§18). MCP adds a second
representation of the same surface, with its own auth story, for zero current consumer. Build the API
first; MCP is a thin adapter over a stable API and a nightmare over an unstable one.

**The trigger, concretely:** the first time you want a non-browser client to drive MyNotes. At that
point MCP is ~200 lines over the existing API and the right answer. **A2A is not relevant** — it is
for agent-to-agent negotiation across organisational boundaries, and MyNotes has no peer agents.

**Learn now?** Understand MCP's shape (server/client/transport/capabilities) — it is the dominant
standard and you will meet it constantly. You do not need to implement one yet.

---

## 5. Databases and persistence

### The landscape, including what you would not have known to ask about

| Category | Representative | What it is for |
|---|---|---|
| **Relational / OLTP** | **PostgreSQL**, MySQL | transactions, constraints, joins. The default, correctly |
| **Distributed SQL** | CockroachDB, YugabyteDB, TiDB | SQL + horizontal scale + multi-region, at latency cost |
| **Serverless Postgres** | Neon, Supabase, Aurora Serverless | Postgres with scale-to-zero and branching. **Neon's branch-per-PR is genuinely useful for CI** |
| **Document** | MongoDB, Couchbase | schema-flexible aggregates |
| **Key-value** | Redis, Valkey, DynamoDB | caching, counters, sessions |
| **Embedded** | **SQLite**, DuckDB, LMDB | in-process, zero ops. SQLite is the most-deployed DB in the world |
| **Graph** | Neo4j, Memgraph | relationship traversal as the primary query |
| **Vector** | pgvector, Qdrant, Weaviate, LanceDB | similarity search over embeddings |
| **Search** | Elasticsearch, OpenSearch, Typesense, Meilisearch | ranked full-text |
| **Analytical / columnar** | **DuckDB**, ClickHouse | aggregate scans over many rows |
| **Event store** | EventStoreDB, Kafka-as-log | append-only history as the source of truth |
| **Object storage** | S3, R2, MinIO, Backblaze B2 | large immutable blobs. **Cloudflare R2 has no egress fees**, which matters for PDF delivery |
| **Time series** | TimescaleDB, Prometheus, InfluxDB | metrics over time |

### Why PostgreSQL is the right choice here — and it is, specifically

Not "because it is the default." Because the frozen design asks for six things, and Postgres provides
all six in one engine:

| Design requirement | Postgres feature |
|---|---|
| atomic CAS for claims and admission | `UPDATE … WHERE epoch = :observed`, `INSERT … ON CONFLICT … DO UPDATE … WHERE` |
| the publication transaction (claim + metadata atomically) | real multi-statement transactions |
| uniqueness over derived identity | `UNIQUE` over hash columns |
| the `stale()` dependency walk | indexed joins on `DependencyEdge` |
| immutability enforced, not documented | `REVOKE UPDATE, DELETE` |
| per-decision addressability — §7's diagnosis of why three V1 mechanisms were unwired | ordinary rows and indexes |

**A detail worth knowing, because the design depends on it:** Postgres treats `NULL`s as **distinct**
in a `UNIQUE` constraint, which is exactly why TD §5.11a makes `member` non-null with a `''` sentinel.
PG15+ offers `NULLS NOT DISTINCT` as an alternative, and the design's approach is the safer one
because it does not depend on a non-default flag.

**Nothing in the landscape beats it for this workload.** Distributed SQL buys multi-region we do not
need at latency we would feel. A document store would give up the constraints that *are* the
correctness model. SQLite would be a real option if the renderer and app were one process forever,
but the T2 split would break it.

### Two things worth adopting later, neither urgent

- **Neon or Supabase for CI** — a Postgres branch per pull request means the `repo/` suite runs against
  a real database with no shared-instance flakiness. Evaluate when CI gets slow or flaky.
- **Cloudflare R2 for artifacts** — S3-compatible, zero egress. PDFs are the egress-heavy part of this
  product. Evaluate at M10 when object storage lands.

### Vector databases — deliberately not needed, and this is worth stating

You listed vector DBs among the tools you were taught first. The frozen design has **no retrieval
step**. §0's investigation is explicit: *"retrieval is a branch, not a spine,"* and 1 of 10 corpus
cases had an authority in play. If source grounding ever arrives (OQ-1), the right first move is
`pgvector` in the Postgres you already run — not a separate vector service. **RAG is the most
over-recommended architecture in this space, and it is not your architecture.**

---

## 6. Queues, messaging, asynchronous execution

### The distinctions you asked for

```
QUEUE               a buffer. "Someone do this." At-least-once; you own retries and state.
SCHEDULER           "do this at 3am." Cron.
EVENT LOG           ordered, replayable, multiple independent consumers with offsets.
WORKFLOW ENGINE     runs a multi-step graph; knows which step you are on.
DURABLE EXECUTION   your FUNCTION survives a crash; completed steps are not re-run.
```

These are layers, not competitors. Durable execution is usually implemented *over* a queue; an event
log is a different shape entirely (fan-out and replay, not work distribution).

### Options

| Option | Category | Infra | Fits? |
|---|---|---|---|
| **Postgres `SKIP LOCKED`** | queue | **none beyond the DB** | **Yes — what the design already specifies** |
| **pgqueuer / pgmq / pg-boss** | queue libraries over Postgres | none | Worth a look; `pgqueuer` adds `LISTEN/NOTIFY` so workers wake instead of polling |
| Celery | task queue | + Redis/RabbitMQ | No — the Python standard, and a broker we do not need |
| Redis / BullMQ | queue | + Redis | No |
| RabbitMQ | broker | + server | No |
| Kafka / Redpanda | event log | + cluster | No — we have no fan-out or replay requirement |
| NATS | messaging | + server | No |
| SQS / Cloud Tasks | managed queue | cloud | No — ties the design to one cloud |

Sources: [Prisma on SKIP LOCKED](https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked),
[pgqueuer vs Celery](https://github.com/janbjorge/pgqueuer/discussions/298),
[replacing MQ with Postgres](https://mvpfactory.io/blog/replacing-your-message-queue-with-postgresql-skip-locked-queues-listen-notify).

**The capacity number that settles it:** Postgres `SKIP LOCKED` holds comfortably to roughly
**10,000 jobs/minute** before needing something bigger. Our measured ceiling is ~90 projects/minute
at a 1,000 rpm provider limit. We are three orders of magnitude inside the envelope.

**One worthwhile addition:** `LISTEN/NOTIFY` so the Work Coordinator wakes on an enqueue instead of
polling every 30 s. That is a latency improvement, not an architecture change, and it belongs at M6.

**And the honest caveat from the same literature:** Postgres-based durable execution *"breaks first on
contention — every step does at least one write, and hot workflows that fan out to thousands of
children will hammer a single cluster."* Our fan-out is ~5–12 sections per module. Far from it, and
worth knowing as the eventual failure mode.

---

## 7. Model gateways

**The problem:** one path to a provider, with retries, classification, deadlines, budgets, admission,
and a record of every call.

**Options**, with the vendor-bias warning from §0 applied:

| Option | What it is | Self-host | Notes |
|---|---|---|---|
| **our `MODEL_CALL`** | ~300 lines | — | Already specified to an unusual depth: 10 failure classes, admission, FIFO provider slots, the ledger |
| **LiteLLM** | the most-used OSS gateway, 100+ providers | yes | Python-native, easy. Critiques of its performance ceiling and "thin enterprise governance" come mostly from competitors; treat as unverified |
| **Portkey** | gateway + control plane, 1,600+ models | hybrid | Observability, guardrails, prompt management |
| **Bifrost** | Go gateway, claims 54× better P99 than LiteLLM | yes | **The claim is published by the company that builds it.** Unverified |
| **Cloudflare AI Gateway** | managed, edge | no | Caching, rate limiting, analytics, zero ops |
| **OpenRouter** | provider aggregator | no | Already our provider |
| **Vercel AI Gateway** | managed | no | Sub-20 ms routing |

Sources: [Eden AI](https://www.edenai.co/post/best-alternatives-to-litellm),
[Kosmoy](https://www.kosmoy.com/resources/blog/litellm-alternatives/),
[markaicode](https://markaicode.com/alternatives/litellm-alternatives/).

### Verdict: keep ours, and the reason is specific rather than defensive

A gateway product gives you provider routing and retries. **It does not give you the three things our
gateway exists for:**

1. **Admission tied to our Task budget.** `Task.calls_admitted` is a conditional increment against a
   budget that belongs to *our* domain object. No external gateway knows what a Task is.
2. **The `CallLedger` as a derivation record.** Our ledger rows carry `result_identity` and
   `task_epoch`, which is how *"why did this project cost 46 calls"* is answerable. A gateway logs
   calls; it does not know what a derivation is.
3. **Failure classes mapped to our retry semantics.** `output_truncated` → narrowing retry exists
   because A5 truncated 2 of 10 derive calls. That is domain knowledge.

**What a gateway would genuinely add:** multi-provider fallback, which we do not have and will want the
first time OpenRouter has an outage during a demo.

**Recommendation:** keep `MODEL_CALL` as the single path. **Consider LiteLLM as a *library* behind the
provider adapter** (`gateway/providers/`) if and when multi-provider fallback is wanted — it slots in
*under* our gateway, not instead of it. Do not adopt a gateway *proxy*: it would become a second
provider path, which §8.6b exists to prevent.

---

## 8. Observability

**The most important finding here is a "don't build on it yet."**

OpenTelemetry's **OTLP protocol is stable**. Its **GenAI semantic conventions are not**. As of mid-2026
every `gen_ai.*` attribute, span, metric and event is marked stability **"Development"** — and in June
2026 the GenAI conventions were *moved out* of the main semantic-conventions repo into a dedicated
`semantic-conventions-genai` repository, which had not produced a tagged release as of mid-July
([praesidia](https://praesidia.ai/blog/opentelemetry-genai-semantic-conventions-status),
[greptime](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions)).

**So: no `gen_ai.*` attribute is safe to build dashboards, alerts or storage schemas against today.**
The core shape (operation name, provider, model, token usage) has been stable since v1.37.0 and
Datadog and Grafana consume it, so the *direction* is settled — but the names are not.

| Option | Category | Adopt? |
|---|---|---|
| **our `obs/log.py`** | structured JSON events | **Keep.** TD §17's question-shaped event set is more useful than generic spans |
| **OpenTelemetry (traces/metrics)** | vendor-neutral telemetry | **Adopt the OTLP shape at M12**, for request/DB/render spans. Worth it: one exporter, any backend |
| **OTel GenAI semconv** | LLM-specific attribute names | **Know it exists. Do not depend on it yet.** Mirror the four core attribute names so a later migration is a rename |
| **LangSmith** | LLM tracing + evals | No — tied to the LangChain ecosystem we are not in |
| **Phoenix / Arize** | OSS LLM observability | Evaluate at M12 if trace inspection becomes the bottleneck |
| **Braintrust** | evals + observability, CI gating | See §9 |
| Sentry | error tracking | Adopt at T1 deployment. Cheap, immediate value |

**Deliberate position:** structured events now, OTLP spans at M12, GenAI semconv when it stabilises.
And one gap worth closing earlier than M12 — **correlation IDs**. A 670-second multi-call workflow
without a trace id threaded through every event is painful to debug. That is small, and belongs at M2.

---

## 9. Evaluation

Current practice has settled into **three layers**, and our `evals/` sits in one of them:

```
1  capability benchmarks        MMLU-style. Irrelevant to us.
2  application metrics          RAGAS (RAG), DeepEval (pytest-shaped), Promptfoo (matrix + red-team)
3  hosted platform              LangSmith, Braintrust, Phoenix/Arize — annotation, dashboards, CI gating
```

The converged pattern is **two tools**: a lightweight framework for CI gating, plus a platform for
human annotation and regression tracking. The standard CI shape is a **versioned golden dataset of
100–500 examples** run on every PR ([bigdataboutique](https://bigdataboutique.com/blog/llm-evaluation-frameworks-metrics-best-practices),
[Braintrust](https://www.braintrust.dev/articles/deepeval-alternatives-2026)).

Notable: **Promptfoo became part of OpenAI in 2026 and remains MIT-licensed**
([promptquorum](https://www.promptquorum.com/prompt-engineering/best-prompt-testing-evaluation-tools)).

### How our approach compares — better than I expected in one way, behind in another

**Ahead:** our `evals/` holds **hand-written reference plans** per corpus case, and the 12 plan-quality
dimensions came from the references rather than from a generic metric library. That is a *golden
dataset with domain-specific judgments*, which is the thing most teams never build and the thing that
makes evaluation meaningful. The recorded runs double as the CI fixture, which is unusually tidy.

**Behind:** three things.

1. **It is not wired into CI as a gate.** 100–500 examples on every PR is current practice; we have 10
   cases run by hand.
2. **No LLM-as-judge.** Our checks are deterministic (substring coverage). Several of the 12 dimensions
   — redundancy, whether a capability clause is answerable — need a judge, and M4 of the design says so
   (`M1` is *"heuristic today … a judge later"*).
3. **No annotation surface.** Reference plans are hand-written markdown; there is no way to record
   *"this plan was wrong and here is why"* as structured data.

**Recommendation:** keep the harness and references. At M4, make the recorded runs a CI fixture (the
design already specifies this). **Adopt DeepEval at M12**, not earlier — it is the pytest-shaped one
and our tests are pytest. Defer any hosted platform until U7 (*what does a project cost on a paid
provider?*) is answered, because evaluation without repeatable runs is not evaluation.

---

## 10. Python engineering

**Assessment: yes, the setup is current and strong.** uv + ruff + pyright-strict + pydantic-settings
is what well-maintained Python repositories converged on, and it is what the public Anthropic and
OpenAI SDKs ship.

### One thing worth knowing, and not adopting yet

**`ty`** — Astral's Rust type checker, from the team behind ruff and uv. In **beta as of 2026**, with
1.0 targeted. It is **10–60× faster** than mypy (Home Assistant: 2.19 s vs 45.66 s; incremental
recheck in PyTorch: 4.7 ms vs pyright's 386 ms) — and passes **~53% of the typing conformance suite
against pyright's 98%** ([InfoWorld](https://www.infoworld.com/article/4108979/python-type-checker-ty-now-in-beta.html),
[danilchenko.dev](https://www.danilchenko.dev/posts/ty-vs-mypy-vs-pyright/),
[pydevtools](https://pydevtools.com/handbook/topics/ty/)).

**Verdict:** stay on pyright strict. The conformance gap matters for a codebase whose thesis is typed,
enforced relationships. Re-evaluate at 1.0; the guidance in the field is to run `ty` *alongside*
pyright rather than instead of it.

Also worth knowing exists: **pyrefly** (Meta's Rust checker, same trade), **basedpyright** (a pyright
fork with stricter defaults).

**Small gaps in our setup:**

| Gap | Fix |
|---|---|
| `uv.lock` not generated yet | `make bootstrap` |
| no SBOM / supply-chain attestation | `uv export` + `pip-audit` in CI; `sigstore` later |
| no `pip-audit` / dependency CVE scan | add to CI — ten lines |
| no mutation testing | `mutmut` on `core/identity` only, where correctness is everything |
| no property-based tests | **Hypothesis on `core/identity`** — canonical JSON is exactly the shape property testing is for |

That Hypothesis suggestion is the most valuable item in this table. *"For any two logically-equal
inputs, the envelope is equal; for any difference in an included field, it differs"* is a property, and
the golden table is a finite sample of it.

---

## 11. API and service architecture

**Our shape:** `client → backend → {agent, engine, core}` as packages, two processes, import walls.

**Assessment: this is current best practice, not a compromise.** The industry position consolidated
around the **modular monolith** — a single deployable with enforced internal boundaries — after a
decade of microservice regret. The things that make it work are exactly what we have: explicit module
boundaries, enforced dependencies, and splits driven by measured need.

What makes ours stronger than most:

- **boundaries enforced by a test**, not by review. Most "modular monoliths" lose their modularity
  within a year because nothing fails when someone imports across a layer.
- **a numeric split condition** — `render slots > min((mem − 65 MB)/240 MB, vCPU)`. Most teams split
  on a diagram or on team structure.
- **ports as Protocols**, which is hexagonal architecture / ports-and-adapters without the ceremony.

**Not needed:** event-driven decomposition (no fan-out requirement), service mesh, gRPC between
packages, API gateway.

**Worth knowing exists:** the **transactional outbox** pattern — if MyNotes ever needs to notify an
external system *and* commit domain state, that is the pattern that avoids the dual-write bug. Not now.

---

## 12. Rendering

**Current state of the art is close to what we chose**, with one number worth re-examining.

| Option | Verdict |
|---|---|
| **Playwright/Chromium** | **Keep.** Best fidelity, needed for JS and modern CSS. Warm-pool latency reportedly under 10 ms for simple documents |
| **WeasyPrint** | Pure Python, CSS Paged Media, smallest output (8–21 KB), actively maintained — but **~75× slower than a warm Playwright** and runs no JS. §6's CSS audit already ruled it out on `@page :first` and full-bleed |
| **Gotenberg** | Chromium behind an HTTP API. **This is what T2 should look like** rather than a hand-rolled render service |
| **Typst** | Fast deterministic layout, knows space before drawing — the property §6 wants. But 2,480 lines of Jinja/CSS would be rewritten. Not before §5 settles |
| wkhtmltopdf | Dead. Unmaintained, old WebKit |

Sources: [pdf4.dev benchmark](https://pdf4.dev/blog/html-to-pdf-benchmark-2026),
[Playwright vs WeasyPrint](https://pdf4.dev/blog/playwright-vs-weasyprint).

**The one claim worth revisiting:** our measurement found launch is 1.39 s = ~55% of a 2.5 s render, and
we refused pooling because a pooled browser holds ~240 MB permanently on a 512 MB instance. That logic
still holds *at T1*. But "warm-pool latency under 10 ms" suggests pooling matters more at volume than our
single-instance measurement implied. The design already names the exception (pool per batch at T2), so
this is a confirmation rather than a change.

**Gotenberg is the genuine find here.** When T2's condition fires, the design says *"extract the
renderer as a service."* Gotenberg is that service, maintained, and the design's own §6 already cites
it as the reference stateless microservice. Use it rather than building one.

---

## 13. Security and identity

Separating what we need now from hardening, since you asked.

| Concern | Now (T1) | Hardening | Know it exists |
|---|---|---|---|
| **authentication** | access gate (a shared code — **not auth**) | real auth when U6 is answered | OIDC/OAuth2, passkeys/WebAuthn, Clerk/WorkOS/Auth0, Supabase Auth |
| **authorization** | every read scoped by `(user_id, project_id)` | — | **Postgres RLS** · policy engines: **OPA**, **Cedar** (AWS), **OpenFGA** (Zanzibar-style) |
| **secrets** | `.env`, gitignored | a secret manager at deploy | SOPS, age, Vault, cloud KMS, sealed-secrets |
| **tenant isolation** | `user_id` column + scoped queries | **RLS is the mechanical version** | schema-per-tenant, DB-per-tenant |
| **service identity** | n/a (one process) | — | **SPIFFE/SPIRE**, mTLS, workload identity federation |
| **API security** | CORS from env, access gate | rate limits (we have admission), input size caps | OWASP API Top 10 |
| **supply chain** | pinned ranges | lockfile + `pip-audit` | **SBOM**, **sigstore**, **SLSA** provenance |
| **prompt injection** | n/a — no tool loop, no untrusted retrieval | becomes real the moment sources are ingested | this is the one AI-specific risk that will land on you |

**Two things I would raise now rather than at hardening:**

1. **Postgres RLS is worth knowing before M1, not after.** Retrofitting row-level security onto a
   schema is painful; designing with it in mind is free. You do not have to enable it — just know that
   `user_id` on every table is what makes it possible later.
2. **Prompt injection becomes a real risk at §0's ingestion.** The moment a user-supplied syllabus
   reaches a prompt, its content is untrusted input to a model that produces decisions. Not a problem
   today because ingestion is deferred; worth knowing it arrives *with* that feature.

---

# 14. Things I should have told you earlier

Concepts and tools a serious AI application engineer should know exist. **Learn now** means it changes
decisions you are making this month.

### Execution and state — the biggest blind spot, and the most consequential

| | What it is | Why it matters | Learn now? |
|---|---|---|---|
| **Durable execution** | your function survives process death; completed steps are not re-run | the exact problem a multi-call paid workflow has | **Yes — critical** |
| **Workflow engine** | executes a step graph and tracks position | the category above durable execution | **Yes** |
| **Fencing token** | a monotonic number proving a lease is current | a lease *without* one is unsafe; we needed this and found it | **Yes — we use it** |
| **Idempotency key** | caller-supplied id making retries no-ops | the single most useful distributed-systems primitive | **Yes** |
| **Optimistic concurrency / CAS** | `UPDATE … WHERE version = :observed` | the whole claim protocol | **Yes** |
| **`SKIP LOCKED`** | Postgres row-level queue primitive | why we need no Redis | **Yes** |
| **`LISTEN/NOTIFY`** | Postgres pub/sub | wake workers without polling | Yes, shallow |
| **Transactional outbox** | commit data and "send this" in one transaction | the fix for the dual-write bug | Know it exists |
| **Saga / compensation** | step-by-step undo for things you cannot roll back | multi-service transactions | Know it exists |
| **Event sourcing / CQRS** | state as a fold over an event log; separate read models | audit trails, temporal queries. **We deliberately do not use it** | Know it exists |
| **At-least-once vs effectively-once** | exactly-once across a network is impossible | our §7.5 R3 window is irreducible for this reason | **Yes** |
| **Little's law** | in-flight = arrival rate × duration | how we computed capacity without guessing | **Yes** |
| **Backpressure / admission control** | refuse early rather than queue forever | our §8.6a | **Yes** |

### AI-specific

| | What it is | Learn now? |
|---|---|---|
| **Model gateway** | a proxy for routing/retries/budgets across providers | **Yes** |
| **Structured outputs / constrained decoding** | forcing a model to emit schema-valid JSON | **Yes — it is what `agent/` does** |
| **Prompt caching** | provider-side reuse of a prompt prefix | Yes, shallow — tokens are not our bill |
| **MCP** | standard protocol for tools→agent | **Yes — shape only** |
| **A2A** | standard protocol for agent→agent, v1.0, 150+ orgs | Know it exists |
| **Agent SDK vs agent framework vs orchestration** | three different categories, routinely conflated | **Yes** |
| **LLM-as-judge** | a model scoring another model's output | **Yes — our OQ-1 needs it** |
| **Golden dataset / regression evals** | versioned examples run in CI | **Yes** |
| **OTel GenAI semantic conventions** | standard attribute names for LLM telemetry — **still Development status** | Know it exists; do not build on it |
| **Context engineering** | the discipline that replaced "prompt engineering" | Yes, shallow |

### Data and infrastructure

| | What it is | Learn now? |
|---|---|---|
| **Distributed SQL** | CockroachDB/Yugabyte/TiDB — SQL with horizontal scale | Know it exists |
| **Serverless Postgres** | Neon/Supabase — scale-to-zero, **branch per PR** | Yes — useful for CI |
| **Object storage + egress economics** | S3/R2/MinIO; **R2 has no egress fees** | **Yes — PDFs are egress** |
| **Embedded analytics** | DuckDB — SQL over files, in-process | Know it exists; good for analysing our own runs |
| **Content-addressed storage** | name bytes by their hash | **Yes — we use it** |
| **Postgres RLS** | row-level security as mechanical tenant isolation | **Yes — before the schema sets** |
| **pgvector** | vectors inside Postgres | Know it exists; the right first move *if* grounding arrives |

### Engineering practice

| | What it is | Learn now? |
|---|---|---|
| **Property-based testing** | Hypothesis — assert properties, let it find counterexamples | **Yes — ideal for `core/identity`** |
| **Deterministic simulation testing** | run the whole system on a controlled clock and scheduler to find races reproducibly (FoundationDB's method; Antithesis commercialises it) | Know it exists — **this is what our `Clock` port is a small step toward** |
| **Mutation testing** | mutate code, assert tests fail | Know it exists |
| **Golden-file / snapshot testing** | assert output matches a reviewed artifact | Yes — our renderer tests |
| **SBOM / sigstore / SLSA** | supply-chain provenance | Know it exists |
| **Feature flags** | ship dark, enable per-tenant | Know it exists |
| **Modular monolith** | one deployable, enforced internal boundaries | **Yes — it is what we are building** |
| **Hexagonal / ports and adapters** | domain core, I/O at the edges via interfaces | **Yes — it is what `ports/` is** |

---

# 15. MyNotes evaluated against the landscape

## A. Keep — chosen correctly, now with reasons from outside the project

| | Why it survives review |
|---|---|
| **PostgreSQL** | the only engine providing all six things the design needs (§5). Not a default — a fit |
| **Postgres-as-queue** (`SKIP LOCKED`) | capacity headroom of ~3 orders of magnitude |
| **the claim protocol** | content-addressed memoisation with fencing. **No off-the-shelf engine does this**, and it is the design's real content |
| **`MODEL_CALL` as the single path** | admission tied to our Task budget, and a ledger that records derivations rather than calls. No gateway product knows what those are |
| **no agent framework** | we own control flow deliberately; every framework in §2 would take it |
| **Playwright/Chromium** | still the fidelity leader |
| **modular monolith + import walls** | current best practice, and enforced rather than aspirational |
| **uv + ruff + pyright-strict** | matches what the public Anthropic/OpenAI SDKs ship |
| **hand-written reference plans as a golden dataset** | ahead of common practice. Most teams never build this |
| **no RAG, no vector DB** | correct. `retrieval is a branch, not a spine` |

## B. Reconsider — with the actual trade

### B1 · DBOS Transact for the Task layer

| | |
|---|---|
| **What** | replace `work/{states,lease,lifecycle,coordinator}.py` with a Postgres-native durable-execution library |
| **For** | ~400 lines of the most concurrency-sensitive code we would otherwise own, test and maintain. Durable queues, concurrency limits, cron and restart recovery arrive built. Needs no new infrastructure — it uses the Postgres we already require |
| **Against** | a dependency in the correctness kernel. It may own schema we need to coexist with. **I could not verify whether it exposes a fencing token** — and a lease without one is unsafe for our R2 timeline. Python 3.14 support unverified |
| **Verdict** | **Spike at M6, two hours, three questions** (§3). Adopt only if schema coexistence, fencing and 3.14 all pass. Our claim protocol stays either way |

### B2 · PydanticAI for the model-call layer

| | |
|---|---|
| **What** | replace hand-written request/parse/validate/repair in `agent/` |
| **For** | we already depend on Pydantic; every call is schema-shaped; the repair-once pattern is built in |
| **Against** | must sit *above* `MODEL_CALL`, never beside it. If it insists on owning the HTTP client, it creates the second provider path §8.6b forbids |
| **Verdict** | **Evaluate at M2.** One acceptance test: can it use an injected client? |

### B3 · LiteLLM as a library under the provider adapter

| | |
|---|---|
| **What** | multi-provider fallback inside `gateway/providers/` |
| **For** | the first OpenRouter outage during a demo. 100+ providers for free |
| **Against** | a dependency for a capability we have not needed yet |
| **Verdict** | **Trigger-based** — adopt when a second provider is actually wanted. Library, never proxy |

### B4 · Gotenberg when T2 fires

| | |
|---|---|
| **What** | Chromium-behind-HTTP instead of a hand-built render service |
| **For** | maintained; the design's own §6 already names it as the reference stateless renderer |
| **Against** | none, at the point T2's condition fires |
| **Verdict** | **Trigger-based.** When T2 arrives, use Gotenberg rather than writing one |

## C. Missing from our radar — genuine gaps

| | What to do |
|---|---|
| **Property-based testing of identity** | **Add at M0.** Hypothesis over canonical JSON and the three key constructions. The golden table is a finite sample of a property; this tests the property |
| **Correlation / trace IDs** | **Add at M2.** A 670 s multi-call workflow without one is painful to debug |
| **`LISTEN/NOTIFY` for worker wake-up** | Add at M6. Latency, not architecture |
| **Dependency CVE scanning** | **Add now.** `pip-audit` in CI is ten lines |
| **Postgres RLS awareness** | **Before M1's schema.** You need not enable it; design so it is possible |
| **Prompt-injection posture** | Write it down before ingestion lands. It arrives *with* that feature, not after |
| **Multi-provider fallback** | Acknowledge the single point of failure now; fix per B3 |
| **Neon/Supabase branch-per-PR for CI** | Evaluate when the `repo/` suite gets slow or flaky |
| **R2 for artifact egress** | Evaluate at M10 |

## D. Premature — interesting, and would add complexity now

Temporal (a cluster for a single-process app) · Restate (a second runtime) · Kafka/NATS (no fan-out
requirement) · a vector DB (no retrieval step) · any agent framework (we own control flow) · a gateway
*proxy* (a second provider path) · OTel GenAI semconv (still Development status) · a hosted eval
platform (needs repeatable runs first, gated on U7) · service mesh, gRPC, microservices · MCP server
(no consumer) · A2A (no peer agents) · event sourcing (no temporal-query requirement).

## E. Trigger-based — adopt when the condition appears, not before

| Technology | Trigger |
|---|---|
| MCP server | the first non-browser client wanting to drive MyNotes |
| LiteLLM | a second provider is wanted |
| Gotenberg | T2's numeric render condition fires |
| OTel spans + a backend | more than one process, or latency debugging gets hard |
| DeepEval in CI | plan quality becomes a tracked metric (post-U7) |
| Postgres RLS enforcement | the second real tenant |
| Real auth (OIDC/passkeys) | U6 answered as "product" |
| `pgvector` | source grounding (OQ-1) is actually built |
| Distributed SQL | multi-region, which is not on any roadmap |
| `ty` | its 1.0, with conformance near pyright's |

---

# 16. The "world-class repo" question, by dimension

**What you would actually see opening a very well-maintained production repository**, versus where we
are. I can speak to publicly observable repositories (the Anthropic and OpenAI Python SDKs, Postgres,
Kubernetes, Temporal, Astral's tools); I cannot speak to anyone's private monorepo and will not
pretend to.

| Dimension | What excellent looks like | Us | Gap |
|---|---|---|---|
| **Architecture quality** | explicit boundaries, dependency rules enforced, decisions recorded with rationale | **Above the bar.** Frozen contract, AST-enforced walls, decisions with measured evidence and named trade-offs | — |
| **Developer experience** | one command to a working env; discoverable tasks; fast feedback | **At the bar.** `make bootstrap`, `make check`, Makefile with help | `uv.lock` not generated; no devcontainer |
| **Reproducibility** | lockfile, pinned toolchain, pinned CI images, hermetic tests | **Approaching.** Ranges + lock, pinned `postgres:17` | lock not generated; no `.python-version` |
| **Testing** | layered unit→integration→e2e; tests for *invariants*, not just paths; no skipped critical tests | **Above the bar.** Inexpressibility tests for construction-enforced invariants, a concurrency suite with an injected clock, `filterwarnings=error` | no property-based tests; no mutation testing |
| **CI/CD** | fast static gate, parallel jobs, real services, cached deps, required checks | **At the bar.** 3 jobs, Postgres service, uv cache, `UV_FROZEN` | no CD; no required-checks config; no release automation |
| **Static analysis** | lint + format + strict types, all enforced | **At the bar.** ruff 18 rule families, pyright strict, `reportUnnecessaryTypeIgnoreComment=error` | unverified locally — tools not installed |
| **Observability** | structured logs, correlation IDs, traces, metrics, actionable errors | **Below the bar.** Structured events with question-shaped helpers, but **no correlation ID** and no traces | correlation IDs (M2), OTLP (M12) |
| **Security** | no secrets in repo, dependency scanning, least privilege, documented threat model | **Below the bar.** `.env` gitignored, `.env.example` documented, immutability by privilege | **no `pip-audit`**, no SBOM, no threat model |
| **Dependency management** | lockfile, upper bounds, scoped per module, renovation automation | **At the bar.** Upper bounds with a stated reason, deps annotated per permitted package | no Renovate/Dependabot |
| **Documentation** | README that gets you running; ADRs; why-comments | **Above the bar.** A design corpus most projects never produce, and why-comments citing evidence | no ADR *format* — the design docs serve the role, less greppably |
| **Operational readiness** | health/readiness split, graceful shutdown, migrations, runbooks, resource limits | **Below the bar, correctly for M0.** `/health` answers from the right process | readiness vs liveness; graceful drain; migration runner; runbook |

**Three honest summary statements:**

1. **Architecture, testing philosophy and documentation are above what most production repos achieve.**
   The import wall as an executable test and the inexpressibility tests are things I rarely see.
2. **Observability, security scanning and operational readiness are below the bar**, and two of those
   are cheap: `pip-audit` in CI, and a correlation ID in `obs/log.py`.
3. **The thing a reviewer would notice first** is that none of the static tooling has been *run*. A
   repo whose CI config is correct and unexecuted is a repo with an unknown number of violations. First
   `make check` will produce a list.

---

# 17. Recommendation

### 1 · Freeze permanently

The domain model, the architecture's component set, and the technical design's **identity model,
claim protocol, publication transaction, fencing semantics, and invariant set**. The review found
nothing that contradicts them, and found external literature arriving at the same lease/fencing design
independently.

### 2 · Change before implementation — four small things

| | Where | Effort |
|---|---|---|
| **Hypothesis property tests for `core/identity`** | M0, the current task | ~1 hour |
| **`pip-audit` in the static CI job** | now | ~10 min |
| **Correlation ID in `obs/log.py` + `MODEL_CALL`** | M2 | ~1 hour |
| **Note RLS-compatibility in the M1 schema** (a comment; do not enable) | M1 | ~0 |

**Nothing else.** Two spikes are scheduled (DBOS at M6, PydanticAI at M2) and neither blocks M0.

### 3 · Learn now

**Durable execution** and the vocabulary around it — fencing tokens, idempotency keys, leases,
at-least-once vs effectively-once. You already *use* all four; knowing the names means you can read the
literature and recognise when someone is selling you a solved problem.

Then: **`SKIP LOCKED`**, **Little's law**, **admission control vs accounting**, **structured
outputs**, **MCP's shape**, **property-based testing**.

### 4 · Merely know exists

A2A · event sourcing/CQRS · sagas · transactional outbox · distributed SQL · serverless Postgres ·
pgvector · DuckDB · SPIFFE · OPA/Cedar/OpenFGA · SBOM/sigstore/SLSA · deterministic simulation testing ·
Temporal/Restate/Inngest/Trigger.dev · LangGraph/ADK/Agents SDK · Phoenix/Braintrust/LangSmith · OTel
GenAI semconv · Gotenberg · Typst · `ty`/pyrefly.

### 5 · Deliberately do not use

An agent framework · a gateway proxy · a vector database · RAG · Kafka/NATS/RabbitMQ/Redis ·
Temporal · microservices · event sourcing · an MCP server (yet) · A2A · LangChain.

**For each, the reason is a missing requirement rather than a preference** — which is the difference
between a deliberate choice and an accidental one, and the whole point of this review.

### 6 · Revisit later

Per §15.E's trigger table. Each has a condition, not a date.

### 7 · The next coding milestone — unchanged

**`core/identity`**, with one addition from this review:

```
core/identity/{canonical,envelope,task_key,claim_key,member,content,fingerprint}.py
tests/test_boundaries.py          the wall, already written
tests/unit/test_identity.py       the §15.2 golden table, both directions
tests/unit/test_identity_props.py Hypothesis properties            ◄── NEW, from §10
```

The property tests are the review's one change to the current task, and they are the right shape for
it: *for any two logically-equal inputs the envelope is equal; for any difference in an included field
it differs; for any difference in an excluded field it does not.* The golden table samples that;
Hypothesis searches it.

---

## Sources

[Durable execution deep dive (LabHub)](https://labhub.hopto.org/blog/culture/2026-05-14-durable-execution-engines-2026-temporal-restate-inngest-trigger-dev-dbos-deep-dive-2026?lang=en) ·
[Restate vs Temporal vs DBOS (Kanopy)](https://kanopylabs.com/blog/restate-vs-temporal-vs-dbos-durable-execution) ·
[Temporal alternatives (ZenML)](https://www.zenml.io/blog/temporal-alternatives) ·
[DBOS Transact Python](https://github.com/dbos-inc/dbos-transact-py) ·
[Why Postgres for durable execution (DBOS)](https://www.dbos.dev/blog/why-postgres-durable-execution) ·
[Durable execution, idempotency, or both](https://opulion.dev/ground-truth/durable-execution-idempotency-or-both) ·
[Durable workflows on Postgres (InfoQ)](https://www.infoq.com/articles/durable-workflows-postgres/) ·
[Agent frameworks (LangChain)](https://www.langchain.com/resources/ai-agent-frameworks) ·
[Picking an agent framework (AWS)](https://builder.aws.com/content/3AzsgG6TreTO3uLRqpWNxfEyUhe/picking-an-ai-agent-framework-in-2026) ·
[LangGraph vs Agents SDK vs PydanticAI](https://open-techstack.com/blog/langgraph-vs-openai-agents-sdk-vs-pydanticai-2026/) ·
[A2A one-year milestone (Linux Foundation)](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year) ·
[State of agentic AI standards 2026](https://dev.to/alexmercedcoder/the-state-of-agentic-ai-standards-in-2026-mcp-a2a-webmcp-osi-and-the-protocol-stack-taking-3o2l) ·
[Agent interoperability protocols survey (arXiv)](https://arxiv.org/pdf/2505.02279) ·
[LiteLLM alternatives (Eden AI)](https://www.edenai.co/post/best-alternatives-to-litellm) ·
[LiteLLM alternatives (Kosmoy)](https://www.kosmoy.com/resources/blog/litellm-alternatives/) ·
[OTel GenAI semconv status](https://praesidia.ai/blog/opentelemetry-genai-semantic-conventions-status) ·
[OTel GenAI conventions (Greptime)](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions) ·
[LLM eval frameworks and metrics](https://bigdataboutique.com/blog/llm-evaluation-frameworks-metrics-best-practices) ·
[DeepEval alternatives (Braintrust)](https://www.braintrust.dev/articles/deepeval-alternatives-2026) ·
[Prompt testing tools 2026](https://www.promptquorum.com/prompt-engineering/best-prompt-testing-evaluation-tools) ·
[ty in beta (InfoWorld)](https://www.infoworld.com/article/4108979/python-type-checker-ty-now-in-beta.html) ·
[mypy vs pyright vs ty](https://www.danilchenko.dev/posts/ty-vs-mypy-vs-pyright/) ·
[ty handbook (pydevtools)](https://pydevtools.com/handbook/topics/ty/) ·
[Postgres SKIP LOCKED (Prisma)](https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked) ·
[pgqueuer vs Celery](https://github.com/janbjorge/pgqueuer/discussions/298) ·
[Replacing MQ with Postgres](https://mvpfactory.io/blog/replacing-your-message-queue-with-postgresql-skip-locked-queues-listen-notify) ·
[HTML→PDF benchmark 2026](https://pdf4.dev/blog/html-to-pdf-benchmark-2026) ·
[Playwright vs WeasyPrint](https://pdf4.dev/blog/playwright-vs-weasyprint)
