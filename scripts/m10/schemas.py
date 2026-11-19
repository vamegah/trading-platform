"""
M10 evidence schemas.

Every category must be present in release_evidence.json with status
"accepted" and a path to the evidence file. Optional categories can be
absent. Each accepted category is hashed to prevent tampering.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Status(str, Enum):
    missing = "missing"
    draft = "draft"
    submitted = "submitted"
    accepted = "accepted"
    rejected = "rejected"


class EvidenceCategory(BaseModel):
    status: Status
    path: str
    sha256: Optional[str] = None
    accepted_at: Optional[str] = None
    accepted_by: Optional[str] = None
    notes: Optional[str] = None


class EvidenceManifest(BaseModel):
    version: str = "1.0"
    generated_at: str
    build_sha: str
    environment: str

    # Required categories (mirror the M10-01..M10-11 tasks)
    provider_certification: EvidenceCategory
    broker_certification: EvidenceCategory
    model_validation: EvidenceCategory
    persistent_controls_restore: EvidenceCategory
    cloud_infrastructure_plan: EvidenceCategory
    load_soak_test: EvidenceCategory
    security_assessment: EvidenceCategory
    dr_outage_drill: EvidenceCategory
    legal_compliance_review: EvidenceCategory
    paper_trading_validation: EvidenceCategory

    # Optional extras for M10-05 and later
    scheduler_operational: Optional[EvidenceCategory] = None


REQUIRED_CATEGORIES = [
    "provider_certification",
    "broker_certification",
    "model_validation",
    "persistent_controls_restore",
    "cloud_infrastructure_plan",
    "load_soak_test",
    "security_assessment",
    "dr_outage_drill",
    "legal_compliance_review",
    "paper_trading_validation",
]