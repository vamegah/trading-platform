"""
Security assessment evidence.

Reads the external pen test report and the internal vulnerability scan.
"""
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))


def collect(environment: str) -> str:
    return TEMPLATES.get_template("security_assessment.md.j2").render(
        environment=environment,
        critical=os.getenv("M10_SEC_CRITICAL", "0"),
        high=os.getenv("M10_SEC_HIGH", "0"),
        medium=os.getenv("M10_SEC_MEDIUM", "0"),
        low=os.getenv("M10_SEC_LOW", "0"),
        report_path="evidence/security/pentest.pdf",
    )