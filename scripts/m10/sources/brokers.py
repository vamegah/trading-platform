"""
Broker certification evidence.

For each broker:
  * Sandbox order submitted and cancelled successfully.
  * Reconciliation (positions match expectations).
  * Outage recovery (queue and retry).
  * Live credentials approved.
"""
import os

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))

BROKERS = ["alpaca", "ibkr"]


def collect(environment: str) -> str:
    rows = []
    for broker in BROKERS:
        rows.append({
            "broker": broker,
            "sandbox_submit": os.getenv(f"{broker.upper()}_SANDBOX_SUBMIT", "unknown"),
            "sandbox_cancel": os.getenv(f"{broker.upper()}_SANDBOX_CANCEL", "unknown"),
            "reconciliation": os.getenv(f"{broker.upper()}_RECON", "unknown"),
            "outage_recovery": os.getenv(f"{broker.upper()}_OUTAGE", "unknown"),
            "live_approved": os.getenv(f"{broker.upper()}_LIVE_APPROVED", "false"),
        })

    return TEMPLATES.get_template("broker_certification.md.j2").render(
        environment=environment, rows=rows
    )