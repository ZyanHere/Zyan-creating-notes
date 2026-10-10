"""Drive the frozen V1 across the corpus and record what it did.

    python -m harness.run --stub                   prove the plumbing, no model calls
    python -m harness.run --cases agentic-ai-interview
    python -m harness.run --trials 3               the whole corpus, three times
    python -m harness.run --phase generate         also write module PDFs

One JSON record per trial, written the moment the trial ends. A run that dies on
a rate limit at case 7 keeps cases 1-6; rerunning skips what already has a record
unless `--force`. On a 50-requests-a-day budget that is not a convenience.

V1 IS NOT MODIFIED. It is imported, handed an explicit store directory and an
explicit output directory, and driven through the same calls `backend/api.py`
makes -- including the intake-vs-correction routing, so what is measured is the
path the product actually takes.
"""

from __future__ import annotations

import argparse
import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from harness import baseline, observe
from harness.providers import Counting, Stub

HERE = Path(__file__).resolve().parent.parent
CORPUS = HERE / "corpus" / "cases.json"
RUNS = HERE / "runs"

# A crash barrier on the scripted intake loop, not a policy. V1 has its own
# MAX_INTAKE_ROUNDS; this only stops the harness looping if that ever fails.
MAX_TURNS = 8


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_cases(only: list[str] | None) -> list[dict]:
    cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
    if not only:
        return cases
    chosen = [c for c in cases if c["id"] in only]
    missing = set(only) - {c["id"] for c in chosen}
    if missing:
        raise SystemExit(f"no such case(s): {', '.join(sorted(missing))}")
    return chosen


def say(service, view, text: str):
    """One utterance, routed exactly as `backend/api.py::add_utterance` routes it.

    Before a plan exists an utterance is an intake answer; after one exists it is
    a correction. Mirrored rather than chosen by the harness, so the baseline
    measures the product's own routing.
    """
    if view.state in ("asking", "needs_subject", "ready"):
        return service.answer(view.project_id, text)
    return service.correct(view.project_id, text)


def run_trial(case: dict, trial: int, *, run_dir: Path, stub: bool, phase: str) -> dict:
    baseline.attach()
    from agent import curriculum  # noqa: PLC0415 - after attach()
    from agent.providers import select_provider
    from backend import service as v1_service
    from backend.planning import PlanService
    from backend.store import FileStore

    started = time.monotonic()
    provider = Stub(subject=case["title"]) if stub else Counting(select_provider())
    record: dict = {
        "case_id": case["id"],
        "case_title": case["title"],
        "trial": trial,
        "phase": phase,
        "stub": stub,
        "started_at": _now(),
        "request": case["request"],
        "baseline": baseline.fingerprint(),
        "provider": {"name": provider.name, "model": provider.model},
        "stages": [],
        "failure": None,
    }
    stage_seconds: dict[str, float] = {}

    def stage(name: str) -> None:
        record["stages"].append(name)
        stage_seconds[name] = time.monotonic()

    def close(name: str) -> None:
        stage_seconds[name] = round(time.monotonic() - stage_seconds[name], 2)

    store = FileStore(run_dir / "store" / f"{case['id']}-t{trial}")
    service = PlanService(store, provider=provider)

    try:
        stage("create")
        view = service.create(case["request"])
        close("create")
        record["project_id"] = view.project_id
        record["after_create"] = observe.intake(view.to_json())

        # --- intake -------------------------------------------------------
        stage("intake")
        answers = list(case.get("intake_answers") or [])
        turns = 0
        while view.state in ("asking", "needs_subject") and answers and turns < MAX_TURNS:
            view = say(service, view, answers.pop(0))
            turns += 1
        record["intake_turns"] = turns
        record["intake_answers_unused"] = len(answers)
        record["intake"] = observe.intake(view.to_json())
        close("intake")

        # --- plan ---------------------------------------------------------
        stage("plan")
        view = service.proceed(view.project_id)
        close("plan")
        record["plan"] = observe.plan_view(view.to_json(), slugify=v1_service.slugify)

        # --- corrections --------------------------------------------------
        corrections = list(case.get("corrections") or [])
        if corrections:
            stage("correct")
            record["corrections"] = []
            for said in corrections:
                view = say(service, view, said)
                record["corrections"].append(observe.correction(view.to_json(), said))
            close("correct")
            record["plan_after_corrections"] = observe.plan_view(
                view.to_json(), slugify=v1_service.slugify
            )

        # --- approval -----------------------------------------------------
        stage("approve")
        try:
            commitment = service.approve(view.project_id)
            snapshot = commitment.snapshot
            record["approval"] = {
                "approved": True,
                "decision_count": len(commitment.decision_ids),
                "refused_because": None,
            }
        except Exception as exc:  # noqa: BLE001 - recorded, never interpreted
            snapshot = None
            record["approval"] = {
                "approved": False,
                "decision_count": 0,
                "refused_because": f"{type(exc).__name__}: {exc}",
            }
        close("approve")

        # --- generation ---------------------------------------------------
        wanted = case.get("generate_modules") or []
        if phase == "generate" and wanted and snapshot is not None:
            stage("generate")
            record["generation"] = []
            out_dir = run_dir / "artifacts" / case["id"] / f"t{trial}"
            available = {m.index: m for m in curriculum.modules(snapshot)}
            for index in wanted:
                module = available.get(index)
                if module is None:
                    record["generation"].append(
                        {"index": index, "error": f"no module {index} in this plan"}
                    )
                    continue
                try:
                    scoped = curriculum.plan_for(snapshot, index)
                    result = v1_service.generate(
                        case["request"], out_dir=out_dir, plan=scoped
                    )
                    record["generation"].append(
                        observe.generation(module.title, index, result)
                    )
                except Exception as exc:  # noqa: BLE001
                    record["generation"].append(
                        {
                            "index": index,
                            "module": module.title,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
            close("generate")

    except Exception as exc:  # noqa: BLE001 - one trial must not cost the run
        record["failure"] = {
            "stage": record["stages"][-1] if record["stages"] else "setup",
            "type": type(exc).__name__,
            "message": str(exc)[:2000],
            "traceback": traceback.format_exc()[-4000:],
        }

    record["finished_at"] = _now()
    record["seconds_total"] = round(time.monotonic() - started, 2)
    record["seconds_by_stage"] = {
        k: v for k, v in stage_seconds.items() if isinstance(v, float) and v < 1e6
    }
    record["cost"] = provider.totals()
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure the frozen V1.")
    parser.add_argument("--cases", nargs="*", help="case ids; default all")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--phase", choices=("plan", "generate"), default="plan",
                        help="'plan' stops at approval. 'generate' also writes PDFs.")
    parser.add_argument("--run", help="run directory name; default a timestamp")
    parser.add_argument("--stub", action="store_true",
                        help="no model calls. Proves the harness, not V1.")
    parser.add_argument("--force", action="store_true",
                        help="redo trials that already have a record")
    args = parser.parse_args(argv)

    root = baseline.attach()
    cases = load_cases(args.cases)
    run_dir = RUNS / (args.run or ("stub" if args.stub else datetime.now().strftime("%Y%m%d-%H%M%S")))
    (run_dir / "records").mkdir(parents=True, exist_ok=True)

    fingerprint = baseline.fingerprint()
    frozen = fingerprint["matches_baseline"]
    print(f"  V1        {root}")
    print(f"  source    {fingerprint['source_hash'][:12]} "
          f"({fingerprint['source_files']} files) "
          + {True: "matches the frozen baseline",
             False: "*** DOES NOT MATCH THE BASELINE ***",
             None: "(baseline hash not pinned)"}[frozen])
    if not args.stub:
        print(f"  model     {baseline.provider_fingerprint()}")
    print(f"  run       {run_dir}")
    print(f"  cases     {len(cases)} x {args.trials} trial(s), phase={args.phase}\n")

    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "started_at": _now(),
                "baseline": fingerprint,
                "provider": None if args.stub else baseline.provider_fingerprint(),
                "phase": args.phase,
                "trials": args.trials,
                "stub": args.stub,
                "cases": [c["id"] for c in cases],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    done = skipped = failed = 0
    for case in cases:
        for trial in range(1, args.trials + 1):
            path = run_dir / "records" / f"{case['id']}-t{trial}.json"
            if path.exists() and not args.force:
                # Resume skips MEASUREMENTS, not gaps. A trial that died on a
                # spent rate limit wrote a record saying so, and skipping it
                # tomorrow would freeze the budget's failures into the baseline.
                try:
                    previous = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    previous = {"failure": {"type": "unreadable record"}}
                if not previous.get("failure"):
                    print(f"  - {case['id']} t{trial}  (already recorded)")
                    skipped += 1
                    continue
                print(f"  ~ {case['id']} t{trial}  (retrying: previous run "
                      f"failed at {previous['failure'].get('stage', '?')})")
            print(f"  > {case['id']} t{trial}", flush=True)
            record = run_trial(
                case, trial, run_dir=run_dir, stub=args.stub, phase=args.phase
            )
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            if record["failure"]:
                failed += 1
                print(f"    FAILED at {record['failure']['stage']}: "
                      f"{record['failure']['type']}: {record['failure']['message'][:160]}")
            else:
                plan = record.get("plan", {})
                part = plan.get("partition", {})
                print(f"    {record['seconds_total']}s  "
                      f"{record['cost']['model_calls']} calls  "
                      f"{part.get('module_count', '?')} modules  "
                      f"{plan.get('scope', {}).get('covered_count', '?')} concepts")
                done += 1

    print(f"\n  {done} recorded, {skipped} skipped, {failed} failed -> {run_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
