import asyncio
import json
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from backend.shared.redis_client import redis_client

T = TypeVar("T")


@dataclass(frozen=True)
class AsyncCacheResult:
    key: str
    hit: bool
    stale: bool
    value: object


async def get_json(key: str) -> dict | list | None:
    cached = redis_client.get(key)
    if not cached:
        return None
    payload = json.loads(cached)
    if isinstance(payload, dict) and "_cache_written_at" in payload and "value" in payload:
        return payload
    return {"value": payload, "_cache_written_at": time.time()}


async def set_json(key: str, value: object, ttl_seconds: int) -> None:
    payload = {"value": value, "_cache_written_at": time.time()}
    redis_client.setex(key, ttl_seconds, json.dumps(payload, default=str))


async def stale_while_revalidate(
    key: str,
    ttl_seconds: int,
    stale_ttl_seconds: int,
    producer: Callable[[], Awaitable[T]],
) -> AsyncCacheResult:
    cached = await get_json(key)
    now = time.time()
    if isinstance(cached, dict) and "value" in cached:
        age = now - float(cached.get("_cache_written_at", now))
        if age <= ttl_seconds:
            return AsyncCacheResult(key, True, False, cached["value"])
        if age <= stale_ttl_seconds:
            asyncio.create_task(_refresh(key, ttl_seconds, producer))
            return AsyncCacheResult(key, True, True, cached["value"])
    value = await producer()
    await set_json(key, value, stale_ttl_seconds)
    return AsyncCacheResult(key, False, False, value)


async def _refresh(key: str, ttl_seconds: int, producer: Callable[[], Awaitable[T]]) -> None:
    try:
        await set_json(key, await producer(), ttl_seconds)
    except Exception:
        return
