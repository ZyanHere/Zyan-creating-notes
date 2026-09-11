# Build Specification — MVP · Rev. 2

**5 Sep 2026 · implements `System-Design.md` (Rev. 4)**

> **Rev. 2 — implementation defects, no architecture reopened.** Explicit migration ordering for circular references (§3); `inputs_hash` given a formal envelope rule and a mechanism that enforces it (§4); delivery gets its own transaction, T9 (§5); conditional decisions become an **applicability branch** rather than throwing stubs (§1); structural verification moves earlier in the build order (§10). Two further defects found on re-read: T7 did not invalidate member-targeted verification, and T8 did not recompute successors' entry premises.
>
> One reported defect was not a defect: `UNIQUE (member_id, ord)` always permitted many versions per member. The column is renamed `version_number` because `ord` meant two different things on two tables, which is what made it misread.

System Design Rev. 4 is the baseline and is **not reopened here**. Architectural questions are settled; this document is answerable only to *"does the implementation satisfy the invariant."* If an implementation contradiction is found, it is raised as a defect against Rev. 4 — it is not resolved by improvising in code.

**Layering.** System Design deliberately said *conceptual records, not tables*. This document is where they become tables, endpoints, transactions and tests. Everything below is **implementation** in Rev. 4 §0's sense, except where it is the direct mechanism for an invariant — those rows are marked.

---

## 1. MVP boundary

### In

**Fifteen decision kinds** — the fourteen artifact decisions of Architecture §3 plus `intake_strategy`, which that section sets apart because its output is evidence rather than a claim about the artifact. All fifteen are implemented; two of them (`select_frame`, `ingest_sources`) resolve through an applicability branch (below) rather than a full implementation.

**Four gates** — plan, demo, draft, layout; `promotion` is deferred with the shared asset. **Five commitment kinds**, because `delivery` is a commitment without a gate (Rev. 4 §5).

Four verification layers, two active. One template, one worker pool, CLI only, single user, project-local composition.

### Out — with the reason from Rev. 4 §12

| Excluded | Consequence for MVP |
|---|---|
| Shared composition asset, versioning, promotion | `derive_structure` runs per project; `concept_id` is project-local; no `promotion` gate |
| Situation-free adjudicator | follows the asset |
| Frontend | CLI drives every gate |
| Auth, accounts, billing | one hard-coded user id |
| Multi-tenancy | **no cross-project reads anywhere** — the one place to be strict, because retrofitting isolation is expensive |
| Broker, separate vector store | job table only |
| Workflow orchestration | linear runner + joint units |
| Template catalogue | exactly one template |
| Streaming progress | poll `GET /jobs/:id` |

### Conditional decisions are applicability branches, not stubs

Rev. 4 §3 marks `select_frame` and `ingest_sources` conditional on the subject. The invariant is that **a conditional capability is never silently skipped** — not that it always throws.

Throwing on the mere presence of sources conflates two different things: a subject can *have* authoritative sources that a *particular artifact* does not require. So every conditional decision resolves applicability first, and records the answer as a decision output like any other.

```python
class Applicability(BaseModel):
    outcome: Literal["applicable", "not_applicable", "unsupported"]
    reason: str

def ingest_sources(env: Envelope) -> SourceStructure | NotApplicable | Infeasible:
    a = applicability(env)
    if a.outcome == "not_applicable":
        return NotApplicable(reason=a.reason)      # normal, recorded, no finding
    if a.outcome == "unsupported":
        return Infeasible(capability="source_ingestion", reason=a.reason)  # MVP path
    ...
```

Three outcomes, three different downstream meanings:

| Outcome | Recorded as | Surfaces to user |
|---|---|---|
| `applicable` | a normal decision output | no |
| `not_applicable` | a decision output — **not an absent row** | no |
| `unsupported` | a decision output carrying an infeasibility | **yes, in the plan** |

`not_applicable` must be a *recorded output* rather than a missing row, because downstream decisions and the dependency closure need to distinguish *considered and skipped* from *never ran* — the same reason `decision.rejected` exists.

`unsupported` is the MVP path for a statute-backed subject, and it discharges Architecture §14's *report infeasibility* obligation. It is not an error path.

---

## 2. Components

```
backend/
  api/            FastAPI routes; no model SDK, no HTML
  store/          repositories + migrations; the only module touching SQL
  worker/         claim loop, runners, reaper
  services/       commit · invalidate · publish · set_status · supersede · correct
  ids/            canonical JSON, hashing, id generation
agent/
  contracts/      Pydantic models — the typed interfaces
  decisions/      one module per decision kind
  prompts/        versioned prompt templates
engine/
  merge · measure · solve · annotate · paginate · validate · render
cli/
```

### Boundary enforcement — mechanism for Rev. 4 §9

A CI check, run as a test, not a lint suggestion:

| Package | Must not import |
|---|---|
| `backend/` | `anthropic`, `engine.measure`, any HTML/geometry module |
| `agent/` | `backend.store`, `sqlalchemy`, `psycopg` |
| `engine/` | `anthropic`, `httpx`, `requests`, `socket` |

`test_boundaries.py` walks the AST of every module and asserts the import sets. The engine's purity is what makes golden-image testing possible; the agent's is what makes decision replay possible.

---

## 3. Schema

Postgres 16. JSONB for every payload Rev. 4 §4 leaves unschematised.

### Migration order — the references are circular

`member.current_artifact_version_id → artifact_version` and `artifact_version.member_id → member` form a cycle; `decision.job_id → job` is a forward reference. The DDL below is written in **logical** order and cannot be executed top to bottom. Migration order is:

```
1  types (all enums)
2  project · utterance
3  member                    WITHOUT current_artifact_version_id FK
4  job                       (references member)
5  decision · dependency     (reference member, job)
6  artifact_version          (references member)
7  commitment                (references artifact_version)
8  verification · set_status
9  ALTER member ADD CONSTRAINT fk_member_current_artifact
     FOREIGN KEY (current_artifact_version_id) REFERENCES artifact_version
10 indexes and triggers
```

Step 9 is the cycle-breaker. `migrations/0001_init.sql` follows exactly this order; `test_migrations.py::test_init_applies_to_empty_database` runs it against a scratch database in CI, which is what stops the ordering from rotting.

```sql
CREATE TYPE decision_kind AS ENUM (
  'intake_strategy','interpret_situation','select_frame','ingest_sources',
  'derive_structure','relevance','traversal','consequence','scope','partition',
  'section','representation','draft','render_config','layout_feasibility');

CREATE TYPE decision_status    AS ENUM ('candidate','committed');
CREATE TYPE decision_freshness AS ENUM ('current','stale');
CREATE TYPE commitment_kind    AS ENUM ('plan','demo','draft','layout','delivery');
CREATE TYPE job_state          AS ENUM ('queued','running','needs_input','blocked','done','failed','abandoned');
CREATE TYPE dependency_kind    AS ENUM ('declared','recorded');
CREATE TYPE supersession_kind  AS ENUM ('revision','retraction');

CREATE TABLE project (
  id uuid PRIMARY KEY, user_id uuid NOT NULL, title text NOT NULL,
  taxonomy_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE utterance (                      -- testimony: append-only
  id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES project,
  ord int NOT NULL, role text NOT NULL, text text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, ord));

CREATE TABLE decision (
  id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES project,
  kind decision_kind NOT NULL,
  status decision_status NOT NULL DEFAULT 'candidate',
  freshness decision_freshness NOT NULL DEFAULT 'current',
  member_id uuid NULL REFERENCES member, job_id uuid NULL REFERENCES job,
  inputs_hash text NOT NULL,
  model text, prompt_version text, effort text, params jsonb,
  output jsonb NOT NULL, rejected jsonb, cost jsonb,
  created_at timestamptz NOT NULL DEFAULT now());

-- INVARIANT 2: the memo key. Lookup here replaces a model call.
-- NB the explicit uuid cast: coalesce over a uuid column needs it.
CREATE UNIQUE INDEX decision_memo ON decision
  (project_id, kind,
   coalesce(member_id, '00000000-0000-0000-0000-000000000000'::uuid),
   inputs_hash);

-- INVARIANT 3 + correction routing: closure walks start here.
CREATE INDEX decision_stale ON decision (project_id, freshness)
  WHERE freshness = 'stale';

CREATE TABLE dependency (
  from_decision_id uuid NOT NULL REFERENCES decision,
  to_decision_id   uuid NOT NULL REFERENCES decision,
  kind dependency_kind NOT NULL,
  PRIMARY KEY (from_decision_id, to_decision_id, kind));
CREATE INDEX dependency_reverse ON dependency (from_decision_id);  -- closure direction

CREATE TABLE commitment (
  id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES project,
  kind commitment_kind NOT NULL, member_id uuid NULL REFERENCES member,
  snapshot jsonb NOT NULL,                    -- self-describing, stands alone
  decision_ids uuid[] NOT NULL,
  decision_ids_hash text NOT NULL,
  artifact_version_id uuid NULL REFERENCES artifact_version,   -- kind='delivery'
  decision_environment jsonb NOT NULL,
  approved_by uuid, approved_at timestamptz NOT NULL DEFAULT now(),
  superseded_by uuid NULL REFERENCES commitment);

-- INVARIANT 1: re-committing an identical decision set is identity.
CREATE UNIQUE INDEX commitment_identity ON commitment
  (project_id, kind,
   coalesce(member_id, '00000000-0000-0000-0000-000000000000'::uuid),
   decision_ids_hash)
  WHERE kind <> 'delivery';

-- Delivery is identified by WHAT WAS DELIVERED, not by a decision set:
-- downloading the same version twice is one delivery. (T9)
CREATE UNIQUE INDEX commitment_delivery_identity ON commitment (artifact_version_id)
  WHERE kind = 'delivery';

CREATE TABLE member (
  id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES project,
  ord int NOT NULL, title text NOT NULL, job text NOT NULL,
  requires uuid[] NOT NULL DEFAULT '{}',
  declared_exit jsonb NOT NULL, actual_exit jsonb NULL,
  entry_premise jsonb NOT NULL, entry_premise_hash text NOT NULL,
  current_inputs_hash text NULL,              -- INVARIANT 5: CAS target
  current_artifact_version_id uuid NULL REFERENCES artifact_version,
  state text NOT NULL DEFAULT 'planned',
  UNIQUE (project_id, ord));

-- A member has MANY artifact versions. `version_number` is monotonic per member.
-- (Renamed from `ord` in Rev. 2: `member.ord` is a position in the set and
--  `artifact_version.ord` was a version counter. Same name, different meaning.)
CREATE TABLE artifact_version (
  id uuid PRIMARY KEY, member_id uuid NOT NULL REFERENCES member,
  version_number int NOT NULL,
  bytes_ref text NOT NULL, bytes_hash text NOT NULL, format text NOT NULL,
  doc_model_hash text NOT NULL,
  render_environment jsonb NOT NULL,          -- INVARIANT 10
  decision_ids uuid[] NOT NULL,
  pagination jsonb NOT NULL,                  -- block_id -> page
  stamp text NOT NULL,                        -- INVARIANT 11
  superseded_by uuid NULL REFERENCES artifact_version,
  supersession_kind supersession_kind NULL,   -- INVARIANT 13
  removed_at timestamptz NULL, removal_reason text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (member_id, version_number));

CREATE TABLE job (
  id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES project,
  unit text NOT NULL, member_id uuid NULL REFERENCES member,
  state job_state NOT NULL DEFAULT 'queued',
  input_decision_ids uuid[] NOT NULL,          -- INVARIANT 4: freshness re-check
  attempts int NOT NULL DEFAULT 0, last_error text,
  claimed_at timestamptz, started_at timestamptz, finished_at timestamptz);
CREATE INDEX job_claimable ON job (project_id, state) WHERE state = 'queued';
CREATE INDEX job_stuck ON job (state, claimed_at) WHERE state = 'running';

CREATE TABLE verification (
  id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES project,
  layer text NOT NULL,
  target_kind text NOT NULL,                   -- 'decision' | 'member'  ← Rev. 2 fix
  target_id uuid NOT NULL,
  covered jsonb NOT NULL,
  entry_premise_hash text NULL,                -- INVARIANT 7
  freshness decision_freshness NOT NULL DEFAULT 'current',
  findings jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE set_status (                      -- INVARIANT 6
  project_id uuid PRIMARY KEY REFERENCES project,
  completeness text NOT NULL,                  -- complete | incomplete | blocked
  blocking_members uuid[] NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now());
```

**Immutability of `artifact_version`** — mechanism for invariant 9:

```sql
CREATE FUNCTION artifact_version_immutable() RETURNS trigger AS $$
BEGIN
  IF NEW.bytes_ref  IS DISTINCT FROM OLD.bytes_ref
  OR NEW.bytes_hash IS DISTINCT FROM OLD.bytes_hash
  OR NEW.pagination IS DISTINCT FROM OLD.pagination
  OR NEW.stamp      IS DISTINCT FROM OLD.stamp THEN
    RAISE EXCEPTION 'artifact_version content is immutable (invariant 9)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_artifact_version_immutable BEFORE UPDATE ON artifact_version
  FOR EACH ROW EXECUTE FUNCTION artifact_version_immutable();
```

Supersession, retraction and removal update *other* columns and remain legal. **Removal blanks `bytes_ref` and sets `removed_at` + `removal_reason`; it never deletes the row** — the identity and its history survive erasure.

---

## 4. Hashing — `backend/ids`

Every invariant that depends on content addressing depends on this module being right.

```python
def canonical(obj) -> bytes:
    # sorted keys, no whitespace, NFC-normalised strings, floats rejected
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()

```

### The envelope rule — mechanism for invariant 2

> **`inputs_hash` is computed over the complete effective input envelope: everything the decision function can observe.** Not merely its declared arguments.

If anything a decision reads sits outside the hash, the memo returns a result computed under conditions that no longer hold — which does not merely waste money, it serves a stale judgment as a current one. Invariant 2 is unenforceable without this.

**Stating the rule is not enough; it is enforced structurally.** Every decision function takes exactly one parameter — a frozen envelope — and can reach nothing else:

```python
@dataclass(frozen=True)
class Envelope:
    kind: str
    member_id: UUID | None
    inputs: tuple[tuple[str, str], ...]      # (decision_id, output_hash), sorted
    model: str
    prompt_version: str
    effort: str
    params: Mapping[str, Any]
    taxonomy_version: str
    asset_version: str | None
    source_versions: tuple[tuple[str, str], ...]
    system_instructions_hash: str
    tool_outputs: tuple[tuple[str, str], ...]   # (tool, result_hash), sorted

    def hash(self) -> str:
        return sha256(canonical(asdict(self))).hexdigest()
```

**What the mechanism delivers, and what it does not.** The one-parameter signature proves that **no declared input bypasses the envelope**. It does not prove purity: a function can still read a global, call `datetime.now()`, or read an environment variable. Three layers, none sufficient alone:

| Layer | Catches | Misses |
|---|---|---|
| one-parameter signature (AST walk) | a second argument — a declared bypass | ambient reads |
| import denylist on `agent/decisions/` — `os`, `time`, `datetime`, `random`, `secrets`, `httpx`, `requests`, `socket` | the ambient-read paths we can name | a transitive import, a mutable default |
| determinism probe | anything the first two miss — empirically | paths the test does not exercise |

The probe is the one that bites: with the model client stubbed to a fixed response, running a decision twice against an identical envelope must produce a byte-identical `output_hash`. A timestamp, a random seed or an env read breaks it.

> **The claim at its true strength: structural discipline plus empirical detection. Not a proof of isolation.**

Tool and retrieval results are hashed into the envelope *before* the model call, so a decision that consumed a retrieval is memoised against that retrieval and not against a later one.

**Floats are rejected, not rounded.** A float that serialises differently across platforms silently breaks memoisation, which silently doubles the most expensive spend in the system.

`decision_ids_hash = sha256(canonical(sorted(str(i) for i in ids)))` — order-independent, because approving the same set in a different order is the same approval.

---

## 5. Transaction boundaries

The eight that matter. Everything else is a single statement.

### T1 · Claim — invariant 4

```sql
BEGIN;
  SELECT * FROM job
   WHERE project_id = $1 AND state = 'queued'
   ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1;

  -- freshness re-check AT CLAIM, not at enqueue
  SELECT count(*) FROM decision
   WHERE id = ANY($job.input_decision_ids) AND freshness = 'stale';

  -- > 0  → UPDATE job SET state='abandoned'
  -- = 0  → UPDATE job SET state='running', claimed_at=now(), attempts=attempts+1
COMMIT;
```

Without the re-check, one scope change during a thirty-member build burns the entire queue. This is the largest single cost saving in the system and it is four lines.

### T2 · Decision write, and T3 · Job completion — invariant 2

**Two transactions, in this order, deliberately.**

```
T2   BEGIN; INSERT decision (with output, cost) ON CONFLICT (memo) DO NOTHING;
            INSERT dependency rows;
     COMMIT;

     ← a crash here is safe: the job is requeued, recomputes the same
       inputs_hash, hits the memo, and makes ZERO model calls

T3   BEGIN; UPDATE job SET state='done', finished_at=now(); COMMIT;
```

Collapsing these into one transaction is the natural instinct and it is **wrong**: a crash rolls back the decision too, and the most expensive work in the system is paid for twice.

### T4 · Joint unit write — Rev. 4 §1

```
BEGIN;
  INSERT decision (section);
  INSERT decision (representation);
  INSERT dependency (recorded) rows from the constraint report;
COMMIT;
```

One transaction, non-negotiable. A partial write leaves a joint unit with one sibling missing and no recorded constraints — a state the invalidation model cannot interpret.

### T5 · Commit and fan-out — invariant 1

```python
with tx():
    row = insert_commitment_on_conflict_do_nothing(...)  # RETURNING id
    if row is None:
        return existing_commitment(...)        # duplicate: DO NOT enqueue
    enqueue_member_jobs(...)
```

Insert and enqueue share one transaction so a commitment can never exist without its jobs; `DO NOTHING` plus the returning-guard is what makes a retried approval identity rather than a second fan-out.

### T6 · Publish — invariant 5

```sql
BEGIN;
  UPDATE member
     SET current_artifact_version_id = $new, current_inputs_hash = $fresh
   WHERE id = $member AND current_inputs_hash IS NOT DISTINCT FROM $expected;
  -- 0 rows: a fresher derivation already published. Discard this result.
COMMIT;
```

Compare-and-set. The stale job's output stays in the content-addressed store and is simply never pointed at.

### T7 · Invalidation — invariant 3

```sql
BEGIN;
  WITH RECURSIVE closure(id) AS (
      SELECT $target
      UNION
      SELECT d.to_decision_id FROM dependency d JOIN closure c ON d.from_decision_id = c.id)
  UPDATE decision SET freshness = 'stale' WHERE id IN (SELECT id FROM closure);

  -- Rev. 2 fix: verification targets are decisions OR members. The closure
  -- only reaches decisions, so member-level verification (the simulated
  -- reader over a whole member) was never being invalidated.
  UPDATE verification SET freshness = 'stale'
   WHERE (target_kind = 'decision' AND target_id IN (SELECT id FROM closure))
      OR (target_kind = 'member'   AND target_id IN (
            SELECT DISTINCT member_id FROM decision
             WHERE id IN (SELECT id FROM closure) AND member_id IS NOT NULL));
COMMIT;
```

Set-based, therefore idempotent. **It marks; it does not enqueue.** Nothing here schedules a model call.

`UNION`, not `UNION ALL`, in the recursive CTE: joint units produce mutually-recorded edges between siblings, so the graph has cycles and only deduplication terminates the walk. Do not "optimise" this.

#### Member-level verification has two independent triggers

They live in different transactions and **neither subsumes the other**. Missing either leaves a member looking verified when it is not.

| Trigger | Meaning | Where |
|---|---|---|
| **a** · a decision belonging to that member is stale | its content changed | **T7**, the `target_kind='member'` branch above |
| **b** · the member's `entry_premise_hash` changed | the reader arriving at it changed | **T8**, Case A or B |

Trigger (a) also covers project-scoped decisions — `scope` and `partition` carry `member_id IS NULL`, but the closure walks onward through them to the member-scoped `section`, `representation` and `draft` decisions, so a scope change reaches member verification by that path rather than needing its own rule.

Trigger (b) is invisible to T7 by construction: a predecessor's exit moving changes nothing about *this* member's own decisions, so no decision of theirs appears in the closure. This is precisely Rev. 4 invariant 7 — a successor's verification is invalidated **while its content is unchanged**.

### T8 · Member commit and exit check — invariant 7

```
BEGIN;
  UPDATE member SET actual_exit = $actual, state = 'committed';
  IF actual_exit DIVERGES FROM declared_exit:
      -- Rev. 2 fix: the successors' ENTRY PREMISE is derived from this exit,
      -- so it must be recomputed before anything keyed to it is invalidated.
      recompute entry_premise + entry_premise_hash for every member
        whose `requires` contains this one;
      mark those members' decisions   stale   (via the T7 closure);
      mark those members' verification stale  (keyed on entry_premise_hash);
      record a divergence finding for the plan surface;
  recompute set_status;                       -- invariant 6
COMMIT;
```

Recomputing the premise and invalidating what depends on it must be one transaction: a premise updated without the invalidation leaves successors *looking* current against a premise they were never verified under.

#### Successor-premise propagation, precisely

Premises derive from predecessors' **exits**, so propagation depends on *which* exit moved. The two cases behave differently and only one is transitive inside the transaction.

```
CASE A — actual_exit diverged from declared_exit
         DIRECT successors only (members whose `requires` contains this one).
         Not transitive now: the successor's own actual_exit has not changed,
         and its successors are still verified against its DECLARED exit,
         which is intact.
         Transitivity arrives later and naturally — the stale successor
         re-derives, records a new actual_exit, and T8 fires again for its
         own successors if that diverges in turn.

CASE B — declared_exit changed (the partition repair route, Rev. 4 inv. 7)
         TRANSITIVE CLOSURE over `requires`, immediately, in this transaction.
         Declared exits are the contract every downstream member was planned
         against, so lowering one invalidates the whole downstream chain at
         once, not one hop per re-derivation.
```

Case B walks in **topological order** over `requires` so each member's premise is recomputed after every predecessor it depends on. Termination is guaranteed because `requires` is a DAG — a cycle would mean two members each assuming the other's exit, which partition legality already forbids. `test_partition.py::test_requires_graph_is_acyclic` asserts it at partition time rather than trusting it at propagation time.

### T9 · Delivery — invariant 12, Rev. 4 §5

Delivery is a commitment **without a gate**: nothing is checked when a file leaves, but reliance begins there. It is a separate moment from render — often days later — and therefore a separate boundary.

```python
with tx():
    av = artifact_version_for_download(member_id)      # current, not removed
    row = insert_commitment_on_conflict_do_nothing(
        kind="delivery", artifact_version_id=av.id,
        snapshot=self_describing(av), decision_ids=av.decision_ids,
        decision_environment=env_of(av))
    # duplicate download → no second commitment (commitment_delivery_identity)
    return av.bytes_ref
```

Distinct from T5 in three ways: no jobs are enqueued, no approval is recorded, and identity keys on **`artifact_version_id`** rather than a decision set — because downloading the same version twice is one delivery, whatever produced it.

---

## 6. Invariant → mechanism → test

Every row is executable. Test ids are file paths.

| # | Invariant | Mechanism | Test |
|---|---|---|---|
| 1 | commitment names exact decisions; re-commit is identity | `commitment_identity` unique index + T5 guard | `test_idempotency.py::test_double_approve_one_commitment_one_fanout` |
| 2 | result durable before job done; hash total | T2 before T3; `decision_memo` index | `test_crash.py::test_crash_between_t2_and_t3_makes_zero_model_calls` |
| 3 | invalidation idempotent | T7 set update | `test_invalidation.py::test_duplicate_correction_converges` |
| 4 | freshness re-checked at claim | T1 | `test_cancellation.py::test_queued_jobs_abandoned_without_model_calls` |
| 5 | publish only if current | T6 CAS | `test_cancellation.py::test_stale_publish_loses_regardless_of_order` |
| 6 | set completeness first-class | `set_status` + T8 | `test_partial_failure.py::test_passing_members_downloadable_set_incomplete` |
| 7 | exit failure invalidates successors | T8 divergence branch | `test_exit_divergence.py::test_successor_verification_stales_with_unchanged_content` |
| 8 | commitment pins decision environment | `decision_environment` captured in T5 | `test_environment.py::test_prompt_bump_yields_reconciliation_not_silent_rederive` |
| 9 | no silent replacement | immutability trigger | `test_artifact.py::test_bytes_update_rejected`, `::test_removal_keeps_row_and_reason` |
| 10 | two environments | separate columns | `test_artifact.py::test_font_bump_alone_creates_new_version` |
| 11 | artifact self-identifying | stamp injected at `merge` | `test_artifact.py::test_stamp_extractable_from_rendered_pdf` |
| 12 | version-in-hand authoritative | `GET /artifact-versions/:id` + T9 | `test_versions.py::test_old_version_answers_itself_and_names_successor`, `test_delivery.py::test_repeat_download_is_one_delivery_commitment` |
| 13 | supersession ≠ retraction | `supersede_service` severity trigger | `test_versions.py::test_critical_fix_marks_retraction_not_revision` |
| — | envelope is complete | one-parameter decision signature | `test_envelope.py::test_every_decision_takes_only_an_envelope`, `::test_asset_version_bump_changes_hash` |
| — | conditional decisions never silently skipped | applicability branch (§1) | `test_conditional.py::test_not_applicable_is_a_recorded_output`, `::test_unsupported_surfaces_in_plan` |
| — | migration order holds | deferred FK in step 9 (§3) | `test_migrations.py::test_init_applies_to_empty_database` |
| — | member-level verification invalidates | T7 `target_kind` branch | `test_invalidation.py::test_member_verification_stales_on_decision_change` |
| — | entry premise recomputed before invalidation | T8 | `test_exit_divergence.py::test_successor_premise_recomputed_in_same_tx` |

### The two tests that need fault injection

Sleeps make these flaky and prove nothing. Both runners accept a test-only hook.

```python
# invariant 2
def test_crash_between_t2_and_t3_makes_zero_model_calls(spy_model):
    run_job(job, fault_after="decision_write")     # raises after T2 commits
    assert job.state == "running"
    reaper.sweep()                                  # requeues
    run_job(job)
    assert spy_model.call_count == 0                # memo hit
    assert decision_count(job) == 1

# invariant 5
def test_stale_publish_loses_regardless_of_order(barrier):
    stale = start_job(member, inputs_hash="old")
    fresh = start_job(member, inputs_hash="new")
    barrier.release(fresh); barrier.release(stale)  # stale finishes LAST
    assert member.current_artifact_version_id == fresh.artifact_version_id
```

---

## 7. Agent

```python
# agent/contracts — the typed interface. No store import anywhere in this package.
class Situation(BaseModel): ...
class Relevance(BaseModel): ...
class ScopeAndPartition(BaseModel):
    scope: Scope
    partition: Partition
    constraints: list[Constraint]      # → dependency(kind='recorded'), T4
```

| Decision | Call | Effort |
|---|---|---|
| `interpret_situation`, `relevance`, `scope_and_partition` | `messages.parse` | `high` |
| `section_and_representation` | `messages.parse` | `xhigh` |
| `draft` | `messages.stream` → `get_final_message()` | `high` |
| `traversal`, `consequence`, `render_config` | `messages.parse` | `medium` |

`model="claude-opus-5"`, `thinking={"type": "adaptive"}` throughout. Streaming for `draft` because `max_tokens` is large enough to risk request timeouts.

**Prompts are versioned files**, hashed into `prompt_version`. A prompt edit without a version bump silently poisons the memo — `test_prompts.py::test_every_prompt_file_hash_matches_recorded_version` runs in CI.

**Joint functions return their constraint report.** Without it there is nothing to write as a recorded dependency and Rev. 4 §2's fourth structure has no source.

---

## 8. Engine

```
merge → measure → solve → annotate → paginate → validate → print
```

One Chromium page per document; `validate` and `print` share the measurement pass. **The stamp is injected at `merge`** — it is content, not a print-time overlay, so it survives into the extracted text and can be asserted on.

```python
engine.validate(doc_model, template_id) -> list[Violation]
engine.render(doc_model, template_id)   -> RenderResult(bytes, pagination, render_environment)
```

`render_environment` is **captured by the engine, not passed to it**: template version, engine version, resolved browser build, resolved font faces and versions. Anything the engine reads and the caller cannot see must be reported by the engine or invariant 10 is unenforceable.

**Golden-image tests** compare rendered PNGs against references, pinned to the CI browser and font versions. They are the reason `engine/` may not touch the network.

Browser lifecycle: one long-lived Chromium per worker process, one page per render, hard timeout 30s, process recycled every 200 renders.

---

## 9. API — MVP subset

```
POST /projects                      {text}                  → project + first utterance
POST /projects/:id/utterances       {text}
POST /projects/:id/plan                                     → jobs
GET  /projects/:id/plan                                     → plan · findings · extent · infeasibilities
POST /projects/:id/plan/approve     {decision_ids}          [gate, idempotent]
GET  /projects/:id/set-status

POST /members/:id/demo
POST /members/:id/demo/approve      {decision_ids}          [gate, idempotent]
GET  /members/:id/versions                                  → all, newest first
GET  /artifact-versions/:id                                 → bytes + supersession note
POST /members/:id/override          {finding_id, reason}

POST /projects/:id/corrections      {text}                  → re-derivation plan + estimate
POST /corrections/:id/confirm                               → jobs
GET  /jobs/:id
GET  /decisions/:id                                         → record + dependencies
```

`decision_ids` is **required** on both approve endpoints — that is what makes invariant 1 work. An approval that does not name what it approves cannot be idempotent and cannot be reconciled later.

`GET /decisions/:id` answers *"why isn't X in here?"* — it is a product endpoint, not a debug one.

---

## 10. Build order

Dependency-driven. Each step ends with its invariant tests green.

1. **`ids/` + schema + repositories.** Hashing first — every later invariant rests on it. *Tests: canonicalisation, float rejection, order-independent `decision_ids_hash`.*
2. **Job table, T1 claim, reaper.** *Invariant 4.*
3. **Derivation runner with T2/T3 split and the memo.** *Invariant 2 — the fault-injection test.*
4. **Agent contracts + `interpret_situation` + `derive_structure` + `relevance`.** First real model calls; nothing gated yet.
5. **Traversal, consequence, and the `scope_and_partition` joint unit with T4.** First recorded dependencies.
6. **Structural verification.** *Moved earlier in Rev. 2.* It is deterministic code with no model call, and several lifecycle transitions already depend on it — T8's exit check most of all. Treating it as a late feature means building the exit check against nothing.
7. **T7 invalidation + corrections endpoint.** *Invariant 3.* The system can now be corrected before it can render.
8. **T5 commit + plan gate.** *Invariants 1, 8.*
9. **`section_and_representation`, draft, members, T8.** *Invariants 6, 7.*
10. **Engine, layout gate, T6 publish.** *Invariant 5.*
11. **Artifact versions, stamp, supersession, T9 delivery.** *Invariants 9–13.*
12. **Correctness verification**, severity-budgeted. Model-judgment sampled; source-grounded and human deferred with ingestion.

Steps 1–3 are the spine. If the fault-injection test in step 3 does not pass, nothing later is trustworthy.

---

## 11. Definition of done

- All thirteen invariant tests green, including both fault-injection tests.
- `test_boundaries.py` green — three import boundaries hold.
- One project end to end: request → plan → approve → demo → approve → build → PDF with an extractable stamp.
- One correction end to end matching Rev. 2's appendix trace: *"you missed distributed caching"* reaches `relevance`, leaves `derive_structure` untouched, marks committed members `superseded` not `dirty`, and returns a costed re-derivation plan.
- A statute-backed subject reaches the plan surface and **reports that it cannot ingest sources** rather than proceeding.
- Golden images stable across three consecutive CI runs.

## 12. Deferred to the first release after MVP

Multi-worker soak at burst; browser pool sizing; retraction delivery channel (Rev. 4 §13 — the only obligation that may need to reach a user outside the product); version diff rendering; `dependency` closure index tuning under a real graph.
