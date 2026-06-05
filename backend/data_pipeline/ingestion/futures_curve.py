import requests

from backend.shared.config import settings


def fetch_futures_curve(root_symbol: str) -> list[dict[str, str | float]]:
    if settings.amberdata_api_key:
        response = requests.get(
            "https://api.amberdata.com/markets/futures/curves",
            params={"instrument": root_symbol.upper()},
            headers={"x-api-key": settings.amberdata_api_key},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("payload", {}).get("data", payload.get("data", []))
        return [
            {
                "root_symbol": root_symbol.upper(),
                "contract": row.get("instrument") or row.get("contract"),
                "price": float(row.get("price", row.get("settlementPrice", 0))),
                "expiration": row.get("expiration"),
                "source": "amberdata",
            }
            for row in rows
        ]
    return [
        {"root_symbol": root_symbol.upper(), "contract": f"{root_symbol.upper()}M26", "price": 100.0, "source": "sample"},
        {"root_symbol": root_symbol.upper(), "contract": f"{root_symbol.upper()}U26", "price": 101.2, "source": "sample"},
    ]
