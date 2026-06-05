import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evidence_manifest import validate_manifest  # noqa: E402


M9_ROW = re.compile(r"\| (M9-\d+) \| (?P<task>.*?) \| .*? \| (?P<status>todo|doing|blocked|done) \|")


def parse_m9_tasks(tasks_path: Path = Path("TASKS.md")) -> list[dict[str, str]]:
    rows = []
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        match = M9_ROW.match(line)
        if match:
            rows.append(
                {
                    "id": match.group(1),
                    "task": match.group("task"),
                    "status": match.group("status"),
                }
            )
    return rows


def build_review(evidence_manifest: Path | None = None) -> dict[str, object]:
    tasks = parse_m9_tasks()
    open_tasks = [task for task in tasks if task["status"] != "done"]
    evidence = None
    if evidence_manifest:
        result = validate_manifest(evidence_manifest)
        evidence = {
            "manifest": str(evidence_manifest),
            "valid": result.valid,
            "missing": result.missing,
            "failing": result.failing,
            "accepted": result.accepted,
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "milestone": "M9",
        "total_tasks": len(tasks),
        "completed_tasks": len(tasks) - len(open_tasks),
        "open_tasks": open_tasks,
        "evidence": evidence,
        "release_candidate_approved": not open_tasks and (evidence is None or evidence["valid"]),
        "live_trading_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Review M9 release-candidate readiness.")
    parser.add_argument("--output")
    parser.add_argument("--evidence-manifest")
    parser.add_argument("--fail-open", action="store_true", help="Exit non-zero when M9 has open tasks.")
    args = parser.parse_args()

    review = build_review(Path(args.evidence_manifest) if args.evidence_manifest else None)
    payload = json.dumps(review, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    if args.fail_open and not review["release_candidate_approved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
