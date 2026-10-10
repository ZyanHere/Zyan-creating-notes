# AI Application Engineering — Technology Landscape & Learning Map

**A conceptual taxonomy, not a product list.** The products change; the categories do not. If you know
what a *category* is called, you can find its current best tool in an afternoon. If you do not, no
amount of searching helps — which is the problem this document exists to fix.

**Researched October 2026.** Products are representative, not exhaustive, and are named only to anchor
a category.

---

## How this is classified

| | Meaning |
|---|---|
| 🔴 **Learn deeply now** | changes decisions you are making this month. Read the primary docs, build something small |
| 🟠 **Learn conceptually** | understand what it solves and when it is right. You should be able to explain it to someone |
| 🔵 **Know it exists** | recognise the word, know roughly which box it sits in, look it up when it appears |
| ⚪ **Ignore for now** | real technology, not your problem |

A classification is about *you, now* — not about the technology's importance. Kafka is 🔵 for you and
foundational for a streaming team.

---

## The standing rule this document comes from

```
Problem → Technology category → Current ecosystem (mature · modern · emerging)
        → Tradeoff analysis → Recommendation → What we rejected, and why
```

You should never need to know a technology's name before it gets considered. Where something is
relevant and unnecessary, the form is: *"This exists. It solves X. We do not need it because Y"* — with
a **trigger** rather than a date.

---

# 1 · Model layer

**The problem:** get structured, reliable output from a language model, at acceptable cost and
latency.

| Category | What it is | Representative | Class |
|---|---|---|---|
| **Model API / SDK** | a typed client for one provider's HTTP API. No orchestration | `anthropic`, `openai`, `google-genai` | 🔴 |
| **Structured outputs** | constraining a model to emit schema-valid JSON, usually enforced provider-side | OpenAI structured outputs, Anthropic tool-use-as-schema, Pydantic models | 🔴 |
| **Constrained decoding** | the *mechanism* underneath: mask the token distribution so only grammar-valid tokens can be sampled | Outlines, llguidance, XGrammar, GBNF | 🟠 |
| **Model gateway** | a proxy over many providers: routing, retries, rate limits, budgets, caching, observability | LiteLLM, Portkey, Cloudflare AI Gateway, OpenRouter, Bifrost | 🔴 |
| **Provider routing / fallback** | choose a model per request; fail over when one is down or slow | gateway feature; OpenRouter natively | 🟠 |
| **Prompt caching** | provider-side reuse of a repeated prompt prefix, billed at a discount | Anthropic, OpenAI, Gemini | 🟠 |
| **Batch inference** | submit many requests for cheaper, slower, asynchronous processing | OpenAI/Anthropic batch APIs | 🔵 |
| **Inference serving** | you host the weights; throughput engineering becomes yours | vLLM, SGLang, TensorRT-LLM, llama.cpp | 🔵 |
| **Inference concepts** | KV cache · continuous batching · speculative decoding · quantisation · context window vs effective context | — | 🟠 |
| **Fine-tuning / adaptation** | LoRA, QLoRA, DPO, RLHF — changing the model rather than the prompt | — | 🔵 |
| **Embeddings** | text → vector, for similarity rather than generation | provider endpoints, `sentence-transformers` | 🟠 |

**The distinction people blur:** *structured outputs* is the feature you use; *constrained decoding*
is how it works. You need the first deeply and the second conceptually — enough to know why a schema
with a recursive type or an unbounded string can hurt you.

**The one worth internalising:** **structured outputs changed application architecture.** Before them,
you parsed prose and prayed. After them, a model call is a typed function returning a validated
object — which is why MyNotes has no agent framework. Once calls are typed, ordinary code is a
perfectly good orchestrator.

---

# 2 · Agent layer

**The problem:** let a model take actions, in sequence, with tools, possibly with other agents.

| Category | What it is | Representative | Class |
|---|---|---|---|
| **Typed agent library** | schema-validated model calls, retry-on-validation-error, minimal control flow | **PydanticAI** | 🔴 |
| **Agent SDK** | a vendor's opinionated runtime for loops, tools, handoffs | OpenAI Agents SDK, Claude Agent SDK | 🟠 |
| **Agent framework** | batteries-included multi-agent runtime, often with a UI and deployment story | Google ADK, CrewAI, Agno, Strands, Microsoft Agent Framework | 🟠 |
| **Graph / state-machine orchestration** | you declare nodes and edges; the runtime executes, checkpoints and resumes | **LangGraph** | 🟠 |
| **Tool calling** | the protocol by which a model requests a function call and receives its result | every provider | 🔴 |
| **MCP** — Model Context Protocol | standard wire protocol so *any* host can discover and call *any* tool server. Tools → agent | Linux Foundation project | 🔴 (shape) |
| **A2A** — Agent2Agent | standard protocol for agents to negotiate across organisational boundaries. Agent → agent. **v1.0, 150+ orgs, production use**; IBM's ACP merged into it | Linux Foundation project | 🔵 |
| **Multi-agent patterns** | supervisor/worker, debate, reflection, hierarchical delegation | — | 🟠 |
| **Context engineering** | the discipline that replaced "prompt engineering": deciding what goes in the window, in what order, at what cost | — | 🔴 |
| **Agent memory** | short-term (the window), episodic (past sessions), semantic (facts), procedural (learned skill) | Mem0, Zep, Letta | 🟠 |
| **Computer/browser use** | agents driving a GUI or browser | Playwright-based, provider computer-use APIs | 🔵 |

**The distinction that matters most, and that assistants routinely blur:**

```
a MODEL SDK            gives you one call
a TYPED AGENT LIBRARY  gives you one VALIDATED call, with retry
an AGENT SDK/FRAMEWORK decides your CONTROL FLOW
GRAPH ORCHESTRATION    makes control flow a declared artifact, with checkpointing
```

**The question that chooses between them:** *who owns control flow?* If your application knows the
sequence of steps, you do not need an agent framework and should not take one — it will own the thing
you already know. If the sequence is genuinely model-decided, you do.

**MyNotes owns its control flow**, which is why it has no framework. That is a position, not a gap.

**MCP in one paragraph**, because you will meet it constantly: a server exposes tools, resources and
prompts over JSON-RPC (stdio or HTTP); a client inside a host discovers and calls them. Before MCP,
every (host × tool) pair was bespoke. The value is N×M → N+M, which is only value when N or M exceeds
one. Learn its **shape**; implement one when you have a second consumer.

---

# 3 · Execution layer — the vocabulary you were missing

**The problem:** run work that is long, fallible, expensive, and must not be done twice.

This is the single most valuable section in this document, because the words are unguessable and the
concepts are what separate a demo from a system.

## The layers, in order of what they guarantee

| Category | What it is | Guarantees | Representative | Class |
|---|---|---|---|---|
| **Queue** | a buffer. "Someone do this." You own retries and state | at-least-once delivery | Postgres `SKIP LOCKED`, Redis/BullMQ, SQS, Celery, pgqueuer, pgmq | 🔴 |
| **Scheduler** | runs things at times | it fires, eventually | cron, APScheduler, Cloud Scheduler | 🟠 |
| **Event log** | append-only, ordered, replayable; many consumers with independent offsets | ordering, replay | Kafka, Redpanda, NATS JetStream, Pulsar | 🔵 |
| **Workflow engine** | executes a multi-step graph and tracks which step you are on | the graph completes | Airflow, Dagster, Prefect, Step Functions | 🟠 |
| **Durable execution** | your **function** survives process death; completed steps are not re-run | **effectively-once per step** | **Temporal, Restate, DBOS, Inngest, Trigger.dev** | 🔴 |

**These are layers, not competitors.** Durable execution is usually implemented over a queue. An event
log is a different shape entirely — fan-out and replay, not work distribution.

## Durable execution, properly

**The problem it solves, in one sentence:** *a function that calls a paid API, crashes, and restarts
must not pay twice.*

Two implementation families, and knowing which you are looking at tells you its failure modes:

```
JOURNAL REPLAY        re-run the function from the top; completed steps are served
(Temporal, Restate)   from a journal instead of executing. Your code must be
                      deterministic, because it is replayed.

DB CHECKPOINTING      each step ends with a database transaction storing its result.
(DBOS, Inngest,       No replay, no determinism requirement, but every step is a write.
 Trigger.dev)
```

| | Infrastructure | Latency | Notes |
|---|---|---|---|
| **Temporal** | server cluster | 50–200 ms invocation | the mature standard; best for complex long-lived cross-service workflows |
| **Restate** | **single binary**, embedded storage | single-digit ms | same guarantees, far less infra; viable on a request path; virtual-object model from Orleans |
| **DBOS** | **none — a library over Postgres** | DB-bound | best when Postgres is already your trusted state |
| **Inngest / Trigger.dev** | hosted | — | excellent DX, TypeScript-first |

**Its failure mode, worth knowing before you adopt:** Postgres-backed durable execution *"breaks first
on contention — every step does at least one write, and hot workflows that fan out to thousands of
children will hammer a single cluster."* Journal-replay engines scale further and cost a cluster.

## The consistency primitives

| Concept | What it is | Class |
|---|---|---|
| **Idempotency key** | a caller-supplied id that makes a retry a no-op | 🔴 |
| **Optimistic concurrency / CAS** | `UPDATE … WHERE version = :observed` — concurrency control without locks | 🔴 |
| **Lease** | a time-bounded right to work on something | 🔴 |
| **Fencing token** | a monotonic number proving your lease is current. **A lease without one is not safe** | 🔴 |
| **Checkpointing** | recording completed work so it is not redone | 🔴 |
| **At-least-once / at-most-once / effectively-once** | delivered ≥1 / ≤1 / observable effect exactly once. **True exactly-once across a network is impossible** | 🔴 |
| **Backpressure** | slowing or refusing input when you cannot keep up | 🔴 |
| **Admission control** | deciding *before* doing the work whether you may. **Different from accounting, which records it after** | 🔴 |
| **Transactional outbox** | write business data and "send this message" in **one** transaction, so you cannot commit one without the other | 🟠 |
| **Saga / compensation** | multi-step transaction undone step-by-step, because you cannot un-send an email | 🟠 |
| **Event sourcing** | state *is* the log of events; current state is a fold over it | 🟠 |
| **CQRS** | separate write model from read models, often with event sourcing | 🔵 |
| **Two-phase commit** | distributed atomic commit. Mostly avoided; sagas exist because of its cost | 🔵 |
| **Deterministic replay** | re-executing from a log must produce the same result — the constraint journal engines impose | 🟠 |

**The lease trade, memorised:** *too short and a slow-but-alive worker has its work stolen; too long
and recovery after a crash is delayed.* That is why a fencing token exists — it makes theft safe rather
than preventing it.

**Admission vs accounting, because it is the error I made in MyNotes and had to fix:** a post-hoc
ledger tells you that you overspent. Only a pre-call conditional increment stops you. They are
different mechanisms and one cannot do the other's job.

---

# 4 · Data layer

**The problem:** store things, find them again, and keep them correct under concurrency.

| Category | What it is for | Representative | Class |
|---|---|---|---|
| **Relational / OLTP** | transactions, constraints, joins. The default, correctly | **PostgreSQL**, MySQL, SQLite | 🔴 |
| **Distributed SQL** | SQL + horizontal scale + multi-region, at latency cost | CockroachDB, YugabyteDB, TiDB, Spanner | 🔵 |
| **Serverless Postgres** | Postgres with scale-to-zero and **branch-per-PR** | Neon, Supabase, Aurora Serverless | 🟠 |
| **Document** | schema-flexible aggregates | MongoDB, Couchbase, Firestore | 🔵 |
| **Key-value** | caching, counters, sessions, locks | Redis, Valkey, DynamoDB, etcd | 🟠 |
| **Embedded** | in-process, zero ops. SQLite is the most-deployed database in the world | **SQLite**, DuckDB, LMDB, RocksDB | 🟠 |
| **Vector** | similarity search over embeddings | **pgvector**, Qdrant, Weaviate, LanceDB, Milvus | 🟠 |
| **Search** | ranked full-text, facets, typo tolerance | Elasticsearch, OpenSearch, Typesense, Meilisearch, Postgres FTS | 🟠 |
| **Analytical / columnar** | aggregate scans over many rows | **DuckDB**, ClickHouse, BigQuery, Snowflake | 🟠 |
| **Event store** | append-only history as the source of truth | EventStoreDB, Kafka-as-log | 🔵 |
| **Object storage** | large immutable blobs. **Egress pricing is the deciding factor** | S3, **Cloudflare R2** (no egress fee), MinIO, B2, GCS | 🔴 |
| **Time series** | metrics over time, with retention and downsampling | TimescaleDB, Prometheus, InfluxDB, VictoriaMetrics | 🟠 |
| **Graph** | relationship traversal as the primary query | Neo4j, Memgraph, Apache AGE | 🔵 |
| **Cache** | a faster copy, with an invalidation problem | Redis, Memcached, CDN | 🟠 |

## Postgres features worth knowing specifically

Most "we need another database" conclusions are really "we did not know Postgres does this."

| Feature | What it replaces |
|---|---|
| `FOR UPDATE SKIP LOCKED` | a job queue — holds comfortably to ~10,000 jobs/min |
| `LISTEN` / `NOTIFY` | a pub/sub broker, for wake-ups |
| `INSERT … ON CONFLICT … DO UPDATE … WHERE` | atomic upsert-with-condition — the admission primitive |
| `jsonb` + GIN | a document store, for most purposes |
| **Row-level security (RLS)** | an authorization layer, enforced in the database |
| `pgvector` | a vector database, until scale says otherwise |
| full-text search | a search engine, at moderate scale |
| logical replication / CDC | a change-data-capture pipeline |
| **NULLs are DISTINCT in `UNIQUE`** | — a sharp edge, not a feature. PG15+ adds `NULLS NOT DISTINCT` |

**The one most people miss:** **RLS**. It moves tenant isolation from "every query remembers to filter"
to "the database refuses." Retrofitting it is painful; designing so it remains possible is free.

## RAG and vector databases — the most over-recommended architecture

**What RAG is:** embed documents, store vectors, retrieve the nearest at query time, put them in the
prompt.

**When it is right:** the model must answer from a corpus it was not trained on, that corpus is large,
and the questions are unpredictable.

**When it is not:** the corpus is small (put it in the prompt); the questions are structured (use SQL);
the "retrieval" is really a lookup by key; or there is no corpus at all.

**Why it dominates recommendations anyway:** it has the most tutorial content of any AI architecture.
That is a property of the corpus, not of your problem. 🟠 — understand it, be sceptical of it, and when
you do need it start with **pgvector in the database you already run**, not a separate service.

---

# 5 · Production engineering

| Category | What it is | Class |
|---|---|---|
| **Modular monolith** | one deployable, enforced internal boundaries. **The current default**, after a decade of microservice regret | 🔴 |
| **Microservices** | independent deployables. Buys independent scaling and deployment; costs distributed-systems problems in every interaction | 🟠 |
| **Hexagonal / ports and adapters** | domain core, I/O at the edges behind interfaces | 🔴 |
| **Dependency injection** | pass collaborators in rather than constructing them. In Python: usually plain constructor arguments; FastAPI's `Depends` for request scope | 🔴 |
| **Service boundaries** | where to split: around data ownership, not around teams or nouns | 🟠 |
| **API design** | REST, RPC, GraphQL, gRPC — and the versioning and pagination questions that outlive the choice | 🔴 |
| **Idempotent API design** | `Idempotency-Key` headers, safe retries, exactly-once *effects* | 🔴 |
| **Distributed systems basics** | CAP, partial failure, clock skew, retry storms, thundering herds, the fallacies of distributed computing | 🟠 |
| **Backends for frontends** | a per-client API layer | 🔵 |
| **Strangler fig** | incrementally replacing a system by routing traffic away from it | 🔵 |

**The boundary rule worth internalising:** *a module boundary you cannot enforce is a boundary you will
lose.* Comments and conventions decay; an import test does not. This is the single highest-leverage
practice in this section and almost nobody does it.

---

# 6 · Observability and evaluation

**The problem:** know what your system did, and whether it did it well. Those are two different
problems and need different tools.

## Observability — what happened

| Category | What it is | Representative | Class |
|---|---|---|---|
| **Structured logging** | events as data, not prose. One line of JSON beats a paragraph | `structlog`, stdlib `logging` + JSON | 🔴 |
| **Correlation / trace IDs** | one id threaded through every event of one operation | — | 🔴 |
| **Metrics** | counters, gauges, histograms. Aggregates, not events | Prometheus, StatsD | 🟠 |
| **Distributed tracing** | spans with parent/child, showing where time went | Jaeger, Tempo, Zipkin | 🟠 |
| **OpenTelemetry** | the vendor-neutral standard for all three. **OTLP is stable** | OTel SDKs + collector | 🔴 |
| **OTel GenAI semantic conventions** | standard attribute names for LLM telemetry. **Still "Development" status as of mid-2026**; moved to a separate repo in June 2026 | — | 🟠 |
| **LLM tracing / observability** | prompt, completion, tokens, cost, latency per call, and the tree of an agent run | LangSmith, Phoenix/Arize, Langfuse, Braintrust, Helicone | 🟠 |
| **Error tracking** | exceptions with context, grouped and alerted | Sentry | 🟠 |
| **Profiling** | where CPU and memory actually go | py-spy, memray, Pyroscope | 🟠 |

**The trap:** adopting a GenAI-specific observability vendor before you have structured logs with
correlation ids. The vendor gives you a pretty trace of an agent run; it does not tell you why your
Postgres connection pool exhausted.

**The thing to know:** no `gen_ai.*` attribute is safe to build dashboards on yet. Mirror the four core
names (operation, provider, model, token usage) so a later migration is a rename.

## Evaluation — whether it was good

| Category | What it is | Representative | Class |
|---|---|---|---|
| **Golden dataset** | a versioned set of inputs with known-good outputs or human judgments | — | 🔴 |
| **Regression evals in CI** | run the golden set on every change; block on a score drop. 100–500 examples is the norm | DeepEval, Promptfoo, RAGAS | 🔴 |
| **LLM-as-judge** | a model scoring another model's output against a rubric | all of the above | 🔴 |
| **Eval platforms** | annotation UI, dashboards, trace→dataset, CI gating | Braintrust, LangSmith, Phoenix | 🟠 |
| **Capability benchmarks** | MMLU, GPQA, SWE-bench — about *models*, rarely about your app | — | 🔵 |
| **Red-teaming / adversarial evals** | finding inputs that break it | Promptfoo, Garak | 🟠 |
| **Online evals / guardrails** | scoring or blocking in production, in the request path | — | 🟠 |

**The layered pattern practice converged on:**

```
1  capability benchmarks     about the MODEL. Rarely your concern.
2  application metrics       about YOUR app. Lightweight, in CI, gating merges.
3  hosted platform           human annotation, regression tracking, dashboards.
```

The converged recommendation is **two tools**: one lightweight framework for CI gating, one platform
for annotation and tracking.

**The hardest and most valuable part is not the tool.** It is building the golden dataset — deciding
what "good" means for your product, writing reference outputs by hand, and keeping them versioned.
Teams skip it because it is unglamorous, then wonder why their evals do not catch anything.

**And the unavoidable prerequisite:** evaluation needs *repeatable runs*. On a rate-limited free tier,
you cannot evaluate; you can only sample.

---

# 7 · Security

| Category | What it is | Representative | Class |
|---|---|---|---|
| **Authentication** | who is this | — | 🔴 |
| **Authorization** | may they do this | — | 🔴 |
| **Sessions** | server-side state keyed by an opaque token. **The right default for first-party web apps** | — | 🔴 |
| **JWT** | a signed, self-describing token. Fast to validate, **hard to revoke** | — | 🔴 |
| **OAuth 2.0 / OIDC** | delegated authorization / federated identity. "Log in with…" | Auth0, Clerk, WorkOS, Keycloak, Supabase Auth | 🟠 |
| **Passkeys / WebAuthn** | public-key credentials replacing passwords. Phishing-resistant | — | 🟠 |
| **mTLS / service identity** | services proving who they are to each other | **SPIFFE/SPIRE**, cloud workload identity | 🔵 |
| **Policy engines** | authorization as declarative policy, outside the application | **OPA**/Rego, **Cedar** (AWS), **OpenFGA** (Zanzibar-style) | 🟠 |
| **Row-level security** | authorization enforced by the database | Postgres RLS | 🟠 |
| **Secrets management** | keeping credentials out of code and images | Vault, cloud KMS, SOPS, age, sealed-secrets | 🟠 |
| **Supply-chain security** | knowing and attesting what is in your build | **SBOM** (CycloneDX/SPDX), **sigstore**, **SLSA**, `pip-audit` | 🟠 |
| **Prompt injection** | untrusted text reaching a model that takes actions. **The AI-native vulnerability class** | — | 🔴 |
| **Data exfiltration via tools** | an injected instruction making an agent leak through a tool it legitimately has | — | 🟠 |
| **Tenant isolation** | one customer cannot reach another's data | scoped queries → RLS → schema-per-tenant → DB-per-tenant | 🔴 |
| **Rate limiting / quotas** | abuse and cost control | — 🔴 |

**The JWT-versus-session decision, since it is the one you will face first:**

```
first-party app, one backend, a database you query anyway
    → OPAQUE SESSION TOKEN, server-side state.
      Revocation is a DELETE. Logout is real.

many services, validating without a DB round trip
    → short-lived JWT access token + opaque refresh token (the 2026 hybrid default)

JWT as a session token with a revocation denylist
    → you have built a session store with extra steps
```

**Prompt injection deserves its own paragraph**, because it has no clean fix and it is the one risk
that is genuinely new. Any text a model reads is potentially an instruction: a web page, a PDF, a
user-supplied syllabus, a tool's output. Defences are *layers*, not solutions — least-privilege tools,
human confirmation for consequential actions, output filtering, treating retrieved content as data
with explicit framing, and never granting an agent a capability whose misuse you could not tolerate.
**The risk arrives the moment you ingest untrusted documents**, not when you deploy.

---

# 8 · Testing

| Category | What it is | Representative | Class |
|---|---|---|---|
| **Unit** | one function, no I/O | pytest | 🔴 |
| **Integration** | real dependencies — a real database, not a mock | pytest + testcontainers | 🔴 |
| **End-to-end** | the whole system as a user meets it | Playwright, pytest | 🟠 |
| **Property-based** | assert a *property*; the framework searches for counterexamples | **Hypothesis**, fast-check | 🔴 |
| **Snapshot / golden-file** | assert output matches a reviewed artifact | syrupy, pytest-regressions | 🟠 |
| **Contract testing** | consumer and provider agree on an interface, verified independently | Pact | 🔵 |
| **Mutation testing** | mutate the code; if tests still pass, they were not testing it | mutmut, cosmic-ray | 🟠 |
| **Load / stress** | behaviour under volume | k6, Locust, vegeta | 🟠 |
| **Deterministic simulation testing** | run the whole system on a controlled clock and scheduler so races are **reproducible** | FoundationDB's method; **Antithesis** commercialises it | 🟠 |
| **Chaos / fault injection** | break things deliberately in a running system | Toxiproxy, Chaos Mesh | 🔵 |
| **Fuzzing** | random/guided inputs hunting crashes | Atheris, AFL | 🔵 |

**The two most undervalued, both 🔴 or close:**

**Property-based testing.** A hand-written table of examples is a finite sample of a property you could
have stated. *"For any two logically-equal inputs, the hash is equal"* is testable directly, and
Hypothesis will find the surrogate-pair string you never thought of. Anything involving
canonicalisation, serialisation, parsing or identity is exactly its shape.

**Deterministic simulation testing.** The reason concurrency bugs are hard is that you cannot reproduce
them. If time and scheduling are **injected** rather than ambient, a race becomes a test. You do not
need Antithesis to get most of the value — a `Clock` port and an injected scheduler get you a long way,
and *"never call `datetime.now()` outside the clock"* is a rule with outsized returns.

---

# 9 · Infrastructure and deployment

| Category | What it is | Representative | Class |
|---|---|---|---|
| **Containers** | a reproducible process image | Docker, Podman, OCI | 🔴 |
| **Local orchestration** | several containers for development | docker compose | 🔴 |
| **PaaS** | push code, get a URL. The right default for a small team | Render, Railway, Fly.io, Heroku | 🔴 |
| **Serverless functions** | per-request compute, scale to zero. **Hostile to long-running work** | Lambda, Cloud Run, Vercel Functions | 🟠 |
| **Kubernetes** | container orchestration, and a career | k8s, k3s, EKS/GKE/AKS | 🟠 |
| **IaC** | infrastructure as reviewable code | Terraform, OpenTofu, Pulumi, CDK | 🟠 |
| **Service mesh** | mTLS, retries and traffic policy between services | Istio, Linkerd | 🔵 |
| **CI/CD** | build, test, ship on every change | GitHub Actions, GitLab CI, Buildkite | 🔴 |
| **Deployment strategies** | blue-green, canary, rolling, **feature flags** | — | 🟠 |
| **Edge / CDN** | serve bytes near the user; sometimes run code there | Cloudflare, Fastly | 🟠 |
| **Artifact registries** | where images and packages live | GHCR, ECR, PyPI | 🟠 |

**The trap worth naming:** **serverless and long-running AI work are a poor fit.** A 342-second
planning call does not survive a 30-second function timeout, and the workarounds (fire-and-poll,
step functions, streaming keep-alives) are more complex than a small always-on process. Choose
serverless for the *frontend* and request-path work; keep long work on something that stays alive.

---

# 10 · Python engineering specifically

| Category | Current best | Class |
|---|---|---|
| **Package / project manager** | **uv** (Rust; resolver + lockfile + Python version management). Alternatives: Poetry, PDM, pip-tools | 🔴 |
| **Lockfile** | `uv.lock` — reproducibility, non-negotiable | 🔴 |
| **Lint + format** | **ruff** (replaces flake8 + isort + black + much of pylint) | 🔴 |
| **Type checker** | **pyright** / basedpyright (strict). **mypy** still the reference. **ty** (Astral, Rust) in beta — 10–60× faster, ~53% conformance vs pyright's 98%. **pyrefly** (Meta) similar trade | 🔴 |
| **Validation / settings** | **pydantic v2**, **pydantic-settings** | 🔴 |
| **Async** | `asyncio`; `anyio` for structured concurrency; TaskGroups | 🔴 |
| **Web framework** | **FastAPI** (ASGI, typed, DI). Litestar as a serious alternative; Django for batteries | 🔴 |
| **DB driver** | **psycopg3** (async, pipeline mode); asyncpg; SQLAlchemy 2.0 for an ORM | 🔴 |
| **Testing** | pytest + pytest-asyncio + **Hypothesis** + testcontainers | 🔴 |
| **Task running** | Make, just, or `uv run` scripts | 🟠 |
| **Pre-commit** | `pre-commit` hooks | 🟠 |

**The shift worth understanding:** Astral (ruff, uv, ty) rewrote Python tooling in Rust, and the speed
difference changed behaviour — a type check that takes five seconds runs on every save; one that takes
forty-five runs in CI if you remember. **Tool latency is a correctness feature**, because it changes how
often the tool runs.

---

# 11 · What to learn, in order

Not a reading list — a build list. Each item is something you understand by doing once.

### Now (this month)

1. **Durable execution + its vocabulary** — idempotency key, lease, fencing token, at-least-once vs
   effectively-once. You already use all four. Read Temporal's and DBOS's conceptual docs; the
   vocabulary transfers everywhere.
2. **Postgres as more than a table store** — `SKIP LOCKED`, `LISTEN/NOTIFY`, `ON CONFLICT … WHERE`,
   RLS. Build a 50-line job queue on `SKIP LOCKED`. It will change what you reach for.
3. **Admission control vs accounting** — the distinction that cost MyNotes a revision to get right.
4. **Structured outputs** — the thing that makes typed AI applications possible.
5. **Property-based testing** — one afternoon with Hypothesis on a canonicalisation function.
6. **The auth boundary** — `Principal`, a session store, authorization on every scoped read. Smallest
   version that is architecturally correct.
7. **MCP's shape** — server, client, transport, capabilities. Read the spec's overview.

### Conceptually (next few months)

Journal-replay vs DB-checkpointing durable execution · event sourcing and CQRS, enough to recognise
when someone needs them · sagas and the outbox pattern · OpenTelemetry's three signals · LLM-as-judge
and golden datasets · OAuth 2.0/OIDC flows · policy engines (OPA/Cedar) · RAG, sceptically · agent
frameworks, enough to decline them for a reason · hexagonal architecture · deterministic simulation
testing.

### Know it exists

A2A · distributed SQL · Kafka/NATS · graph databases · service mesh · Kubernetes internals · SPIFFE ·
SLSA/sigstore · contract testing · fuzzing · inference serving (vLLM/SGLang) · fine-tuning ·
multi-agent patterns · computer-use agents · chaos engineering · `ty`/pyrefly.

### Ignore for now

Blockchain-anything · AGI-adjacent framing · "autonomous agent swarms" with no task to do ·
a vector database before you have a retrieval problem · Kubernetes before you have more than one
service · microservices before you have more than one team.

---

# 12 · The honest meta-lesson

Three biases shape what gets recommended to you, and knowing them is worth more than any single
technology on this page.

**1 · Tutorial volume is not production relevance.** LangChain, RAG and vector databases have the most
written about them, so they surface first. Durable execution, content-addressed memoisation and
admission control have far less written about them and far more bearing on whether a system works.
The imbalance lives in the corpus.

**2 · Vendor content dominates comparison searches.** Searching *"X alternatives 2026"* returns pages
written largely by X's competitors, ranking themselves first, with benchmark numbers nobody has
reproduced. Read them for the *category map* — which is genuinely useful — and treat the rankings as
advertising.

**3 · "Newer" and "better" are different axes, and "well-known" is a third.** The question is never
*"is this modern?"* It is *"what problem does this solve, do I have that problem, and what does it
cost me to adopt?"* A technology you rejected for a stated reason is a decision. A technology you
never heard of is an accident.

**The discipline that follows:** for any serious decision, name the *category* first. Categories are
stable, findable, and small in number. Products churn. If you know that *"durable execution"* is a
category, you will find Temporal, Restate and DBOS in ten minutes — and you will also know that your
hand-rolled version is a member of that category, which is the thing that is genuinely hard to see
from inside.

---

## Sources

[Durable execution engines compared (LabHub)](https://labhub.hopto.org/blog/culture/2026-05-14-durable-execution-engines-2026-temporal-restate-inngest-trigger-dev-dbos-deep-dive-2026?lang=en) ·
[Restate vs Temporal vs DBOS](https://kanopylabs.com/blog/restate-vs-temporal-vs-dbos-durable-execution) ·
[DBOS system tables](https://docs.dbos.dev/explanations/system-tables) ·
[DBOS Transact Python](https://github.com/dbos-inc/dbos-transact-py) ·
[Durable execution, idempotency, or both](https://opulion.dev/ground-truth/durable-execution-idempotency-or-both) ·
[Agent frameworks (LangChain)](https://www.langchain.com/resources/ai-agent-frameworks) ·
[Picking an agent framework (AWS)](https://builder.aws.com/content/3AzsgG6TreTO3uLRqpWNxfEyUhe/picking-an-ai-agent-framework-in-2026) ·
[A2A one-year milestone (Linux Foundation)](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year) ·
[Agent interoperability protocols survey](https://arxiv.org/pdf/2505.02279) ·
[OTel GenAI semconv status](https://praesidia.ai/blog/opentelemetry-genai-semantic-conventions-status) ·
[LLM eval frameworks and metrics](https://bigdataboutique.com/blog/llm-evaluation-frameworks-metrics-best-practices) ·
[JWT vs opaque tokens](https://guptadeepak.com/jwt-vs-opaque-tokens-api-authentication-2026/) ·
[Stop defaulting to JWTs](https://reptile.haus/journal/stop-defaulting-to-jwts-choosing-the-right-session-architecture-in-2026/) ·
[Session management](https://identitysecurity.tech/paths/session-management/) ·
[Postgres SKIP LOCKED](https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked) ·
[ty in beta (InfoWorld)](https://www.infoworld.com/article/4108979/python-type-checker-ty-now-in-beta.html) ·
[mypy vs pyright vs ty](https://www.danilchenko.dev/posts/ty-vs-mypy-vs-pyright/)
