from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    user_id: str
    portfolio_id: str | None = None
    risk_profile: str = "balanced"


class ThirdPartyAgent(ABC):
    name: str
    version: str
    supported_asset_types: tuple[str, ...] = ("equity",)

    @abstractmethod
    async def analyze(self, symbol: str, context: AgentContext) -> dict:
        raise NotImplementedError

