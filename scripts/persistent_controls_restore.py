import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.user_service.privacy import PrivacyManager  # noqa: E402
from backend.shared.audit import DatabaseAuditStore  # noqa: E402
from backend.shared.database import Base  # noqa: E402
from backend.shared.models import AuditLog, PrivacyRecordModel, SecretRecord  # noqa: E402
from backend.shared.secret_store import SecretStore  # noqa: E402


def _load_external_evidence(evidence_path: str | None) -> dict[str, Any]:
    if not evidence_path:
        return {}
    return json.loads(Path(evidence_path).read_text(encoding="utf-8"))


def run_restore_drill(output: str | None = None, evidence_path: str | None = None) -> dict[str, object]:
    external = _load_external_evidence(evidence_path)
    external_checks = {
        "kms_or_vault_backed": external.get("kms_or_vault_backed") is True,
        "production_backup_restored": external.get("production_backup_restored") is True,
        "secret_store_restore_verified": external.get("secret_store_restore_verified") is True,
        "audit_store_restore_verified": external.get("audit_store_restore_verified") is True,
        "privacy_store_restore_verified": external.get("privacy_store_restore_verified") is True,
        "compliance_evidence_restore_verified": external.get("compliance_evidence_restore_verified") is True,
    }
    with TemporaryDirectory() as tmpdir:
        database_path = Path(tmpdir) / "controls.db"
        engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(bind=engine, tables=[AuditLog.__table__, SecretRecord.__table__, PrivacyRecordModel.__table__])
        sessions = sessionmaker(bind=engine)

        SecretStore(sessions).put("broker_key", "secret-value")
        audit = DatabaseAuditStore(sessions)
        audit.append("RESTORE_DRILL", {"status": "started"}, user_id=1)
        privacy = PrivacyManager(sessions)
        privacy.upsert_consent("user-1", "person@example.com", {"analytics": True})

        restored_engine = create_engine(f"sqlite:///{database_path}")
        restored_sessions = sessionmaker(bind=restored_engine)
        restored_secret = SecretStore(restored_sessions).get("broker_key")
        restored_audit = DatabaseAuditStore(restored_sessions).verify()
        restored_privacy = PrivacyManager(restored_sessions).export("user-1")

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "secret_restored": restored_secret == "secret-value",
            "audit_chain_valid": restored_audit["valid"] is True,
            "privacy_record_restored": restored_privacy["exists"] is True,
            **external_checks,
            "missing_external_evidence": [key for key, value in external_checks.items() if not value],
            "passed": restored_secret == "secret-value" and restored_audit["valid"] is True and restored_privacy["exists"] is True,
            "production_ready": False,
            "notes": "Local restore drill passed. Production signoff still requires KMS/Vault-backed restore evidence.",
        }
        report["production_ready"] = bool(report["passed"]) and all(external_checks.values())
        restored_engine.dispose()
        engine.dispose()
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run persistent controls restore drill.")
    parser.add_argument("--output")
    parser.add_argument("--evidence")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()
    report = run_restore_drill(args.output, args.evidence)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_invalid and not report["production_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
