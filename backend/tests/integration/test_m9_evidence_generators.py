import json
from pathlib import Path

from scripts.broker_certification import build_template as broker_template, validate as validate_brokers
from scripts.cloud_infrastructure_plan import build_report as cloud_plan
from scripts.persistent_controls_restore import run_restore_drill
from scripts.provider_certification import build_template as provider_template, validate as validate_providers
from scripts.run_dr_drill import DR_STEPS, build_report as dr_report
from scripts.security_assessment import REQUIRED_CHECKS, validate_assessment


def _accept_all(records: dict) -> dict:
    for group in records.values():
        for checks in group.values():
            for key, value in list(checks.items()):
                if isinstance(value, bool):
                    checks[key] = True
                elif key == "artifact_uri":
                    checks[key] = "s3://release-evidence/report.json"
    return records


def test_provider_certification_template_blocks_until_all_checks_are_accepted(tmp_path: Path) -> None:
    path = tmp_path / "providers.json"
    payload = provider_template()
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert validate_providers(path)["valid"] is False

    payload["providers"] = _accept_all({"providers": payload["providers"]})["providers"]
    payload["accepted"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert validate_providers(path)["valid"] is True

    payload["providers"]["polygon"]["artifact_uri"] = ""
    path.write_text(json.dumps(payload), encoding="utf-8")

    blocked = validate_providers(path)
    assert blocked["valid"] is False
    assert "polygon:artifact_uri" in blocked["failing"]


def test_broker_certification_template_blocks_until_all_checks_are_accepted(tmp_path: Path) -> None:
    path = tmp_path / "brokers.json"
    payload = broker_template()
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert validate_brokers(path)["valid"] is False

    payload["brokers"] = _accept_all({"brokers": payload["brokers"]})["brokers"]
    payload["accepted"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert validate_brokers(path)["valid"] is True

    payload["brokers"]["alpaca"]["artifact_uri"] = ""
    path.write_text(json.dumps(payload), encoding="utf-8")

    blocked = validate_brokers(path)
    assert blocked["valid"] is False
    assert "alpaca:artifact_uri" in blocked["failing"]


def test_persistent_controls_restore_drill_passes_locally_but_requires_kms_for_production() -> None:
    report = run_restore_drill()

    assert report["passed"] is True
    assert report["secret_restored"] is True
    assert report["audit_chain_valid"] is True
    assert report["privacy_record_restored"] is True
    assert report["production_ready"] is False


def test_persistent_controls_restore_accepts_external_kms_restore_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "persistent-controls-evidence.json"
    evidence.write_text(
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

    report = run_restore_drill(evidence_path=str(evidence))

    assert report["production_ready"] is True
    assert report["missing_external_evidence"] == []


def test_cloud_infrastructure_plan_detects_required_repo_scaffolding() -> None:
    report = cloud_plan()

    assert report["passed"] is True
    assert report["terraform_markers_present"] is True
    assert report["kubernetes_manifests_present"] is True
    assert report["cloud_backend_configured"] is False
    assert report["production_ready"] is False


def test_cloud_infrastructure_plan_accepts_external_apply_and_dr_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "cloud-apply-evidence.json"
    evidence.write_text(
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

    report = cloud_plan(evidence_path=str(evidence))

    assert report["production_ready"] is True
    assert report["missing_external_evidence"] == []


def test_dr_drill_accepts_only_completed_environment_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "dr-evidence.json"
    evidence.write_text(
        json.dumps({"steps": {step: "passed" for step in DR_STEPS}}),
        encoding="utf-8",
    )

    report = dr_report(evidence_path=str(evidence))

    assert report["passed"] is True
    assert report["production_ready"] is True


def test_security_assessment_validator_blocks_findings_without_acceptance(tmp_path: Path) -> None:
    assessment = tmp_path / "security.json"
    payload = {
        "checks": {key: {"passed": True, "artifact_uri": "s3://security/report"} for key in REQUIRED_CHECKS},
        "findings": {"critical": 0, "high": 1},
        "risk_acceptances": [],
    }
    assessment.write_text(json.dumps(payload), encoding="utf-8")

    blocked = validate_assessment(assessment)
    assert blocked["valid"] is False

    payload["risk_acceptances"] = [
        {
            "security_owner": "security",
            "engineering_owner": "engineering",
            "expiration_date": "2026-06-15",
        }
    ]
    assessment.write_text(json.dumps(payload), encoding="utf-8")

    accepted = validate_assessment(assessment)
    assert accepted["valid"] is True

    payload["risk_acceptances"][0]["expiration_date"] = "2020-01-01"
    assessment.write_text(json.dumps(payload), encoding="utf-8")

    expired = validate_assessment(assessment)
    assert expired["valid"] is False
    assert expired["risk_acceptance_valid"] is False
