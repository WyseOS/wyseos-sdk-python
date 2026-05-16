from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scenarios import default_run_prefix, filter_scenarios  # type: ignore

if TYPE_CHECKING:
    from runner import ScenarioRunResult  # type: ignore


STATUSES = ("PASS", "FAIL", "ERROR", "TIMEOUT")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run X capability E2E scenarios.")
    parser.add_argument("--all", action="store_true", help="Run all scenarios.")
    parser.add_argument("--scenario", help="Run one scenario by id.")
    parser.add_argument("--environment", choices=("local", "remote"))
    parser.add_argument("--capability", choices=("extension", "api"))
    parser.add_argument("--task-type", choices=("reply", "publish", "interact"))
    return parser.parse_args()


def _summary(results: list[ScenarioRunResult]) -> dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    for result in results:
        if result.status in counts:
            counts[result.status] += 1
    return {
        "passed": counts["PASS"],
        "failed": counts["FAIL"],
        "errors": counts["ERROR"],
        "timeouts": counts["TIMEOUT"],
        "total": len(results),
    }


def _print_summary(summary: dict[str, int]) -> None:
    print(
        "Summary: "
        f"{summary['passed']} passed, "
        f"{summary['failed']} failed, "
        f"{summary['errors']} errors, "
        f"{summary['timeouts']} timeouts, "
        f"{summary['total']} total"
    )


def _write_report(
    path: Path,
    run_id: str,
    started_at: datetime,
    ended_at: datetime,
    results: list[ScenarioRunResult],
) -> None:
    report: dict[str, Any] = {
        "run_id": run_id,
        "started_at": _iso(started_at),
        "ended_at": _iso(ended_at),
        "summary": _summary(results),
        "results": [result.to_json() for result in results],
    }
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    args = _parse_args()
    has_filter = any((args.scenario, args.environment, args.capability, args.task_type))
    if args.all and has_filter:
        print("--all cannot be combined with other filters.", file=sys.stderr)
        return 2
    if not args.all and not has_filter:
        print("Specify --all or at least one filter.", file=sys.stderr)
        return 2

    base_dir = Path(__file__).resolve().parent
    scenarios = filter_scenarios(
        scenario_id=args.scenario,
        environment=args.environment,
        capability=args.capability,
        task_type=args.task_type,
    )
    if not scenarios:
        print("No scenarios matched.", file=sys.stderr)
        return 2

    from config import load_e2e_config  # type: ignore
    from runner import run_scenario  # type: ignore

    config = load_e2e_config(base_dir)
    result_dir = config.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    log_path = result_dir / "latest.log"
    json_path = result_dir / "latest.json"
    log_path.write_text("", encoding="utf-8")

    run_id = default_run_prefix()
    started_at = _now()
    results: list[ScenarioRunResult] = []

    try:
        for scenario in scenarios:
            print(f"Running {scenario.id}...")
            result = run_scenario(config, scenario, run_id, log_path)
            results.append(result)
            print(f"{result.status} {result.scenario_id}")
    except KeyboardInterrupt:
        print("Interrupted. Writing partial results.", file=sys.stderr)

    ended_at = _now()
    summary = _summary(results)
    _write_report(json_path, run_id, started_at, ended_at, results)
    _print_summary(summary)

    if results and all(result.status == "PASS" for result in results):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
