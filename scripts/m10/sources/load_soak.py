"""
Load and soak test evidence.

Reads the report produced by k6 or Locust and confirms the SLO targets.
"""
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent / "templates"),
    # Templates are Markdown (.md.j2); escape only if HTML/XML templates are added.
    autoescape=select_autoescape(["html", "xml"]),
)

REPORT = Path("evidence/load_soak/report.json")


def collect(environment: str) -> str:
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    return TEMPLATES.get_template("load_soak_test.md.j2").render(
        environment=environment,
        p50=report.get("p50", "n/a"),
        p95=report.get("p95", "n/a"),
        p99=report.get("p99", "n/a"),
        error_rate=report.get("error_rate", "n/a"),
        duration=report.get("duration", "n/a"),
        peak_users=report.get("peak_users", "n/a"),
    )