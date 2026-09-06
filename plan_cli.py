"""The plan conversation, without a browser.

    python plan_cli.py "teach me human evolution for NEET"
    python plan_cli.py --script turns.txt "teach me human evolution for NEET"
    python plan_cli.py --resume <project-id>

A harness over the same `PlanService` the HTTP API uses, so the loop can be
exercised without the frontend running. `--script` feeds one line per turn from a
file instead of the keyboard; it is the same code path.

Stops at approval. Nothing is rendered, no template is chosen, no PDF exists.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

# The Windows console defaults to cp1252 and cannot encode the rules below. A
# UnicodeEncodeError while *printing* would discard a plan that cost two model
# calls, so replace unencodable characters instead of raising.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

BAR = "─" * 74


def _wrap(text: str, indent: str = "    ") -> str:
    return textwrap.fill(str(text), width=74, initial_indent=indent, subsequent_indent=indent)


def show(view) -> None:
    d = view.decisions
    s = d.get("interpret_situation", {})
    print(f"\n{BAR}\n  PLAN — {s.get('subject', view.title)}\n{BAR}")

    print("\n  READ AS")
    for k, v in (("job", s.get("job")), ("for", s.get("purpose")),
                 ("assumes", s.get("entry_point")), ("after", s.get("target_capability"))):
        print(f"    {k:<9} {v}")
    if s.get("capacity"):
        print(f"    {'capacity':<9} {s['capacity']}")

    if s.get("stated"):
        print("\n  YOU SAID")
        for c in s["stated"]:
            print(f"    · {c}")

    # Semantics §3: silence is the system's decision, so what it decided has to
    # be as visible as what the user said. Never collapsed, never a footnote.
    if s.get("inferred"):
        print("\n  WE DECIDED (you didn't say)")
        for i in s["inferred"]:
            print(f"    · {i}")

    covered = d.get("scope", {}).get("covered", [])
    print(f"\n  COVERS ({len(covered)})")
    for c in covered:
        print(f"    · {c['concept']}  [{c['depth']}]")
        print(_wrap(c["why"], "        "))
    if d.get("scope", {}).get("cut"):
        print(f"    cut for capacity: {', '.join(d['scope']['cut'])}")

    exclusions = d.get("consequence", {}).get("exclusions", [])
    if exclusions:
        print(f"\n  DELIBERATELY NOT ({len(exclusions)})")
        for e in exclusions:
            print(f"    · {e['topic']}")
            print(_wrap(f"without it: {e['consequence']}", "        "))
            print(_wrap(f"learn it: {e['when_to_learn']}", "        "))

    units = {u["heading"]: u for u in d.get("partition", {}).get("units", [])}
    order = d.get("traversal", {}).get("sequence", list(units))
    print(f"\n  UNITS ({len(units)})")
    for n, heading in enumerate(order, 1):
        unit = units.get(heading, {"why_here": ""})
        print(f"    {n}. {heading}")
        print(_wrap(unit.get("why_here", ""), "        "))

    if d.get("traversal", {}).get("why"):
        print("\n  ORDER")
        print(_wrap(d["traversal"]["why"]))

    print("\n  EXTENT")
    print(_wrap(view.extent))

    questions = view.questions
    if questions:
        print(f"\n  OPEN — {len(questions)} question(s) where the answer changes the plan")
        for q in questions:
            print(f"\n    ? {q['question']}")
            print(_wrap(f"matters because: {q['why_it_matters']}", "      "))
            print(_wrap(f"otherwise I'll assume: {q['default_if_unanswered']}", "      "))


def show_turn(turn: dict | None) -> None:
    if not turn:
        return
    print(f"\n{BAR}")
    print(_wrap(f"read as: {turn['reading']}", "  "))
    if turn["out_of_scope"]:
        print(_wrap(f"not a plan decision: {turn['out_of_scope']}", "  "))
    if turn["not_understood"]:
        print("  ! that didn't land anywhere — try saying it differently")
    print(f"  changed:   {', '.join(turn['actual']) or '(nothing)'}")
    print(f"  unchanged: {', '.join(turn['unchanged'])}")
    # Reported, never repaired.
    if turn["unclaimed_drift"]:
        print(f"  ! moved without being routed to: {', '.join(turn['unclaimed_drift'])}")
    if turn["claimed_but_unchanged"]:
        print(f"  ! routed to but unchanged: {', '.join(turn['claimed_but_unchanged'])}")


def main(argv: list[str] | None = None) -> int:
    from backend import config  # loads .env

    _ = config
    parser = argparse.ArgumentParser(description="Agree a plan before anything is built.")
    parser.add_argument("request", nargs="?", help="What you want, in your own words.")
    parser.add_argument("--resume", help="Continue an existing project by id.")
    parser.add_argument("--script", type=Path, help="One turn per line, instead of the keyboard.")
    args = parser.parse_args(argv)

    from backend.planning import PlanService

    service = PlanService()
    turns: list[str] = []
    if args.script:
        turns = [
            line.strip()
            for line in args.script.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

    if args.resume:
        view = service.view(args.resume)
    elif args.request:
        print("\n  reading what you asked for…")
        view = service.create(args.request)
    else:
        parser.error("give a request, or --resume <project-id>")

    print(f"\n  project {view.project_id}")

    while True:
        show(view)
        print(f"\n{BAR}")
        print("  Type a correction, or 'approve'. Answering a question is a correction.")

        if turns:
            reply = turns.pop(0)
            print(f"  > {reply}")
        elif args.script:
            print("  > (script exhausted; not approved)")
            return 1
        else:
            try:
                reply = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n  stopped. resume with --resume {view.project_id}\n")
                return 1

        if not reply:
            continue
        if reply.lower() in {"approve", "approved", "ok", "yes"}:
            break

        print("\n  revising…")
        try:
            view = service.correct(view.project_id, reply)
        except Exception as error:
            # Every turn is already persisted, so a provider 502 costs this turn
            # and not the conversation. One of them discarded a whole session
            # during development, which is why this is here.
            print(f"\n  that turn failed: {error}")
            print(f"  nothing was lost; resume with --resume {view.project_id}\n")
            if args.script:
                return 1
            continue
        show_turn(view.to_json()["last_turn"])

    commitment = service.approve(view.project_id)
    print(f"\n{BAR}\n  APPROVED\n{BAR}")
    print(f"  commitment {commitment.id}")
    print(f"  {len(commitment.decision_ids)} decisions committed")
    print(f"  {commitment.snapshot['extent']}")
    print("\n  The demo stage would come next. It does not exist yet.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
