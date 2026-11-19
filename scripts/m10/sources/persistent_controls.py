"""
Persistent controls restore evidence.

Verifies:
  * Vault/Secrets Manager snapshot restore.
  * Audit log restore with hash chain intact.
  * Privacy data restore from encrypted RDS snapshot.
  * Compliance record restore from Smarsh/Proofpoint archives.
"""
import os

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))


def collect(environment: str) -> str:
    checks = {
        "vault_restore": os.getenv("M10_VAULT_RESTORE", "pending"),
        "audit_restore": os.getenv("M10_AUDIT_RESTORE", "pending"),
        "privacy_restore": os.getenv("M10_PRIVACY_RESTORE", "pending"),
        "compliance_restore": os.getenv("M10_COMPLIANCE_RESTORE", "pending"),
        "audit_chain_valid": os.getenv("M10_AUDIT_CHAIN_VALID", "unknown"),
    }
    return TEMPLATES.get_template("persistent_controls_restore.md.j2").render(
        environment=environment, **checks
    )