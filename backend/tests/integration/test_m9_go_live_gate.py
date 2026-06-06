import json
from pathlib import Path

from scripts.evidence_manifest import build_template
from scripts.go_live_gate import build_gate
from scripts.model_validation_report import build_template as model_template, validate_report


def test_model_validation_report_requires_human_approval_and_model_gates(tmp_path: Path) -> None:
    path = tmp_path / "model-validation.json"
    payload = model_template()
    path.write_text(json.dumps(payload), encoding="utf-8")

    blocked = validate_report(path)
    assert blocked["valid"] is False
    assert blocked["human_approved"] is False

    payload["challenger"].update(
        {
            "artifact_uri": "s3://models/signal/1.1.0/model.json",
            "out_of_sample_score": 0.68,
            "calibration_error": 0.08,
            "drift_score": 0.08,
            "explainability_report_uri": "s3://models/signal/1.1.0/shap.json",
            "training_data_snapshot_id": "features-v2",
        }
    )
    payload["human_approval"].update(
        {
            "approved": True,
            "approver": "ml-review-board",
            "reviewed_at": "2026-05-15T00:00:00Z",
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    accepted = validate_report(path)
    assert accepted["valid"] is True
    assert accepted["model_decision"]["promotion_allowed"] is True


def test_go_live_gate_refuses_unaccepted_evidence_and_bad_runtime_config(tmp_path: Path) -> None:
    manifest = tmp_path / "release_evidence.json"
    manifest.write_text(json.dumps(build_template()), encoding="utf-8")

    gate = build_gate("production", manifest, live_requested=True)

    assert gate["go_live_allowed"] is False
    assert gate["evidence_valid"] is False
    assert gate["open_tasks"] == []
    assert gate["runtime_issues"]


def test_go_live_gate_requires_manifest_live_intent_even_with_valid_evidence_and_runtime(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://trading_user:trading_password@localhost:5432/trading_test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    env_file = tmp_path / "prod.env"
    env_file.write_text(
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
    manifest_payload = build_template()
    for record in manifest_payload["evidence"].values():
        record.update(
            {
                "accepted": True,
                "artifact_uri": "s3://release-evidence/report.json",
                "owner": "release",
                "reviewed_at": "2026-05-15T00:00:00Z",
                "notes": "reviewed",
            }
        )
    manifest = tmp_path / "release_evidence.json"
    manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")

    blocked = build_gate("Production", manifest, live_requested=True, env_file=env_file)
    assert blocked["go_live_allowed"] is False
    assert blocked["evidence_valid"] is True
    assert blocked["runtime_issues"] == []
    assert blocked["release_intent_matches"] is False
    assert "manifest_release_intent_mismatch" in blocked["blocking_reasons"]

    manifest_payload["release"]["live_trading_requested"] = True
    manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")

    allowed = build_gate("Production", manifest, live_requested=True, env_file=env_file)
    assert allowed["go_live_allowed"] is True
    assert allowed["blocking_reasons"] == []
