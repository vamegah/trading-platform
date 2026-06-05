import asyncio
import time
from typing import Any, Awaitable, Callable

from backend.shared.audit import audit_chain
from backend.shared.config import settings
from backend.shared.external_api.circuit_breaker import CircuitBreaker
from backend.shared.external_api.cost_governor import CostGovernor


class ExternalAPIError(RuntimeError):
    pass


class ExternalAPIRouter:
    def __init__(
        self,
        circuit_breaker: CircuitBreaker | None = None,
        cost_governor: CostGovernor | None = None,
    ) -> None:
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.cost_governor = cost_governor or CostGovernor()

    async def call(
        self,
        provider: str,
        endpoint: str,
        func: Callable[[], Awaitable[Any]],
        timeout_ms: int = 1000,
        rate_limit_per_minute: int = 60,
        priority: str = "normal",
        audit_payload: dict[str, Any] | None = None,
    ) -> Any:
        self.cost_governor.allow(
            f"{provider}:{endpoint}",
            units=1,
            per_minute=rate_limit_per_minute,
            priority=priority,
        )
        started = time.perf_counter()
        status = "success"
        try:
            result = await self.circuit_breaker.call(
                provider,
                lambda: asyncio.wait_for(func(), timeout=timeout_ms / 1000),
            )
            return result
        except Exception as exc:
            status = exc.__class__.__name__
            raise
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            details = {
                "provider": provider,
                "endpoint": endpoint,
                "status": status,
                "latency_ms": latency_ms,
                "environment": settings.environment,
                "payload": audit_payload or {},
            }
            audit_chain.append("external_api_call", details)

    def status(self) -> dict[str, object]:
        return {
            "circuit_breakers": self.circuit_breaker.snapshot(),
            "cost_governor": self.cost_governor.snapshot(),
        }


external_api_router = ExternalAPIRouter()
