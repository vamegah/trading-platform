"""
Cloud infrastructure plan evidence.

Captures:
  * Terraform plan output
  * Terraform apply output
  * Managed service inventory
  * Backup policies
  * DR region verification
"""
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))


def collect(environment: str) -> str:
    tf_dir = Path(f"infrastructure/terraform/envs/{environment}")
    plan_log = tf_dir / "plan.log"
    apply_log = tf_dir / "apply.log"
    dr_ok = os.getenv("M10_DR_REGION_VERIFIED", "pending")

    return TEMPLATES.get_template("cloud_infrastructure_plan.md.j2").render(
        environment=environment,
        plan_log=str(plan_log),
        apply_log=str(apply_log),
        dr_ok=dr_ok,
        backups=_backups(),
    )


def _backups() -> list[dict]:
    # Example placeholder; replace with actual AWS queries
    return [
        {"service": "rds", "retention_days": 7, "last_snapshot": "auto"},
        {"service": "s3", "versioning": True, "lifecycle": "30d noncurrent"},
    ]