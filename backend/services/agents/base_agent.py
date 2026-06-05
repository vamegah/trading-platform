from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    def __init__(self, name: str, asset_type: str = "equity"):
        self.name = name
        self.asset_type = asset_type

    @abstractmethod
    async def analyze(self, symbol: str, asset_type: str | None = None, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError
