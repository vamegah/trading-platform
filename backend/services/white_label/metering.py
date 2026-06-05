def record_usage(partner_id: str, endpoint: str, units: int = 1) -> dict[str, str | int]:
    return {"partner_id": partner_id, "endpoint": endpoint, "units": units, "status": "recorded"}

