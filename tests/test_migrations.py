"""Build Spec §3 -- migration ordering.

The ordering in 0001_init.sql is load-bearing: member <-> artifact_version is a
reference cycle broken only by the ALTER at step 9, and decision -> job is a
forward reference. Nothing in the file itself prevents someone reordering it
into "logical" order and breaking it. This test does.

Requires a scratch Postgres. Set DATABASE_URL, e.g.

    DATABASE_URL=postgresql://localhost/notes_scratch python -m pytest tests/test_migrations.py

Without it these skip -- deliberately visibly, so a green run on a machine with
no database is not mistaken for a verified migration.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg", reason="psycopg not installed")

DATABASE_URL = os.environ.get("DATABASE_URL")
MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "0001_init.sql"

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL not set; no scratch database available"
)


@pytest.fixture()
def scratch():
    """A schema created fresh per test and dropped after."""
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS scratch CASCADE")
        conn.execute("CREATE SCHEMA scratch")
        conn.execute("SET search_path TO scratch")
        yield conn
        conn.execute("DROP SCHEMA IF EXISTS scratch CASCADE")


def test_init_applies_to_empty_database(scratch):
    """The whole file, top to bottom, against nothing. This is the ordering test."""
    scratch.execute("SET search_path TO scratch")
    scratch.execute(MIGRATION.read_text(encoding="utf-8"))

    tables = {
        row[0]
        for row in scratch.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'scratch'"
        ).fetchall()
    }
    assert tables == {
        "project", "utterance", "member", "job", "decision", "dependency",
        "artifact_version", "commitment", "verification", "set_status",
    }


def test_cycle_breaker_constraint_exists(scratch):
    """Step 9. If someone folds this FK back into CREATE TABLE member, the
    migration stops applying and test_init_applies_to_empty_database fails --
    this test names why."""
    scratch.execute("SET search_path TO scratch")
    scratch.execute(MIGRATION.read_text(encoding="utf-8"))

    found = scratch.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = 'fk_member_current_artifact'"
    ).fetchone()
    assert found, "the member -> artifact_version cycle-breaker is missing"


def test_delivery_commitment_must_name_an_artifact(scratch):
    """CHECK delivery_names_an_artifact -- T9 identity depends on it."""
    scratch.execute("SET search_path TO scratch")
    scratch.execute(MIGRATION.read_text(encoding="utf-8"))

    scratch.execute(
        "INSERT INTO project (id, user_id, title, taxonomy_version) "
        "VALUES (gen_random_uuid(), gen_random_uuid(), 't', 'v1')"
    )
    pid = scratch.execute("SELECT id FROM project").fetchone()[0]

    with pytest.raises(psycopg.errors.CheckViolation):
        scratch.execute(
            "INSERT INTO commitment (id, project_id, kind, snapshot, decision_ids,"
            " decision_ids_hash, decision_environment)"
            " VALUES (gen_random_uuid(), %s, 'delivery', '{}', '{}', 'h', '{}')",
            (pid,),
        )
