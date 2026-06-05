from typing import Optional

from backend.shared.config import settings
from backend.services.execution_service.broker_connectors.base import (
    BaseBroker,
    BrokerCapabilities,
    BrokerConfigurationError,
    BrokerOrder,
)


class AlpacaBroker(BaseBroker):
    name = "alpaca"

    def __init__(
        self,
        mode: str = "sandbox",
        api_key: str | None = None,
        api_secret: str | None = None,
        certified_live: bool = False,
    ):
        super().__init__(mode)
        self.api_key = api_key or settings.alpaca_api_key
        self.api_secret = api_secret or settings.alpaca_api_secret
        self.certified_live = certified_live

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker=self.name,
            mode=self.mode,
            asset_classes=("equity", "etf"),
            order_types=("MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP"),
            supports_fractional=True,
            supports_shorting=True,
            supports_margin=True,
            supports_streaming=True,
            supports_automated=self.certified_live,
            max_order_notional=500000.0 if self.mode == "sandbox" else 250000.0,
            max_participation_rate=0.15,
            requires_credentials=self.live_mode,
            certified_live=self.certified_live,
        )

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "LIMIT",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> BrokerOrder:
        if self.live_mode:
            if not self.api_key or not self.api_secret:
                raise BrokerConfigurationError("alpaca live mode requires API key and secret")
            self.ensure_live_ready()
        return self._record_fill(
            symbol,
            side,
            quantity,
            limit_price or stop_price or 100.0,
            order_type,
            limit_price,
            stop_price,
        )

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        return self.orders[broker_order_id]

    async def cancel_order(self, broker_order_id: str) -> bool:
        if broker_order_id in self.orders:
            self.orders[broker_order_id].status = "CANCELED"
            return True
        return False

    async def get_positions(self) -> dict[str, float]:
        return dict(self.positions)

    async def get_account_value(self) -> float:
        return self.cash + sum(quantity * 100.0 for quantity in self.positions.values())
