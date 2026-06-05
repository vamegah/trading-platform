import time
from dataclasses import dataclass


class RateLimitExceeded(RuntimeError):
    pass


@dataclass
class Bucket:
    capacity: float
    tokens: float
    refill_per_second: float
    updated_at: float


class CostGovernor:
    def __init__(self) -> None:
        self.buckets: dict[str, Bucket] = {}
        self.usage: dict[str, float] = {}

    def allow(
        self,
        key: str,
        units: float = 1,
        per_minute: float = 60,
        priority: str = "normal",
    ) -> bool:
        bucket = self.buckets.get(key)
        now = time.time()
        if not bucket:
            bucket = Bucket(per_minute, per_minute, per_minute / 60, now)
            self.buckets[key] = bucket
        elapsed = max(0.0, now - bucket.updated_at)
        bucket.tokens = min(bucket.capacity, bucket.tokens + elapsed * bucket.refill_per_second)
        bucket.updated_at = now
        if bucket.tokens >= units:
            bucket.tokens -= units
            self.usage[key] = self.usage.get(key, 0.0) + units
            return True
        if priority == "realtime":
            self.usage[f"{key}:overage"] = self.usage.get(f"{key}:overage", 0.0) + units
            return True
        raise RateLimitExceeded(f"rate limit exceeded for {key}")

    def record_llm_tokens(self, model: str, purpose: str, tokens: int) -> None:
        self.usage[f"llm:{model}:{purpose}:tokens"] = self.usage.get(f"llm:{model}:{purpose}:tokens", 0.0) + tokens

    def snapshot(self) -> dict[str, object]:
        return {
            "usage": dict(self.usage),
            "buckets": {
                key: {"capacity": bucket.capacity, "tokens": round(bucket.tokens, 2)}
                for key, bucket in self.buckets.items()
            },
        }
