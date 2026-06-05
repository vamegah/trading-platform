from datetime import datetime, timezone


def normalize_trade_event(event: dict) -> dict[str, object] | None:
    if event.get("ev") != "T":
        return None
    return {
        "stream": "price:ticks",
        "symbol": event["sym"].upper(),
        "price": float(event["p"]),
        "timestamp": event.get("t") or datetime.now(timezone.utc).isoformat(),
    }


async def polygon_stock_stream(events: list[dict] | None = None) -> list[dict[str, object]]:
    normalized = []
    for event in events or []:
        item = normalize_trade_event(event)
        if item:
            normalized.append(item)
    return normalized
