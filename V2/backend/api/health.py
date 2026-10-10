"""/health -- answered by THIS process.

V1's lesson, and it cost three rounds of diagnosis: a check run in a terminal proves
nothing about a server started from somewhere else. A sandbox with a redirected
%LOCALAPPDATA% reported a complete browser install while the backend correctly
reported it missing.

So every probe here runs in-process, and the response says which process answered.
"""

from __future__ import annotations

import os
from typing import Any

from config import settings


def renderer_status() -> dict[str, Any]:
    """Whether this process could render right now.

    A stub until the engine exists (M5). It reports `unknown` rather than `ok`,
    because the one thing this endpoint must never do is claim a capability it has not
    checked.
    """
    try:
        from engine.capability import version
    except ImportError:
        return {"state": "not_built", "detail": "engine arrives with M5"}
    probe = getattr(version, "browser_status", None)
    if probe is None:
        return {"state": "not_built", "detail": "engine arrives with M5"}
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
