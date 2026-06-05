import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from backend.services.execution_service.broker_registry import broker_supports_order, broker_supports_quantity
from backend.services.execution_service.broker_connectors.base import BaseBroker, BrokerConfigurationError, BrokerOrder
from backend.shared.config import settings
from backend.shared.security import Permission, has_permission


@dataclass(frozen=True)
class MarketImpactEstimate:
    expected_execution_price: float
    impact_cost_bps: float
    permanent_impact_bps: float
    temporary_impact_bps: float
    assumed_daily_volume: float
    participation_rate: float


class AlmgrenChrissImpactModel:
    def __init__(
        self,
        eta: float | None = None,
        gamma: float | None = None,
        beta: float | None = None,
        default_daily_volume: float | None = None,
    ):
        self.eta = eta if eta is not None else settings.market_impact_eta
        self.gamma = gamma if gamma is not None else settings.market_impact_gamma
        self.beta = beta if beta is not None else settings.market_impact_beta
        self.default_daily_volume = (
            default_daily_volume
            if default_daily_volume is not None
            else settings.market_impact_default_daily_volume
        )

    def estimate(
        self,
        symbol: str,
        order_size: float,
        side: str,
        current_price: float,
        daily_volume: float | None = None,
        volatility: float | None = None,
    ) -> MarketImpactEstimate:
        assumed_daily_volume = max(daily_volume or self.default_daily_volume, 1.0)
        participation = min(abs(order_size) / assumed_daily_volume, 1.0)
        sigma = volatility if volatility is not None else settings.market_impact_default_volatility

        permanent_impact = self.eta * participation
        temporary_impact = self.gamma * (participation**self.beta) * sigma
        direction = 1 if side.upper() == "BUY" else -1
        expected_price = current_price * (1 + direction * (permanent_impact + temporary_impact))

        return MarketImpactEstimate(
            expected_execution_price=round(expected_price, 4),
            impact_cost_bps=round(abs(expected_price - current_price) / current_price * 10000, 2),
            permanent_impact_bps=round(abs(permanent_impact) * 10000, 2),
            temporary_impact_bps=round(abs(temporary_impact) * 10000, 2),
            assumed_daily_volume=assumed_daily_volume,
            participation_rate=round(participation, 6),
        )


class OrderRouter:
    def __init__(self, broker: BaseBroker, impact_model: AlmgrenChrissImpactModel | None = None):
        self.broker = broker
        self.impact_model = impact_model or AlmgrenChrissImpactModel()

    async def execute_twap(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        duration_minutes: int = 5,
        slices: int = 10,
        sleep_seconds: float = 0.0,
    ) -> dict[str, object]:
        quantity_per_slice = total_quantity / max(slices, 1)
        interval = sleep_seconds if sleep_seconds else 0.0
        orders: list[BrokerOrder] = []

        for index in range(max(slices, 1)):
            orders.append(
                await self.broker.place_order(
                    symbol,
                    side,
                    quantity_per_slice,
                    order_type="MARKET",
                )
            )
            if interval and index < slices - 1:
                await asyncio.sleep(interval)

        return {
            "symbol": symbol.upper(),
            "strategy": "TWAP",
            "orders": orders,
            "filled_quantity": sum(order.filled_quantity for order in orders),
            "child_order_count": len(orders),
        }

    async def execute_vwap(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        duration_minutes: int = 5,
        sleep_seconds: float = 0.0,
    ) -> dict[str, object]:
        volume_curve = await self._get_volume_curve(symbol)
        orders: list[BrokerOrder] = []
        for minute, volume_fraction in volume_curve.items():
            quantity = total_quantity * volume_fraction
            orders.append(await self.broker.place_order(symbol, side, quantity, order_type="MARKET"))
            if sleep_seconds and minute < duration_minutes - 1:
                await asyncio.sleep(sleep_seconds)

        return {
            "symbol": symbol.upper(),
            "strategy": "VWAP",
            "orders": orders,
            "filled_quantity": sum(order.filled_quantity for order in orders),
            "child_order_count": len(orders),
        }

    def estimate_market_impact(
        self,
        symbol: str,
        side: str,
        quantity: float,
        current_price: float,
        daily_volume: float | None = None,
        volatility: float | None = None,
    ) -> dict[str, float]:
        estimate = self.impact_model.estimate(
            symbol=symbol,
            order_size=quantity,
            side=side,
            current_price=current_price,
            daily_volume=daily_volume,
            volatility=volatility,
        )
        return estimate.__dict__

    async def execute_iceberg(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        visible_quantity: float,
        limit_price: float = 100.0,
    ) -> dict[str, object]:
        orders: list[BrokerOrder] = []
        remaining = total_quantity
        while remaining > 0:
            slice_quantity = min(visible_quantity, remaining)
            orders.append(
                await self.broker.place_order(
                    symbol,
                    side,
                    slice_quantity,
                    order_type="LIMIT",
                    limit_price=limit_price,
                )
            )
            remaining -= slice_quantity
        return {
            "symbol": symbol.upper(),
            "strategy": "ICEBERG",
            "orders": orders,
            "filled_quantity": sum(order.filled_quantity for order in orders),
            "visible_quantity": visible_quantity,
            "child_order_count": len(orders),
        }

    def choose_strategy(
        self,
        quantity: float,
        daily_volume: float,
        urgency: str = "normal",
        order_type: str = "MARKET",
    ) -> str:
        participation = abs(quantity) / max(daily_volume, 1.0)
        normalized_urgency = urgency.lower()
        if order_type.upper() in {"LIMIT", "STOP", "STOP_LIMIT"} and participation < 0.03:
            return order_type.upper()
        if normalized_urgency == "high" and participation < 0.05:
            return "MARKET"
        if participation >= 0.2:
            return "ICEBERG"
        if participation >= 0.08:
            return "VWAP"
        if normalized_urgency in {"low", "patient"}:
            return "TWAP"
        return "LIMIT" if order_type.upper() == "LIMIT" else "MARKET"

    def route_decision(
        self,
        quantity: float,
        daily_volume: float,
        urgency: str = "normal",
        order_type: str = "MARKET",
    ) -> dict[str, object]:
        participation = abs(quantity) / max(daily_volume, 1.0)
        strategy = self.choose_strategy(quantity, daily_volume, urgency, order_type)
        if strategy == order_type.upper() and order_type.upper() in {"LIMIT", "STOP", "STOP_LIMIT"}:
            reason = "explicit_order_type_low_participation"
        elif strategy == "MARKET":
            reason = "high_urgency_low_participation" if urgency.lower() == "high" else "normal_urgency_low_participation"
        elif strategy == "TWAP":
            reason = "patient_urgency_time_slicing"
        elif strategy == "VWAP":
            reason = "medium_participation_volume_slicing"
        else:
            reason = "high_participation_iceberg"
        return {
            "strategy": strategy,
            "reason": reason,
            "participation_rate": round(participation, 6),
            "urgency": urgency,
            "requested_order_type": order_type.upper(),
        }

    async def smart_route(
        self,
        symbol: str,
        side: str,
        quantity: float,
        asset_type: str = "equity",
        order_type: str = "MARKET",
        urgency: str = "normal",
        current_price: float = 100.0,
        daily_volume: float = 1_000_000,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> dict[str, object]:
        notional = abs(quantity) * current_price
        decision = self.route_decision(quantity, daily_volume, urgency, order_type)
        chosen = str(decision["strategy"])
        route_id = f"route-{uuid4()}"
        caps = self.broker.capabilities()
        supported, violations = broker_supports_order(self.broker, asset_type, chosen, notional)
        quantity_supported, quantity_violations = broker_supports_quantity(self.broker, quantity)
        violations.extend(quantity_violations)
        capacity_warning = float(decision["participation_rate"]) > caps.max_participation_rate
        if not supported:
            return {
                "status": "rejected",
                "route_id": route_id,
                "violations": violations,
                "strategy": chosen,
                "broker": caps.broker,
                "mode": caps.mode,
                "route_decision": decision,
                "alternate_strategy": "LIMIT" if "unsupported_order_type" in violations and "LIMIT" in caps.order_types else None,
            }
        if not quantity_supported:
            return {
                "status": "rejected",
                "route_id": route_id,
                "violations": violations,
                "strategy": chosen,
                "broker": caps.broker,
                "mode": caps.mode,
                "route_decision": decision,
            }
        impact = self.estimate_market_impact(symbol, side, quantity, current_price, daily_volume)
        try:
            if chosen == "TWAP":
                result = await self.execute_twap(symbol, side, quantity, slices=5)
            elif chosen == "VWAP":
                result = await self.execute_vwap(symbol, side, quantity)
            elif chosen == "ICEBERG":
                result = await self.execute_iceberg(
                    symbol,
                    side,
                    quantity,
                    visible_quantity=max(1, quantity * 0.1),
                    limit_price=limit_price or current_price,
                )
            else:
                order = await self.broker.place_order(
                    symbol,
                    side,
                    quantity,
                    order_type=chosen,
                    limit_price=limit_price or current_price if chosen == "LIMIT" else None,
                    stop_price=stop_price,
                )
                result = {
                    "symbol": symbol.upper(),
                    "strategy": chosen,
                    "orders": [order],
                    "filled_quantity": order.filled_quantity,
                    "child_order_count": 1,
                }
        except BrokerConfigurationError as exc:
            return {
                "status": "rejected",
                "route_id": route_id,
                "violations": ["broker_configuration_error"],
                "reason": str(exc),
                "strategy": chosen,
                "broker": caps.broker,
                "mode": caps.mode,
                "route_decision": decision,
            }
        orders = [_order_payload(order) for order in result.get("orders", [])]
        return {
            **result,
            "status": "routed",
            "route_id": route_id,
            "broker": caps.broker,
            "mode": caps.mode,
            "market_impact": impact,
            "route_decision": decision,
            "execution_plan": {
                "route_id": route_id,
                "symbol": symbol.upper(),
                "side": side.upper(),
                "strategy": chosen,
                "notional": round(notional, 2),
                "participation_rate": decision["participation_rate"],
                "capacity_warning": capacity_warning,
                "max_participation_rate": caps.max_participation_rate,
                "child_order_count": result.get("child_order_count", len(orders)),
                "created_at": datetime.now(UTC).isoformat(),
            },
            "order_events": orders,
            "routing_warnings": ["capacity_warning"] if capacity_warning else [],
        }

    async def _get_volume_curve(self, symbol: str) -> dict[int, float]:
        return {0: 0.18, 1: 0.22, 2: 0.2, 3: 0.22, 4: 0.18}


def route_order(order) -> dict[str, str | float]:
    return {
        "service": "execution_service",
        "status": "accepted",
        "symbol": order.symbol.upper(),
        "quantity": order.quantity,
    }


def _order_payload(order: BrokerOrder | dict) -> dict[str, object]:
    if isinstance(order, dict):
        return order
    return {
        "broker_order_id": order.broker_order_id,
        "status": order.status,
        "symbol": order.symbol,
        "side": order.side,
        "order_type": order.order_type,
        "filled_quantity": order.filled_quantity,
        "average_price": order.average_price,
        "commission": order.commission,
        "timestamp": order.timestamp.isoformat(),
    }


def execution_precheck(payload: dict) -> dict[str, object]:
    violations = []
    mode = str(payload.get("mode", "manual")).lower()
    broker_mode = str(payload.get("broker_mode", payload.get("account_mode", "sandbox"))).lower()
    risk_breach_events = list(payload.get("risk_breach_events") or [])
    live_risk_result = payload.get("live_risk_result") or payload.get("risk_monitor") or {}
    if isinstance(live_risk_result, dict):
        risk_breach_events.extend(live_risk_result.get("risk_breach_events", []))

    def add_violation(name: str) -> None:
        if name not in violations:
            violations.append(name)

    if not payload.get("suitability_completed", False):
        add_violation("suitability_required")
    suitability_decision = payload.get("suitability_decision") or {}
    if isinstance(suitability_decision, dict):
        requested_strategy = payload.get("requested_strategy") or mode
        if requested_strategy in suitability_decision.get("restricted_strategies", []):
            add_violation("suitability_restricted_strategy")
        if mode == "automated" and suitability_decision.get("automation_allowed") is False:
            add_violation("suitability_restricted_strategy")
    if payload.get("auth_token_valid") is False or payload.get("authenticated") is False:
        add_violation("auth_required")
    roles = payload.get("roles")
    if roles is not None:
        required_permission = (
            Permission.TRADE_AUTOMATED
            if mode == "automated"
            else Permission.TRADE_ONE_CLICK
            if mode in {"one_click", "live"}
            else None
        )
        if required_permission and not has_permission(roles, required_permission):
            add_violation(f"missing_permission:{required_permission.value}")
    if payload.get("risk_breach", False) or risk_breach_events:
        add_violation("portfolio_risk_breach")
    if payload.get("stale_signal", False):
        add_violation("stale_signal")
    if payload.get("kill_switch_active", False):
        add_violation("kill_switch_active")
    if isinstance(live_risk_result, dict) and live_risk_result.get("kill_switch_required", False):
        add_violation("kill_switch_active")
    if payload.get("manual_pause_active", False):
        add_violation("manual_pause_active")
    if mode == "one_click" and not (
        payload.get("one_click_acknowledged", False)
        or payload.get("order_preview_acknowledged", False)
    ):
        add_violation("one_click_acknowledgement_required")
    if mode == "automated" and not payload.get("automation_consent", False):
        add_violation("automation_consent_required")
    if mode == "automated" and not (
        payload.get("automation_acknowledgement_signed", False)
        or payload.get("signed_acknowledgement_id")
    ):
        add_violation("signed_automation_acknowledgement_required")
    if (mode == "live" or broker_mode == "live") and not payload.get("live_trading_acknowledged", False):
        add_violation("live_trading_acknowledgement_required")
    if (mode == "live" or broker_mode == "live") and not (
        payload.get("signed_live_agreement_id")
        or payload.get("live_trading_agreement_signed", False)
    ):
        add_violation("signed_live_agreement_required")

    cancel_pending_orders = bool(violations)
    required_actions = sorted(
        {
            str(event.get("action"))
            for event in risk_breach_events
            if isinstance(event, dict) and event.get("action")
        }
    )
    if cancel_pending_orders and "cancel_pending_orders" not in required_actions:
        required_actions.append("cancel_pending_orders")
    return {
        "allowed": not violations,
        "mode": mode,
        "violations": violations,
        "risk_breach_events": risk_breach_events,
        "new_orders_blocked": bool(violations),
        "cancel_pending_orders": cancel_pending_orders,
        "manual_review_required": bool(violations),
        "required_actions": required_actions,
        "violation_details": [
            {
                "code": violation,
                "severity": "critical" if violation in {"portfolio_risk_breach", "kill_switch_active"} else "blocking",
            }
            for violation in violations
        ],
        "consent_requirements": {
            "one_click_acknowledged": mode != "one_click"
            or bool(payload.get("one_click_acknowledged") or payload.get("order_preview_acknowledged")),
            "automation_consent": mode != "automated" or bool(payload.get("automation_consent")),
            "automation_acknowledgement_signed": mode != "automated"
            or bool(payload.get("automation_acknowledgement_signed") or payload.get("signed_acknowledgement_id")),
            "live_trading_acknowledged": (mode != "live" and broker_mode != "live")
            or bool(payload.get("live_trading_acknowledged")),
            "live_agreement_signed": (mode != "live" and broker_mode != "live")
            or bool(payload.get("signed_live_agreement_id") or payload.get("live_trading_agreement_signed")),
        },
        "auth_checked": payload.get("auth_token_valid") is not None or payload.get("authenticated") is not None,
        "reason": "Order passed risk checks." if not violations else "Order failed closed.",
    }
