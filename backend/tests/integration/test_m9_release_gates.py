import json
import subprocess
import sys
from pathlib import Path


def test_deploy_workflow_has_plan_apply_smoke_and_evidence_gates() -> None:
    workflow = Path(".github/workflows/deploy.yml").read_text(encoding="utf-8")

    assert "Terraform validate" in workflow
    assert "Plan deployment" in workflow
    assert "Upload Terraform plan" in workflow
    assert "terraform apply" in workflow
    assert "APPLY_INFRASTRUCTURE" in workflow
    assert "Smoke test deployed gateway" in workflow
    assert "Record release candidate evidence" in workflow
    assert "Attest release evidence" in workflow
    assert "Generate production change log" in workflow
    assert "Live trading go-live gate" in workflow
    assert "go_live_gate.py" in workflow
    assert "rollback" in workflow


def test_terraform_topology_exposes_release_services_and_gates() -> None:
    terraform = Path("infrastructure/terraform/main.tf").read_text(encoding="utf-8")

    for required in (
        "api-gateway",
        "signal-orchestrator",
        "execution-service",
        "kms",
        "audit-store",
        "secret-store",
        "release_gates",
        "image_tag",
    ):
        assert required in terraform


def test_production_readiness_script_outputs_required_evidence(tmp_path: Path) -> None:
    output = tmp_path / "readiness.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/production_readiness.py",
            "--environment",
            "staging",
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["environment"] == "staging"
    assert report["live_trading_allowed"] is False
    assert "load_test" in report["required_evidence"]
    assert "security_assessment" in report["required_evidence"]


def test_release_preflight_scripts_generate_machine_readable_reports(tmp_path: Path) -> None:
    load_report = tmp_path / "load.json"
    dr_report = tmp_path / "dr.json"

    subprocess.run(
        [
            sys.executable,
            "scripts/run_load_test.py",
            "--users",
            "10000",
            "--instruments",
            "5000",
            "--replicas",
            "12",
            "--duration-minutes",
            "240",
            "--environment",
            "staging",
            "--distributed-evidence",
            "--output",
            str(load_report),
        ],
        check=True,
    )
    subprocess.run(
        [sys.executable, "scripts/run_dr_drill.py", "--output", str(dr_report)],
        check=True,
    )

    load = json.loads(load_report.read_text(encoding="utf-8"))
    dr = json.loads(dr_report.read_text(encoding="utf-8"))

    assert load["passed"] is True
    assert load["production_ready"] is True
    assert load["distributed_evidence"] is True
    assert load["target_latency_ms"] == 500
    assert dr["passed"] is False
    assert dr["production_ready"] is False
    assert dr["steps"]["live_trading_remains_disabled"] == "requires_environment_evidence"


def test_release_candidate_review_approves_completed_m9_without_external_manifest(tmp_path: Path) -> None:
    output = tmp_path / "review.json"
    subprocess.run(
        [sys.executable, "scripts/release_candidate_review.py", "--output", str(output)],
        check=True,
    )

    review = json.loads(output.read_text(encoding="utf-8"))

    assert review["release_candidate_approved"] is True
    assert review["live_trading_allowed"] is False
    assert review["open_tasks"] == []
