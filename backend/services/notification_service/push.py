def send_notification(message: str, channel: str = "push", priority: str = "normal") -> dict[str, str]:
    return {"status": "queued", "channel": channel, "priority": priority, "message": message}


def send_black_swan_alert(reason: str, severity: str = "critical") -> dict[str, str]:
    return send_notification(
        message=f"Black-swan alert: {reason}",
        channel="push",
        priority=severity,
    )
