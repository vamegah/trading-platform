import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, TypeVar

from backend.shared.redis_client import redis_client

T = TypeVar("T")


@dataclass(frozen=True)
class CacheResult:
    key: str
    hit: bool
    latency_ms: float
    value: object
    ttl_seconds: int
    namespace: str
    expires_at: str | None


_cache_metrics = {
    "hits": 0,
    "misses": 0,
    "sets": 0,
}


def _namespace(key: str) -> str:
    return key.split(":", 1)[0] if ":" in key else "default"


def cache_get_or_set(key: str, ttl_seconds: int, producer: Callable[[], T]) -> CacheResult:
    started = time.perf_counter()
    cached = redis_client.get(key)
    if cached:
        _cache_metrics["hits"] += 1
        return CacheResult(
            key,
            True,
            round((time.perf_counter() - started) * 1000, 3),
            json.loads(cached),
            ttl_seconds,
            _namespace(key),
            None,
        )
    value = producer()
    redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
    _cache_metrics["misses"] += 1
    _cache_metrics["sets"] += 1
    return CacheResult(
        key,
        False,
        round((time.perf_counter() - started) * 1000, 3),
        value,
        ttl_seconds,
        _namespace(key),
        (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat(),
    )


def cache_set(key: str, value: object, ttl_seconds: int = 60) -> None:
    redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
    _cache_metrics["sets"] += 1


def cache_stats() -> dict[str, object]:
    total = _cache_metrics["hits"] + _cache_metrics["misses"]
    hit_rate = _cache_metrics["hits"] / total if total else 0.0
    return {
        **_cache_metrics,
        "requests": total,
        "hit_rate": round(hit_rate, 4),
        "target_hit_rate": 0.9,
        "within_target": hit_rate >= 0.9 if total else True,
    }


def instrument_cache_key(symbol: str) -> str:
    return f"instrument:{symbol.upper()}"


def scanner_cache_key(
    universe: list[str],
    min_confidence: float,
    factor: str | None = None,
    sector: str | None = None,
    custom_criteria: dict | None = None,
) -> str:
    normalized = ",".join(sorted(symbol.upper() for symbol in universe))
    criteria = json.dumps(custom_criteria or {}, sort_keys=True)
    return f"scanner:{normalized}:{min_confidence}:{factor or 'any'}:{sector or 'any'}:{criteria}"
