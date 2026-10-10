# MyNotes V2 — Implementation Plan

Derived from the frozen design. **This document does not modify it.**

---

# 1. Design Freeze Declaration

> **DESIGN FROZEN:** The current Technical System Design is the implementation contract. No further
> architectural revisions are permitted unless implementation discovers a true contradiction that
> makes the system impossible to build as specified.

**The frozen set, exactly:**

| Document | Version | Status |
|---|---|---|
| `Domain-Model.md` | Rev. 4.1 | frozen |
| `Architecture.md` | Rev. 5 | frozen — component set |
| `Technical-Design.md` | **Rev. 11** — the current file | **frozen as the implementation contract** |

*(The task names "Rev. 10 / the current version in the file". Those differ by one correction pass —
the file is at Rev. 11. The instruction "freeze this exact version" governs: **the file as it stands
is the contract.** No revision was made for this task.)*

**What is explicitly not a reason to reopen the design:**

- a concrete workflow needing to be wired to `step()` · `step_shared()` · `FIND_RESULT` ·
  `RECONCILE` · `RESERVE` · `ATTACH` · `ATTACH_PROVENANCE` · `PUBLISH` · `MODEL_CALL`
- any choice of class arrangement, module naming, library, or driver
- implementation-level ambiguity that a default choice resolves (→ §7)

The design's stated intent is that those nine primitives **become the implementation's canonical
mechanisms rather than being duplicated per workflow** (TD §7.3). Wiring a workflow to one of them is
*executing* the design, not amending it.

**The one escape hatch, and its bar:** a true contradiction that makes the system unbuildable as
specified. Not "unclear", not "awkward", not "I would have done it differently". If one is found, it
is recorded as a single named finding against a named TD section, with the trace that proves it —
the same evidentiary standard the design itself was held to.

---

# 2. Implementation Architecture / Repository Structure

## 2.1 Derivation, not invention

The structure follows TD §2's five component **kinds** — `dom` (pure, no I/O), `orch`, `infra`,
`store`, `decl` — and the three import rules the design makes load-bearing:

```
dom never writes · orch owns every transaction · only the Gateway reaches a provider
the renderer never imports the domain's types (duck-typed mappings)
```

V1 proves this works by enforcement rather than convention (`tests/test_boundaries.py`, a FORBIDDEN
table over AST imports), and its own comment is the instruction for timing: *"Written at M1, when
there are three packages to keep apart, rather than at M8 when the damage is already done."*

## 2.2 Layout

```
mynotes/
├── core/                       dom — PURE. No I/O. No port parameters. Importable by anything.
│   ├── identity/
│   │   ├── canonical.py        canonical JSON (TD §5.1): UTF-8, sorted keys, NFC, ints only
│   │   ├── envelope.py         envelope(kind, member, inputs, env)          TD §5.1
│   │   ├── task_key.py         task_key(kind, inputs)                        TD §5.12
│   │   ├── claim_key.py        claim_key(domain, identity)                   TD §5.12a
│   │   ├── member.py           member encoding + the '' root sentinel        TD §5.11a
│   │   ├── content.py          sha256 content hashes, ContentRef paths       TD §4.3
│   │   └── fingerprint.py      request_fingerprint                           TD §18.3
│   ├── types/
│   │   ├── decisions.py        DecisionKind, Situation, Job, Projection, Scope, Partition,
│   │   │                       Sections, Ordering, Coverage, Cut, Module, Section
│   │   ├── blocks.py           Prose | StructuralClaim | Presentation | Reference, Licence
│   │   ├── document.py         Document, front matter, MarkedGap
│   │   ├── source.py           Source kinds, Authority (locked lookup), ScopeTier, Frame
│   │   └── results.py          Envelope, ClaimDomain, TaskKind, failure classes
│   ├── policy/
│   │   ├── sufficiency.py      sufficiency(...) -> Verdict                   TD §9.1
│   │   └── template.py         template_policy(situation, job) -> TemplateId TD §12.1
│   ├── compute/
│   │   ├── extent.py           extent(scope, partition, constants, cap_decl) TD §12.2a
│   │   ├── feasibility.py      feasibility(scope, cap_decl)                  TD §12.2
│   │   ├── integrity.py        integrity(decision_set, cap_decl)             TD §E5
│   │   └── fulfilment.py       check_unit(order, section)                    TD §9.5
│   └── document/
│       ├── builder.py          build_document(...) -> Document | BuildError  TD §9.6
│       └── validate.py         validate_blocks(...)                          TD §9.6, §9.7
│
├── ports/                      Protocol definitions ONLY. No implementations, no I/O.
│   ├── stores.py               DecisionStore · ClaimStore · MemoStore · DocumentStore ·
│   │                           ArtifactStore · TaskStore · SourceStore · LedgerStore
│   ├── objects.py              ObjectStore (payload put/get, content-addressed)
│   ├── gateway.py              ModelGateway
│   ├── renderer.py             Renderer (merge + print + availability + capability)
│   └── clock.py                Clock — injected, so lease-expiry tests never sleep
│
├── claim/                      the D17 protocol. Takes ports; owns no SQL.
│   ├── protocol.py             step() · step_shared() — THE ONLY claim path  TD §7.3
│   ├── operations.py           RESERVE_NEW · RESERVE_TAKEOVER · HEARTBEAT · COMMIT  TD §7.2
│   ├── find.py                 FIND_RESULT(domain, identity)                 TD §7.3c
│   ├── reconcile.py            RECONCILE(key, domain, existing)              TD §7.3c
│   ├── publish.py              PUBLISH — per-domain branches                 TD §7.3a
│   └── attach.py               ATTACH · ATTACH_PROVENANCE                    TD §7.3b, §9.6a
│
├── work/                       the Task system
│   ├── states.py               Task state machine, transitions, resumability TD §8.5, §8.8
│   ├── lease.py                LEASE · HEARTBEAT · COMPLETE — epoch-fenced   TD §8.3
│   ├── lifecycle.py            CANCEL · RESUME                               TD §8.7, §8.8
│   ├── coordinator.py          admission · backlog · shedding · orphan sweep TD §8.2, §8.4
│   └── admission.py            calls_admitted CAS · UserQuotaBucket upsert   TD §8.6a
│
├── gateway/                    the ONLY package permitted a provider SDK
│   ├── model_call.py           MODEL_CALL — the single canonical path         TD §8.6b
│   ├── slots.py                ACQUIRE/RELEASE_PROVIDER_SLOT — FIFO           TD §8.6b ③
│   ├── classify.py             failure classification (10 classes)           TD §8.5
│   ├── budget.py              attempt deadline · Task budget · jitter        TD §8.6
│   ├── ledger.py               CallLedger append                             TD §8.8a
│   └── providers/
│       └── openrouter.py       one adapter; others drop in beside it
│
├── engine/                     the Renderer. MUST NOT import core.types.
│   ├── merge.py                merge(doc_mapping, template_source) — dom     TD §12.3
│   ├── checks.py               unrendered · realization pairing · honesty    TD §12.3
│   ├── print.py                Chromium, bounded slots, probes               TD §12.4, §12.5
│   ├── capability/
│   │   ├── needs.py            ① ProseFailure → {served, weight, licenses}   TD §12.2
│   │   ├── honesty.py          ② relation → permitted (geometry, convention) TD §12.2
│   │   └── version.py          renderer_build · render_env_hash · decl ver   TD §12.1
│   └── templates/              the four Jinja templates + template_version
│
├── flows/                      orch — TD §9's workflows. Compose primitives; restate nothing.
│   ├── intake.py               §9.1 — synchronous
│   ├── planning.py             §9.2
│   ├── correction.py           §9.3
│   ├── approval.py             §9.4 — + §9.4a approved_extent
│   ├── generation.py           §9.5
│   ├── document.py             §9.6
│   ├── render.py               §9.8
│   ├── extraction.py           §9.8a
│   └── export.py               §9.9 + §9.9a canonical zip
│
├── store/                      infra — the ONLY package permitted psycopg
│   ├── pg/
│   │   ├── pool.py             connection pool
│   │   ├── decisions.py        DecisionStore impl (+ SharedDerivation, edges, slot bump)
│   │   ├── claims.py           ClaimStore impl — the five one-statement operations
│   │   ├── tasks.py            TaskStore impl
│   │   ├── commitments.py      Commitment + members
│   │   ├── memo.py             MemoIndex
│   │   ├── documents.py        Document + Construction + Provenance
│   │   ├── artifacts.py        ArtifactIndex
│   │   ├── sources.py          Source + SourceExtraction
│   │   ├── routing.py          RoutingResult
│   │   └── ledger.py           CallLedger + UserQuotaBucket
│   ├── objects/
│   │   ├── local.py            filesystem adapter (T0/T1)
│   │   └── s3.py               S3-compatible adapter (T1+)
│   ├── gc.py                   the unit rule + reverse-order deletion         TD §10.6, §10.6a
│   └── migrations/
│       └── 0001_init.sql       one migration, the whole frozen schema
│
├── api/
│   ├── app.py                  FastAPI + uvicorn entry (V1's banner discipline kept)
│   ├── conversation.py         create · utterance · intake turn
│   ├── plan.py                 read plan · approve
│   ├── tasks.py                start · status · cancel · resume
│   └── delivery.py             artifact · export
│
├── obs/
│   ├── events.py               the TD §17 record set
│   └── log.py                  structured JSON to stdout at T1
│
└── config.py                   env-driven settings; CORS; access gate; caps

tests/
├── test_boundaries.py          THE IMPORT WALL — written in Phase 0           TD §15.8
├── unit/                       identity · state machines · pure compute
├── repo/                       real Postgres: constraints, CAS, upsert, FKs
├── protocol/                   claim correctness, reconcile, publish, attach
├── concurrency/               two workers, claim loss, lease expiry, races
├── gateway/                    admission, quota, slots, classification
├── workflow/                   each §9 flow end to end
├── render/                     env identity, determinism, honesty, duplicates
├── export/                     commitment scoping, byte determinism
├── recovery/                   crash windows, orphans, restart
└── e2e/                        intake → approved → generated → rendered → exported
```

## 2.3 The import wall (Phase 0 deliverable)

Modelled directly on V1's working `FORBIDDEN` table, extended for the frozen design's rules:

```python
FORBIDDEN = {
  "core":    ("psycopg", "httpx", "requests", "socket", "fastapi", "playwright", "jinja2",
              "store", "gateway", "work", "claim", "flows", "api", "engine"),
  "ports":   ("psycopg", "httpx", "playwright", "store", "gateway", "engine", "flows"),
  "claim":   ("psycopg", "httpx", "playwright", "store.pg", "flows", "api"),
  "work":    ("psycopg", "httpx", "playwright", "store.pg", "flows", "api"),
  "gateway": ("psycopg", "playwright", "store.pg", "flows", "api", "core.types"),
  "engine":  ("httpx", "requests", "socket", "urllib.request", "psycopg",
              "core.types", "flows", "api"),            # ← duck-typed mappings only
  "store":   ("httpx", "playwright", "flows", "api", "gateway"),
  "flows":   ("psycopg", "playwright"),                 # composes via ports
}
ONLY_GATEWAY_MAY_IMPORT = ("openai", "anthropic", "httpx")   # TD §15.8, Rev. 11
```

Three rules deserve naming because they encode design decisions rather than taste:

- **`core` may import nothing but `core`.** That is what makes *"no `dom` function takes a port
  parameter"* mechanical rather than reviewed (TD §B).
- **`engine` may not import `core.types`.** V1's reason survives: a duck-typed mapping is what lets a
  template fix cost a render (~3.4 s) instead of a generation (~323 s).
- **Only `gateway` may import a provider SDK or `httpx`.** TD §15.8's Rev. 11 addition, with its own
  stated limit: an import wall bounds Python imports, never a subprocess's network — Chromium's font
  fetching is handled separately (TD §12.5, pinned fonts, no `networkidle`).

---

# 3. Phased Build Order

Eleven phases. Each lists **what · why here · TD sections · depends on · exit tests**.

Two corrections to the ordering proposed in the task, both required by the design:

| Proposed | Corrected | Why |
|---|---|---|
| Domain types → **DB schema** → identity | Domain types → **identity** → DB schema | The schema's `UNIQUE` constraints are *over identity columns* (`envelope`, `claim_key`, `construction_key`, `version_number`). The migration cannot be written before the identity shape exists. Identity is also pure, so it is testable with zero infrastructure — the cheapest possible first phase |
| Gateway → **Coordinator/admission** | **Admission** → Gateway | `MODEL_CALL` step ① *is* tenant admission and step ② *is* per-origin admission (TD §8.6b). The Gateway cannot be built complete before the admission primitives exist |

And one addition: the **capability declaration** must precede the planning flow, because `extent` and
`feasibility` both read it (TD §12.2a) and planning calls both.

---

### Phase 0 — Scaffold and the import wall

**What** · repo layout, `pyproject.toml`, empty packages with `__init__.py`, `tests/test_boundaries.py`
with the full `FORBIDDEN` table, CI running pytest, a `Clock` port.
**Why here** · V1's own instruction: write the wall when there are packages to keep apart, not after
the damage. An empty wall passes trivially and fails the first violation.
**TD** · §2, §15.8. **Depends on** · nothing.
**Exit** · `test_boundaries` passes against empty packages; CI green; a deliberately-injected bad
import fails the build.

### Phase 1 — Domain types and identity · **the pure kernel**

**What** · `core/types/*` (Pydantic v2 models, closed vocabularies as `Literal`), then
`core/identity/*`: canonical JSON, `envelope()`, `task_key()`, `claim_key()`, member encoding,
content hashes, request fingerprint.
**Why here** · everything downstream is addressed by these functions. Pure, no I/O, no DB — so the
golden inclusion/exclusion suite (TD §15.2) can be complete before any infrastructure exists, and
**U1 stops being a risk at the earliest possible moment.**
**TD** · §4.1, §5.1, §5.1a, §5.2, §5.3–§5.9a, §5.11, §5.11a, §5.12, §5.12a.
**Depends on** · Phase 0.
**Exit** · the full §15.2 table — for **every** kind, each listed input changes the key and **each
listed exclusion does not**; canonical-JSON stability across key order / whitespace / NFC;
`test_three_key_constructions_are_disjoint`; `test_brief_hash_matches_renderer` (one struct, two
consumers).

### Phase 2 — Schema, migrations, repositories

**What** · `0001_init.sql` for all 20 tables with every constraint from §5 below; `store/pg/*`
repositories behind `ports/stores.py`; the object-store adapter.
**Why here** · the claim protocol's correctness **is** database atomicity (CAS, `ON CONFLICT`,
isolation). It cannot be meaningfully tested against an in-memory fake — so real Postgres must exist
before Phase 3. *(This is the reason the proposed order is right here and I am not changing it.)*
**TD** · §4.2, §4.3, §4.4, §10.1–§10.6a.
**Depends on** · Phase 1 (identity column shapes).
**Exit** · every constraint in §5's inventory is asserted by a `repo/` test that *tries to violate it
and is refused* — not by reading the DDL. Append-only tables reject `UPDATE`/`DELETE` at the
privilege level. `test_derived_identities_are_tabled` passes.

### Phase 3 — The claim protocol · **the correctness kernel**

**What** · the five one-statement operations; `FIND_RESULT`; `RECONCILE`; `PUBLISH` with all six
domain branches; `ATTACH`; `ATTACH_PROVENANCE`; `step()` / `step_shared()` with the `on_result` hook.
**Why here** · every workflow composes this. Building a workflow first would mean building it twice.
**TD** · §7.1–§7.5, §7.3a–§7.3c, §9.6a.
**Depends on** · Phases 1–2.
**Exit** · the whole of §15.4 — 16-thread single-flight; fencing rejects a slow worker (R2);
takeover race (R5); write-once (R6); heartbeat detects fencing; content-addressed payloads cannot
overwrite; `test_publish_is_atomic`; `test_fenced_publish_writes_nothing`;
`test_version_row_never_without_edges`; `test_unique_envelope_survives_claim_loss`;
`test_claim_loss_costs_at_most_one_call`; `test_publish_adopts_an_existing_result`. **Lease expiry is
injected via the `Clock` port — never by sleeping.**

### Phase 4 — The Task system

**What** · state machine, per-kind `task_key` inputs, `LEASE`/`HEARTBEAT`/`COMPLETE` with epoch
fencing, `CANCEL` with its state predicate, `RESUME` with its resumability predicate, orphan sweep.
**Why here** · the Coordinator and the Gateway's per-origin admission both need Task state; workflows
need Tasks to run in.
**TD** · §8.1, §8.3–§8.5, §8.7, §8.8.
**Depends on** · Phases 2–3.
**Exit** · `test_regenerate_under_new_commitment_is_a_NEW_task`;
`test_regenerate_under_same_commitment_is_idempotent`; `test_resume_incomplete_task`;
`test_resume_refused_for_provider_refused`; `test_double_resume_is_a_noop`;
`test_cancel_on_terminal_task_is_rejected`; `test_completion_wins_tie_with_cancel`;
`test_cancel_keeps_committed_memos`.

### Phase 5 — Admission, ledger, Model Gateway

**What** · `calls_admitted` CAS; `UserQuotaBucket` upsert; `CallLedger` append; FIFO provider slots;
`MODEL_CALL` with all five steps; failure classification; attempt deadline; jitter; provider adapter.
**Why here** · admission before the Gateway (the correction above). After this phase **no code path
can reach a provider except through `MODEL_CALL`**, and the import wall proves it.
**TD** · §8.5, §8.6, §8.6a, §8.6b, §8.8a.
**Depends on** · Phases 2–4.
**Exit** · `test_budget_is_enforced_under_concurrency` (8 concurrent, budget 2 → exactly 2 admitted);
`test_cold_quota_bucket_admits`; `test_tenant_quota_is_enforced_at_admission`;
`test_provider_cap_holds_across_both_origins`; `test_provider_slot_is_released_on_failure`;
`test_429_is_retried` / `test_400_is_terminal`;
`test_task_budget_exhaustion_is_distinguishable`; `test_lifetime_spend_is_derivable_without_a_resume`;
`test_admitted_but_crashed_call_fails_safe`; `test_provider_boundary_is_mechanically_exclusive`.

### Phase 6 — Pure compute and the capability declaration

**What** · `core/policy/*`, `core/compute/*`, `core/document/*`; `engine/capability/*` (both tables,
`renderer_build`, `render_env_hash`, `capability_decl_version`).
**Why here** · `extent` and `feasibility` read the declaration (§12.2a) and planning calls both, so
the declaration precedes planning. All of it is pure, so it is fast to test and needs no flow.
**TD** · §2's `dom` surface, §12.1, §12.2, §12.2a, §E5, §9.7.
**Depends on** · Phases 1, 2 (for the types it reads).
**Exit** · one test per runtime invariant (S1, S2, S2b, S3, S4, S5, S12) and a
*type-level* test per construction-enforced invariant asserting the violation is **inexpressible**
(S6, S7, S8, S9, S10, S11, S13, S14); `test_dom_signatures_match_section_2`;
`test_S14_identity_not_positional`; `test_S7_inexpressible`.

### Phase 7 — Renderer and artifacts

**What** · `merge` + the three merge-time checks; bounded Chromium slots; the two layout probes;
`ArtifactIndex` publication through `step("render", …)`.
**Why here** · needs the declaration (Phase 6) and the claim protocol (Phase 3); needs **no** model
call, so it can be built and tested against the saved `V2/runs/generate-01` document JSON that the
design cites throughout. Parallelisable with Phase 8 if two people are working.
**TD** · §9.8, §12.1–§12.5.
**Depends on** · Phases 3, 6.
**Exit** · `test_honesty_table_enforced`; `test_realization_paired_in_source_order`;
`test_unrendered_kind_reported`; `test_no_margin_argument`; `test_viewport_is_a4`;
`test_no_network_at_render`; `test_render_claim_prevents_duplicate_artifacts`;
`test_one_artifact_per_document_environment`; `test_render_claim_loss_does_not_re_render`.

### Phase 8 — Domain workflows

**What**, in dependency order within the phase:

```
8a  intake (sync)              §9.1   → situation · job · scope_tier · frame
8b  source extraction          §9.8a  → SourceExtraction, computed state §9.8b
8c  structure (shared)         §5.3   → step_shared, ATTACH
8d  planning                   §9.2   → projection · scope · partition · sections · ordering
                                        + extent · feasibility · integrity
8e  correction                 §9.3   → routing, targeted versions, stale walk
8f  approval                   §9.4   → Commitment, members, approved_extent §9.4a
8g  generation                 §9.5   → memo fan-out, two attempts, incomplete
8h  document construction      §9.6   → build, validate, ATTACH_PROVENANCE
```

**Why this order** · 8a produces the readings 8b–8d consume; 8c is the one shared derivation and
exercises `ATTACH` before anything depends on it; 8d needs 8c plus Phase 6's compute; 8e/8f operate on
8d's output; 8g needs a Commitment; 8h needs memos.
**Depends on** · Phases 3–7.
**Exit** · one `workflow/` test per sub-phase, plus: `test_frame_reads_situation_readings`;
`test_late_old_extractor_cannot_regress_the_source`; `test_extractor_upgrade_invalidates_structure`;
`test_second_project_reuses_shared_derivation`; `test_shared_derivation_does_not_leak_staleness`;
`test_job_correction_stales_downstream_not_structure`; `test_prompt_bump_is_not_stale`;
`test_stale_blocks_approval_when_integrity_is_clean`;
`test_reapproval_after_template_edit_is_a_new_commitment`;
`test_approved_extent_survives_recalibration`; `test_generation_resume_costs_the_remainder`;
`test_incomplete_writes_no_document`; `test_identical_content_is_one_document`;
`test_document_claim_loss_rebuilds_provenance`; `test_document_provenance_attaches_on_hit`.

### Phase 9 — Export and API

**What** · `flows/export.py` with commitment-scoped resolution and the canonical zip; then the API
surface (TD §18) including cancel/resume and signed-URL delivery.
**Why here** · export needs artifacts; the API needs every flow it exposes.
**TD** · §9.9, §9.9a, §18.1–§18.4, §13.3.
**Depends on** · Phases 7–8.
**Exit** · `test_export_uses_commitment_documents`; `test_export_task_key_changes_with_artifact_set`;
`test_export_refuses_when_a_module_is_unrendered`; `test_export_refuses_unsatisfiable_pin`;
`test_export_reports_newer_plan_without_refusing`; `test_export_zip_is_byte_deterministic`;
`test_export_has_no_claim_row`; `test_intake_retry_does_not_double_append`;
`test_request_id_mismatch_returns_409`; `test_concurrent_appends_get_distinct_ord`.

### Phase 10 — Observability, recovery, E2E, deployment

**What** · the §17 event set; GC with the unit rule; `recovery/` suite; `e2e/` suite with a stubbed
gateway replaying `V2/runs/`; the T1 image with pinned fonts, env CORS, access gate.
**Why here** · needs everything; and the E2E suite is the evidence for §9's Definition of Done.
**TD** · §10.6, §10.6a, §11, §16, §17, §15.5–§15.9.
**Depends on** · all.
**Exit** · the full Definition of Done (§9 below).

---

# 4. Design → Code Mapping

## 4.1 Identity

| Design concept | TD § | Code location | Main types/functions | Depends on | Tests |
|---|---|---|---|---|---|
| canonical JSON | §5.1 | `core/identity/canonical.py` | `dumps(obj) -> bytes` | — | `test_canonical_json_stable` |
| envelope | §5.1, §5.3–§5.9a | `core/identity/envelope.py` | `envelope(kind, member, inputs, env) -> Envelope` | canonical | the §15.2 table, both directions |
| task key | §5.12 | `core/identity/task_key.py` | `task_key(kind, inputs)`; `TaskKind` | canonical | `test_task_key_is_separate_from_envelope` |
| claim key | §5.12a | `core/identity/claim_key.py` | `claim_key(domain, identity)`; `ClaimDomain` | canonical | `test_three_key_constructions_are_disjoint` |
| member encoding | §5.11a | `core/identity/member.py` | `root()`, `module(id)`, `ordering_level(...)` | — | `test_null_member_cannot_duplicate_envelope` |
| content hashes / refs | §4.3 | `core/identity/content.py` | `content_hash(bytes)`, `ContentRef` | — | `test_content_addressed_payload_prevents_overwrite` |
| request fingerprint | §18.3 | `core/identity/fingerprint.py` | `request_fingerprint(role, text)` | canonical | `test_request_id_mismatch_returns_409` |
| brief inputs | §5.7a | `core/types/decisions.py` | `BriefInputs` + `brief_inputs_hash` | canonical | `test_brief_hash_matches_renderer` |
| render env identity | §12.1 | `engine/capability/version.py` | `renderer_build()`, `render_env_hash()`, `capability_decl_version()` | templates | `test_one_artifact_per_document_environment` |

**The nesting matters and the code must express it** (§12.1): `renderer_build ⊂ render_env_hash ⊂
capability_decl_version`. Implement as three functions where each calls the previous — not three
independent hashes over overlapping inputs, which is how Rev. 6 let them drift.

## 4.2 Task / claim protocol

| Concept | TD § | Location | Functions | Depends on | Tests |
|---|---|---|---|---|---|
| Claim states | §7.1 | `core/types/results.py` + `store/pg/claims.py` | `ClaimState`, the 3-state machine | identity | `test_committed_is_write_once` |
| the five operations | §7.2 | `claim/operations.py` | `lookup · reserve_new · reserve_takeover · heartbeat · commit` | ClaimStore | `test_two_workers_one_envelope`, `test_takeover_race` |
| lease + epoch fencing | §7.2, §8.3 | `claim/operations.py`, `work/lease.py` | CAS statements with `epoch=` predicates | Clock | `test_fencing_rejects_slow_worker`, `test_heartbeat_detects_fencing` |
| `FIND_RESULT` | §7.3c | `claim/find.py` | `find_result(domain, identity)` — six branches | repos | `test_step_checks_for_an_existing_result_before_reserving` |
| `RECONCILE` | §7.3c | `claim/reconcile.py` | `reconcile(key, domain, ref)` | ClaimStore | `test_claim_loss_costs_at_most_one_call` |
| `PUBLISH` | §7.3a | `claim/publish.py` | `publish(key, epoch, ref, meta)` — six domain branches, **one transaction** | all repos | `test_publish_is_atomic`, `test_fenced_publish_writes_nothing` |
| `ATTACH` | §7.3b | `claim/attach.py` | `attach(key, project, kind, member, deps)` | DecisionStore | `test_second_project_reuses_shared_derivation` |
| `ATTACH_PROVENANCE` | §9.6a | `claim/attach.py` | `attach_provenance(key, commitment_id)` | DocumentStore | `test_document_claim_loss_rebuilds_provenance` |
| **`step` / `step_shared`** | §7.3 | `claim/protocol.py` | `step(domain, identity, derive_fn, on_result=identity_fn)` | all the above | `test_no_workflow_restates_the_claim_branches` |
| Task states | §8.5, §8.8 | `work/states.py` | `TaskState`, `resumable(task)` | — | `test_resume_incomplete_task` |
| cancel / resume | §8.7, §8.8 | `work/lifecycle.py` | `cancel(id)`, `resume(id)` — both epoch-fenced | TaskStore | `test_cancel_on_terminal_task_is_rejected` |
| recovery | §8.4, §11 | `work/coordinator.py` | `sweep_orphans()` | Clock | the `recovery/` suite |

## 4.3 Accounting and admission

| Concept | TD § | Location | Functions | Tests |
|---|---|---|---|---|
| `UserQuotaBucket` | §8.6a | `work/admission.py` + `store/pg/ledger.py` | `admit_tenant(user, cap)` — upsert with condition on `DO UPDATE` | `test_cold_quota_bucket_admits` |
| Task budget | §8.6, §8.6a | `work/admission.py` | `admit_task(id, epoch, max_calls)` — conditional increment | `test_budget_is_enforced_under_concurrency` |
| per-origin limits | §8.6b | `gateway/model_call.py` | `origin='task'` CAS · `origin='sync'` in-process turn counter | `test_turn_call_cap_bounds_one_turn` |
| provider limits | §8.6b ③ | `gateway/slots.py` | `acquire(provider)` / `release(provider)` — FIFO, `finally` | `test_provider_cap_holds_across_both_origins` |
| `CallLedger` | §8.8a | `gateway/ledger.py` | `record(origin, operation, task?, outcome, …)` — unfenced | `test_fenced_worker_call_is_still_accounted` |
| derived spend | §8.8a | `store/pg/ledger.py` | `spent(task, epoch)`, `spent_lifetime(task)`, `quota(user, window)` | `test_lifetime_spend_accumulates_across_resumes` |
| render limits | §12.5 | `engine/print.py` | a slot pool sized `min((mem−65MB)/240MB, vCPU)` | `test_render_claim_prevents_duplicate_artifacts` |
| DB pool | §14 | `store/pg/pool.py` | pool size config | load check in Phase 10 |

## 4.4 Model Gateway — one canonical path

```
ports/gateway.py        ModelGateway Protocol — the only interface flows see
gateway/model_call.py   MODEL_CALL: ① tenant ② per-origin ③ ACQUIRE slot
                                    ④ try: call / finally: RELEASE  ⑤ ledger
gateway/classify.py     10 failure classes (§8.5); 429 and Retry-After are RETRIABLE
gateway/budget.py       attempt deadline (120 s); Task budget; full jitter
gateway/slots.py        FIFO semaphore per provider, size = cap
gateway/providers/      adapters — the only modules importing a provider SDK
```

**Invariant the wall enforces:** no module outside `gateway/` imports a provider SDK or `httpx`. Every
model invocation in `flows/` goes through the `ModelGateway` port. This is TD §15.8's
`test_provider_boundary_is_mechanically_exclusive`, and it is the thing that keeps §8.6b's
centralisation true as the code grows.

## 4.5 Domain workflows — dependency graph

```
                         ┌──────────────┐
  Utterance ────────────►│   intake     │ §9.1  sync, ≤30 s SLA
                         └──┬────┬──────┘
                 situation  │    │  job
                            ▼    ▼
              ┌──────────── scope_tier ─── frame ◄── source_set
              │                 │            │
              │                 └──────┬─────┘
   Source ──► extraction §9.8a ────────┤   (content-addressed, global)
              │                        ▼
              └──────────────► structure §5.3  step_shared + ATTACH
                                       ▼
                                  planning §9.2
                      projection → scope → partition → sections → ordering
                                       │
                         ┌─────────────┼──────────────┐
                         ▼             ▼              ▼
                    extent §12.2a  feasibility   integrity §E5
                                       ▼
                     correction §9.3 ◄─┴─► approval §9.4 (+ §9.4a)
                                             ▼
                                       generation §9.5   memo fan-out
                                             ▼
                                  document construction §9.6
                                             ▼
                                        render §9.8
                                             ▼
                                        export §9.9
```

**Every box above calls `step()`.** None contains its own `LOOKUP`/`RESERVE`/`MISS` branches — TD
§7.3's rule, enforced by `test_no_workflow_restates_the_claim_branches`.

Per-workflow trace (input → identity → task → claim → derive → publish):

| Flow | Task key | Claim domain / identity | `derive_fn` | `on_result` | Result row |
|---|---|---|---|---|---|
| intake | *none* — sync | `decision:situation` / `{envelope}` | interpret | — | `DecisionVersion` |
| extraction | `{content_hash, extractor_version}` | `source_extract` / same pair | extract | — | `SourceExtraction` |
| structure | part of `plan` | `decision:structure` / `{envelope}` | derive | **`ATTACH`** | `SharedDerivation` + pointer |
| planning | `{structure_envelope, situation_v, job_v, tier_v, frame_v}` | `decision:<kind>` / `{envelope}` ×5 | derive | — | `DecisionVersion` ×5 |
| correction | `{utterance_id}` | `routing` / `{envelope}` | route | — | `RoutingResult` |
| approval | *none* — sync | *none* | — | — | `Commitment` + members |
| generation | `{commitment_id, module_id}` | `memo` / `{brief_envelope}` × sections | 2 attempts, keep better | — | `MemoIndex` |
| document | part of `generate` | `document` / `{construction_key}` | build + validate | **`ATTACH_PROVENANCE`** | `Document` + Construction + Provenance |
| render | `{document_id, render_env_hash}` | `render` / same pair | merge + print | — | `ArtifactIndex` |
| export | `{export_hash}` | **none — deliberate** | resolve + zip | — | object only |

## 4.6 Rendering

| Concept | TD § | Location |
|---|---|---|
| capability declaration ① need coverage | §12.2 | `engine/capability/needs.py` |
| capability declaration ② honesty table | §12.2 | `engine/capability/honesty.py` |
| `renderer_build` / `render_env_hash` / `capability_decl_version` | §12.1 | `engine/capability/version.py` |
| template content hash | §12.1 | `engine/templates/` + `version.py` |
| merge + the three merge-time checks | §12.3 | `engine/merge.py`, `engine/checks.py` |
| print, probes, bounded slots | §12.4, §12.5 | `engine/print.py` |
| artifact publication | §9.8 | `flows/render.py` via `step("render", …)` |
| artifact lookup by pinned env | §9.9 ① | `store/pg/artifacts.py` — index on `(document_id, capability_decl_version)` |
| deterministic output | §9.9a | `flows/export.py` (zip); render is **not** byte-deterministic, which is why it has a claim |

## 4.7 Export

```
Commitment
   ▼ ordering member version  →  module order          §9.9 ①
   ▼ sections member version  →  the committed section set per module
   ▼ Document whose construction memo set matches that section set
   ▼ ArtifactIndex WHERE capability_decl_version = C.environment.capability_decl_version
   ▼ export_input = [{module_id, ordinal, document_id, artifact_id, bytes_hash}]
   ▼ export_hash  = sha256(canonical_json(export_input))     →  Task key AND object path
   ▼ canonical zip §9.9a  — fixed order, fixed 1980 timestamps, 0644, no extra fields
   ▼ PUT export-zip/<export_hash>   — existence check makes a second build a no-op
   ▼ Task result {export_hash, path, size, export_input}
   ▼ delivery: inline ≤ threshold, else short-TTL signed URL      §13.3
```

---

# 5. Database Implementation Plan

20 tables, from TD §4.2/§4.2a. **No table is invented here.**

| Table | Purpose | PK | Unique | FK | Indexes | Lifecycle |
|---|---|---|---|---|---|---|
| `Project` | tenancy root; `next_ord` slot | `id` | — | — | `(user_id)` | never |
| `Utterance` | testimony, append-only (S11) | `id` | `(project_id, ord)`, `(project_id, request_id)` | `project_id` | `(project_id, ord)` | never |
| `Source` | uploaded bytes + kind | `id` | `(project_id, content_hash)` | `project_id` | `(content_hash)` | with project |
| `SourceExtraction` | **global** extraction result incl. `infeasible` | `(content_hash, extractor_version)` | = PK | — | `(content_hash)` | **never** |
| `Decision` | the slot; `next_version` counter | `(project_id, kind, member)` | = PK | `project_id` | — | with project |
| `SharedDerivation` | **global** shared payload | `id` | `(kind, envelope)` | — | `(kind, envelope)` | **never** |
| `DecisionVersion` | immutable version / shared pointer | `id` | `(project_id, kind, member, envelope)`, `(project_id, kind, member, version_number)` | `Decision`, `shared_id` | `(project_id, kind, member, version_number DESC)` | never |
| `DependencyEdge` | the graph `stale` walks | `(version_id, depends_on_id)` | = PK | both → `DecisionVersion` | **`(depends_on_id)`** — the stale query | with version |
| `Commitment` | approval act, pinned env | `id` | `(project_id, version_set_hash, environment_hash)` | `project_id` | `(project_id)` | never |
| `CommitmentMember` | per-member pinning (S10) | `(commitment_id, kind, member)` | = PK | `commitment_id`, `version_id` | — | with commitment |
| `Claim` | **D17 coordination** | `key` | = PK | — | `(state, lease_until)` for the sweep | with its result unit |
| `MemoIndex` | generated section index | `key` | = PK | — | `(project_id)` for GC | unit: claim+index+payload |
| `Document` | identified by content | `id` | `(project_id, module_id, content_hash)`, `(project_id, module_id, seq)` | `project_id` | `(project_id, module_id, seq DESC)` | never |
| `DocumentConstruction` | idempotency index onto Document | `construction_key` | = PK | `document_id` | `(document_id)` | with document |
| `DocumentProvenance` | commitments → document | `(document_id, commitment_id)` | = PK | both | `(commitment_id)` | with document |
| `ArtifactIndex` | delivered bytes | `id` | **`(document_id, render_env_hash)`**, `(document_id, template_id, seq)` | `document_id` | `(document_id, capability_decl_version)` — export's lookup | never |
| `RoutingResult` | the router's own output | `envelope` | = PK | `project_id` | `(project_id)` | unit: claim+row+payload, 90 d |
| `Task` | process state | `id` | `(project_id, kind, idempotency_key)` | `project_id` | `(state, lease_until)`, `(project_id)` | terminal + 30 d |
| `UserQuotaBucket` | admission windows | `(user_id, window_start)` | = PK | — | `(window_start)` for GC | 7 d |
| `CallLedger` | accounting + audit | `id` | — | **none — by design** | `(task_id, task_epoch)`, `(user_id, started_at)`, `(started_at)` | 1 y |

## 5.1 Transaction boundaries

| Operation | Scope |
|---|---|
| append `Utterance` | single insert (+ `next_ord` bump on `Project`) |
| `RESERVE_NEW` / `RESERVE_TAKEOVER` / `HEARTBEAT` | **one statement each**, no transaction |
| **`PUBLISH`** | **ONE transaction**: claim CAS first, then the domain's result rows + slot/seq bumps |
| `RECONCILE` | one transaction: find by canonical identity, insert claim `ON CONFLICT DO NOTHING` |
| `ATTACH` / `ATTACH_PROVENANCE` | one transaction each, idempotent |
| mint `Commitment` + members | one transaction |
| `stale_set` walk | one read transaction, `REPEATABLE READ` |
| Task lease / complete / cancel / resume | one statement each, epoch-fenced |
| admission (task and tenant) | **one statement each** — this is what makes them atomic |
| `CallLedger` append | one insert, **unfenced** |
| GC of a claimed result | claim+index in one transaction, **then** the payload |

**Nothing spans Postgres and object storage.** Closed by write ordering (payload first) and deletion
ordering (reference first), not by coordination.

## 5.2 Rows by mutability class

| Class | Tables | Mechanism |
|---|---|---|
| **append-only** | `Utterance`, `CallLedger`, `DependencyEdge`, `DocumentProvenance` | revoke `UPDATE`/`DELETE` |
| **immutable after insert** | `DecisionVersion`, `SharedDerivation`, `Document`, `DocumentConstruction`, `ArtifactIndex`, `MemoIndex`, `SourceExtraction`, `RoutingResult`, `Commitment`, `CommitmentMember` | revoke `UPDATE` |
| **atomic CAS only** | `Claim` (state/epoch/result_ref), `Task` (state/epoch/lease/calls_admitted), `UserQuotaBucket` (calls_admitted) | every write carries a `WHERE` predicate |
| **epoch-fenced** | `Claim`, `Task` | `AND epoch = :observed` |
| **counter rows** | `Decision.next_version`, `Project.next_ord`, `Document.seq`, `ArtifactIndex.seq` | `UPDATE … RETURNING`, inside the publishing transaction |
| **freely updatable** | *none* | — |

**Enforced, not documented.** TD §4.4's instruction is explicit: *"Enforced by revoking
`UPDATE`/`DELETE`, not by convention."* So the migration ends with grants, and `repo/` tests assert
that an attempted mutation is **refused by the database**.

Columns that must **not** exist, because their absence is a design decision (C4): `status`,
`freshness`, `superseded_by` on any row; `spent` / `spent_lifetime` on `Task`; `extracted_ref` /
`state` on `Source`. A `repo/` test asserts the information schema does not contain them.

## 5.3 Dependency-ordered deletion

```
GC unit for any claimed result:   Claim + index/result row   →  THEN payload
                                  (one transaction)             (object delete)
Crash between the two leaves an ORPHAN PAYLOAD — reclaimed by the orphan sweep.
The reverse order would leave a FALSE HIT, which nothing detects.
```

---

# 6. Canonical Service Interfaces

Signature shapes, not code. Every workflow composes these.

### `claim/protocol.py` — `step()`

```
Purpose        the ONE path by which any reusable result is produced or reused
Inputs         domain: ClaimDomain · identity: dict · derive_fn: () -> Result
               on_result: (Result) -> Result = identity_fn
Outputs        Result
Errors         Fenced (retry internally) · DeriveFailed(class) · Inconsistent
Transaction    none held across derive_fn; PUBLISH is one transaction internally
Idempotency    by claim_key(domain, identity); a committed claim short-circuits
Concurrency    single-flight; BUSY yields the slot (T10); EXPIRED takes over by CAS
```

`step_shared()` is the same with a mandatory `on_result = ATTACH`.

### `claim/find.py` — `FIND_RESULT`

```
Purpose        answer "does this result already exist?" by CANONICAL IDENTITY, not claim key
Inputs         domain, identity
Outputs        ContentRef | None
Errors         none — absence is a value
Transaction    one read
Idempotency    pure read
Concurrency    safe; a concurrent publisher simply means the next loop sees HIT
```

### `claim/reconcile.py` — `RECONCILE`

```
Purpose        rebuild a lost Claim from an existing result — zero model calls
Inputs         key, domain, existing_ref
Outputs        None
Errors         none — ON CONFLICT DO NOTHING
Transaction    one
Idempotency    fully; concurrent reconcilers write an identical row
Concurrency    the row is born COMMITTED (terminal), so its epoch is never compared
```

### `claim/publish.py` — `PUBLISH`

```
Purpose        commit the claim AND its result rows atomically
Inputs         key, epoch, payload_ref, metadata (domain-shaped)
Outputs        bool — False means fenced or already committed
Errors         none raised for a conflict; adopt-on-conflict returns the existing ref
Transaction    ONE. Statement ① is the CAS; a fenced worker performs no inserts.
Idempotency    write-once; COMMITTED is terminal
Concurrency    exactly one publisher wins per key
```

### `gateway/model_call.py` — `MODEL_CALL`

```
Purpose        the single canonical path to any provider
Inputs         user_id, project_id, operation, origin, task_ref?, prompt, schema, deadline
Outputs        Completion
Errors         the 10 classes of §8.5, each with retriable/terminal already decided
Transaction    none — ledger append is its own insert
Idempotency    NOT idempotent. Callers get idempotency from step()'s claim.
Concurrency    tenant admission → per-origin admission → FIFO provider slot → release in finally
```

### `ports/stores.py` — repository Protocols

```
DecisionStore    by_envelope · put_version(+edges, slot bump) · current · versions ·
                 dependents_of · stale_set
ClaimStore       lookup · reserve_new · reserve_takeover · heartbeat · commit · reconcile
TaskStore        create · lease · heartbeat · complete · cancel · resume · orphans
MemoStore        by_key · put
DocumentStore    by_content · by_construction_key · put · attach_provenance
ArtifactStore    by_document_and_env · put
SourceStore      put_source · extraction · put_extraction
LedgerStore      record · spent · spent_lifetime · quota_window · admit_tenant
ObjectStore      put(bytes) -> ContentRef · get(ref) · delete(ref) · exists(ref)
```

Every method states its own transaction boundary; **`flows/` never opens a transaction directly.**

### `ports/renderer.py`

```
Renderer         availability() -> Available | Missing(reason)
                 capability(template_id) -> CapabilityDeclaration     (both tables)
                 merge(doc_mapping, template_id) -> Html + MergeReport    pure
                 print(html) -> bytes + LayoutReport                      bounded slot
```

`doc_mapping` is a plain mapping — **never a `core.types` object.** The import wall enforces it.

---

# 7. Implementation Decisions Required

Only decisions that cannot be mechanically inferred. Ordinary coding choices are excluded by
construction.

### D-1 · Postgres isolation level for claim operations

**Recommended** `READ COMMITTED` (the default). **Reason** every claim operation is a single statement
whose atomicity comes from the statement itself (`UPDATE … WHERE epoch =`, `INSERT … ON CONFLICT`), and
`PUBLISH` is gated by the CAS as statement ①. `REPEATABLE READ` only for the `stale_set` walk, which
TD §10.2 already specifies. **Alternatives** `SERIALIZABLE` everywhere — rejected: it buys nothing the
CAS does not already give, and adds retry handling. **Architecture impact** none.
**Default** `READ COMMITTED`.

### D-2 · Async driver vs sync-in-threadpool

**Recommended** `psycopg3` **async**, with the renderer on a bounded thread pool.
**Reason** TD §3.1 specifies exactly this shape — async everywhere except a bounded render pool, with
`sync_playwright` left anchored. **Alternatives** sync everywhere (V1's shape) — rejected because
§G5's concurrency model depends on not paying a thread to wait. **Architecture impact** none; it is
§3.1 implemented. **Default** async psycopg3.

### D-3 · Migration mechanism

**Recommended** plain numbered SQL files applied by a tiny runner, starting from `0001_init.sql`.
**Reason** V1 already has `migrations/0001_init.sql` written in this style; the frozen schema is one
migration; and raw SQL is the only form in which `REVOKE UPDATE` and partial indexes are obviously
correct. **Alternatives** Alembic — rejected for now: autogeneration actively fights
revoke-based immutability. **Architecture impact** none. **Default** numbered SQL.

### D-4 · Object store adapter at T1

**Recommended** S3-compatible (`objects/s3.py`), with `objects/local.py` for T0 and tests.
**Reason** TD §16 states the trade: a persistent volume is acceptable **only** if genuinely
persistent, and choosing it forfeits signed URLs (§13.3) so the API proxies every PDF byte.
**Alternatives** volume-only — acceptable at T1 if §13.3 delivery is dropped; that is a product call.
**Architecture impact** none (it is a named T1 choice). **Default** S3-compatible.

### D-5 · FIFO provider-slot primitive

**Recommended** `asyncio.Semaphore` per provider. **Reason** CPython's implementation wakes waiters in
arrival order, which satisfies §8.6b's FIFO requirement without a queue. **Alternatives** an explicit
`asyncio.Queue` of tokens — adopt if a future runtime's semaphore is not FIFO. **Architecture impact**
none. **Default** `asyncio.Semaphore`, with a comment naming the FIFO dependency so it is checked if
the runtime changes.

### D-6 · How `builder_version` and `extractor_version` are computed

**Recommended** a content hash over the implementing module's source, exactly as
`engine/render.py:_template_version` hashes a template. **Reason** TD §5.8 names this as the
`CHOICE` and gives the reason: hand-bumped versions get forgotten, and this one is invisible when
wrong. **Alternatives** a hand-maintained constant — rejected by the design. **Architecture impact**
none. **Default** source content hash.

### D-7 · Test Postgres provisioning

**Recommended** a disposable container per test session, one schema per test module.
**Reason** `repo/`, `protocol/` and `concurrency/` tests assert real database semantics — TD §15.4's
suite is meaningless against a fake, which Phase 2's ordering note already establishes.
**Alternatives** a shared local instance — fine for a solo developer; flaky in CI.
**Architecture impact** none. **Default** container per session.

### D-8 · Domain type library

**Recommended** Pydantic v2 for `core/types` (discriminated unions for `Block`, `Literal` for closed
vocabularies, `model_validator` for the X1 guard). **Reason** the frozen design inherits V1's typed
contracts, several invariants are specified as *inexpressible* rather than *checked* (S6–S14), and
Pydantic is how V1 achieves that. **Alternatives** dataclasses + manual validation — more code, same
result. **Architecture impact** none. **Default** Pydantic v2.

### D-9 · Stub gateway for CI

**Recommended** replay recorded responses from `V2/runs/` behind the `ModelGateway` port.
**Reason** TD §15.7 specifies it and names the reason — CC6, *"free-tier reliability contaminates
every measurement."* **Alternatives** live calls in CI — rejected; it would make the invariant suite
dependent on a 50-request daily cap. **Architecture impact** none. **Default** replay.

### D-10 · `identity_fn` default for `on_result`

**Recommended** a module-level `def identity_fn(x): return x`. **Reason** TD §7.3 gives `on_result` a
default so most domains pass nothing; an explicit named function keeps the trace readable in logs.
**Alternatives** `None` + a branch — equivalent. **Architecture impact** none. **Default** named
function.

**Explicitly not decisions:** package names, file splits, formatter, type-checker settings, logger
choice, test naming. Those are coding choices and are settled by whoever writes the first module.

---

# 8. Test Strategy

Every critical invariant gets at least one named scenario. Tests named in TD §15 are the contract;
the groupings below add the scenarios the plan needs.

### 8.1 Unit — pure, no I/O

- **identity, both directions**: for each kind, each listed input changes the key; **each listed
  exclusion does not.** The exclusion half is what catches real bugs.
  Named: `structure` excludes `entry_point` and `project_id`; `memo` excludes `commitment_id`,
  siblings, `capacity`, `depth_register`; `document` excludes `commitment_id`; `frame` excludes
  `entry_point` and **includes** sources and purpose.
- canonical-JSON stability across key order, whitespace, NFC.
- `test_brief_hash_matches_renderer` — one struct, two consumers.
- state machines: `resumable(task)` over all states × failure classes.
- pure compute: one test per runtime invariant S1/S2/S2b/S3/S4/S5/S12.
- **inexpressibility** tests for S6–S14: constructing the violation must raise, not be detected.

### 8.2 Repository / DB — real Postgres

For every constraint in §5's inventory, a test that **attempts the violation and asserts refusal**.
Plus:
- append-only tables reject `UPDATE` and `DELETE` at the privilege level;
- the forbidden columns (§5.2) are absent from the information schema;
- `DependencyEdge(depends_on_id)` index exists — the `stale` query depends on it;
- `(document_id, capability_decl_version)` index exists — export's lookup depends on it;
- `ArtifactIndex` refuses a second row for one `(document_id, render_env_hash)`.

### 8.3 Protocol

`test_publish_is_atomic` · `test_fenced_publish_writes_nothing` ·
`test_version_row_never_without_edges` · `test_committed_is_write_once` ·
`test_claim_loss_costs_at_most_one_call` · `test_publish_adopts_an_existing_result` ·
`test_step_checks_for_an_existing_result_before_reserving` ·
`test_document_provenance_attaches_on_hit` · `test_document_claim_loss_rebuilds_provenance` ·
`test_no_workflow_restates_the_claim_branches` · `test_every_defined_operation_is_reachable` ·
`test_every_claiming_workflow_is_representable` · `test_every_claim_domain_is_handled`.

### 8.4 Concurrency — the suite that must never be skipped

`test_two_workers_one_envelope` (16 threads, one key → one call) ·
`test_fencing_rejects_slow_worker` (R2) · `test_takeover_race` (R5) ·
`test_heartbeat_detects_fencing` · `test_content_addressed_payload_prevents_overwrite` ·
`test_shared_claim_is_single_flight_across_projects` ·
`test_budget_is_enforced_under_concurrency` · `test_tenant_quota_is_enforced_at_admission` ·
`test_provider_cap_holds_across_both_origins` · `test_concurrent_appends_get_distinct_ord` ·
`test_late_old_extractor_cannot_regress_the_source` ·
`test_render_claim_prevents_duplicate_artifacts` · `test_completion_wins_tie_with_cancel`.

**Lease expiry is injected through the `Clock` port.** TD §15.4's `CHOICE` is explicit: sleeping makes
these slow and flaky, and they are the tests that must never be skipped.

### 8.5 Model Gateway

`test_429_is_retried` · `test_400_is_terminal` · `test_cold_quota_bucket_admits` ·
`test_provider_slot_is_released_on_failure` · `test_task_budget_exhaustion_is_distinguishable` ·
`test_failed_call_is_in_the_ledger` · `test_fenced_worker_call_is_still_accounted` ·
`test_lifetime_spend_is_derivable_without_a_resume` ·
`test_lifetime_spend_accumulates_across_resumes` · `test_windowed_quota_is_computable` ·
`test_wall_budget_counts_reservation_waiting` · `test_admitted_but_crashed_call_fails_safe` ·
`test_sync_intake_call_is_admitted_and_ledgered` · `test_sync_calls_count_toward_tenant_quota` ·
`test_turn_call_cap_bounds_one_turn` · `test_provider_boundary_is_mechanically_exclusive`.

### 8.6 Workflow

One per §9 flow, plus: `test_frame_reads_situation_readings` ·
`test_source_extraction_is_shared` · `test_infeasible_extraction_is_a_recorded_row` ·
`test_extractor_upgrade_invalidates_structure` ·
`test_extractor_upgrade_does_not_touch_sourceless_projects` ·
`test_second_project_reuses_shared_derivation` ·
`test_shared_derivation_does_not_leak_staleness` ·
`test_shared_derivation_survives_project_deletion` ·
`test_job_correction_stales_downstream_not_structure` · `test_prompt_bump_is_not_stale` ·
`test_ordering_is_sequence_not_wallclock` · `test_superseded_uses_sequence` ·
`test_stale_blocks_approval_when_integrity_is_clean` ·
`test_reapproval_after_template_edit_is_a_new_commitment` ·
`test_double_click_approve_is_one_commitment` · `test_approved_extent_survives_recalibration` ·
`test_generation_resume_costs_the_remainder` · `test_incomplete_writes_no_document` ·
`test_identical_content_is_one_document` · `test_derive_prompt_bump_yields_a_new_plan_task` ·
`test_source_change_yields_a_new_plan_task`.

### 8.7 Rendering

`test_honesty_table_enforced` · `test_realization_paired_in_source_order` ·
`test_unrendered_kind_reported` · `test_no_margin_argument` · `test_viewport_is_a4` ·
`test_no_network_at_render` · `test_one_artifact_per_document_environment` ·
`test_render_claim_loss_does_not_re_render`.
**Golden files compare page count, `scale` and extracted text — never pixels** (TD §15.6's `CHOICE`:
pixel diffs across Chromium builds are noise, and the environment is pinned anyway).

### 8.8 Export

`test_export_uses_commitment_documents` · `test_export_task_key_changes_with_artifact_set` ·
`test_export_refuses_when_a_module_is_unrendered` · `test_export_refuses_unsatisfiable_pin` ·
`test_export_reports_newer_plan_without_refusing` · `test_export_zip_is_byte_deterministic`
(two builds, different processes, hours apart) · `test_export_has_no_claim_row`.

### 8.9 Recovery

`test_crash_between_payload_and_commit` · `test_at_least_once_is_bounded` ·
`test_memo_gc_cannot_produce_a_false_hit` · `test_routing_gc_retires_its_claim` ·
`test_extraction_claim_loss_does_not_re_extract` · `test_unique_envelope_survives_claim_loss` ·
orphan sweep re-leases an abandoned Task · coordinator restart loses nothing committed ·
`test_cancel_keeps_committed_memos`.

### 8.10 End-to-end

`test_intake_to_artifact` — one module, stubbed gateway, real stores; **assert the provenance chain
walks back from the artifact to the originating `Utterance`** ·
`test_correction_reuses_structure` (structure call count is 0 on the re-plan) ·
`test_approval_refuses_then_repairs` · plus one full run: intake → plan → correct → approve →
generate → render → export, asserting the exported zip contains exactly what the commitment approved.

---

# 9. Definition of Done

Nothing counts because code exists. Each line names its **evidence**.

### Correctness
- [ ] every runtime invariant (S1–S5, S12) has a passing test; every construction-enforced invariant
      (S6–S11, S13, S14) has a test proving the violation is **inexpressible**
- [ ] the §15.2 identity suite passes in **both** directions for every kind
- [ ] `test_no_workflow_restates_the_claim_branches` passes — one claim path exists
- [ ] `test_every_claiming_workflow_is_representable` passes — every workflow has a domain, a key, a
      PUBLISH branch and a result row
- [ ] §15.8's grep suite passes: no stale identity formula, no duplicated protocol fact

### Functional
- [ ] each §9 workflow has a passing `workflow/` test
- [ ] the E2E run produces an artifact whose provenance walks back to an `Utterance`
- [ ] approval refuses on stale **and** on integrity, with `decisions_implicated` populated
- [ ] a disclosed-and-approved shortfall yields a `Reference`, never prose or a false figure

### Concurrency
- [ ] 16 workers on one envelope → exactly **one** model call, evidenced by the `CallLedger`
- [ ] R2's fencing timeline reproduced under an injected clock; loser's payload is an orphan
- [ ] budget 2 with 8 concurrent requests → exactly 2 admitted
- [ ] provider slots never exceeded with task and sync origins mixed
- [ ] the whole `concurrency/` suite runs with **no `sleep()`**

### Persistence
- [ ] every constraint in §5 proven by an attempted violation that was refused
- [ ] append-only tables reject `UPDATE`/`DELETE` by privilege
- [ ] forbidden columns absent from the information schema
- [ ] claim loss recovers with ≤ 1 model call, evidenced by the ledger
- [ ] GC leaves orphans, never a false HIT — proven for memo **and** routing

### Rendering
- [ ] honesty violations are refused at merge time
- [ ] one artifact per `(document, environment)`, enforced by the DB
- [ ] zero network requests during a render
- [ ] re-render after a template edit costs a render, not a generation

### Observability
- [ ] every derivation logs `{result_domain, result_identity, reused, reconciled, claim_epoch, fenced}`
- [ ] every model call has a `CallLedger` row, including failures and fenced workers
- [ ] *"why did this project cost N calls?"* answerable from the ledger alone
- [ ] *"is this still what I approved?"* answerable from `stale()` alone

### Performance
- [ ] planning and generation run off the request path; no sync op exceeds its §3.2 budget
- [ ] an intake turn meets the 30 s SLA on the target provider, **p95 recorded** — not one sample
- [ ] render slots sized by the measured formula on the **actual** instance (U3 closed with a number)
- [ ] concurrent generation benchmarked; the `~4–5×` claim is confirmed or replaced (U4 closed)

### Deployment
- [ ] T1 image with pinned fonts; `/health` answers from the rendering process
- [ ] CORS env-driven; access gate present and **not described as auth**
- [ ] migration applies to an empty database and is idempotent on re-run
- [ ] a restart loses no committed work; in-flight Tasks resume from their memos

---

# 10. First Coding Task

> ## `core/identity` — canonical JSON and the three key constructions
>
> **Scope.** `core/identity/canonical.py`, `envelope.py`, `task_key.py`, `claim_key.py`,
> `member.py`, `content.py`, `fingerprint.py` — plus `tests/test_boundaries.py` with the full
> `FORBIDDEN` table, and `tests/unit/test_identity.py` carrying the §15.2 golden table.

**Why this one.** It is the only module with **zero dependencies** — no database, no provider, no
browser, no types beyond the primitives it hashes. And everything else is addressed by it: the
schema's uniqueness constraints are over its outputs, the claim protocol keys on them, Tasks key on
them, GC units are identified by them. It is also where **U1 — the risk the design names as "the
first thing to get wrong"** — is either closed or not.

**Acceptance criteria, all from the frozen design:**

1. **Canonical JSON** (§5.1): UTF-8, keys sorted by code point, no insignificant whitespace, strings
   NFC-normalised, **integers only** — no floats. Arrays ordered where order is semantic, sorted
   where it is not, per the kind's spec.
2. **Three constructions, provably disjoint** (§5.1, §5.12, §5.12a): `envelope(kind, member, inputs,
   env)`, `task_key(kind, inputs)` with `"domain": "task"`, `claim_key(domain, identity)` with its
   `"domain"` discriminator. 128-bit output, `v: 1` in every payload.
3. **`member` is never null** (§5.11a): `""` is the root sentinel, in the key payload and later in the
   column. The encoding table is the single source.
4. **The golden suite** (§15.2), both directions, for every kind — and the **exclusion** half is the
   acceptance bar, not the inclusion half: `structure` must not change on `entry_point` or
   `project_id`; `memo` must not change on `commitment_id`, a sibling section, `capacity` or
   `depth_register`; `document` must not change on `commitment_id`; `frame` **must** change on
   sources and purpose and **must not** on `entry_point`.
5. **`test_three_key_constructions_are_disjoint`**: the same inputs through all three produce three
   different keys.
6. **The import wall exists and is enforced** (§15.8): `core` may import nothing but `core`. Verify by
   adding a deliberate `import httpx` to a `core` module, watching CI fail, and removing it.

**Explicitly out of scope:** any table, any flow, any provider call, `BriefInputs`' field list (it
needs `core/types`, which is the second task).

**Done when** the golden table is complete for every kind in §5.10's summary, the disjointness test
passes, and the boundary test fails on an injected violation.

---

**The second task, for sequencing only:** `core/types` — the domain models and closed vocabularies,
which `BriefInputs` and the §15.2 `memo` row depend on. The third is `0001_init.sql` with the full
constraint set. Do not start Phase 3 until Phase 2's constraint-violation tests pass, because the
claim protocol's correctness **is** those constraints.
