"""Provider selection.

Scaffolding, but the *ordering* encodes a finding worth protecting: our workload
is few requests with very large outputs, so request-capped tiers beat
token-per-minute-capped ones. Groq's free plan allows 8k tokens/minute, and a
single study document is ~15k tokens -- one call does not fit. OpenRouter's free
variants cap requests (20/min, 50/day) and not tokens, so the same free budget
buys ~50 documents a day instead of zero. That daily budget is account-wide
across every :free model, so exhausting it is not worked around by switching
slugs -- only by switching providers.

Gemini is last on a different axis: its free-tier terms allow training on
submitted content and human review of input and output.
"""

from __future__ import annotations

import pytest

from agent.providers import (
    AnthropicProvider,
    GeminiProvider,
    NoProviderConfigured,
    OpenAICompatibleProvider,
    select_provider,
)

ALL_KEYS = [
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "PROVIDER",
    "MODEL",
    "MAX_OUTPUT_TOKENS",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ALL_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_no_keys_names_every_option(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(NoProviderConfigured) as excinfo:
        select_provider()
    message = str(excinfo.value)
    for key in ("OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"):
        assert key in message
    # The error is where someone learns the tradeoff, so it has to state it.
    assert "8k tokens/minute" in message
    assert "human reviewers" in message


def test_openrouter_is_the_free_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    provider = select_provider()
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "openrouter"
    # The exact slug churns -- gpt-oss-120b:free was withdrawn from the free
    # tier within days of being chosen. Assert the shape, not the name.
    assert provider.model.endswith(":free")


def test_openrouter_beats_groq_when_both_are_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ordering finding: request caps beat token-per-minute caps for our shape."""
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert select_provider().name == "openrouter"



def test_the_rate_limit_message_points_at_the_way_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 429 on OpenRouter is account-wide across every :free model, so the
    message must say that switching slugs is not the fix -- that was the loop
    people actually got stuck in."""
    import httpx

    from agent import providers

    response = httpx.Response(429, text='{"error": {"code": 429}}')
    with pytest.raises(providers.ProviderRefused) as caught:
        providers._raise_for_status(response, "openrouter", "some/model:free")

    assert "switching slugs will not help" in str(caught.value)


def test_anthropic_wins_over_every_free_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    """The free tiers are scaffolding. A real key means we are done scaffolding."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    provider = select_provider()
    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-opus-5"


def test_gemini_is_last_resort(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert select_provider().name == "openrouter"

    monkeypatch.delenv("OPENROUTER_API_KEY")
    assert isinstance(select_provider(), GeminiProvider)


def test_google_api_key_also_selects_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    assert isinstance(select_provider(), GeminiProvider)


@pytest.mark.parametrize(
    "forced,key,expected",
    [
        ("groq", "GROQ_API_KEY", "groq"),
        ("cerebras", "CEREBRAS_API_KEY", "cerebras"),
        ("gemini", "GEMINI_API_KEY", "gemini"),
        ("openrouter", "OPENROUTER_API_KEY", "openrouter"),
    ],
)
def test_provider_override(
    monkeypatch: pytest.MonkeyPatch, forced: str, key: str, expected: str
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")  # would otherwise win
    monkeypatch.setenv(key, "x")
    monkeypatch.setenv("PROVIDER", forced)
    assert select_provider().name == expected


def test_forcing_a_provider_without_its_key_fails_loudly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setenv("PROVIDER", "anthropic")
    with pytest.raises(NoProviderConfigured):
        select_provider()


def test_model_override_applies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setenv("MODEL", "some/other-model:free")
    assert select_provider().model == "some/other-model:free"


def test_max_output_tokens_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Free variants may cap completions below our default; the knob has to exist
    before someone hits a truncation they cannot explain."""
    import importlib

    monkeypatch.setenv("MAX_OUTPUT_TOKENS", "8000")
    import agent.generate as generate

    importlib.reload(generate)
    try:
        assert generate.MAX_TOKENS == 8000
    finally:
        monkeypatch.delenv("MAX_OUTPUT_TOKENS")
        importlib.reload(generate)


def test_exhausted_retries_raise_a_catchable_type(monkeypatch) -> None:
    """The exhausted-retry path used to raise a bare `RuntimeError` — the one
    type nothing can catch without also catching genuine bugs. A provider outage
    therefore reached the user as a 500 with a stack trace, after minutes of
    silent retrying.
    """
    import httpx

    from agent import providers

    def always_fails(self, *args, **kwargs):
        raise httpx.ConnectError("upstream refused")

    monkeypatch.setattr(httpx.Client, "post", always_fails)
    monkeypatch.setattr(providers, "_TRANSIENT_BACKOFF", 0)

    provider = providers.OpenAICompatibleProvider(
        api_key="k", base_url="https://example.invalid", model="m", label="stub"
    )
    with pytest.raises(providers.ProviderUnavailable) as caught:
        provider.complete(system="s", user="u", schema={}, max_tokens=10)

    assert "after 3 attempts" in str(caught.value)
    assert "upstream refused" in str(caught.value)


def test_every_provider_failure_the_api_can_hit_is_caught() -> None:
    """`_guard` must name each one. A provider failure is not a server fault and
    must not surface as a traceback."""
    import inspect

    from backend import api

    source = inspect.getsource(api._guard)
    for exception in ("NoProviderConfigured", "ProviderUnavailable", "OutputTruncated"):
        assert exception in source, f"{exception} would escape as a 500"
