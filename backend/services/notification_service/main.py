import json
import os
from collections.abc import Callable, Iterable
from typing import Any

import redis

try:
    from firebase_admin import messaging
except ImportError:
    messaging = None


def get_user_fcm_tokens() -> list[str]:
    tokens = os.getenv("FCM_TOKENS", "")
    return [token.strip() for token in tokens.split(",") if token.strip()]


def _messaging_client():
    if messaging is None:
        raise RuntimeError("firebase-admin is required to run the notification worker")
    return messaging


def build_signal_message(signal: dict[str, object], token: str) -> Any:
    client = _messaging_client()
    return client.Message(
        notification=client.Notification(
            title=f"{signal['symbol']} {signal['direction']}",
            body=f"Conviction: {float(signal['conviction']):.0%} - {signal['summary']}",
        ),
        token=token,
    )


def process_signal(
    signal: dict[str, object],
    tokens: Iterable[str],
    sender: Callable[[Any], object] | None = None,
) -> int:
    sender = sender or _messaging_client().send
    sent = 0
    for token in tokens:
        sender(build_signal_message(signal, token))
        sent += 1
    return sent


def run_worker(channel: str = "signals:high_conviction") -> None:
    client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    pubsub = client.pubsub()
    pubsub.subscribe(channel)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        signal = json.loads(message["data"])
        process_signal(signal, get_user_fcm_tokens())


if __name__ == "__main__":
    run_worker()
