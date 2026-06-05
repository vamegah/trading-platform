import json
import subprocess
import sys
from pathlib import Path

from scripts.evidence_manifest import REQUIRED_EVIDENCE, build_template, validate_manifest
from scripts.legal_compliance_review import REQUIRED_APPROVALS, validate
from scripts.paper_trading_validation import build_report


def test_evidence_manifest_template_contains_every_open_external_gate(tmp_path: Path) -> None:
    manifest_path = tmp_path / "release_evidence.json"
    manifest_path.write_text(json.dumps(build_template()), encoding="utf-8")

    result = validate_manifest(manifest_path)

    assert result.valid is False
    assert len(result.failing) == sum(len(value) for value in REQUIRED_EVIDENCE.values())
    assert result.missing == []


def test_evidence_manifest_accepts_complete_reviewed_evidence(tmp_path: Path) -> None:
    manifest = build_template()
    for record in manifest["evidence"].values():
        record.update(
            {
                "accepted": True,
                "artifact_uri": "s3://release-evidence/report.json",
                "owner": "owner",
                "reviewed_at": "2026-05-15T00:00:00Z",
                "notes": "reviewed",
            }
        )
    manifest_path = tmp_path / "release_evidence.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = validate_manifest(manifest_path)

    assert result.valid is True
    assert len(result.accepted) == sum(len(value) for value in REQUIRED_EVIDENCE.values())


def test_paper_trading_validation_requires_extended_clean_reconciled_run() -> None:
    weak = build_report([], days=5)
    trades = [
        {
            "status": "executed",
            "reconciled": True,
            "slippage_bps": 8,
            "risk_breach": False,
            "model_drift_alert": False,
            "model_version_id": "signal-orchestrator-v1.0.0",
            "data_snapshot_id": "snapshot:paper:2026-05-15",
            "attribution": {"source_breakdown": {"technical": 0.5, "fundamental": 0.5}},
        }
        for _ in range(25)
    ]
    strong = build_report(trades, days=45)
    missing_attribution = build_report([{**paper_trade, "attribution": {}} for paper_trade in trades], days=45)

    assert weak["passed"] is False
    assert missing_attribution["passed"] is False
    assert strong["passed"] is True
    assert strong["attribution_inputs_complete"] is True
    assert strong["average_slippage_bps"] == 8


def test_legal_compliance_review_requires_all_approvals(tmp_path: Path) -> None:
    payload = {
        "live_trading_approved": True,
        "approvals": {
            key: {
                "approved": True,
                "approver": "counsel",
                "reviewed_at": "2026-05-15T00:00:00Z",
                "artifact_uri": "s3://legal/review.pdf",
                "notes": "approved",
            }
            for key in REQUIRED_APPROVALS
        },
    }
    path = tmp_path / "legal.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert validate(path)["valid"] is True

    payload["approvals"]["privacy_policy"]["approved"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert validate(path)["valid"] is False

    payload["approvals"]["privacy_policy"]["approved"] = True
    payload["approvals"]["privacy_policy"]["artifact_uri"] = ""
    path.write_text(json.dumps(payload), encoding="utf-8")

    blocked = validate(path)
    assert blocked["valid"] is False
    assert "privacy_policy:artifact_uri" in blocked["missing_metadata"]


def test_release_review_includes_manifest_status(tmp_path: Path) -> None:
    manifest_path = tmp_path / "release_evidence.json"
    output = tmp_path / "review.json"
    manifest_path.write_text(json.dumps(build_template()), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/release_candidate_review.py",
            "--evidence-manifest",
            str(manifest_path),
            "--output",
            str(output),
        ],
        check=True,
    )
    review = json.loads(output.read_text(encoding="utf-8"))

    assert review["release_candidate_approved"] is False
    assert review["evidence"]["valid"] is False
    assert review["evidence"]["failing"]
