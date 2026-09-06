-- Build Spec §3 -- initial schema.
--
-- ORDERING IS LOAD-BEARING. member <-> artifact_version is a reference cycle and
-- decision -> job is a forward reference, so this file cannot be reordered into
-- "logical" order. Step 9 is the cycle-breaker. test_migrations.py applies this
-- to a scratch database in CI, which is what stops the ordering from rotting.

BEGIN;

-- ===========================================================================
-- 1. types
-- ===========================================================================

CREATE TYPE decision_kind AS ENUM (
  'intake_strategy', 'interpret_situation', 'select_frame', 'ingest_sources',
  'derive_structure', 'relevance', 'traversal', 'consequence', 'scope',
  'partition', 'section', 'representation', 'draft', 'render_config',
  'layout_feasibility');

CREATE TYPE decision_status    AS ENUM ('candidate', 'committed');
CREATE TYPE decision_freshness AS ENUM ('current', 'stale');
CREATE TYPE commitment_kind    AS ENUM ('plan', 'demo', 'draft', 'layout', 'delivery');
CREATE TYPE dependency_kind    AS ENUM ('declared', 'recorded');
CREATE TYPE supersession_kind  AS ENUM ('revision', 'retraction');
CREATE TYPE verification_layer AS ENUM ('structural', 'model_judgment',
                                        'source_grounded', 'human');
CREATE TYPE verification_target AS ENUM ('decision', 'member');
CREATE TYPE set_completeness   AS ENUM ('complete', 'incomplete', 'blocked');
CREATE TYPE job_state AS ENUM ('queued', 'running', 'needs_input',
                               'blocked', 'done', 'failed', 'abandoned');

-- ===========================================================================
-- 2. project, utterance
-- ===========================================================================

CREATE TABLE project (
  id               uuid PRIMARY KEY,
  user_id          uuid NOT NULL,
  title            text NOT NULL,
  taxonomy_version text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- Testimony: append-only, never rewritten (Rev. 4 §4).
CREATE TABLE utterance (
  id         uuid PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES project,
  ord        int  NOT NULL,
  role       text NOT NULL,
  text       text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, ord)
);

-- ===========================================================================
-- 3. member -- WITHOUT the current_artifact_version_id FK (added at step 9)
-- ===========================================================================

CREATE TABLE member (
  id                  uuid PRIMARY KEY,
  project_id          uuid NOT NULL REFERENCES project,
  ord                 int  NOT NULL,          -- position in the set
  title               text NOT NULL,
  job                 text NOT NULL,          -- construct | orient | retrieve | look_up | procedure
  requires            uuid[] NOT NULL DEFAULT '{}',
  declared_exit       jsonb NOT NULL,
  actual_exit         jsonb NULL,
  entry_premise       jsonb NOT NULL,
  entry_premise_hash  text  NOT NULL,
  current_inputs_hash text  NULL,             -- invariant 5: CAS target
  current_artifact_version_id uuid NULL,      -- FK added at step 9
  state               text NOT NULL DEFAULT 'planned',
  UNIQUE (project_id, ord)
);

-- ===========================================================================
-- 4. job
-- ===========================================================================

CREATE TABLE job (
  id                 uuid PRIMARY KEY,
  project_id         uuid NOT NULL REFERENCES project,
  unit               text NOT NULL,
  member_id          uuid NULL REFERENCES member,
  state              job_state NOT NULL DEFAULT 'queued',
  input_decision_ids uuid[] NOT NULL DEFAULT '{}',  -- invariant 4
  attempts           int  NOT NULL DEFAULT 0,
  last_error         text,
  claimed_at         timestamptz,
  started_at         timestamptz,
  finished_at        timestamptz
);

-- ===========================================================================
-- 5. decision, dependency
-- ===========================================================================

CREATE TABLE decision (
  id             uuid PRIMARY KEY,
  project_id     uuid NOT NULL REFERENCES project,
  kind           decision_kind NOT NULL,
  status         decision_status    NOT NULL DEFAULT 'candidate',
  freshness      decision_freshness NOT NULL DEFAULT 'current',
  member_id      uuid NULL REFERENCES member,
  job_id         uuid NULL REFERENCES job,
  inputs_hash    text NOT NULL,
  output_hash    text NOT NULL,     -- feeds downstream envelopes
  model          text,
  prompt_version text,
  effort         text,
  params         jsonb,
  output         jsonb NOT NULL,    -- may be {"outcome":"not_applicable",...}
  rejected       jsonb,             -- considered and dropped, with reasons
  cost           jsonb,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE dependency (
  from_decision_id uuid NOT NULL REFERENCES decision,
  to_decision_id   uuid NOT NULL REFERENCES decision,
  kind             dependency_kind NOT NULL,
  PRIMARY KEY (from_decision_id, to_decision_id, kind)
);

-- ===========================================================================
-- 6. artifact_version
-- ===========================================================================

-- A member has MANY artifact versions; version_number is monotonic per member.
CREATE TABLE artifact_version (
  id                 uuid PRIMARY KEY,
  member_id          uuid NOT NULL REFERENCES member,
  version_number     int  NOT NULL,
  bytes_ref          text NULL,      -- nulled on removal; the row survives
  bytes_hash         text NOT NULL,  -- IDENTITY
  format             text NOT NULL,
  doc_model_hash     text NOT NULL,  -- explanation: what
  render_environment jsonb NOT NULL, -- explanation: how (invariant 10)
  decision_ids       uuid[] NOT NULL,
  pagination         jsonb NOT NULL, -- block_id -> page. Artifact-owned.
  stamp              text NOT NULL,  -- invariant 11
  superseded_by      uuid NULL REFERENCES artifact_version,
  supersession_kind  supersession_kind NULL,   -- invariant 13
  removed_at         timestamptz NULL,
  removal_reason     text NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (member_id, version_number)
);

-- ===========================================================================
-- 7. commitment
-- ===========================================================================

CREATE TABLE commitment (
  id                   uuid PRIMARY KEY,
  project_id           uuid NOT NULL REFERENCES project,
  kind                 commitment_kind NOT NULL,
  member_id            uuid NULL REFERENCES member,
  snapshot             jsonb NOT NULL,   -- self-describing; stands alone
  decision_ids         uuid[] NOT NULL,
  decision_ids_hash    text NOT NULL,
  artifact_version_id  uuid NULL REFERENCES artifact_version,  -- kind='delivery'
  decision_environment jsonb NOT NULL,   -- invariant 8
  approved_by          uuid NULL,
  approved_at          timestamptz NOT NULL DEFAULT now(),
  superseded_by        uuid NULL REFERENCES commitment,
  CONSTRAINT delivery_names_an_artifact CHECK (
    (kind = 'delivery') = (artifact_version_id IS NOT NULL))
);

-- ===========================================================================
-- 8. verification, set_status
-- ===========================================================================

CREATE TABLE verification (
  id                 uuid PRIMARY KEY,
  project_id         uuid NOT NULL REFERENCES project,
  layer              verification_layer  NOT NULL,
  target_kind        verification_target NOT NULL,
  target_id          uuid NOT NULL,
  covered            jsonb NOT NULL,
  entry_premise_hash text NULL,          -- invariant 7 / T8 trigger (b)
  freshness          decision_freshness NOT NULL DEFAULT 'current',
  findings           jsonb NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE set_status (                -- invariant 6
  project_id       uuid PRIMARY KEY REFERENCES project,
  completeness     set_completeness NOT NULL,
  blocking_members uuid[] NOT NULL DEFAULT '{}',
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- ===========================================================================
-- 9. cycle-breaker
-- ===========================================================================

ALTER TABLE member
  ADD CONSTRAINT fk_member_current_artifact
  FOREIGN KEY (current_artifact_version_id) REFERENCES artifact_version;

-- ===========================================================================
-- 10. indexes and triggers
-- ===========================================================================

-- INVARIANT 2: the memo key. A hit here replaces a model call.
-- The ::uuid cast is required: coalesce over a uuid column needs it.
CREATE UNIQUE INDEX decision_memo ON decision
  (project_id, kind,
   coalesce(member_id, '00000000-0000-0000-0000-000000000000'::uuid),
   inputs_hash);

-- INVARIANT 3 / correction routing: closure walks start from stale rows.
CREATE INDEX decision_stale ON decision (project_id, freshness)
  WHERE freshness = 'stale';

CREATE INDEX decision_member ON decision (member_id) WHERE member_id IS NOT NULL;

-- Closure direction for T7's recursive walk.
CREATE INDEX dependency_forward ON dependency (from_decision_id);

-- INVARIANT 1: re-committing an identical decision set is identity.
CREATE UNIQUE INDEX commitment_identity ON commitment
  (project_id, kind,
   coalesce(member_id, '00000000-0000-0000-0000-000000000000'::uuid),
   decision_ids_hash)
  WHERE kind <> 'delivery';

-- T9: delivery is identified by WHAT WAS DELIVERED, not by a decision set --
-- downloading the same version twice is one delivery.
CREATE UNIQUE INDEX commitment_delivery_identity
  ON commitment (artifact_version_id) WHERE kind = 'delivery';

CREATE INDEX job_claimable ON job (project_id, state) WHERE state = 'queued';
CREATE INDEX job_stuck     ON job (state, claimed_at) WHERE state = 'running';

CREATE INDEX verification_target_idx ON verification (target_kind, target_id);

-- INVARIANT 9: a delivered artifact can never be silently replaced.
-- Supersession, retraction and removal update OTHER columns and stay legal;
-- removal blanks bytes_ref and records a reason, but never deletes the row.
CREATE FUNCTION artifact_version_immutable() RETURNS trigger AS $$
BEGIN
  IF NEW.bytes_hash     IS DISTINCT FROM OLD.bytes_hash
  OR NEW.doc_model_hash IS DISTINCT FROM OLD.doc_model_hash
  OR NEW.pagination     IS DISTINCT FROM OLD.pagination
  OR NEW.stamp          IS DISTINCT FROM OLD.stamp
  OR NEW.member_id      IS DISTINCT FROM OLD.member_id
  OR NEW.version_number IS DISTINCT FROM OLD.version_number THEN
    RAISE EXCEPTION 'artifact_version content is immutable (invariant 9)';
  END IF;
  -- bytes_ref may only be cleared (removal), never repointed.
  IF NEW.bytes_ref IS DISTINCT FROM OLD.bytes_ref AND NEW.bytes_ref IS NOT NULL THEN
    RAISE EXCEPTION 'artifact_version bytes_ref may be cleared, not repointed (invariant 9)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_artifact_version_immutable
  BEFORE UPDATE ON artifact_version
  FOR EACH ROW EXECUTE FUNCTION artifact_version_immutable();

COMMIT;
