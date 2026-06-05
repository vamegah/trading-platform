import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_APPROVALS = [
    "customer_disclosures",
    "suitability_policy",
    "privacy_policy",
    "audit_retention_policy",
    "live_trading_terms",
    "adviser_broker_dealer_position",
    "jurisdiction_restrictions",
    "marketing_claims_review",
]
REQUIRED_APPROVAL_METADATA = ("approver", "reviewed_at", "artifact_uri", "notes")


def build_template(output: str | None = None) -> dict[str, object]:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "approvals": {
            key: {
                "approved": False,
                "approver": "",
                "reviewed_at": "",
                "artifact_uri": "",
                "notes": "",
            }
            for key in REQUIRED_APPROVALS
        },
        "live_trading_approved": False,
    }
    if output:
        Path(output).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def validate(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    approvals = payload.get("approvals", {})
    missing = [key for key in REQUIRED_APPROVALS if key not in approvals]
    unapproved = [key for key in REQUIRED_APPROVALS if not approvals.get(key, {}).get("approved")]
    missing_metadata = [
        f"{key}:{metadata_key}"
        for key in REQUIRED_APPROVALS
        for metadata_key in REQUIRED_APPROVAL_METADATA
        if key in approvals and approvals[key].get("approved") is True and not approvals[key].get(metadata_key)
    ]
    valid = (
        not missing
        and not unapproved
        and not missing_metadata
        and payload.get("live_trading_approved") is True
    )
    return {
        "valid": valid,
        "missing": missing,
        "unapproved": unapproved,
        "missing_metadata": missing_metadata,
        "live_trading_approved": payload.get("live_trading_approved") is True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or validate legal/compliance approval evidence.")
    parser.add_argument("--output")
    parser.add_argument("--validate")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()

    result = validate(Path(args.validate)) if args.validate else build_template(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.fail_invalid and result.get("valid") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
