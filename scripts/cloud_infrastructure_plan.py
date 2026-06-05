import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_TERRAFORM_MARKERS = [
    "api-gateway",
    "postgres",
    "redis",
    "object-storage",
    "kms",
    "audit-store",
    "secret-store",
    "aws_db_instance",
    "aws_elasticache_replication_group",
    "aws_s3_bucket",
    "aws_kms_key",
]
REQUIRED_K8S_FILES = [
    "backend-deployment.yaml",
    "frontend-deployment.yaml",
    "redis-cluster.yaml",
    "hpa-config.yaml",
    "safety-deployment.yaml",
    "stress-test-deployment.yaml",
    "external-secrets.yaml",
]


def _load_external_evidence(evidence_path: str | None) -> dict[str, Any]:
    if not evidence_path:
        return {}
    return json.loads(Path(evidence_path).read_text(encoding="utf-8"))


def build_report(output: str | None = None, evidence_path: str | None = None) -> dict[str, object]:
    terraform_text = "\n".join(path.read_text(encoding="utf-8") for path in Path("infrastructure/terraform").glob("*.tf"))
    k8s_files = {path.name for path in Path("infrastructure/k8s").glob("*.yaml")}
    missing_markers = [marker for marker in REQUIRED_TERRAFORM_MARKERS if marker not in terraform_text]
    missing_k8s = [name for name in REQUIRED_K8S_FILES if name not in k8s_files]
    external = _load_external_evidence(evidence_path)
    external_checks = {
        "cloud_backend_configured": external.get("cloud_backend_configured") is True,
        "production_apply_verified": external.get("production_apply_verified") is True,
        "dr_region_verified": external.get("dr_region_verified") is True,
        "backup_policy_verified": external.get("backup_policy_verified") is True,
        "monitoring_verified": external.get("monitoring_verified") is True,
    }
    repository_passed = not missing_markers and not missing_k8s
    production_ready = repository_passed and all(external_checks.values())
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "terraform_markers_present": not missing_markers,
        "kubernetes_manifests_present": not missing_k8s,
        "missing_terraform_markers": missing_markers,
        "missing_kubernetes_manifests": missing_k8s,
        **external_checks,
        "missing_external_evidence": [key for key, value in external_checks.items() if not value],
        "passed": repository_passed,
        "production_ready": production_ready,
        "notes": "Repository infrastructure plan is present. Production readiness requires cloud backend credentials, terraform plan/apply evidence, and DR verification.",
    }
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cloud infrastructure plan evidence.")
    parser.add_argument("--output")
    parser.add_argument("--evidence")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()
    report = build_report(args.output, args.evidence)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_invalid and not report["production_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
