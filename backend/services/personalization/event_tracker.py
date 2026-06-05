def track_event(event: dict) -> dict[str, object]:
    return {
        "status": "accepted",
        "event_type": event.get("event_type", "unknown"),
        "user_id": event.get("user_id"),
    }

