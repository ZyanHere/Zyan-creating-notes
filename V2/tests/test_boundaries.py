"""Package boundaries — Build-Plan §2.3, and the first thing written.

    client  ->  backend  ->  agent    ->  LLM (via backend.gateway ONLY)
                        ->  engine   ->  PDF
    core    <-  used by everything; imports nothing but itself

Four rules, none of them conventions:

  * `core` imports nothing but `core`. That is what makes "no dom function takes a
    port parameter" mechanical rather than reviewed -- a pure function cannot reach
    a store it cannot import.

  * `engine` may not import `core.types`. It renders a document-shaped MAPPING. That
    boundary is what lets a template fix cost a render (~3.4s) instead of a
    generation (~323s), and it is why `render_environment` can be captured in the
    engine at all.

  * only `backend.gateway` may import a provider SDK or an HTTP client. Every model
    invocation goes through MODEL_CALL. A second path to a provider is the defect
    the design spent a revision removing.

  * `agent` never touches persistence. If a decision needs a measurement from the
    engine, the backend takes it and passes it in as evidence.

Written now, when there are five packages to keep apart, rather than later when the
damage is already done. V1's own boundary test carries the same note, and it was
right.

The known limit, stated so nobody over-trusts this file: an import wall bounds what
the Python imports. It says nothing about what a SUBPROCESS does -- V1's engine test
passed while the browser it drove fetched webfonts. Chromium's network is handled by
pinning fonts, not here.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PACKAGES = ("core", "ports", "agent", "engine", "backend", "obs")

# A package may not import any of these, at any depth.
FORBIDDEN: dict[str, tuple[str, ...]] = {
    # Pure. No I/O, no infrastructure, no siblings. The whole point.
    #
    # `config` is on this list deliberately: a pure function that reads settings is not
    # pure. Settings are passed in as values, which is also what makes a dom function
    # testable without an environment.
    "core": (
        "psycopg", "sqlalchemy", "httpx", "requests", "socket", "urllib.request",
        "fastapi", "uvicorn", "playwright", "jinja2", "anthropic", "openai",
        "pydantic_settings", "config", "os", "pathlib",
        "agent", "engine", "backend", "ports", "obs",
    ),
    # Protocol definitions only. No implementations means no dependencies.
    "ports": (
        "psycopg", "httpx", "requests", "playwright", "jinja2", "anthropic", "openai",
        "pydantic_settings", "config",
        "agent", "engine", "backend",
    ),
    # Reasons about content. Never persists, never renders, never calls a provider
    # directly -- it asks the gateway.
    "agent": (
        "psycopg", "sqlalchemy", "playwright", "jinja2", "fastapi",
        "anthropic", "openai", "httpx", "requests", "socket",
        "engine", "backend.store", "backend.api", "backend.claim", "backend.work",
    ),
    # Renders a MAPPING. Not the domain's types, and no network of its own.
    "engine": (
        "httpx", "requests", "socket", "urllib.request", "psycopg", "sqlalchemy",
        "anthropic", "openai", "fastapi",
        "core.types", "core.policy", "core.compute", "core.document",
        "agent", "backend",
    ),
    # Coordinates. May import engine and agent -- that is its job. May not reason
    # about content, and may not reach a provider outside the gateway (below).
    "backend": ("anthropic", "openai"),
    # Observability records; it never participates.
    "obs": (
        "psycopg", "httpx", "playwright", "anthropic", "openai",
        "agent", "engine", "backend", "core",
    ),
}

# `backend` is allowed the bare `import engine` / `import agent` / `import core` --
# coordinating them is the point. What it may not do is reach a provider outside the
# one module that owns that boundary.
PROVIDER_SDKS = ("anthropic", "openai", "httpx", "requests")
ONLY_PROVIDER_PATH = "backend/gateway"


def _modules(package: str) -> list[Path]:
    root = ROOT / package
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _imported_names(tree: ast.AST) -> set[str]:
    """Every dotted name this module imports, at any depth."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # a relative import stays inside its own package
                continue
            if node.module:
                names.add(node.module)
    return names


def _violates(imported: str, forbidden: str) -> bool:
    """`forbidden` matches `imported` exactly, or as a dotted prefix."""
    return imported == forbidden or imported.startswith(forbidden + ".")


@pytest.mark.parametrize("package", PACKAGES)
def test_package_imports_nothing_forbidden(package: str) -> None:
    forbidden = FORBIDDEN[package]
    offences: list[str] = []

    for path in _modules(package):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _imported_names(tree):
            for bad in forbidden:
                if _violates(imported, bad):
                    offences.append(f"{path.relative_to(ROOT)} imports {imported!r}")

    assert not offences, (
        f"{package}/ broke its boundary:\n  " + "\n  ".join(sorted(offences))
    )


def test_only_the_gateway_reaches_a_provider() -> None:
    """Every model invocation goes through MODEL_CALL.

    Checked separately from FORBIDDEN because `backend` as a whole is allowed a lot;
    this is the one thing only ONE of its subpackages may do.
    """
    offences: list[str] = []

    for path in _modules("backend"):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(ONLY_PROVIDER_PATH):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _imported_names(tree):
            for sdk in PROVIDER_SDKS:
                if _violates(imported, sdk):
                    offences.append(f"{rel} imports {imported!r}")

    assert not offences, (
        "only backend/gateway may reach a provider:\n  " + "\n  ".join(sorted(offences))
    )


def test_core_is_importable_without_anything_else() -> None:
    """The strongest form of the purity rule: core must import standing alone.

    If this passes while the package is empty it proves nothing; it starts biting the
    moment core/identity exists, which is the next task.
    """
    import importlib

    importlib.import_module("core")


def test_every_package_exists() -> None:
    """The wall is only a wall if it covers the whole perimeter."""
    missing = [p for p in PACKAGES if not (ROOT / p).is_dir()]
    assert not missing, f"packages named in FORBIDDEN but absent: {missing}"
