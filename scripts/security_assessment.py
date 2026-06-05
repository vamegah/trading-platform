import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path


REQUIRED_CHECKS = {
    "sast": "bandit -r backend scripts -ll",
    "python_dependencies": "pip-audit -r requirements.txt",
    "frontend_dependencies": "npm audit --audit-level=high",
    "secrets": "detect-secrets scan --all-files",
    "containers": "trivy image trading-platform-backend:latest",
    "iac": "terraform validate && terraform plan",
    "api_penetration_test": "external DAST or penetration test report",
}


def build_assessment() -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "required_checks": REQUIRED_CHECKS,
        "release_policy": {
            "critical_findings_allowed": 0,
            "high_findings_allowed_without_risk_acceptance": 0,
            "risk_acceptance_requires": ["security_owner", "engineering_owner", "expiration_date"],
        },
        "passed": False,
        "notes": "This is the release evidence template. CI runs several checks, but final signoff requires uploaded scan results and remediation records.",
    }


def validate_assessment(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    checks = payload.get("checks", {})
    missing = []
    failing = []
    missing_artifacts = []
    for key in REQUIRED_CHECKS:
        if key not in checks:
            missing.append(key)
            continue
        value = checks[key]
        if value.get("passed") is not True:
            failing.append(key)
        if not value.get("artifact_uri"):
            missing_artifacts.append(key)
    findings = payload.get("findings", {})
    critical = int(findings.get("critical", 0))
    high = int(findings.get("high", 0))
    risk_acceptances = payload.get("risk_acceptances", [])
    risk_acceptance_required = high > 0
    risk_acceptance_valid = not risk_acceptance_required or (
        bool(risk_acceptances) and all(_valid_risk_acceptance(item) for item in risk_acceptances)
    )
    valid = (
        not missing
        and not failing
        and not missing_artifacts
        and critical == 0
        and risk_acceptance_valid
    )
    return {
        "valid": valid,
        "missing": missing,
        "failing": failing,
        "missing_artifacts": missing_artifacts,
        "critical_findings": critical,
        "high_findings": high,
        "risk_acceptance_required": risk_acceptance_required,
        "risk_acceptance_valid": risk_acceptance_valid,
    }


def _valid_risk_acceptance(item: dict[str, object]) -> bool:
    if not item.get("security_owner") or not item.get("engineering_owner") or not item.get("expiration_date"):
        return False
    try:
        expiration = date.fromisoformat(str(item["expiration_date"]))
    except ValueError:
        return False
    return expiration >= date.today()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or validate security assessment evidence.")
    parser.add_argument("--validate")
    parser.add_argument("--output", default="security-assessment-template.json")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()

    if args.validate:
        result = validate_assessment(Path(args.validate))
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.fail_invalid and not result["valid"]:
            raise SystemExit(1)
        return

    payload = json.dumps(build_assessment(), indent=2, sort_keys=True)
    Path(args.output).write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
