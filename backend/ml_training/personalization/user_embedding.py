def build_user_embedding(user_events: list[dict], dimensions: int = 8) -> list[float]:
    density = min(len(user_events) / 100, 1.0)
    return [round(density, 4) for _ in range(dimensions)]

