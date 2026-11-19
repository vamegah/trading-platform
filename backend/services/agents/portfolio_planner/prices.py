"""
Market price provider.

Uses Polygon.io. Falls back to a deterministic default only when explicitly
configured via ALLOW_RANDOM_PRICES=true, which is intended for unit tests.
"""
import logging
import os
import random
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from polygon import RESTClient

load_dotenv(override=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
POLYGON_PLAN = os.getenv("POLYGON_PLAN", "free")
ALLOW_RANDOM_PRICES = os.getenv("ALLOW_RANDOM_PRICES", "false").lower() == "true"
DEFAULT_MISSING_PRICE = float(os.getenv("DEFAULT_MISSING_PRICE", "0"))


def is_market_open() -> bool:
    client = RESTClient(POLYGON_API_KEY)
    return client.get_market_status().market == "open"


def get_all_share_prices_polygon_eod() -> dict[str, float]:
    client = RESTClient(POLYGON_API_KEY)
    probe = client.get_previous_close_agg("SPY")[0]
    last_close = datetime.fromtimestamp(probe.timestamp / 1000, tz=timezone.utc).date()
    results = client.get_grouped_daily_aggs(last_close, adjusted=True, include_otc=False)
    return {r.ticker: r.close for r in results}


@lru_cache(maxsize=2)
def get_market_for_prior_date(today: str) -> dict[str, float]:
    return get_all_share_prices_polygon_eod()


def get_share_price_polygon_eod(symbol: str) -> float:
    today = datetime.now().date().strftime("%Y-%m-%d")
    return get_market_for_prior_date(today).get(symbol, 0.0)


def get_share_price_polygon_min(symbol: str) -> float:
    client = RESTClient(POLYGON_API_KEY)
    result = client.get_snapshot_ticker("stocks", symbol)
    return (result.min.close if result.min and result.min.close else result.prev_day.close)


def get_share_price_polygon(symbol: str) -> float:
    if POLYGON_PLAN == "paid":
        return get_share_price_polygon_min(symbol)
    return get_share_price_polygon_eod(symbol)


def get_share_price(symbol: str) -> float:
    if POLYGON_API_KEY:
        try:
            return get_share_price_polygon(symbol)
        except Exception as exc:
            logger.warning("Polygon lookup failed for %s: %s", symbol, exc)

    if ALLOW_RANDOM_PRICES:
        logger.warning("Using random price for %s (ALLOW_RANDOM_PRICES=true)", symbol)
        return float(random.randint(1, 100))

    logger.error("No price for %s; returning default", symbol)
    return DEFAULT_MISSING_PRICE