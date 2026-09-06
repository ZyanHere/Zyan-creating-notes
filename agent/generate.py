"""M1: one request in, one Document out.

Deliberately a single model call. Splitting it into the decision taxonomy is M3;
doing that now would mean building the seams before we know the output is worth
building anything around.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from agent.contracts import Document
from agent.providers import Completion, Provider, select_provider

PROMPT_VERSION = "document_v2"
MAX_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "32000"))
_PROMPTS = Path(__file__).parent / "prompts"


@dataclass(frozen=True, slots=True)
class Generated:
    """A document plus what it cost to produce it.

    Cost is recorded from M1 because it can never be backfilled, and by M6 it is
    what makes a correction's price quotable before the user pays it.
    """

    document: Document
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    repairs: int = 0


@lru_cache(maxsize=8)
def _system_prompt(version: str) -> str:
    return (_PROMPTS / f"{version}.md").read_text(encoding="utf-8")


def generate_document(request: str, *, provider: Provider | None = None) -> Generated:
    """Produce one educational artifact from a learner's request, in their words."""
    provider = provider or select_provider()
    schema = Document.model_json_schema()
    system = _system_prompt(PROMPT_VERSION)

    completion = provider.complete(
        system=system, user=request, schema=schema, max_tokens=MAX_TOKENS
    )
    document, repairs, completion = _parse_or_repair(
        completion, provider=provider, system=system, request=request, schema=schema
    )

    return Generated(
        document=document,
        provider=completion.provider,
        model=completion.model,
        prompt_version=PROMPT_VERSION,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        repairs=repairs,
    )


def _parse_or_repair(
    completion: Completion,
    *,
    provider: Provider,
    system: str,
    request: str,
    schema: dict,
) -> tuple[Document, int, Completion]:
    """Validate; on failure, hand the model its own error once.

    Pydantic is the guarantee, not the provider. Native structured output makes
    the first attempt succeed more often; it does not change what is authoritative.
    """
    try:
        return Document.model_validate_json(_strip_fence(completion.text)), 0, completion
    except (ValidationError, ValueError) as first_error:
        repair_request = (
            f"{request}\n\n"
            "Your previous reply did not validate. Fix exactly this and reply "
            "with the corrected JSON object only:\n\n"
            f"{str(first_error)[:2000]}"
        )
        retry = provider.complete(
            system=system, user=repair_request, schema=schema, max_tokens=MAX_TOKENS
        )
        try:
            document = Document.model_validate_json(_strip_fence(retry.text))
        except (ValidationError, ValueError) as second_error:
            raise ValueError(
                f"{provider.name}/{provider.model} produced invalid output twice.\n"
                f"first:  {str(first_error)[:600]}\n"
                f"second: {str(second_error)[:600]}\n"
                f"head:   {retry.text[:300]!r}"
            ) from second_error

        merged = Completion(
            text=retry.text,
            input_tokens=completion.input_tokens + retry.input_tokens,
            output_tokens=completion.output_tokens + retry.output_tokens,
            model=retry.model,
            provider=retry.provider,
        )
        return document, 1, merged


def _strip_fence(text: str) -> str:
    """Some models wrap JSON in a markdown fence despite being told not to."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.split("\n", 1)[1] if "\n" in stripped else ""
    if body.rstrip().endswith("```"):
        body = body.rstrip()[: -len("```")]
    return body.strip()
