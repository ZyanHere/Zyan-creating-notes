"""Model providers.

TEMPORARY SCAFFOLDING. The product targets `claude-opus-5`; this module exists
so M1 can be exercised on a free tier before committing spend. It lives here
because swapping a model provider must touch `agent/` and nothing else -- the
backend, the engine and the contracts do not know a provider exists.

Two paths, deliberately:

  * Anthropic gets native structured output (`output_config.format`), which
    guarantees the response parses.
  * Everyone else gets the schema in the prompt plus JSON mode, and Pydantic
    does the guaranteeing. That sidesteps every difference between JSON Schema
    dialects -- $ref support, anyOf handling, additionalProperties -- which is
    exactly where portable structured output goes wrong.

Raw HTTP for the free providers rather than two more SDKs: this is scaffolding
with a delete date, and both APIs are a single JSON POST.

WHY OPENROUTER IS THE FREE DEFAULT (checked Sept 2026)
------------------------------------------------------
Our workload is *few requests, very large outputs* -- one document is roughly
3k in and 12-15k out. That shape makes per-minute token caps the binding
constraint, not request counts:

    Groq free / gpt-oss-120b   30 RPM, 1K RPD, 8K TPM, 200K TPD
                               -> a single ~15k-token call exceeds TPM outright,
                                  and TPD allows only ~13 documents/day
    OpenRouter :free variants  20 RPM, 50 RPD (1000 once $10 has ever been
                               purchased) -- request-based, no TPM
                               -> ~50 documents/day, free

So the request-capped provider beats the token-capped one for us, which is the
opposite of how these tiers are usually ranked.

The 50/day budget is account-wide across every :free variant, so exhausting it
is not worked around by switching to another free slug.

Gemini is deliberately last: Google's free-tier terms state that submitted
content is used to "provide, improve, and develop Google products and services"
and that "human reviewers may read, annotate, and process your API input and
output". The paid tier excludes both. Available, not default.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

TIMEOUT = httpx.Timeout(600.0, connect=15.0)


_TRANSIENT_ATTEMPTS = 3
_TRANSIENT_BACKOFF = 2.0  # seconds, multiplied by the attempt number


class _Transient(RuntimeError):
    """Worth another try: an upstream 5xx or a transport fault."""


class ProviderUnavailable(RuntimeError):
    """Every retry was spent and the upstream never answered usefully.

    Distinct from `_Transient`, which means *try again*: this one means we did,
    and stopped. It exists because the exhausted-retry path used to raise a bare
    `RuntimeError` -- the one exception type nothing can catch without also
    catching genuine bugs -- so a provider outage surfaced to the user as a 500
    with a stack trace, after eight minutes of silent retrying.
    """


class ProviderRefused(RuntimeError):
    """A 4xx: the request itself is wrong, and retrying changes nothing.

    A withdrawn model name, an exhausted rate limit, a bad key. Named for the
    same reason as `ProviderUnavailable` -- it was a bare `RuntimeError`, so a
    404 for a model that is simply no longer offered reached the user as a 500
    with a stack trace instead of the message that already says what to set.
    """


class NoProviderConfigured(RuntimeError):
    pass


class OutputTruncated(RuntimeError):
    """The model stopped because it hit a token ceiling.

    Raised explicitly because the alternative -- letting truncated JSON reach
    Pydantic -- produces an error about a missing bracket, which sends you
    looking in the wrong place entirely.
    """


@dataclass(frozen=True, slots=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str


class Provider(Protocol):
    name: str
    model: str

    def complete(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> Completion: ...


# ---------------------------------------------------------------------------
# Anthropic -- the real target
# ---------------------------------------------------------------------------


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("MODEL", "claude-opus-5")

    def complete(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> Completion:
        import anthropic

        client = anthropic.Anthropic(timeout=600.0)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": schema},
            },
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if response.stop_reason == "max_tokens":
            raise OutputTruncated(
                f"{self.name}/{self.model} hit max_tokens={max_tokens}. "
                "Raise MAX_OUTPUT_TOKENS or narrow the request."
            )
        text = next(b.text for b in response.content if b.type == "text")
        return Completion(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
            provider=self.name,
        )


# ---------------------------------------------------------------------------
# Free tiers -- scaffolding
# ---------------------------------------------------------------------------

_SCHEMA_INSTRUCTION = """
Reply with a single JSON object and nothing else. No prose before or after it,
no markdown fence. It must validate against this JSON Schema:

{schema}
""".strip()


class OpenAICompatibleProvider:
    """OpenRouter, Groq, Cerebras -- anything speaking /chat/completions."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        label: str,
        extra_headers: dict[str, str] | None = None,
        override: str | None = None,
    ) -> None:
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._extra = extra_headers or {}
        # An explicit override beats MODEL, which beats the provider default.
        # Reading the situation and designing a curriculum are different jobs
        # and do not need the same model.
        self.model = override or os.environ.get("MODEL", model)
        self.name = label

    def complete(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> Completion:
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system
                    + "\n\n"
                    + _SCHEMA_INSTRUCTION.format(schema=json.dumps(schema)),
                },
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self._key}", **self._extra}

        # Free-tier upstreams return 502 "temporarily overloaded" often enough
        # that a single attempt loses whole conversations. Retry only what is
        # safely retryable -- transport faults and upstream 5xx -- and never a
        # 4xx, which will fail identically.
        payload = None
        for attempt in range(_TRANSIENT_ATTEMPTS):
            try:
                with httpx.Client(timeout=TIMEOUT) as client:
                    response = client.post(
                        f"{self._base}/chat/completions", headers=headers, json=body
                    )
                _raise_for_status(response, self.name, self.model)
                payload = response.json()
                if "error" in payload and not payload.get("choices"):
                    raise _Transient(json.dumps(payload["error"])[:400])
                break
            except (_Transient, httpx.TransportError) as error:
                if attempt == _TRANSIENT_ATTEMPTS - 1:
                    raise ProviderUnavailable(
                        f"{self.name}/{self.model} did not answer after "
                        f"{_TRANSIENT_ATTEMPTS} attempts. Last error: {error}"
                    ) from error
                time.sleep(_TRANSIENT_BACKOFF * (attempt + 1))
        assert payload is not None

        choice = payload["choices"][0]
        if choice.get("finish_reason") == "length":
            raise OutputTruncated(
                f"{self.name}/{self.model} truncated at max_tokens={max_tokens}. "
                "This free variant may cap completions below that -- "
                "set MAX_OUTPUT_TOKENS lower, or narrow the request."
            )

        usage = payload.get("usage") or {}
        return Completion(
            text=choice["message"]["content"] or "",
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model=self.model,
            provider=self.name,
        )


class GeminiProvider:
    """Available, not default -- see the data-use note at the top of this module."""

    name = "gemini"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._key = api_key
        self.model = model or os.environ.get("MODEL", "gemini-2.5-flash")

    def complete(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> Completion:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        body = {
            "system_instruction": {
                "parts": [
                    {"text": system},
                    {"text": _SCHEMA_INSTRUCTION.format(schema=json.dumps(schema))},
                ]
            },
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": max_tokens,
            },
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, params={"key": self._key}, json=body)
        _raise_for_status(response, self.name, self.model)

        payload = response.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"gemini returned no candidates: {json.dumps(payload)[:400]}")

        candidate = candidates[0]
        if candidate.get("finishReason") == "MAX_TOKENS":
            raise OutputTruncated(
                f"gemini/{self.model} truncated at maxOutputTokens={max_tokens}."
            )
        parts = candidate.get("content", {}).get("parts") or []
        usage = payload.get("usageMetadata", {})
        return Completion(
            text="".join(part.get("text", "") for part in parts),
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            model=self.model,
            provider=self.name,
        )


def _raise_for_status(response: httpx.Response, provider: str, model: str) -> None:
    if response.is_success:
        return
    detail = response.text[:500]
    hint = ""
    if response.status_code in (400, 404) and "model" in detail.lower():
        hint = f"\n  Set MODEL=<name> if {model!r} is no longer offered on this tier."
    elif response.status_code == 429:
        # The daily budget is account-wide across every :free variant, so the
        # obvious move -- try a different free model -- fails identically, and a
        # message that does not say so sends you round the loop again.
        hint = (
            "\n  Rate limited. OpenRouter free variants allow 20/min and 50/day "
            "until $10 of credit has ever been purchased, and that daily budget is "
            "shared by every :free model on the account -- switching slugs will not "
            "help."
        )
    # 5xx is the upstream having a bad minute; 4xx will fail the same way again.
    error = _Transient if response.status_code >= 500 else ProviderRefused
    raise error(f"{provider} returned {response.status_code}: {detail}{hint}")


# ---------------------------------------------------------------------------
# selection
# ---------------------------------------------------------------------------

_OPENROUTER = (
    "https://openrouter.ai/api/v1",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter",
    {"HTTP-Referer": "https://github.com/notes-engine", "X-Title": "Notes Engine"},
)

_OPENAI_COMPATIBLE: dict[str, tuple[str, str, str, dict[str, str]]] = {
    "OPENROUTER_API_KEY": _OPENROUTER,
    "GROQ_API_KEY": (
        "https://api.groq.com/openai/v1",
        "openai/gpt-oss-120b",
        "groq",
        {},
    ),
    "CEREBRAS_API_KEY": ("https://api.cerebras.ai/v1", "gpt-oss-120b", "cerebras", {}),
}


def select_provider(model: str | None = None) -> Provider:
    """Anthropic if configured, then OpenRouter, then the rest.

    Override with PROVIDER=anthropic|openrouter|groq|cerebras|gemini
    and MODEL=<name>.

    `model` overrides both, for one call. Reading a request and asking the next
    question is a comprehension task; deriving a curriculum is a design task.
    They were served by the same very large model because nothing had ever
    asked for anything else, not because they need the same one.
    """
    forced = os.environ.get("PROVIDER", "").strip().lower()

    if forced in ("", "anthropic") and os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider(model)

    for env_name, (base, default, label, headers) in _OPENAI_COMPATIBLE.items():
        if forced not in ("", label):
            continue
        key = os.environ.get(env_name)
        if key:
            return OpenAICompatibleProvider(
                key, base, default, label, headers, override=model
            )

    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if forced in ("", "gemini") and gemini_key:
        return GeminiProvider(gemini_key, model)

    raise NoProviderConfigured(
        "No model provider configured. Set one of:\n"
        "  OPENROUTER_API_KEY  free default -- openrouter.ai/keys\n"
        "                      50 documents/day on gpt-oss-120b:free, no data-for-training\n"
        "  ANTHROPIC_API_KEY   the real target; ~40c for one document on claude-opus-5\n"
        "  GROQ_API_KEY        free, but 8k tokens/minute caps a single long generation\n"
        "  CEREBRAS_API_KEY    $5 one-time trial credit\n"
        "  GEMINI_API_KEY      free, but free-tier input/output is used for training\n"
        "                      and may be read by human reviewers\n"
        "\nOptionally PROVIDER=<name>, MODEL=<name>, MAX_OUTPUT_TOKENS=<n>."
    )
