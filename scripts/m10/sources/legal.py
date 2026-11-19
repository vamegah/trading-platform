"""
Legal and compliance evidence.

Verifies counsel approval letters and disclosure documents are present.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))

DOCUMENTS = [
    "terms_of_service.pdf",
    "privacy_policy.pdf",
    "risk_disclosure.pdf",
    "suitability_questionnaire.pdf",
    "registration_position_letter.pdf",
    "marketing_review.pdf",
]


def collect(environment: str) -> str:
    base = Path("evidence/legal")
    rows = [
        {"document": d, "present": (base / d).exists()} for d in DOCUMENTS
    ]
    return TEMPLATES.get_template("legal_compliance_review.md.j2").render(
        environment=environment, rows=rows
    )