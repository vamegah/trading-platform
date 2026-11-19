import requests

from backend.shared.config import settings


def fetch_options_chain(symbol: str) -> list[dict[str, str | float]]:
    if settings.ivolatility_api_key:
        response = requests.get(
            "https://rest.ivolatility.com/equities/options",
            params={"symbol": symbol.upper()},
            headers={"Authorization": f"Bearer {settings.ivolatility_api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data", payload if isinstance(payload, list) else [])
        return [
            {
                "underlying": symbol.upper(),
                "expiration": row.get("expiration") or row.get("expiry"),
                "strike": float(row.get("strike", 0)),
                "type": str(row.get("type", row.get("optionType", "call"))).lower(),
                "bid": float(row.get("bid", 0)),
                "ask": float(row.get("ask", 0)),
                "implied_volatility": float(row.get("iv", row.get("implied_volatility", 0))),
                "delta": float(row.get("delta", 0)),
                "gamma": float(row.get("gamma", 0)),
                "theta": float(row.get("theta", 0)),
                "vega": float(row.get("vega", 0)),
                "open_interest": float(row.get("open_interest", row.get("openInterest", 0))),
                "source": "ivolatility",
            }
            for row in rows
        ]
    return [
        {
            "underlying": symbol.upper(),
            "expiration": "2026-06-19",
            "strike": 100.0,
            "type": "call",
            "bid": 2.1,
            "ask": 2.25,
            "implied_volatility": 0.34,
            "source": "sample",
        }
    ]
