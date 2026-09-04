"""Model access, via OpenRouter.

OpenRouter speaks the OpenAI API, so one client reaches any model by changing a
string. Nothing else in the agent knows which provider is in use.

Deliberately not using the provider's JSON-schema mode: free models mostly do
not support it, and relying on it would make the pipeline silently
provider-specific. The agent validates what comes back and retries — see
fill.py — which works everywhere and is the honest test of whether a model can
hold to a schema.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# The .env sits next to this package. Load it by absolute path: dotenv's own
# discovery walks up from the working directory, so `python -m agent` from the
# repo root would never look inside agent/ and the key would read as missing.
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()  # a repo-root .env may still override for other tooling

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
# Which models are free changes without notice — llama-3.3-70b:free went paid.
# List today's with: GET https://openrouter.ai/api/v1/models, id ends ":free".
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


class MissingKey(RuntimeError):
    pass


@dataclass
class Client:
    """A thin wrapper: one call, plain text in and out."""

    model: str
    _openai: OpenAI

    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        response = self._openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


def make_client(model: str | None = None) -> Client:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key or key == "your_api_key_here":
        raise MissingKey(
            "OPENROUTER_API_KEY is not set. Copy agent/.env.example to agent/.env "
            "and add a key from https://openrouter.ai/keys"
        )
    return Client(
        model=model or os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL,
        _openai=OpenAI(
            api_key=key,
            base_url=os.getenv("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL,
        ),
    )


def have_key() -> bool:
    key = os.getenv("OPENROUTER_API_KEY")
    return bool(key) and key != "your_api_key_here"
