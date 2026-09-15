"""Persistence for the plan gate.

Rows, not objects. Every row here mirrors a table in `migrations/0001_init.sql`
column for column, so the Postgres implementation is a mechanical port rather
than a redesign — and so the thing this milestone proves (decisions are records
that a correction targets individually) is proved against the real shape.

Four tables are used: `project`, `utterance`, `decision`, `commitment`. The rest
of the schema exists and is untouched.

FileStore is the local implementation. It is not a database: no concurrency, no
transactions, no indexes. It is here because `psycopg` is not installed and
nothing about this milestone's question needs a server running. PostgresStore is
the next step, and `Store` is the seam that keeps it from touching anything else.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _id() -> str:
    return str(uuid.uuid4())


def inputs_hash(*parts: Any) -> str:
    """INVARIANT 2's memo key. Written from the start because it cannot be
    backfilled; nothing reads it yet — memoised re-derivation is not this
    milestone."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


@dataclass
class Project:
    id: str
    user_id: str
    title: str
    taxonomy_version: str = "plan-gate-1"
    created_at: str = field(default_factory=_now)


@dataclass
class Utterance:
    """Testimony: append-only, ordered. The transcript, and the correction history."""

    id: str
    project_id: str
    ord: int
    role: str
    text: str
    created_at: str = field(default_factory=_now)


@dataclass
class Decision:
    id: str
    project_id: str
    kind: str
    status: str  # candidate | committed
    freshness: str  # current | stale
    inputs_hash: str
    output: dict
    model: str | None = None
    prompt_version: str | None = None
    cost: dict | None = None
    created_at: str = field(default_factory=_now)


@dataclass
class Commitment:
    id: str
    project_id: str
    kind: str
    snapshot: dict
    decision_ids: list[str]
    decision_ids_hash: str
    decision_environment: dict
    approved_by: str | None
    approved_at: str = field(default_factory=_now)


def commit_hash(decision_ids: list[str]) -> str:
    """Re-committing an identical set is identity, not a second commitment.

    System Design §5 invariant 1: this is stronger than an idempotency key,
    because it holds across retries, clients and users.
    """
    return hashlib.sha256("|".join(sorted(decision_ids)).encode()).hexdigest()[:32]


class Store(Protocol):
    def create_project(self, user_id: str, title: str) -> Project: ...
    def get_project(self, project_id: str) -> Project | None: ...
    def add_utterance(self, project_id: str, role: str, text: str) -> Utterance: ...
    def utterances(self, project_id: str) -> list[Utterance]: ...
    def put_decision(self, decision: Decision) -> Decision: ...
    def current_decisions(self, project_id: str) -> dict[str, Decision]: ...
    def add_commitment(self, commitment: Commitment) -> Commitment: ...
    def commitment_by_hash(self, project_id: str, hash_: str) -> Commitment | None: ...
    def commitments(self, project_id: str) -> list[Commitment]: ...


class FileStore:
    """One JSON file per project, holding all four tables."""

    def __init__(self, root: Path | str = Path("out/projects")) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- io -----------------------------------------------------------------

    def _path(self, project_id: str) -> Path:
        return self.root / f"{project_id}.json"

    def _read(self, project_id: str) -> dict:
        path = self._path(project_id)
        if not path.exists():
            raise KeyError(project_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, project_id: str, data: dict) -> None:
        self._path(project_id).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- project ------------------------------------------------------------

    def create_project(self, user_id: str, title: str) -> Project:
        project = Project(id=_id(), user_id=user_id, title=title)
        self._write(
            project.id,
            {"project": vars(project), "utterance": [], "decision": [], "commitment": []},
        )
        return project

    def get_project(self, project_id: str) -> Project | None:
        try:
            return Project(**self._read(project_id)["project"])
        except (KeyError, ValueError):
            return None

    def projects(self) -> list[Project]:
        out = []
        for path in self.root.glob("*.json"):
            try:
                out.append(Project(**json.loads(path.read_text(encoding="utf-8"))["project"]))
            except (KeyError, ValueError):
                continue
        return sorted(out, key=lambda p: p.created_at, reverse=True)

    # -- utterance ----------------------------------------------------------

    def add_utterance(self, project_id: str, role: str, text: str) -> Utterance:
        data = self._read(project_id)
        utterance = Utterance(
            id=_id(), project_id=project_id, ord=len(data["utterance"]), role=role, text=text
        )
        data["utterance"].append(vars(utterance))
        self._write(project_id, data)
        return utterance

    def utterances(self, project_id: str) -> list[Utterance]:
        return [Utterance(**row) for row in self._read(project_id)["utterance"]]

    # -- decision -----------------------------------------------------------

    def put_decision(self, decision: Decision) -> Decision:
        """Append. Superseding a kind is a new row, not an update -- the old row
        is what a later correction would have to re-derive from."""
        data = self._read(decision.project_id)
        data["decision"].append(vars(decision))
        self._write(decision.project_id, data)
        return decision

    def current_decisions(self, project_id: str) -> dict[str, Decision]:
        """The latest row per kind. The plan the user sees is a projection of these."""
        current: dict[str, Decision] = {}
        for row in self._read(project_id)["decision"]:
            current[row["kind"]] = Decision(**row)
        return current

    def decision_history(self, project_id: str) -> list[Decision]:
        return [Decision(**row) for row in self._read(project_id)["decision"]]

    # -- commitment ---------------------------------------------------------

    def add_commitment(self, commitment: Commitment) -> Commitment:
        data = self._read(commitment.project_id)
        data["commitment"].append(vars(commitment))
        self._write(commitment.project_id, data)
        return commitment

    def commitment_by_hash(self, project_id: str, hash_: str) -> Commitment | None:
        for row in self._read(project_id)["commitment"]:
            if row["decision_ids_hash"] == hash_:
                return Commitment(**row)
        return None

    def commitments(self, project_id: str) -> list[Commitment]:
        return [Commitment(**row) for row in self._read(project_id)["commitment"]]
