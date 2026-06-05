import requests

from backend.shared.config import settings


def fetch_crypto_onchain(asset: str) -> dict[str, str | float]:
    if settings.cryptoquant_api_key:
        response = requests.get(
            "https://api.cryptoquant.com/v1/btc/market-data/network-indicator",
            headers={"Authorization": f"Bearer {settings.cryptoquant_api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "asset": asset.upper(),
            "source": "cryptoquant",
            "active_addresses": float(payload.get("active_addresses", 0)),
            "transaction_count": float(payload.get("transaction_count", 0)),
        }
    if settings.coinapi_key:
        response = requests.get(
            f"https://rest.coinapi.io/v1/assets/{asset.upper()}",
            headers={"X-CoinAPI-Key": settings.coinapi_key},
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json()
        row = rows[0] if isinstance(rows, list) and rows else {}
        return {
            "asset": asset.upper(),
            "source": "coinapi",
            "price_usd": float(row.get("price_usd", 0)),
            "volume_1day_usd": float(row.get("volume_1day_usd", 0)),
        }
    return {
        "asset": asset.upper(),
        "active_addresses": 125000,
        "transaction_count": 320000,
        "source": "sample",
    }
