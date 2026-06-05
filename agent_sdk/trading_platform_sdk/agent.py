from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentContext:
    user_id: str
    asset_type: str = "equity"
    risk_profile: str = "balanced"
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResult:
    symbol: str
    rating: str
    confidence: float
    rationale: list[str] = field(default_factory=list)


class Agent(ABC):
    name: str = "unnamed-agent"
    version: str = "0.1.0"

    @abstractmethod
    async def analyze(self, symbol: str, context: AgentContext) -> AgentResult:
        raise NotImplementedError

