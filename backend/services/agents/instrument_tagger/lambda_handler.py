"""
InstrumentTagger Lambda handler.

Input:  {"instruments": [{"symbol": "VTI", "name": "...", "instrument_type": "etf"}, ...]}

Output: {"statusCode": 200, "body": {"tagged": N, "updated": [...], "errors": [...]}}
"""
import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Dict, List

import boto3

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from db import Database
from agent import BEDROCK_MODEL_ID, classification_to_db_format, tag_instruments
from observability import observe

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
events_client = boto3.client("events") if EVENT_BUS_NAME else None


def _emit(detail_type: str, detail: dict) -> None:
    if not events_client:
        return
    try:
        events_client.put_events(Entries=[{
            "Source": "trading.instrument_tagger",
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": EVENT_BUS_NAME,
        }])
    except Exception:
        logger.exception("Tagger: failed to emit %s", detail_type)


async def process_instruments(instruments: List[Dict[str, Any]], db: Database) -> Dict[str, Any]:
    """Classify instruments and upsert into the platform DB."""
    logger.info("Tagger: classifying %d instruments", len(instruments))
    classifications = await tag_instruments(instruments)

    updated: List[str] = []
    errors: List[Dict[str, str]] = []
    classifications_payload: List[Dict[str, Any]] = []

    for classification in classifications:
        if classification is None:
            continue
        symbol = classification.symbol
        try:
            instrument = classification_to_db_format(classification)
            db.instruments.upsert(instrument)
            updated.append(symbol)
            classifications_payload.append({
                "symbol": symbol,
                "name": classification.name,
                "type": classification.instrument_type,
                "current_price": classification.current_price,
                "asset_class": classification.allocation_asset_class.model_dump(),
                "regions": classification.allocation_regions.model_dump(),
                "sectors": classification.allocation_sectors.model_dump(),
            })
        except Exception as exc:
            logger.exception("Tagger: failed to persist %s", symbol)
            errors.append({"symbol": symbol, "error": str(exc)})

    return {
        "tagged": len(classifications_payload),
        "updated": updated,
        "errors": errors,
        "classifications": classifications_payload,
    }


def lambda_handler(event, context):
    with observe():
        try:
            logger.info("Tagger invoked: %s", json.dumps(event)[:500])

            if isinstance(event, str):
                event = json.loads(event)

            instruments = event.get("instruments") or []
            if not instruments:
                return {"statusCode": 400, "body": json.dumps({"error": "No instruments provided"})}

            db = Database()
            _emit("tagger.started", {"count": len(instruments)})

            result = asyncio.run(process_instruments(instruments, db))

            _emit("tagger.completed", {
                "tagged": result["tagged"],
                "updated": result["updated"],
                "errors": len(result["errors"]),
            })
            return {"statusCode": 200, "body": json.dumps(result)}

        except Exception as exc:
            logger.exception("Tagger failed")
            _emit("tagger.failed", {"error": str(exc)})
            return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


def health_check() -> Dict[str, Any]:
    """Health payload for M10 evidence and readiness probes."""
    return {
        "service": "instrument_tagger",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "model": BEDROCK_MODEL_ID,
        "events_configured": bool(EVENT_BUS_NAME),
    }


# Local smoke test
if __name__ == "__main__":
    test_instruments = [
        {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "instrument_type": "etf"},
    ]
    print(json.dumps(lambda_handler({"instruments": test_instruments}, None), indent=2))