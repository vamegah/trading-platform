"""
Market data refresh for the Planner.

Fetches current prices for every symbol in a user's portfolio and updates
the instruments table. Non-critical: failures are logged but do not block
analysis.
"""
import logging
from typing import Set

from db import Database
from prices import get_share_price

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def update_instrument_prices(job_id: str, db: Database) -> None:
    """Fetch and persist current prices for all portfolio symbols."""
    try:
        job = db.jobs.find_by_id(job_id)
        if not job:
            logger.error("Market: job %s not found", job_id)
            return

        user_id = job["clerk_user_id"]
        accounts = db.accounts.find_by_user(user_id)

        symbols: Set[str] = set()
        for account in accounts:
            for position in db.positions.find_by_account(account["id"]):
                symbols.add(position["symbol"])

        if not symbols:
            logger.info("Market: no symbols to update")
            return

        logger.info("Market: fetching %d symbols", len(symbols))
        update_prices_for_symbols(symbols, db)

    except Exception:
        logger.exception("Market: error updating prices for job %s", job_id)


def update_prices_for_symbols(symbols: Set[str], db: Database) -> None:
    """Fetch and persist prices for a set of symbols."""
    if not symbols:
        return

    price_map: dict[str, float] = {}
    for symbol in symbols:
        try:
            price = get_share_price(symbol)
            if price and price > 0:
                price_map[symbol] = price
                logger.info("Market: %s=$%.2f", symbol, price)
            else:
                logger.warning("Market: no price for %s", symbol)
        except Exception:
            logger.exception("Market: could not fetch %s", symbol)

    logger.info("Market: retrieved %d/%d prices", len(price_map), len(symbols))

    for symbol, price in price_map.items():
        try:
            instrument = db.instruments.find_by_symbol(symbol)
            if instrument:
                db.client.update(
                    "instruments",
                    {"current_price": price, "last_updated": _now()},
                    "symbol = :symbol",
                    {"symbol": symbol},
                )
        except Exception:
            logger.exception("Market: failed to persist %s", symbol)

    missing = set(symbols) - set(price_map.keys())
    if missing:
        logger.warning("Market: no prices for %s", missing)


def _now():
    from datetime import datetime, UTC
    return datetime.now(UTC)


def get_all_portfolio_symbols(db: Database) -> Set[str]:
    """Return every distinct symbol held in any portfolio."""
    symbols: Set[str] = set()
    try:
        for row in db.query_raw("SELECT DISTINCT symbol FROM positions"):
            if row.get("symbol"):
                symbols.add(row["symbol"])
    except Exception:
        logger.exception("Market: error fetching all symbols")
    return symbols