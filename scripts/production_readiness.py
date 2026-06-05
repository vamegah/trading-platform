import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.shared.config import Settings  # noqa: E402


OPEN_BLOCKERS = {
    "vendor_integrations": [
        "market data provider contracts and sandbox credentials",
        "broker sandbox certification and live account approval",
        "model registry connected to trained production artifacts",
    ],
    "infrastructure": [
        "cloud backend credentials",
        "KMS or Vault-backed secret manager",
        "persistent audit and privacy restore drill",
    ],
    "governance": [
        "security assessment remediation",
        "legal and regulatory approval",
        "extended paper-trading review",
    ],
}


def _default_env_file(environment: str) -> Path:
    normalized = environment.lower()
    if normalized in {"prod", "production"}:
        return Path("config/prod.env")
    return Path(f"config/{normalized}.env")


def build_report(environment: str, env_file: Path | None = None) -> dict[str, object]:
    runtime_env_file = env_file or _default_env_file(environment)
    settings = Settings(
        _env_file=runtime_env_file if runtime_env_file.exists() else ".env",
        environment=environment,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "env_file": str(runtime_env_file),
        "runtime_validation": {
            "production": settings.is_production,
            "issues": settings.production_readiness_issues(),
        },
        "required_evidence": {
            "tests": "pytest -q",
            "frontend_build": "npm run build",
            "python_compile": "python -m compileall backend scripts migrations",
            "migration_forward_backward": "pytest -q backend/tests/integration/test_m9_migrations.py",
            "persistent_controls": "pytest -q backend/tests/integration/test_m9_persistent_controls.py",
            "smoke_test": "python scripts/smoke_test.py <base_url>",
            "load_test": "python scripts/run_load_test.py --users 10000 --instruments 5000 --duration-minutes 240 --environment staging --distributed-evidence --fail-invalid",
            "dr_drill": "python scripts/run_dr_drill.py --evidence <dr-evidence.json> --fail-invalid",
            "security_assessment": "python scripts/security_assessment.py --validate <security-assessment.json> --fail-invalid",
            "model_validation": "python scripts/model_validation_report.py --validate <model-validation.json>",
            "provider_certification": "python scripts/provider_certification.py --validate <provider-report.json>",
            "broker_certification": "python scripts/broker_certification.py --validate <broker-report.json>",
            "persistent_controls_restore": "python scripts/persistent_controls_restore.py --evidence <persistent-controls-evidence.json> --fail-invalid",
            "cloud_infrastructure_plan": "python scripts/cloud_infrastructure_plan.py --evidence <cloud-apply-evidence.json> --fail-invalid",
            "legal_compliance_review": "python scripts/legal_compliance_review.py --validate <legal-review.json>",
            "paper_trading_validation": "python scripts/paper_trading_validation.py --trades <trades.json> --days 30",
            "evidence_manifest": "python scripts/evidence_manifest.py --manifest release_evidence.json --fail-invalid",
            "accept_evidence": "python scripts/accept_evidence.py --manifest release_evidence.json --key <key> --artifact <artifact.json> --owner <team> --notes <summary>",
            "accept_evidence_bundle": "python scripts/accept_evidence_bundle.py --manifest release_evidence.json --evidence-dir release-artifacts/<candidate> --release-candidate <candidate> --live-requested --fail-invalid",
            "go_live_gate": "python scripts/go_live_gate.py --environment production --env-file config/prod.env --evidence-manifest release_evidence.json --live-requested --fail-closed",
        },
        "open_blockers": OPEN_BLOCKERS,
        "live_trading_allowed": False,
    }


def print_rollback_checklist() -> None:
    for item in [
        "Pause automated trading through the safety service.",
        "Promote the previous approved image tag or model version.",
        "Run smoke tests for auth, signals, portfolio risk, execution preflight, and safety pause.",
        "Reconcile broker state, audit records, and customer-facing trade journal.",
        "Record rollback reason, affected users, and follow-up owner.",
    ]:
        print(f"- {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate production readiness evidence.")
    parser.add_argument("--environment", default="staging")
    parser.add_argument("--env-file")
    parser.add_argument("--output")
    parser.add_argument("--rollback-checklist", action="store_true")
    args = parser.parse_args()

    if args.rollback_checklist:
        print_rollback_checklist()
        return

    report = build_report(args.environment, Path(args.env_file) if args.env_file else None)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
