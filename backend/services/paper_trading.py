from datetime import datetime, timezone
from typing import Any

from backend.services.backtest_engine.cost_model import estimate_transaction_cost
from backend.services.execution_service.broker_connectors.base import BrokerOrder, SimulatedBroker
from backend.services.execution_service.order_router import OrderRouter, execution_precheck, route_order
from backend.services.execution_service.trade_journal import journal
from backend.shared.models import OrderRequest


class PaperTradingAccount:
    def __init__(self, balance: float = 100000.0, account_id: str = "paper-demo"):
        self.account_id = account_id
        self.balance = balance
        self.holdings: dict[str, float] = {}
        self.trades: list[dict[str, Any]] = []

    async def execute_signal_async(
        self,
        signal: dict[str, Any],
        order_context: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        plan = self._build_execution_plan(signal, order_context)
        if plan["status"] == "skipped":
            return plan

        broker = SimulatedBroker(mode="sandbox")
        router = OrderRouter(broker)
        route_result = await router.smart_route(
            symbol=str(plan["symbol"]),
            side=str(plan["side"]),
            quantity=float(plan["quantity"]),
            asset_type="equity",
            order_type="MARKET",
            urgency="normal",
            current_price=float(plan["price"]),
            daily_volume=float(signal.get("daily_volume", 1_000_000)),
        )
        return self._record_execution(signal, plan, _serialize_route_result(route_result))

    def execute_signal(
        self,
        signal: dict[str, Any],
        order_context: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        plan = self._build_execution_plan(signal, order_context)
        if plan["status"] == "skipped":
            return plan

        routed = route_order(
            OrderRequest(
                symbol=str(plan["symbol"]),
                side=str(plan["side"]),
                quantity=float(plan["quantity"]),
                order_type="market",
            )
        )
        route_result = {
            "status": "routed",
            "strategy": "MARKET",
            "broker": "paper-sync-router",
            "mode": "sandbox",
            "orders": [routed],
        }
        return self._record_execution(signal, plan, route_result)

    def _build_execution_plan(
        self,
        signal: dict[str, Any],
        order_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        symbol = str(signal["symbol"]).upper()
        action = str(signal.get("signal") or signal.get("recommendation") or "HOLD").upper()
        price = float(signal.get("price", 100.0))
        confidence = float(signal.get("confidence", 0.0))
        stale_signal = bool(
            signal.get("auto_cancel")
            or signal.get("signal_freshness", {}).get("stale_order_action") == "cancel_pending_orders"
        )
        precheck_payload = {
            "mode": "paper",
            "suitability_completed": True,
            "automation_consent": True,
            "stale_signal": stale_signal,
            **(order_context or {}),
        }
        precheck = execution_precheck(precheck_payload)
        if not precheck["allowed"]:
            return {
                "status": "skipped",
                "reason": "execution precheck failed",
                "symbol": symbol,
                "precheck": precheck,
            }
        if confidence < 0.55 or action == "HOLD":
            return {
                "status": "skipped",
                "reason": "low confidence or hold signal",
                "symbol": symbol,
                "precheck": precheck,
            }

        if action == "BUY":
            requested_notional = float(signal.get("position_size") or self.balance * 0.05)
            trade_value = min(max(requested_notional, 0.0), self.balance * 0.1, self.balance * 0.95)
            quantity = int(trade_value / price)
            side = "BUY"
            if quantity <= 0:
                return {
                    "status": "skipped",
                    "reason": "insufficient funds",
                    "symbol": symbol,
                    "precheck": precheck,
                }
        else:
            quantity = self.holdings.get(symbol, 0)
            side = "SELL"
            if quantity <= 0:
                return {
                    "status": "skipped",
                    "reason": "no position",
                    "symbol": symbol,
                    "precheck": precheck,
                }

        return {
            "status": "planned",
            "symbol": symbol,
            "action": action,
            "side": side,
            "quantity": quantity,
            "price": price,
            "precheck": precheck,
        }

    def _record_execution(
        self,
        signal: dict[str, Any],
        plan: dict[str, Any],
        route_result: dict[str, Any],
    ) -> dict[str, object]:
        symbol = str(plan["symbol"])
        action = str(plan["action"])
        quantity = float(plan["quantity"])
        price = float(plan["price"])
        side = str(plan["side"])
        cost = estimate_transaction_cost(
            symbol,
            side,
            quantity,
            price,
            daily_volume=float(signal.get("daily_volume", 1_000_000)),
        )
        gross_notional = quantity * price
        if side == "BUY":
            self.balance -= gross_notional + cost.total_cost
            self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
            net_cash_change = -(gross_notional + cost.total_cost)
        else:
            self.balance += gross_notional - cost.total_cost
            self.holdings.pop(symbol, None)
            net_cash_change = gross_notional - cost.total_cost

        trade = {
            "paper_account_id": self.account_id,
            "symbol": symbol,
            "action": action,
            "side": side,
            "quantity": quantity,
            "price": price,
            "gross_notional": round(gross_notional, 2),
            "net_cash_change": round(net_cash_change, 2),
            "cost": round(cost.total_cost, 2),
            "estimated_transaction_cost": cost.__dict__,
            "precheck": plan["precheck"],
            "router_status": route_result.get("status"),
            "route_result": route_result,
            "execution_model": "paper_uses_live_order_router",
            "paper_execution_parity": {
                "same_precheck_as_live": True,
                "same_order_router_contract": True,
                "same_cost_model_as_backtest": True,
            },
            "model_version_id": signal.get("model_version_id"),
            "data_snapshot_id": signal.get("data_snapshot_id"),
            "factor_exposures": signal.get("factor_exposures", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.trades.append(trade)
        journal_entry = journal.log_trade(trade, signal)
        return {"status": "executed", **trade, "journal_entry": journal_entry}

    def get_balance(self) -> dict[str, object]:
        return {
            "account_id": self.account_id,
            "balance": round(self.balance, 2),
            "holdings": self.holdings,
            "equity_estimate": round(self.balance + sum(quantity * 100.0 for quantity in self.holdings.values()), 2),
        }


def _serialize_route_result(route_result: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(route_result)
    orders = []
    for order in serialized.get("orders", []):
        if isinstance(order, BrokerOrder):
            payload = order.__dict__.copy()
            payload["timestamp"] = order.timestamp.isoformat()
            orders.append(payload)
        else:
            orders.append(order)
    serialized["orders"] = orders
    return serialized


account = PaperTradingAccount()
