#!/usr/bin/env python3
"""
Database reset utility.

Modes:
    --dev               Drop all tables, re-migrate, seed (dev only)
    --prod              Only apply pending migrations + seed (safe)
    --with-test-data    Also create a test user with a sample portfolio
"""
import argparse
import subprocess
import sys

from client import DataAPIClient
from models import Database
from schemas import AccountCreate, PositionCreate, UserCreate
from decimal import Decimal


TABLES_IN_DROP_ORDER = [
    "trading_audit", "trades", "trading_signals", "researcher_events",
    "jobs", "positions", "accounts", "trading_profiles",
    "instruments", "users", "schema_migrations",
]


def drop_all_tables(db: DataAPIClient) -> None:
    print("Dropping tables...")
    for table in TABLES_IN_DROP_ORDER:
        try:
            db.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"  dropped {table}")
        except Exception as exc:
            print(f"  error dropping {table}: {exc}")
    try:
        db.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
    except Exception:
        pass


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)


def create_test_data(db_models: Database) -> None:
    user = UserCreate(
        clerk_user_id="test_user_001",
        display_name="Test User",
        years_until_retirement=25,
        target_retirement_income=Decimal("100000"),
    )
    if not db_models.users.find_by_clerk_id(user.clerk_user_id):
        v = user.model_dump()
        db_models.users.create_user(
            clerk_user_id=v["clerk_user_id"],
            display_name=v["display_name"],
            years_until_retirement=v["years_until_retirement"],
            target_retirement_income=v["target_retirement_income"],
        )
        print("  created test user")

    accounts = [
        AccountCreate(account_name="401(k)", account_purpose="Retirement",
                      cash_balance=Decimal("5000"), cash_interest=Decimal("0.045")),
        AccountCreate(account_name="Roth IRA", account_purpose="Tax-free",
                      cash_balance=Decimal("1000"), cash_interest=Decimal("0.04")),
        AccountCreate(account_name="Taxable Brokerage", account_purpose="General",
                      cash_balance=Decimal("2500"), cash_interest=Decimal("0.035")),
    ]
    existing = db_models.accounts.find_by_user(user.clerk_user_id)
    if existing:
        account_ids = [a["id"] for a in existing]
    else:
        account_ids = []
        for acc in accounts:
            v = acc.model_dump()
            account_ids.append(db_models.accounts.create_account(
                user.clerk_user_id,
                account_name=v["account_name"],
                account_purpose=v["account_purpose"],
                cash_balance=v["cash_balance"],
                cash_interest=v["cash_interest"],
            ))

    if account_ids:
        positions = [("SPY", Decimal("100")), ("QQQ", Decimal("50")),
                     ("BND", Decimal("200")), ("VEA", Decimal("150")),
                     ("GLD", Decimal("25"))]
        account_id = account_ids[0]
        if not db_models.positions.find_by_account(account_id):
            for symbol, qty in positions:
                PositionCreate(account_id=account_id, symbol=symbol, quantity=qty)
                db_models.positions.add_position(account_id, symbol, qty)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--prod", action="store_true")
    parser.add_argument("--with-test-data", action="store_true")
    parser.add_argument("--i-know-what-im-doing", action="store_true")
    args = parser.parse_args()

    if not args.dev and not args.prod:
        parser.error("Specify --dev or --prod")

    if args.prod and not args.i_know_what_im_doing:
        print("Refusing to run destructive ops in --prod without --i-know-what-im-doing")
        sys.exit(1)

    db = DataAPIClient()
    db_models = Database()

    if args.dev:
        drop_all_tables(db)

    print("Running migrations...")
    run(["python", "run_migrations.py"])

    print("Seeding...")
    run(["python", "seed_data.py"])

    if args.with_test_data:
        create_test_data(db_models)

    for table in ["users", "instruments", "accounts", "positions", "jobs",
                  "trading_profiles", "trading_signals", "trades",
                  "researcher_events", "trading_audit"]:
        try:
            count = db.query(f"SELECT COUNT(*) AS c FROM {table}")[0]["c"]
            print(f"  {table}: {count}")
        except Exception:
            print(f"  {table}: (not found)")


if __name__ == "__main__":
    main()