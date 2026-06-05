import time
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


@dataclass
class CircuitState:
    state: str = "closed"
    failures: int = 0
    opened_at: float = 0.0
    last_failure_at: float = 0.0


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        failure_window_seconds: float = 30.0,
        recovery_timeout_seconds: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.failure_window_seconds = failure_window_seconds
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._states: dict[str, CircuitState] = {}

    def state_for(self, provider: str) -> str:
        state = self._states.get(provider, CircuitState())
        if state.state == "open" and time.time() - state.opened_at >= self.recovery_timeout_seconds:
            state.state = "half_open"
            self._states[provider] = state
        return state.state

    async def call(self, provider: str, func: Callable[[], Awaitable[T]]) -> T:
        if self.state_for(provider) == "open":
            raise CircuitOpenError(f"circuit open for {provider}")
        try:
            result = await func()
        except Exception:
            self.record_failure(provider)
            raise
        self.record_success(provider)
        return result

    def record_failure(self, provider: str) -> None:
        now = time.time()
        state = self._states.setdefault(provider, CircuitState())
        if now - state.last_failure_at > self.failure_window_seconds:
            state.failures = 0
        state.failures += 1
        state.last_failure_at = now
        if state.failures >= self.failure_threshold:
            state.state = "open"
            state.opened_at = now

    def record_success(self, provider: str) -> None:
        self._states[provider] = CircuitState()

    def snapshot(self) -> dict[str, dict[str, float | str | int]]:
        return {
            provider: {
                "state": self.state_for(provider),
                "failures": state.failures,
                "opened_at": state.opened_at,
            }
            for provider, state in self._states.items()
        }
