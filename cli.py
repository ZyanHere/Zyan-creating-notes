"""CLI client.

Plays the frontend's role until M4. Like the frontend, it talks to the backend
and never to the agent -- with `--direct` it calls the backend's service layer
in-process rather than over HTTP, which is still the backend, just without a
server running.

    python cli.py "teach me binary search for a beginner"
    python cli.py --http "teach me binary search for a beginner"
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    from backend import config  # loads .env before anything reads the env

    _ = config
    parser = argparse.ArgumentParser(description="Generate one study document.")
    parser.add_argument("request", help="What you want to learn, in your own words.")
    parser.add_argument(
        "--http",
        metavar="URL",
        nargs="?",
        const="http://127.0.0.1:8000",
        help="Go through a running backend instead of calling it in-process.",
    )
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument(
        "--template",
        help="Visual language to render in. Presentation only -- it cannot "
        "change what the document says.",
    )
    args = parser.parse_args(argv)

    started = time.monotonic()

    if args.http:
        import httpx

        response = httpx.post(
            f"{args.http.rstrip('/')}/generate",
            json={"request": args.request},
            timeout=900.0,
        )
        response.raise_for_status()
        payload = response.json()
        title, pdf = payload["title"], payload["pdf"]
        pages = payload["pages"]
        tokens_in, tokens_out = payload["input_tokens"], payload["output_tokens"]
        badge = f"{payload['provider']}/{payload['model']}"
        repairs = payload["repairs"]
        raw = payload["representation"]
        report = _Report(
            pairs=[tuple(pair) for pair in raw["pairs"]],
            undiagnosed=raw["undiagnosed"],
            unlisted=raw["unlisted"],
            unrendered=raw["unrendered"],
            scale=raw["scale"],
        )
    else:
        from backend import service

        result = service.generate(
            args.request, out_dir=args.out, template_id=args.template
        )
        title, pdf = result.title, str(result.pdf_path)
        pages = result.pages_estimate
        tokens_in, tokens_out = result.input_tokens, result.output_tokens
        badge = f"{result.provider}/{result.model}"
        repairs = result.repairs
        report = result.representation

    elapsed = time.monotonic() - started
    repaired = f" · {repairs} repair" if repairs else ""

    print(f"\n  {title}")
    print(f"  {pdf}   {pages} pages")
    print(
        f"  {badge} · {elapsed:.0f}s · "
        f"{tokens_in:,} in / {tokens_out:,} out{repaired}"
    )
    _print_representation(report)
    return 0


@dataclass(frozen=True, slots=True)
class _Report:
    """The --http path's mirror of the service's report, so both paths print
    the same thing."""

    pairs: list
    undiagnosed: int
    unlisted: list
    unrendered: list
    scale: float


def _print_representation(report) -> None:
    """What this run says about the vocabulary, not about the document.

    Printed on every run because a representation failure is invisible in the
    PDF: a block the template could not draw leaves no gap, and a document
    Chromium rescaled looks like a margin bug. Silence here is exactly what let
    three `chips` blocks disappear from a finished artifact.
    """
    counts: dict[tuple[str, str, str, str], int] = {}
    for pair in report.pairs:
        counts[tuple(pair)] = counts.get(tuple(pair), 0) + 1

    print("\n  representation")
    if counts:
        rows = []
        for (diagnosis, kind, relation, realization), n in sorted(counts.items()):
            claim = f"{kind}:{relation}" if relation else kind
            rows.append((diagnosis, claim, realization, n))
        w1 = max(len(r[0]) for r in rows)
        w2 = max(len(r[1]) for r in rows)
        for diagnosis, claim, realization, n in rows:
            # The model's claim, then the geometry the template answered with.
            via = f"  via {realization}" if realization else ""
            times = f" x{n}" if n > 1 else ""
            print(f"    {diagnosis:<{w1}}  ->  {claim:<{w2}}{via}{times}")
    else:
        print("    (no departures from prose)")

    flags = []
    if report.undiagnosed:
        flags.append(f"{report.undiagnosed} departure(s) with no diagnosis")
    for entry in report.unlisted:
        flags.append(f"OUTSIDE the taxonomy: {entry}")
    if report.unrendered:
        flags.append(f"NOT DRAWN by this template: {', '.join(report.unrendered)}")
    if report.scale < 1.0:
        flags.append(f"document rescaled to {report.scale:.0%} by overflow")

    for flag in flags:
        print(f"    ! {flag}")
    if not flags:
        print("    clean")
    print()


if __name__ == "__main__":
    sys.exit(main())
