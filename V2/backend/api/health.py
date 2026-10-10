"""/health -- answered by THIS process.

V1's lesson, and it cost three rounds of diagnosis: a check run in a terminal proves
nothing about a server started from somewhere else. A sandbox with a redirected
%LOCALAPPDATA% reported a complete browser install while the backend correctly
reported it missing.

So every probe here runs in-process, and the response says which process answered.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from typing import Any

from config import settings


def renderer_status() -> dict[str, Any]:
    """Whether this process could render right now.

    A stub until the engine exists (M5). It reports `not_built` rather than `ok`,
    because the one thing this endpoint must never do is claim a capability it has not
    checked.

    Resolved dynamically rather than with a `try: from engine.capability import version`.
    The getattr guard below already made this probe dynamic; doing the lookup half
    statically only bought an error from the type checker, which is correct that at M0
    the module is not there. One mechanism, honestly named.
    """
    absent = {"state": "not_built", "detail": "engine arrives with M5"}
    if importlib.util.find_spec("engine.capability.version") is None:
        return absent
    probe = getattr(importlib.import_module("engine.capability.version"), "browser_status", None)
    if probe is None:
        return absent
    return probe()


def database_status() -> dict[str, Any]:
    """Whether this process can reach the database.

    A stub until the pool exists (M1). Same rule: no optimistic defaults.
    """
    return {"state": "not_built", "detail": "pool arrives with M1"}


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "env": settings.env,
        "pid": os.getpid(),
        "model": settings.provider.model_id,
        "provider_configured": settings.provider_configured,
        "renderer": renderer_status(),
        "database": database_status(),
    }
