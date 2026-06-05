import json
from pathlib import Path

import pytest

from scripts.accept_evidence import accept_evidence
from scripts.accept_evidence_bundle import ARTIFACT_FILENAMES, accept_evidence_bundle
from scripts.broker_certification import REQUIRED_BROKERS, build_template as broker_template
from scripts.cloud_infrastructure_plan import build_report as cloud_report
from scripts.evidence_manifest import build_template, validate_manifest
from scripts.go_live_gate import build_gate
from scripts.legal_compliance_review import REQUIRED_APPROVALS, build_template as legal_template
from scripts.model_validation_report import build_template as model_template
from scripts.paper_trading_validation import build_report as paper_report
from scripts.persistent_controls_restore import run_restore_drill
from scripts.provider_certification import REQUIRED_PROVIDERS, build_template as provider_template
from scripts.run_dr_drill import DR_STEPS, build_report as dr_report
from scripts.run_load_test import build_report as load_report
from scripts.security_assessment import REQUIRED_CHECKS


def test_manifest_rejects_accepted_record_without_required_metadata(tmp_path: Path) -> None:
    manifest = build_template()
    manifest["evidence"]["provider_certification"]["accepted"] = True
    path = tmp_path / "release_evidence.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    result = validate_manifest(path)

    assert result.valid is False
    assert "M9-01:provider_certification" in result.failing


def test_accept_evidence_validates_artifact_before_updating_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "release_evidence.json"
    artifact_path = tmp_path / "provider-certification.json"
    artifact_path.write_text(json.dumps(provider_template()), encoding="utf-8")

    with pytest.raises(ValueError):
        accept_evidence(
            manifest_path,
            "provider_certification",
            artifact_path,
            owner="data-platform",
            notes="reviewed",
        )

    artifact = provider_template()
    for provider in REQUIRED_PROVIDERS:
        for key, value in list(artifact["providers"][provider].items()):
            if isinstance(value, bool):
                artifact["providers"][provider][key] = True
            elif key == "artifact_uri":
                artifact["providers"][provider][key] = "s3://release-evidence/provider.pdf"
    artifact["accepted"] = True
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    result = accept_evidence(
        manifest_path,
        "provider_certification",
        artifact_path,
        owner="data-platform",
        notes="reviewed provider evidence",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["accepted"] is True
    assert "M9-01:provider_certification" not in result["remaining_failing"]
    assert manifest["evidence"]["provider_certification"]["owner"] == "data-platform"
    assert manifest["evidence"]["provider_certification"]["notes"] == "reviewed provider evidence"


def test_accept_evidence_bundle_is_atomic_and_accepts_complete_m10_artifacts(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    _write_valid_m10_artifacts(evidence_dir)
    (evidence_dir / ARTIFACT_FILENAMES["broker_certification"]).unlink()
    manifest_path = tmp_path / "release_evidence.json"

    blocked = accept_evidence_bundle(
        manifest_path,
        evidence_dir,
        release_candidate="rc-20260603",
        live_requested=True,
    )

    assert blocked["valid"] is False
    assert blocked["manifest_updated"] is False
    assert "broker_certification" in blocked["missing"]
    assert not manifest_path.exists()

    _write_valid_broker_artifact(evidence_dir / ARTIFACT_FILENAMES["broker_certification"])
    accepted = accept_evidence_bundle(
        manifest_path,
        evidence_dir,
        release_candidate="rc-20260603",
        live_requested=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert accepted["valid"] is True
    assert accepted["manifest_updated"] is True
    assert len(accepted["accepted"]) == len(ARTIFACT_FILENAMES)
    assert validate_manifest(manifest_path).valid is True
    assert manifest["release"]["candidate"] == "rc-20260603"
    assert manifest["release"]["live_trading_requested"] is True


def test_final_go_live_gate_can_pass_with_complete_m10_bundle_and_valid_runtime(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    _write_valid_m10_artifacts(evidence_dir)
    manifest_path = tmp_path / "release_evidence.json"
    env_file = _write_valid_prod_env(tmp_path / "prod.env")

    accept_evidence_bundle(
        manifest_path,
        evidence_dir,
        release_candidate="rc-20260603",
        live_requested=True,
    )
    gate = build_gate("production", manifest_path, live_requested=True, env_file=env_file)

    assert gate["go_live_allowed"] is True
    assert gate["blocking_reasons"] == []


@pytest.mark.parametrize(
    ("key", "payload"),
    [
        ("persistent_controls_restore", {"production_ready": True, "passed": True}),
        ("cloud_infrastructure_plan", {"production_ready": True, "passed": True}),
        (
            "load_soak_test",
            {
                "production_ready": True,
                "passed": True,
                "users": 10_000,
                "instruments": 5_000,
                "duration_minutes": 240,
                "environment": "staging",
                "distributed_evidence": False,
                "p95_latency_ms": 400,
                "target_latency_ms": 500,
            },
        ),
        (
            "dr_outage_drill",
            {
                "production_ready": True,
                "passed": True,
                "steps": {},
                "rto_minutes": 45,
                "target_rto_minutes": 60,
                "rpo_minutes": 5,
                "target_rpo_minutes": 15,
            },
        ),
        (
            "security_assessment",
            {
                "checks": {check: {"passed": True} for check in REQUIRED_CHECKS},
                "findings": {"critical": 0, "high": 0},
                "risk_acceptances": [],
            },
        ),
        (
            "paper_trading_validation",
            {
                "passed": True,
                "validation_window_days": 45,
                "total_trades": 25,
                "rejected_or_skipped": 0,
                "reconciled_trades": 25,
                "average_slippage_bps": 8,
                "risk_breaches": 0,
                "model_drift_alerts": 0,
                "attribution_inputs_complete": False,
            },
        ),
    ],
)
def test_m10_acceptance_rejects_superficial_production_ready_flags(
    tmp_path: Path,
    key: str,
    payload: dict,
) -> None:
    manifest_path = tmp_path / "release_evidence.json"
    artifact_path = tmp_path / f"{key}.json"
    artifact_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        accept_evidence(manifest_path, key, artifact_path, owner="release", notes="reviewed")


def _write_valid_m10_artifacts(evidence_dir: Path) -> None:
    _write_valid_provider_artifact(evidence_dir / ARTIFACT_FILENAMES["provider_certification"])
    _write_valid_broker_artifact(evidence_dir / ARTIFACT_FILENAMES["broker_certification"])
    _write_valid_model_artifact(evidence_dir / ARTIFACT_FILENAMES["model_validation"])
    _write_valid_persistent_controls_artifact(evidence_dir / ARTIFACT_FILENAMES["persistent_controls_restore"])
    _write_valid_cloud_artifact(evidence_dir / ARTIFACT_FILENAMES["cloud_infrastructure_plan"])
    load_report(
        users=10_000,
        instruments=5_000,
        replicas=12,
        output=str(evidence_dir / ARTIFACT_FILENAMES["load_soak_test"]),
        duration_minutes=240,
        environment="staging",
        distributed_evidence=True,
    )
    _write_valid_security_artifact(evidence_dir / ARTIFACT_FILENAMES["security_assessment"])
    _write_valid_dr_artifact(evidence_dir / ARTIFACT_FILENAMES["dr_outage_drill"])
    _write_valid_legal_artifact(evidence_dir / ARTIFACT_FILENAMES["legal_compliance_review"])
    _write_valid_paper_artifact(evidence_dir / ARTIFACT_FILENAMES["paper_trading_validation"])


def _write_valid_provider_artifact(path: Path) -> None:
    artifact = provider_template()
    for provider in REQUIRED_PROVIDERS:
        for key, value in list(artifact["providers"][provider].items()):
            if isinstance(value, bool):
                artifact["providers"][provider][key] = True
            elif key == "artifact_uri":
                artifact["providers"][provider][key] = f"s3://release-evidence/{provider}.pdf"
    artifact["accepted"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")


def _write_valid_broker_artifact(path: Path) -> None:
    artifact = broker_template()
    for broker in REQUIRED_BROKERS:
        for key, value in list(artifact["brokers"][broker].items()):
            if isinstance(value, bool):
                artifact["brokers"][broker][key] = True
            elif key == "artifact_uri":
                artifact["brokers"][broker][key] = f"s3://release-evidence/{broker}.pdf"
    artifact["accepted"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")


def _write_valid_model_artifact(path: Path) -> None:
    artifact = model_template()
    artifact["challenger"].update(
        {
            "artifact_uri": "s3://models/signal/1.1.0/model.json",
            "out_of_sample_score": 0.68,
            "calibration_error": 0.08,
            "drift_score": 0.08,
            "explainability_report_uri": "s3://models/signal/1.1.0/shap.json",
            "training_data_snapshot_id": "features-v2",
        }
    )
    artifact["human_approval"].update(
        {
            "approved": True,
            "approver": "ml-review-board",
            "reviewed_at": "2026-06-03T00:00:00Z",
            "notes": "approved",
        }
    )
    path.write_text(json.dumps(artifact), encoding="utf-8")


def _write_valid_persistent_controls_artifact(path: Path) -> None:
    evidence_path = path.with_suffix(".evidence.json")
    evidence_path.write_text(
        json.dumps(
            {
                "kms_or_vault_backed": True,
                "production_backup_restored": True,
                "secret_store_restore_verified": True,
                "audit_store_restore_verified": True,
                "privacy_store_restore_verified": True,
                "compliance_evidence_restore_verified": True,
            }
        ),
        encoding="utf-8",
    )
    run_restore_drill(output=str(path), evidence_path=str(evidence_path))


def _write_valid_cloud_artifact(path: Path) -> None:
    evidence_path = path.with_suffix(".evidence.json")
    evidence_path.write_text(
        json.dumps(
            {
                "cloud_backend_configured": True,
                "production_apply_verified": True,
                "dr_region_verified": True,
                "backup_policy_verified": True,
                "monitoring_verified": True,
            }
        ),
        encoding="utf-8",
    )
    cloud_report(output=str(path), evidence_path=str(evidence_path))


def _write_valid_security_artifact(path: Path) -> None:
    artifact = {
        "checks": {
            check: {"passed": True, "artifact_uri": f"s3://release-evidence/security/{check}.json"}
            for check in REQUIRED_CHECKS
        },
        "findings": {"critical": 0, "high": 0},
        "risk_acceptances": [],
    }
    path.write_text(json.dumps(artifact), encoding="utf-8")


def _write_valid_dr_artifact(path: Path) -> None:
    evidence_path = path.with_suffix(".evidence.json")
    evidence_path.write_text(json.dumps({"steps": {step: "passed" for step in DR_STEPS}}), encoding="utf-8")
    dr_report(output=str(path), evidence_path=str(evidence_path))


def _write_valid_legal_artifact(path: Path) -> None:
    artifact = legal_template()
    artifact["live_trading_approved"] = True
    for key in REQUIRED_APPROVALS:
        artifact["approvals"][key].update(
            {
                "approved": True,
                "approver": "counsel",
                "reviewed_at": "2026-06-03T00:00:00Z",
                "artifact_uri": f"s3://release-evidence/legal/{key}.pdf",
                "notes": "approved",
            }
        )
    path.write_text(json.dumps(artifact), encoding="utf-8")


def _write_valid_paper_artifact(path: Path) -> None:
    trades = [
        {
            "status": "executed",
            "reconciled": True,
            "slippage_bps": 8,
            "risk_breach": False,
            "model_drift_alert": False,
            "model_version_id": "signal-orchestrator-v1.0.0",
            "data_snapshot_id": "snapshot:paper:2026-06-03",
            "attribution": {"source_breakdown": {"technical": 0.5, "fundamental": 0.5}},
        }
        for _ in range(25)
    ]
    paper_report(trades, days=45, output=str(path))


def _write_valid_prod_env(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "ENVIRONMENT=production",
                "DATABASE_URL=postgresql+psycopg://trading:strong-pass@db.internal:5432/trading",
                "REDIS_URL=rediss://redis.internal:6379/0",
                "SECRET_KEY=prod-secret-key-12345678901234567890",
                "ENCRYPTION_KEY=prod-encryption-key-12345678901234567890",
                "KMS_KEY_ID=kms-prod-key",
                "AUDIT_STORE_URL=postgresql+psycopg://audit:strong-pass@audit.internal:5432/audit",
                "SECRET_STORE_URL=vault://trading-platform/prod",
                "CREATE_TABLES_ON_STARTUP=false",
                "POLYGON_API_KEY=polygon-prod-key",
                "FMP_API_KEY=fmp-prod-key",
                "TWELVE_DATA_API_KEY=twelve-prod-key",
                "FINNHUB_API_KEY=finnhub-prod-key",
                "SENTRY_DSN=https://sentry.example/1",
                "AUTH0_DOMAIN=auth.example.com",
                "AUTH0_AUDIENCE=api://trading-platform",
                "ALPACA_API_KEY=alpaca-prod-key",
                "ALPACA_API_SECRET=alpaca-prod-secret",
                "IBKR_ACCOUNT_ID=U123456",
                "BROKER_ENCRYPTION_KEY_ID=broker-kms-key",
            ]
        ),
        encoding="utf-8",
    )
    return path
