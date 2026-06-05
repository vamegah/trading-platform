def train_persona_model(events: list[dict]) -> dict[str, int | str]:
    return {"model": "persona_baseline", "events_seen": len(events), "status": "trained"}

