"""Command line entry point: JSON in, PDF out."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .merge import TemplateGap, merge
from .render import render
from .schema import load


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="document-engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="render a document model to PDF")
    r.add_argument("fixture", type=Path)
    r.add_argument("--template", default="study-notes")
    r.add_argument("--theme", default="indigo-light")
    r.add_argument("--out", type=Path, default=None)
    r.add_argument("--html", action="store_true", help="write HTML instead of PDF")

    s = sub.add_parser("schema", help="print the Document Model JSON Schema")

    args = ap.parse_args(argv)

    if args.cmd == "schema":
        from .schema import json_schema

        print(json.dumps(json_schema(), indent=2))
        return 0

    try:
        doc = load(json.loads(args.fixture.read_text(encoding="utf-8")))
    except ValidationError as e:
        print(f"invalid document model: {args.fixture}\n{e}", file=sys.stderr)
        return 2

    try:
        if args.html:
            out = args.out or Path("out") / (args.fixture.stem + ".html")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(merge(doc, args.template, args.theme), encoding="utf-8")
        else:
            out = args.out or Path("out") / (args.fixture.stem + ".pdf")
            render(doc, args.template, args.theme, out=out)
    except TemplateGap as e:
        print(f"template gap: {e}", file=sys.stderr)
        return 3

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
