"""Build Spec §2 -- package boundaries.

    frontend  ->  backend  ->  agent   ->  LLM
                          ->  engine  ->  PDF

Three rules, none of them conventions:

  * the backend never calls a model and never touches geometry -- it coordinates
  * the agent never touches persistence and never imports a sibling subsystem;
    if a decision needs a measurement from the engine, the backend takes it and
    passes it in as evidence
  * the engine imports no model SDK and makes no network call -- that purity is
    what makes golden-image testing possible at M7

Written at M1, when there are three packages to keep apart, rather than at M8
when the damage is already done.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN: dict[str, tuple[str, ...]] = {
    "backend": ("anthropic", "engine.render", "engine.measure", "jinja2", "playwright"),
    "agent": ("psycopg", "sqlalchemy", "fastapi", "engine", "backend.store", "backend.api"),
    "engine": ("anthropic", "httpx", "requests", "socket", "urllib.request", "agent"),
}

# The backend is allowed the bare `import engine` / `import agent` -- coordinating
# them is its job. What it may not do is reach into their internals or their
# dependencies.
ALLOWED_TOP_LEVEL = {"backend": {"engine", "agent"}}


def _modules(package: str) -> list[Path]:
    return sorted((ROOT / package).rglob("*.py"))


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _violates(imported: str, forbidden: str) -> bool:
    """`engine` forbids `engine.render` too; `engine_utils` is not `engine`."""
    return imported == forbidden or imported.startswith(forbidden + ".")


@pytest.mark.parametrize("package", sorted(FORBIDDEN))
def test_package_exists(package: str) -> None:
    assert (ROOT / package).is_dir(), f"{package}/ is missing from the project structure"


@pytest.mark.parametrize("package,forbidden", sorted(FORBIDDEN.items()))
def test_import_boundaries(package: str, forbidden: tuple[str, ...]) -> None:
    allowed = ALLOWED_TOP_LEVEL.get(package, set())
    violations: list[str] = []

    for path in _modules(package):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _imported_names(tree):
            if imported in allowed:
                continue
            for banned in forbidden:
                if _violates(imported, banned):
                    rel = path.relative_to(ROOT).as_posix()
                    violations.append(f"{rel} imports {imported!r} (forbidden: {banned!r})")

    assert not violations, (
        f"{package}/ breaks its boundary:\n  " + "\n  ".join(violations)
    )


def test_agent_does_not_import_a_sibling_subsystem() -> None:
    """Called out separately because it is the rule most likely to be broken for
    a good-sounding reason. layout_feasibility needs measurement from engine/;
    the answer is that the backend measures and passes the result in, not that
    the agent imports the engine."""
    for path in _modules("agent"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _imported_names(tree):
            assert not _violates(imported, "engine"), (
                f"{path.relative_to(ROOT).as_posix()} imports {imported!r}. "
                "The backend should take the measurement and pass it in as evidence."
            )


def test_engine_makes_no_network_call() -> None:
    """The engine's purity is what makes golden images reproducible at M7."""
    for path in _modules("engine"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for imported in _imported_names(tree):
            assert imported.split(".")[0] not in {"httpx", "requests", "urllib", "socket"}, (
                f"{path.relative_to(ROOT).as_posix()} imports {imported!r}"
            )
