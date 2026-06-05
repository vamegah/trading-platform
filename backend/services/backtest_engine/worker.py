import argparse
import asyncio

from backend.services.backtest_engine.event_handlers import BACKTEST_EVENT_HANDLERS
from backend.shared.event_handlers import process_consumer_batch
from backend.shared.events import TOPICS


async def run_once(consumer: str = "backtest-worker") -> dict[str, int]:
    return await process_consumer_batch(
        TOPICS.backtest_commands,
        "backtest-engine",
        consumer,
        BACKTEST_EVENT_HANDLERS,
    )


async def run_forever(consumer: str = "backtest-worker") -> None:
    while True:
        await run_once(consumer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consume backtest command events.")
    parser.add_argument("--consumer", default="backtest-worker")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        print(asyncio.run(run_once(args.consumer)))
        return
    asyncio.run(run_forever(args.consumer))


if __name__ == "__main__":
    main()
