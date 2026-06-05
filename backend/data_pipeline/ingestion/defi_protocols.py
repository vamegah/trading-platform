from backend.shared.config import settings


def fetch_defi_protocol_metrics(protocol: str) -> dict[str, str | float]:
    if settings.is_production and not settings.amberdata_api_key:
        raise RuntimeError("AMBERDATA_API_KEY is required for DeFi metrics in production")
    return {
        "protocol": protocol.lower(),
        "total_value_locked": 100000000.0,
        "fees_24h": 250000.0,
        "source": "local_sample",
    }
