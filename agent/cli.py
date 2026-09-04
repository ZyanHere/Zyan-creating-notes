"""python -m agent fill <plan.json> [--out doc.json] [--pdf out.pdf]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .client import MissingKey, make_client
from .fill import FillError, fill
from .models import load_plan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agent")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fill", help="write the content of a plan's blocks")
    f.add_argument("plan", type=Path)
    f.add_argument("--model", default=None)
    f.add_argument("--out", type=Path, default=None, help="document model JSON")
    f.add_argument("--pdf", type=Path, default=None, help="also render a PDF")
    f.add_argument("--theme", default="indigo-light")

    args = ap.parse_args(argv)
    plan = load_plan(json.loads(args.plan.read_text(encoding="utf-8")))

    try:
        client = make_client(args.model)
    except MissingKey as e:
        print(e, file=sys.stderr)
        return 2

    try:
        result = fill(plan, client)
    except FillError as e:
        print(f"fill failed: {e}", file=sys.stderr)
        return 3

    out = args.out or Path("out") / (args.plan.stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.document.model_dump_json(indent=2, exclude_none=True),
                   encoding="utf-8")
    print(f"{out}   (model {client.model}, {result.attempts} attempt(s))")

    for f_ in result.findings:
        print(f"  finding  section {f_.section + 1} block {f_.block}: "
              f"{f_.kind} — {f_.detail}")

    if args.pdf:
        from engine import render
        render(result.document, theme=args.theme, out=args.pdf)
        print(args.pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
