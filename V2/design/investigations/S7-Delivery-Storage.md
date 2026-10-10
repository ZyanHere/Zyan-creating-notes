# §7 — Delivery and Storage

A deep read of one section. **No design, no decision.**

Evidence key: `[OBSERVED]` in code/spec · `[MEASURED]` in the 11 records ·
`[INFERENCE]` reasoning · `[UNKNOWN]` needs measurement.

**The section where the benchmark is blindest.** Ten records exercised planning and one
exercised generation; **none exercised concurrency, a crash, a rename, or a
regeneration** — which is where this section's defects live.

---

## 1. What this section actually is

**Three responsibilities V1 keeps in one place:**

- **Project state** — the transcript, the decisions, the commitments.
- **Artifacts** — the bytes that were delivered.
- **Delivery** — serving one PDF, and serving a whole curriculum.

**Starts** at the first `create_project`. **Ends** when the user has the file.

---

## 2. What exists today

### Project state

`[OBSERVED]` `backend/store.py` — `FileStore`, *"One JSON file per project, holding all
four tables."* Root `out/projects`, one file per project id, four keys:
`{project, utterance[], decision[], commitment[]}`.

Four record types, and the design is sound on paper:

| Record | Shape | Note |
|---|---|---|
| `Project` | `id, user_id, title, taxonomy_version, created_at` | **ownership is modelled** |
| `Utterance` | `id, project_id, ord, role, text` | *"Testimony: append-only, ordered."* |
| `Decision` | `id, kind, status, freshness, inputs_hash, output, model, prompt_version, cost` | `status: candidate\|committed` × `freshness: current\|stale` |
| `Commitment` | `snapshot, decision_ids, decision_ids_hash, decision_environment, approved_by` | idempotent by hash |

`USER = "local"  # single user until accounts exist; one column to change`
`[OBSERVED]` — so multi-tenancy is anticipated in the schema and deferred in the value.

`taxonomy_version = "plan-gate-1"` is carried **on the project**.

### Artifacts

`[OBSERVED]` `out/artifacts/{project_id}/`, four files per module:

```
{slugify(title)}.pdf
{slugify(title)}.html
{slugify(title)}.json           # the Document — deliberately kept
{slugify(title)}.report.json
```

The Document JSON is retained with a stated reason: *"A template fix should not cost
another generation — and at M5 this is the row that moves into the decision table."*

### Delivery

`[OBSERVED]`

- `GET …/modules/{i}/artifact.pdf` — **inline by default**, `?download=1` to save.
  *"`filename=` alone sets `content-disposition: attachment`, which makes the browser save
  the file instead of showing it."*
- `GET …/export.zip` — the whole curriculum. Separate files, not a merged PDF, with the
  reason: *"each module is its own document with its own cover and page numbering, and
  merging them is a render-engine job (continuous pagination, a combined contents page),
  not a packaging one."* The `NN-` ordering prefix exists **only inside the archive**,
  because on-disk names carry no order and *"unzipping into a folder would otherwise
  present the curriculum alphabetically — which is exactly the order the plan decided
  against."*
- `GET /artifacts/{name}` — a flat legacy endpoint.

---

## 3. Problems

### Observed — and the first one is the most serious in the section

**Artifact identity is derived from mutable content.** `[OBSERVED]`

```python
_module_pdf(project_id, title) -> _project_out(project_id) / f"{slugify(title)}.pdf"
```

A module's PDF is addressed by the slug of its **title**. Three consequences, none
exercised by the benchmark:

1. **A correction that renames a module orphans its artifact.** The old PDF stays on
   disk under the old slug; `module_artifact` looks up the new slug and returns
   *"this module has not been written yet"* — while the file sits beside it. Corrections
   demonstrably re-partition (`ml-weekend`: 5 modules → 3 `[MEASURED]`), so title changes
   are a normal event, not an edge case.
2. **Regeneration overwrites in place.** No version, no history. System Design Rev. 4
   made `artifact_version` **first-class** and retention an invariant after a dedicated
   stress test; neither exists.
3. **Two titles that slugify alike collide silently.** `slugify` lowercases,
   collapses non-alphanumerics and truncates at 60 characters — so two long titles
   sharing a 60-char prefix are one file. **0 collisions measured** `[MEASURED]`, which
   is absence of evidence given that 8 plans produced at most 9 modules each.

**`_write` is truncate-then-overwrite, with no lock and no atomic rename.**
`[OBSERVED]`

```python
def _write(self, project_id, data):
    self._path(project_id).write_text(json.dumps(data, indent=2, …), encoding="utf-8")
```

Two distinct hazards `[INFERENCE]`:

- **Lost update.** Every mutation is read-modify-write of the whole file. `jobs.py`
  spawns a thread per generation, and the frontend polls while a turn runs — two writers
  to one project drop one writer's changes entirely.
- **Corruption on interruption.** `write_text` truncates before writing. A crash or kill
  mid-write leaves invalid JSON, and `_read` raises on parse — **the project becomes
  unopenable**, with no backup and no journal. A plan that took 342 seconds is in that
  file.

Neither has been observed. Neither could be, from eleven single-threaded harness runs.

**Invariant 8 is partially implemented.** `[OBSERVED]` System-Design requires a
commitment to pin *"model, prompt version, taxonomy version, asset version, source
versions."* `decision_environment` carries `prompt_versions` and `models`.
`taxonomy_version` lives on the project, not the commitment. Asset and source versions do
not exist because §0 does not.

**`freshness` is never set to `stale`.** `[OBSERVED]` One write, `"current"`. The
invalidation axis is in the data model and inert — so *"invalidate ≠ regenerate"*, which
survived a dedicated stress test, has no implementation.

**`inputs_hash` is computed and written, never read.** `[OBSERVED]` It is the memoisation
key Build-Spec invariant 2 is about. Nothing looks it up.

**No supersession between commitments.** `[OBSERVED]` Correcting after approval mints a
new commitment with a new hash. Nothing relates the two, so the history of a
corrected-then-re-approved plan is a list with no stated order of authority.

**Postgres is declared and unused.** `[OBSERVED]` `psycopg[binary]` in
`pyproject.toml`; `migrations/0001_init.sql` **written and unapplied**; `FileStore` is
what runs.

**`out/` is working-directory-relative.** `[OBSERVED]` `service.py:24 OUT = Path("out")`,
`store.py:117 Path("out/projects")`. Running from elsewhere silently creates a second,
empty store — which is why `backend/app.py` chdirs to the repo root before importing
anything.

**Ephemeral-disk hostility.** `[INFERENCE]` Everything — project state, artifacts, the
retained Document JSON — is on local disk. On a free PaaS instance with no persistent
volume, all of it vanishes on restart, and free instances restart on idle.

### Passes worth recording

**`/artifacts/{name}` guards path traversal correctly.** `[OBSERVED]`

```python
path = (service.OUT / name).resolve()
if not path.is_file() or service.OUT.resolve() not in path.parents: 404
```

Resolve-then-verify-ancestry is the right shape. `../../etc/passwd` resolves outside
`OUT` and is refused.

**Inline-vs-attachment is handled deliberately**, with the reason in the docstring.

**The export decision is well-argued** — separate files, ordering prefix inside the
archive only, and merging explicitly named as a render-engine job rather than a packaging
one.

**Ownership is in the schema.** `user_id` and `approved_by` exist; only the value is
constant. *"One column to change"* is optimistic but the shape is right.

### Strong inference

- **The durable unit is ambiguous.** State is per-project (one JSON blob); artifacts are
  per-module-title; decisions are per-kind-per-project. Nothing is addressable by the
  thing that produced it, which is why `inputs_hash` has nowhere to be looked up and
  `freshness` has nothing to invalidate *against*.
- **File = module is a partition decision leaking into storage.** The references insist
  curriculum / artifact / file are three boundaries. `Module`'s docstring says *"Becomes
  its own PDF"* — so §2 decides the filesystem layout.
- **This section's defects are all shaped by single-user, single-process, happy-path
  assumptions** that are correct for a laptop and wrong for anything else. That is not a
  criticism of the choice; it is a statement of what changes when the context changes.

### Unknown

- Does a concurrent write actually lose data here? `[UNKNOWN]` — never tested, and
  trivially testable with two threads and no model calls.
- How large does a project JSON get? `[UNKNOWN]` A plan carries 42 concepts, 8 modules,
  6 decision outputs plus a commitment snapshot; the whole file is read and rewritten on
  every mutation.
- What is the retention obligation? `[UNKNOWN]` — *"kept forever"* was explicitly
  demoted from invariant to policy during the design review.

---

## 4. The key architectural question

**What is the durable unit, and what is it addressed by?**

V1 has three answers and they do not agree:

| Thing | Addressed by | Stable under |
|---|---|---|
| project state | project id | everything |
| a decision | `(project, kind)` — current one wins | nothing; superseded silently |
| an artifact | **`slugify(module title)`** | **nothing** — a rename orphans it |

`[INFERENCE]` The third is the problem, and the fix direction is visible in V1's own
design documents: System Design Rev. 4 identifies an artifact version by
`doc_model_hash + render_environment_hash + bytes hash`. **Content-addressing an artifact
by what produced it rather than by what it is called** makes renames harmless,
regenerations non-destructive, and collisions impossible — and it is the same insight that
made `commit_hash` work for idempotent approval.

**The second question:** three mechanisms here are built and unwired — `inputs_hash`,
`freshness`, and (from §2) `feasibility`. `[INFERENCE]` They are unwired for the same
reason: **each needs a per-decision addressable store to act on**, and a single JSON blob
per project cannot provide one. So "wire up invalidation" is not a small change bolted
onto FileStore; it is a storage-shape question.

---

## 5. Where this section starts and ends

**Current** `[OBSERVED]`: `FileStore` is injected into `PlanService`; artifacts are
written by `service.generate(out_dir=…)`; delivery is three endpoints. The store is
already behind a `Store` Protocol with nine methods — **so the seam for replacing it
exists and is honoured.**

**Boundaries worth questioning** `[INFERENCE]`:

- **Project state and artifacts are different storage problems.** One is small, mutable,
  transactional. The other is large, immutable, and wants object storage. V1 puts both
  under `out/`.
- **The retained Document JSON is a third thing** — neither state nor deliverable, but
  the input to a re-render. Its stated future is *"the row that moves into the decision
  table."*
- **Delivery may not belong with storage at all.** Serving bytes over HTTP is not the same
  concern as deciding what persists.

---

## 6. Edge states

| State | V1 behaviour | Problem |
|---|---|---|
| Two writers, one project | last write wins, silently | **lost update** `[INFERENCE]` |
| Crash mid-write | truncated JSON; `_read` raises | **project unopenable** `[INFERENCE]` |
| Module renamed by a correction | old PDF orphaned; endpoint says "not written yet" | artifact identity |
| Module regenerated | overwritten in place | no history |
| Two titles sharing a 60-char slug prefix | one file | 0 measured |
| Requesting an ungenerated module | 404 *"this module has not been written yet"* | correct and clear |
| Export before approval | 409 | correct |
| `../` in `/artifacts/{name}` | 404 | **correctly guarded** |
| Running from the wrong directory | a second empty store | mitigated in `app.py` |
| Disk wiped | everything gone | no backup, no remote copy |

---

## 7. What makes this section valuable

`[OBSERVED]` Four decisions worth keeping:

1. **A `Store` Protocol with nine methods.** The replacement seam is real.
2. **Utterances are append-only and ordered.** The transcript is the one thing that can
   never be wrong.
3. **The Document JSON is retained**, so a template fix costs a render, not a generation.
4. **Export is packaging, not rendering** — and the code says which is which.

And the `NN-` prefix detail is the kind of thing that only comes from using the product:
the ordering the plan decided is preserved in the one place a user actually sees it.

---

## 8. Constraints and cross-section effects

**On §2/§3** — `inputs_hash` and `freshness` cannot be used until decisions are
individually addressable. Memoisation and invalidation are storage-shape questions before
they are planning features.

**On §4** — the retained Document JSON is what makes a re-render possible without a
regeneration. Keep it whatever else changes.

**On §6** — `render_environment` belongs to artifact identity. If the renderer changes,
every previously delivered artifact's identity needs to still mean what it meant.

**On §8** — ephemeral disk makes all of this vanish; a persistent volume or object store
is a deployment decision that this section's shape forces.

**On multi-tenancy** — `user_id` exists, `USER = "local"`. System-Design's own note:
*"a shared composition asset built from private sources is a real disclosure risk."*
Artifacts are currently served by project id with **no authorization check at all** —
which is correct for a single local user and is the first thing that breaks with a second
one.

---

## 9. Solution directions — compared, not chosen

**A. Atomic writes.** Write to a temp file, `os.replace`. *Delivers:* removes the
corruption hazard outright. *Cost:* three lines. **The cheapest risk reduction in the
repository.**

**B. A write lock per project.** *Delivers:* the lost-update hazard. *Cost:* small
in-process; meaningless across processes — which is an argument for (C).

**C. Postgres, using the written migration.** *Delivers:* atomicity, concurrency,
per-decision addressability — and therefore unblocks `inputs_hash`, `freshness` and
supersession. *Cost:* the largest here, and `migrations/0001_init.sql` was written against
the full M5 schema, not a minimal one.

**D. A JSON-blob table as a middle step.** `projects(id, doc jsonb)` behind the existing
`Store` Protocol. *Delivers:* durability and atomicity without the full schema.
*Does not deliver:* per-decision addressability, so the three unwired mechanisms stay
unwired.

**E. Content-address artifacts.** Name by `doc_model_hash` (+ render env), keep a
pointer from module to current version. *Delivers:* renames harmless, regenerations
non-destructive, collisions impossible, history for free. *Cost:* small, and it changes
URLs. *Precedent:* `commit_hash` already does this for approvals.

**F. Object storage for artifacts.** *Delivers:* survives ephemeral disk; separates the
two storage problems. *Cost:* a dependency and a credential.

**G. Version artifacts explicitly.** `artifact_version` as System Design specifies.
*Delivers:* the reconstruction guarantee that document's stress test established.
*Question:* needed before regeneration is a real user action?

**H. Leave it.** *Argument:* it is correct for one user on one laptop and the seam for
replacing it exists. *Argument against:* A is three lines and removes a
project-destroying failure mode.

**The shape:** **A first, unconditionally** — it is three lines against a hazard that
loses 342 seconds of work. E is small and fixes the section's worst design flaw. C
unblocks three mechanisms elsewhere and is the real answer; D is the honest middle step.
F and G follow from deployment and from whether regeneration becomes a user action.

---

## What remains genuinely open

1. **What is the durable unit?** Project, decision, or artifact version — three answers
   currently coexist.
2. **Does a concurrent write actually lose data?** Testable with two threads and no
   model calls.
3. **Postgres now, a blob table first, or neither?** Depends on whether memoisation and
   invalidation are V2 requirements.
4. **Is file = module right**, or is that §2's decision leaking into the filesystem?
5. **What is the retention obligation?** Demoted from invariant to policy and never
   settled.
6. **When does authorization arrive?** `user_id` exists; nothing checks it.
