import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from backend.shared.redis_client import redis_client


@dataclass(frozen=True)
class EventEnvelope:
    topic: str
    event_type: str
    payload: dict
    published_at: str
    event_id: str
    correlation_id: str
    causation_id: str | None = None
    source: str = "unknown"
    schema_version: int = 1
    latency_budget_ms: int = 500


class EventBus:
    max_stream_length = 10000
    latency_budget_ms = 500

    def publish(
        self,
        topic: str,
        event_type: str,
        payload: dict,
        *,
        source: str = "unknown",
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, object]:
        started = time.perf_counter()
        event_id = str(uuid4())
        envelope = EventEnvelope(
            topic=topic,
            event_type=event_type,
            payload=payload,
            published_at=datetime.now(timezone.utc).isoformat(),
            event_id=event_id,
            correlation_id=correlation_id or event_id,
            causation_id=causation_id,
            source=source,
            latency_budget_ms=self.latency_budget_ms,
        )
        encoded = json.dumps(envelope.__dict__, default=str)
        redis_client.publish(topic, encoded)
        if hasattr(redis_client, "rpush"):
            redis_client.rpush(f"events:{topic}", encoded)
        stream_id = None
        if hasattr(redis_client, "xadd"):
            stream_id = redis_client.xadd(
                self.stream_name(topic),
                {"event": encoded},
                maxlen=self.max_stream_length,
                approximate=True,
            )
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        stream_depth = self.stream_depth(topic)
        subscriber_count = self.subscriber_count(topic)
        return {
            "event_id": event_id,
            "correlation_id": envelope.correlation_id,
            "topic": topic,
            "event_type": event_type,
            "published": True,
            "stream": self.stream_name(topic),
            "stream_id": stream_id,
            "latency_ms": latency_ms,
            "within_budget": latency_ms <= envelope.latency_budget_ms,
            "latency_budget_ms": envelope.latency_budget_ms,
            "fanout": {
                "publish_channel": topic,
                "stream": self.stream_name(topic),
                "subscriber_count": subscriber_count,
                "stream_depth": stream_depth,
                "max_stream_length": self.max_stream_length,
            },
            "delivery_guarantee": "at_least_once_stream_and_best_effort_pubsub",
        }

    def recent(self, topic: str, limit: int = 20) -> list[dict]:
        raw_events = self._recent_stream_events(topic, limit)
        if not raw_events and hasattr(redis_client, "lrange"):
            raw_events = redis_client.lrange(f"events:{topic}", max(0, -limit), -1)
        events = []
        for raw_event in raw_events or []:
            try:
                payload = raw_event.get("event") if isinstance(raw_event, dict) else raw_event
                events.append(json.loads(payload))
            except Exception:
                continue
        return events[-limit:]

    def by_correlation(self, correlation_id: str, topics: list[str], limit: int = 100) -> list[dict]:
        matched: list[dict] = []
        for topic in topics:
            for envelope in self.recent(topic, limit):
                if envelope.get("correlation_id") == correlation_id:
                    matched.append(envelope)
        return sorted(matched, key=lambda item: str(item.get("published_at", "")))

    def stream_depth(self, topic: str) -> int:
        stream = self.stream_name(topic)
        if hasattr(redis_client, "xlen"):
            try:
                return int(redis_client.xlen(stream))
            except Exception:
                return len(self._recent_stream_events(topic, self.max_stream_length))
        return len(self._recent_stream_events(topic, self.max_stream_length))

    def subscriber_count(self, topic: str) -> int:
        if hasattr(redis_client, "channels"):
            return len(getattr(redis_client, "channels", {}).get(topic, []))
        return 0

    def health(self, topics: list[str] | None = None) -> dict[str, object]:
        active_topics = topics or []
        stream_depths = {
            topic: self.stream_depth(topic)
            for topic in active_topics
        }
        queue_depth = sum(stream_depths.values())
        redis_info = {}
        if hasattr(redis_client, "info"):
            try:
                redis_info = dict(redis_client.info())
            except Exception:
                redis_info = {"status": "unavailable"}
        return {
            "latency_budget_ms": self.latency_budget_ms,
            "max_stream_length": self.max_stream_length,
            "stream_depths": stream_depths,
            "queue_depth": queue_depth,
            "within_queue_budget": queue_depth <= 1000,
            "redis_info": redis_info,
        }

    def ensure_consumer_group(self, topic: str, group: str) -> dict[str, object]:
        stream = self.stream_name(topic)
        if not hasattr(redis_client, "xgroup_create"):
            return {"stream": stream, "group": group, "created": False, "supported": False}
        try:
            redis_client.xgroup_create(stream, group, id="0", mkstream=True)
            created = True
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise
            created = False
        return {"stream": stream, "group": group, "created": created, "supported": True}

    def read_for_consumer(
        self,
        topic: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> list[dict[str, object]]:
        self.ensure_consumer_group(topic, group)
        if not hasattr(redis_client, "xreadgroup"):
            return []
        messages = redis_client.xreadgroup(
            group,
            consumer,
            {self.stream_name(topic): ">"},
            count=count,
            block=block_ms,
        )
        return self._decode_stream_messages(messages)

    def ack(self, topic: str, group: str, *stream_ids: str) -> int:
        if not stream_ids or not hasattr(redis_client, "xack"):
            return 0
        return int(redis_client.xack(self.stream_name(topic), group, *stream_ids))

    @staticmethod
    def stream_name(topic: str) -> str:
        return f"stream:{topic}"

    def _recent_stream_events(self, topic: str, limit: int) -> list[dict[str, str]]:
        if not hasattr(redis_client, "xrevrange"):
            return []
        rows = redis_client.xrevrange(self.stream_name(topic), count=limit)
        return [fields for _, fields in reversed(rows)]

    @staticmethod
    def _decode_stream_messages(messages) -> list[dict[str, object]]:
        decoded = []
        for stream_name, rows in messages or []:
            for stream_id, fields in rows:
                try:
                    envelope = json.loads(fields["event"])
                except Exception:
                    continue
                decoded.append(
                    {
                        "stream": stream_name,
                        "stream_id": stream_id,
                        "envelope": envelope,
                    }
                )
        return decoded


event_bus = EventBus()
