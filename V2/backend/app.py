"""Run the backend. Only the backend.

The frontend is a separate process in a separate terminal -- that boundary is the one
deployment decision V1 got right, because the browser calls the backend directly and
no serverless timeout enters the path.

    cd V2
    python -m backend.app
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Both of these must follow the sys.path insert above, which is the whole reason this
# file can be run as a script and not only as a module.
from backend.api.health import health  # noqa: E402
from config import settings  # noqa: E402


def _port_in_use(host: str, port: int) -> bool:
    """Uvicorn's own message for this is 'only one usage of each socket address is
    normally permitted', which is true and unhelpful."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _alternative_port_command(port: int) -> str:
    if os.name == "nt":
        return f'$env:PORT="{port}"; python -m backend.app'
    return f"PORT={port} python -m backend.app"


def _banner() -> None:
    status = health()
    renderer = status["renderer"]
    database = status["database"]
    base = f"http://{settings.server.host}:{settings.server.port}"

    print()
    print(f"  backend running   {base}")
    print(
        f"  model             {status['model']}"
        f"{'' if status['provider_configured'] else '   (NO API KEY SET)'}"
    )
    print(f"  renderer          {renderer['state']} - {renderer['detail']}")
    print(f"  database          {database['state']} - {database['detail']}")
    print()
    print("  frontend is separate - in another terminal:")
    print("      npm --prefix client run dev          http://localhost:3000")
    print()


def main() -> int:
    host, port = settings.server.host, settings.server.port

    if _port_in_use(host, port):
        print(f"\n  port {port} is already in use on {host}.")
        print(f"  either stop what is using it, or:   {_alternative_port_command(port + 1)}\n")
        return 1

    _banner()

    try:
        import uvicorn  # noqa: PLC0415  -- deferred on purpose: see the fallback below
    except ImportError:
        print("  uvicorn is not installed yet - the ASGI app arrives with M1.")
        print("  the skeleton is importable and /health is a function you can call:\n")
        print("     ", json.dumps(health(), indent=2).replace("\n", "\n      "))
        print()
        return 0

    # find_spec, not an import: we never want the symbol, only the answer to "does the
    # module exist yet". uvicorn is handed the string below and does its own importing,
    # so importing it here would have been a probe wearing an import's clothes -- and a
    # probe that a type checker is right to reject, because at M0 the module genuinely
    # is not there.
    if importlib.util.find_spec("backend.api.asgi") is None:
        print("  no ASGI app yet - backend/api/asgi.py arrives with M1.\n")
        return 0

    uvicorn.run(
        "backend.api.asgi:app",
        host=host,
        port=port,
        # A plan turn is minutes long. Not a tuning knob — see config.Server.
        timeout_keep_alive=settings.server.timeout_keep_alive,
        reload=os.environ.get("RELOAD") == "1",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
