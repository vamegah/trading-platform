"""
DR and outage drill evidence.

Reads the report produced by the DR test harness.
"""
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))

REPORT = Path("evidence/dr/report.json")


def collect(environment: str) -> str:
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    return TEMPLATES.get_template("dr_outage_drill.md.j2").render(
        environment=environment,
        rto=report.get("rto_minutes", "n/a"),
        rpo=report.get("rpo_minutes", "n/a"),
        region_failover=report.get("region_failover", "pending"),
        provider_failover=report.get("provider_failover", "pending"),
        redis_recovery=report.get("redis_recovery", "pending"),
        broker_outage=report.get("broker_outage", "pending"),
    )