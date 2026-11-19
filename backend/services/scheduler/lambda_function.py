"""
Scheduler Lambda — periodically trigger the Alex Researcher service.

Invoked by EventBridge Scheduler (see terraform/4_researcher/main.tf).
Sends a POST to the researcher's /research endpoint with a configurable
ResearchRequest payload, then logs the structured response to CloudWatch.

Environment variables:
    APP_RUNNER_URL          URL of the researcher service (Lambda Function URL
                            or App Runner), e.g. https://abc.lambda-url.us-east-1.on.aws
                            Do NOT include a trailing slash or path.
    RESEARCHER_API_KEY      Optional shared secret. When set, sent as x-api-key header.
    RESEARCH_MODE           Research mode: auto | ticker | sector | macro | topic
                            Defaults to "auto".
    RESEARCH_TICKERS        Comma-separated tickers for mode=ticker, e.g. "NVDA,MSFT"
    RESEARCH_SECTOR         Sector name for mode=sector, e.g. "Technology"
    RESEARCH_WINDOW         News window: 24h | 7d  (default: 24h)
    RESEARCH_INGEST         Whether to persist the brief: true | false (default: true)
    REQUEST_TIMEOUT_SECONDS Seconds to wait for the researcher (default: 300)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

APP_RUNNER_URL = os.environ.get("APP_RUNNER_URL", "").rstrip("/")
RESEARCHER_API_KEY = os.environ.get("RESEARCHER_API_KEY", "").strip()
RESEARCH_MODE = os.environ.get("RESEARCH_MODE", "auto").strip().lower()
RESEARCH_TICKERS = [
    t.strip().upper()
    for t in os.environ.get("RESEARCH_TICKERS", "").split(",")
    if t.strip()
]
RESEARCH_SECTOR = os.environ.get("RESEARCH_SECTOR", "").strip()
RESEARCH_WINDOW = os.environ.get("RESEARCH_WINDOW", "24h").strip()
RESEARCH_INGEST = os.environ.get("RESEARCH_INGEST", "true").strip().lower() not in {
    "false", "0", "no", "off"
}
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "300"))


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _log(level: str, event: str, **fields: Any) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **{k: v for k, v in fields.items() if v is not None},
    }
    msg = json.dumps(record, default=str)
    getattr(logger, level.lower(), logger.info)(msg)


def _build_payload() -> dict[str, Any]:
    """Build the ResearchRequest payload from environment configuration."""
    payload: dict[str, Any] = {
        "mode": RESEARCH_MODE,
        "window": RESEARCH_WINDOW,
        "ingest": RESEARCH_INGEST,
    }
    if RESEARCH_MODE == "ticker" and RESEARCH_TICKERS:
        payload["tickers"] = RESEARCH_TICKERS
    elif RESEARCH_MODE == "sector" and RESEARCH_SECTOR:
        payload["sector"] = RESEARCH_SECTOR
    return payload


def _post(url: str, payload: dict[str, Any]) -> tuple[int, str]:
    """
    POST JSON to url. Returns (status_code, response_body).
    Uses only stdlib — no external dependencies in the Lambda package.
    """
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if RESEARCHER_API_KEY:
        headers["x-api-key"] = RESEARCHER_API_KEY

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


# ---------------------------------------------------------------------------
# HANDLER
# ---------------------------------------------------------------------------

def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Entry point for EventBridge Scheduler (and direct Lambda invocations).

    event may optionally override any ResearchRequest field:
        {"mode": "ticker", "tickers": ["NVDA"], "window": "7d"}
    If event is empty or contains no researcher keys, the environment-variable
    defaults are used.
    """
    request_id = getattr(context, "aws_request_id", "local")

    if not APP_RUNNER_URL:
        _log("error", "config_missing", request_id=request_id,
             message="APP_RUNNER_URL not set")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "APP_RUNNER_URL not configured"}),
        }

    url = f"{APP_RUNNER_URL}/research"

    # Allow EventBridge detail or direct invocation to override payload fields
    payload = _build_payload()
    researcher_keys = {"mode", "tickers", "sector", "topic", "window", "ingest"}
    overrides = {k: v for k, v in event.items() if k in researcher_keys}
    payload.update(overrides)

    _log(
        "info",
        "research_trigger",
        request_id=request_id,
        url=url,
        mode=payload.get("mode"),
        tickers=payload.get("tickers"),
        sector=payload.get("sector"),
        window=payload.get("window"),
        ingest=payload.get("ingest"),
    )

    status_code, body = _post(url, payload)

    if status_code == 200:
        # Try to log structured brief summary from the ResearchResponse
        try:
            result = json.loads(body)
            brief = result.get("brief") or {}
            _log(
                "info",
                "research_complete",
                request_id=request_id,
                run_id=result.get("run_id"),
                mode=result.get("mode"),
                parse_ok=result.get("parse_ok"),
                duration_ms=result.get("duration_ms"),
                items=len(brief.get("items", [])),
                top_signal=brief.get("top_signal"),
            )
        except Exception:
            _log("info", "research_complete_raw", request_id=request_id,
                 preview=body[:500])

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Research triggered successfully",
                "researcher_status": status_code,
            }),
        }

    # Non-200: log and surface the error
    _log(
        "error",
        "research_failed",
        request_id=request_id,
        status_code=status_code,
        body_preview=body[:500],
    )
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": f"Researcher returned {status_code}",
            "detail": body[:500],
        }),
    }
