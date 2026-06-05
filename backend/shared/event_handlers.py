from collections.abc import Awaitable, Callable
from typing import Any

from backend.shared.event_bus import event_bus

EventHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]


async def process_consumer_batch(
    topic: str,
    group: str,
    consumer: str,
    handlers: dict[str, EventHandler],
    count: int = 10,
    block_ms: int = 1000,
) -> dict[str, int]:
    processed = 0
    skipped = 0
    failed = 0
    acked: list[str] = []

    for message in event_bus.read_for_consumer(topic, group, consumer, count=count, block_ms=block_ms):
        envelope = message["envelope"]
        event_type = str(envelope.get("event_type", ""))
        handler = handlers.get(event_type)
        if not handler:
            skipped += 1
            acked.append(str(message["stream_id"]))
            continue
        try:
            await handler(envelope)
            processed += 1
            acked.append(str(message["stream_id"]))
        except Exception:
            failed += 1

    event_bus.ack(topic, group, *acked)
    return {"processed": processed, "skipped": skipped, "failed": failed}
