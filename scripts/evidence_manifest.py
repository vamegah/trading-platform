import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_EVIDENCE = {
    "M9-01": ["provider_certification"],
    "M9-02": ["broker_certification"],
    "M9-03": ["model_validation"],
    "M9-06": ["persistent_controls_restore"],
    "M9-08": ["cloud_infrastructure_plan"],
    "M9-10": ["load_soak_test"],
    "M9-11": ["security_assessment"],
    "M9-12": ["dr_outage_drill"],
    "M9-13": ["legal_compliance_review"],
    "M9-14": ["paper_trading_validation"],
}


@dataclass(frozen=True)
class EvidenceResult:
    valid: bool
    missing: list[str]
    failing: list[str]
    accepted: list[str]


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"evidence": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(path: Path) -> EvidenceResult:
    manifest = load_manifest(path)
    evidence = manifest.get("evidence", {})
    missing: list[str] = []
    failing: list[str] = []
    accepted: list[str] = []
    for milestone, required_keys in REQUIRED_EVIDENCE.items():
        for key in required_keys:
            record = evidence.get(key)
            if not record:
                missing.append(f"{milestone}:{key}")
                continue
            required_metadata = (
                record.get("accepted") is True
                and bool(record.get("artifact_uri"))
                and bool(record.get("owner"))
                and bool(record.get("reviewed_at"))
                and bool(record.get("notes"))
            )
            if not required_metadata:
                failing.append(f"{milestone}:{key}")
                continue
            accepted.append(f"{milestone}:{key}")
    return EvidenceResult(valid=not missing and not failing, missing=missing, failing=failing, accepted=accepted)


def build_template() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "release": {
            "environment": "production",
            "candidate": "rc-YYYYMMDD",
            "live_trading_requested": False,
        },
        "evidence": {
            key: {
                "accepted": False,
                "artifact_uri": "",
                "owner": "",
                "reviewed_at": "",
                "notes": "",
            }
            for keys in REQUIRED_EVIDENCE.values()
            for key in keys
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate production release evidence manifest.")
    parser.add_argument("--manifest", default="release_evidence.json")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()

    if args.template:
        print(json.dumps(build_template(), indent=2, sort_keys=True))
        return

    result = validate_manifest(Path(args.manifest))
    print(
        json.dumps(
            {
                "valid": result.valid,
                "missing": result.missing,
                "failing": result.failing,
                "accepted": result.accepted,
            },
            indent=2,
            sort_keys=True,
        )
    )
    if args.fail_invalid and not result.valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
