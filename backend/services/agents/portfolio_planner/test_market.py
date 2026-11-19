"""Smoke test for the market data updater."""
import os

from db import Database
from market import update_instrument_prices

USER_ID = os.getenv("TEST_USER_ID", "test_user_001")


def main() -> None:
    db = Database()

    if not db.users.find_by_clerk_id(USER_ID):
        raise SystemExit(f"Test user {USER_ID} not found")

    job_id = db.jobs.create_job(
        clerk_user_id=USER_ID,
        job_type="test_market",
        request_payload={"test": True},
    )
    print(f"Test job {job_id}")

    accounts = db.accounts.find_by_user(USER_ID)
    symbols = set()
    for account in accounts:
        for position in db.positions.find_by_account(account["id"]):
            symbols.add(position["symbol"])
            instrument = db.instruments.find_by_symbol(position["symbol"])
            if instrument:
                print(f"  {position['symbol']}: {instrument.get('current_price')}")

    print(f"\nUpdating {len(symbols)} symbols")
    update_instrument_prices(job_id, db)

    print("\nAfter update:")
    for symbol in symbols:
        instrument = db.instruments.find_by_symbol(symbol)
        if instrument:
            print(f"  {symbol}: {instrument.get('current_price')}")

    db.jobs.delete(job_id)
    print(f"Deleted test job {job_id}")


if __name__ == "__main__":
    main()