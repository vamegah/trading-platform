import argparse
import asyncio

from backend.services.personalization.event_handlers import PERSONALIZATION_EVENT_HANDLERS
from backend.shared.event_handlers import process_consumer_batch
from backend.shared.events import TOPICS


async def run_once(consumer: str = "personalization-worker") -> dict[str, int]:
    return await process_consumer_batch(
        TOPICS.personalization_commands,
        "personalization-engine",
        consumer,
        PERSONALIZATION_EVENT_HANDLERS,
    )


async def run_forever(consumer: str = "personalization-worker") -> None:
    while True:
        await run_once(consumer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consume personalization command events.")
    parser.add_argument("--consumer", default="personalization-worker")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        print(asyncio.run(run_once(args.consumer)))
        return
    asyncio.run(run_forever(args.consumer))


if __name__ == "__main__":
    main()
