import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_PROVIDERS = ["polygon", "alpha_vantage", "news", "social", "crypto_onchain", "options_chain", "futures_curve"]
REQUIRED_PROVIDER_CHECKS = (
    "contract_confirmed",
    "credentials_stored",
    "sandbox_test_passed",
    "sla_documented",
    "data_rights_approved",
    "failover_tested",
)


def build_template(output: str | None = None) -> dict[str, object]:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "providers": {
            provider: {
                "contract_confirmed": False,
                "credentials_stored": False,
                "sandbox_test_passed": False,
                "sla_documented": False,
                "data_rights_approved": False,
                "failover_tested": False,
                "artifact_uri": "",
            }
            for provider in REQUIRED_PROVIDERS
        },
        "accepted": False,
    }
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def validate(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    providers = report.get("providers", {})
    missing = [provider for provider in REQUIRED_PROVIDERS if provider not in providers]
    failing = []
    for provider in REQUIRED_PROVIDERS:
        if provider not in providers:
            continue
        checks = providers[provider]
        for key in REQUIRED_PROVIDER_CHECKS:
            if checks.get(key) is not True:
                failing.append(f"{provider}:{key}")
        if not checks.get("artifact_uri"):
            failing.append(f"{provider}:artifact_uri")
    accepted = not missing and not failing and report.get("accepted") is True
    return {"valid": accepted, "missing": missing, "failing": failing, "accepted": report.get("accepted") is True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or validate provider certification evidence.")
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
