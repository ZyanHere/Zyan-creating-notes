"""Locate the frozen V1, import it read-only, and record exactly which V1 it is.

The harness measures a *specific* V1. A run whose record does not say which V1 it
measured is not a baseline -- it is an anecdote. `fingerprint()` is therefore
written into every trial record, and its `matches_baseline` field is a hash of
V1's own source: if someone applies the parked orphan-gate patch and runs this,
every record says so rather than quietly becoming the new baseline.

A content hash rather than `git status`, because V1 and V2 now share one working
tree -- a dirty tree says nothing about whether V1 itself moved.

Nothing here writes to V1. V1 is put on `sys.path` and read.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

# V1 lives beside V2 inside the one repository. Both are working-tree paths, so
# `git status` is NOT a freeze check any more: the move itself shows as 104
# deletions against HEAD while V1's content is untouched. What matters is
# whether V1's SOURCE is the source we froze, so that is what is hashed below.
DEFAULT_V1 = Path(__file__).resolve().parents[2] / "V1"

# Directories whose contents decide what V1 does. Prompts live under `agent/`
# and templates under `engine/`, so both are covered by the walk.
SOURCE_DIRS = ("agent", "backend", "engine")
SOURCE_FILES = ("pyproject.toml", "cli.py", "plan_cli.py")

# The frozen prototype, verified byte-identical (modulo line endings) to commit
# 1c8a1d7 at the moment the baseline was declared. A run whose hash differs is
# measuring something else and says so in every record it writes.
BASELINE_SOURCE_HASH = "807c8ec99a60d320e745e8ac208b8c7f690ebd273b3930f6680688d159cda116"


def v1_root() -> Path:
    return Path(os.environ.get("V1_ROOT", DEFAULT_V1)).resolve()


@lru_cache(maxsize=1)
def attach() -> Path:
    """Put V1 on the import path. Idempotent.

    Deliberately not `pip install -e`: an explicit path means the record can name
    the directory it measured, and two checkouts of V1 can be compared by setting
    V1_ROOT rather than by reinstalling.
    """
    root = v1_root()
    if not (root / "agent").is_dir():
        raise SystemExit(
            f"No V1 at {root}.\n"
            "Set V1_ROOT to the frozen prototype's repository root."
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Load V1's `.env`, the way V1's own entry points do (`cli.py`,
    # `backend/app.py` both import this first). `agent` deliberately does NOT
    # load it -- that is V1's guard against a test picking up a real key -- so
    # without this `select_provider()` sees no key and the run header reports
    # "no provider configured" while the trials underneath run fine on the key
    # that `backend.service` loaded later. The records then disagree with
    # themselves about which model produced them.
    import backend.config  # noqa: F401, PLC0415 - imported for its side effect

    return root


def _git(*args: str) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(v1_root()), *args],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return done.stdout.strip()
    except Exception:  # noqa: BLE001 - a missing git is not a reason to fail a run
        return ""


def _source_files() -> list[Path]:
    root = v1_root()
    found: list[Path] = []
    for name in SOURCE_DIRS:
        found += [
            p
            for p in (root / name).rglob("*")
            if p.is_file()
            and "__pycache__" not in p.parts
            and p.suffix not in (".pyc", ".pyo")
        ]
    found += [root / name for name in SOURCE_FILES if (root / name).is_file()]
    return sorted(found)


def source_hash() -> tuple[str, int]:
    """Content hash of V1's source. Line endings normalised.

    Normalised because moving the tree on Windows rewrote 35 files from LF to
    CRLF without changing a character of what they say. A freeze check that
    reported those as tampering would be noise, and a noisy guard is one nobody
    reads.
    """
    root = v1_root()
    digest = hashlib.sha256()
    files = _source_files()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest(), len(files)


def fingerprint() -> dict:
    """Which V1 this run measured. Written into every trial record.

    `matches_baseline` is the freeze guard. It is a content comparison, not a
    `git status`: V1 and V2 now share one working tree, so a dirty tree says
    nothing about whether V1 itself moved.
    """
    digest, count = source_hash()
    return {
        "repo": str(v1_root()),
        "commit": _git("rev-parse", "HEAD"),
        "subject": _git("log", "-1", "--pretty=%s"),
        "source_hash": digest,
        "source_files": count,
        "matches_baseline": (
            None if BASELINE_SOURCE_HASH == "UNPINNED" else digest == BASELINE_SOURCE_HASH
        ),
    }


def provider_fingerprint() -> dict:
    """Which model answered. Recorded because V1's own register says provider
    variance was repeatedly mistaken for planner behaviour."""
    attach()
    from agent.providers import select_provider  # noqa: PLC0415 - after attach()

    try:
        provider = select_provider()
        planning = {"provider": provider.name, "model": provider.model}
    except Exception as exc:  # noqa: BLE001
        planning = {"provider": None, "model": None, "error": str(exc)}

    return planning | {
        "interpret_model": os.environ.get("INTERPRET_MODEL") or None,
        "max_output_tokens": os.environ.get("MAX_OUTPUT_TOKENS", "32000"),
    }
