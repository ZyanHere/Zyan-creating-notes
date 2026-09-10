"""Run the backend. Only the backend -- this process starts nothing else.

    cd backend
    python app.py                 the normal way

    python app.py --reload        restart on file changes (see the warning below)

It also works from the repo root as `python backend/app.py`, and behaves
identically either way: the working directory is set to the repo root before
anything runs, because `out/` is resolved relative to it.

The frontend is a separate process in a separate terminal, and stays that way:

    npm --prefix frontend run dev        then open http://localhost:3000

`agent/` and `engine/` are libraries this process imports. There is nothing else
to run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Python puts *this file's* directory on sys.path -- backend/ -- and not the
# repo root, so `import backend` fails outright when this is run as
# `python app.py` from in here. Fix the path before the first-party import.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# `out/` is relative to the working directory: backend/service.py has
# `OUT = Path("out")` and backend/store.py defaults to `Path("out/projects")`.
# Started from backend/ without this, the app would quietly create a second,
# empty out/ in here and come up with none of the existing projects.
os.chdir(ROOT)

# Loads .env before anything reads an API key. Importing `agent` directly does
# not do this, deliberately -- see backend/config.py.
from backend import config  # noqa: E402 - must follow the sys.path fix above

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

# A plan turn is one or two model calls and runs for minutes. Uvicorn's default
# of 5 seconds closes the connection underneath it, and the browser reports the
# result as "Failed to fetch" -- a network error for what was really a working
# server still thinking. This is not a tuning knob.
KEEP_ALIVE = int(os.environ.get("TIMEOUT_KEEP_ALIVE", "900"))


def _port_is_taken() -> bool:
    import socket

    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((HOST, PORT)) == 0


def _set_port(port: int) -> str:
    """The command to run on another port, in the shell actually in use."""
    if os.name == "nt":
        return f'$env:PORT="{port}"; python app.py'
    return f"PORT={port} python app.py"


def main() -> int:
    import uvicorn

    reload = "--reload" in sys.argv

    if _port_is_taken():
        # Uvicorn's own message for this is "only one usage of each socket
        # address is normally permitted", which is true and unhelpful.
        print(f"  Port {PORT} is already in use — the backend is probably running")
        print("  in another terminal. Stop it with Ctrl+C there, or:")
        print(f"      {_set_port(PORT + 1)}")
        return 1

    print(f"  backend running   http://{HOST}:{PORT}")

    if config.provider_is_configured():
        # Printed because "nothing happens when I click" has twice turned out to
        # be the model, and knowing which one is the first thing worth checking.
        from agent.providers import select_provider

        try:
            provider = select_provider()
            print(f"  model             {provider.name}/{provider.model}")
        except Exception as exc:  # noqa: BLE001 - never block startup on this
            print(f"  model             could not be resolved: {exc}")
    else:
        print("  model             NOT CONFIGURED — set OPENROUTER_API_KEY in .env")
        print("                    The app will start; every turn fails with a 503.")

    # Same reasoning as the model line: the failure it prevents surfaces at the
    # very end of a long generation, where it is most expensive to discover.
    # `import engine`, not `from engine.render import ...`: reaching into the
    # engine's internals is what tests/test_boundaries.py forbids the backend.
    import engine

    if install := engine.render.browser_ready():
        print("  renderer          NO BROWSER — PDFs cannot be written")
        print(f"                    Install it once:  {install}")
    else:
        print("  renderer          chromium ready")

    if reload:
        # --reload watches the repo and restarts on any save, which kills an
        # in-flight turn mid-call. Fine while editing; not while using the app.
        print("\n  --reload is on: saving a file will kill any turn in progress.")

    # Set apart from the lines above, which describe what *this* process is
    # doing. This one is an instruction for a second terminal -- when it was
    # formatted like the others it read as a second thing already running.
    print("\n  frontend is separate — in another terminal:")
    print("      npm --prefix frontend run dev        http://localhost:3000")

    print(flush=True)
    uvicorn.run(
        "backend.api:app",
        host=HOST,
        port=PORT,
        timeout_keep_alive=KEEP_ALIVE,
        reload=reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
