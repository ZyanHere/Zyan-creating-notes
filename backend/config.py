"""Application configuration.

The backend is the application boundary, so it owns configuration -- loading a
`.env` file is an application concern, not an agent one. The agent reads plain
environment variables and neither knows nor cares where they came from.

Imported for its side effect by the entry points (`cli.py`, `backend.api`).
Importing `agent` directly -- in a test, say -- deliberately does NOT load
`.env`, so tests cannot accidentally spend money by picking up a real key.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"

# `override=False`: a variable already exported in the shell wins over the file,
# so a one-off `ANTHROPIC_API_KEY=... python cli.py ...` does what it looks like.
load_dotenv(ENV_FILE, override=False)


def provider_is_configured() -> bool:
    return any(
        os.environ.get(name)
        for name in (
            "ANTHROPIC_API_KEY",
            "OPENROUTER_API_KEY",
            "GROQ_API_KEY",
            "CEREBRAS_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        )
    )
