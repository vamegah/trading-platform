from typing import Optional

from backend.services.execution_service.broker_connectors.base import (
    BaseBroker,
    BrokerCapabilities,
    BrokerConfigurationError,
    BrokerOrder,
)


class TDAmeritradeConnector(BaseBroker):
    name = "td_ameritrade"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker=self.name,
            mode="deferred",
            status="deferred",
            asset_classes=("equity", "option"),
            order_types=("MARKET", "LIMIT"),
            supports_cancel_replace=False,
            supports_order_preview=False,
            supports_one_click=False,
            supports_automated=False,
            max_order_notional=0.0,
            max_participation_rate=0.0,
            requires_credentials=True,
            requires_live_certification=True,
            certified_live=False,
            notes="TD Ameritrade retail APIs have migrated to Schwab; connector requires successor API credentials.",
        )

    def status(self) -> dict[str, str]:
        return {
            "broker": self.name,
            "status": "deferred",
            "successor": "schwab",
            "reason": "TD Ameritrade retail APIs have migrated to Schwab; connector requires successor API credentials.",
        }

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "LIMIT",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> BrokerOrder:
        raise BrokerConfigurationError(self.status()["reason"])

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        raise BrokerConfigurationError(self.status()["reason"])

    async def cancel_order(self, broker_order_id: str) -> bool:
        raise BrokerConfigurationError(self.status()["reason"])

    async def get_positions(self) -> dict[str, float]:
        return {}

    async def get_account_value(self) -> float:
        return 0.0
