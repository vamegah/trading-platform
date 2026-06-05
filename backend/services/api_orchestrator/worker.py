import argparse
import asyncio

from backend.services.api_orchestrator.event_handlers import EXTERNAL_API_EVENT_HANDLERS
from backend.shared.event_handlers import process_consumer_batch
from backend.shared.events import TOPICS


async def run_once(consumer: str = "external-api-worker") -> dict[str, int]:
    return await process_consumer_batch(
        TOPICS.external_api_commands,
        "external-api-orchestrator",
        consumer,
        EXTERNAL_API_EVENT_HANDLERS,
    )


async def run_forever(consumer: str = "external-api-worker") -> None:
    while True:
        await run_once(consumer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consume external API command events.")
    parser.add_argument("--consumer", default="external-api-worker")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        print(asyncio.run(run_once(args.consumer)))
        return
    asyncio.run(run_forever(args.consumer))


if __name__ == "__main__":
    main()
