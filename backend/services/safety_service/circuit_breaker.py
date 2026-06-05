from datetime import UTC, datetime

from backend.services.safety_service.black_swan_detector import BlackSwanDetector, BlackSwanSignal


class CircuitBreaker:
    def __init__(self, detector: BlackSwanDetector | None = None):
        self.detector = detector or BlackSwanDetector()
        self.manual_pause = False
        self.manual_reason: str | None = None
        self.halted_at: str | None = None
        self.halted_by: str | None = None

    def is_trading_allowed(self) -> bool:
        return not self.manual_pause

    def guard_order(self, order_context: dict | None = None) -> dict[str, object]:
        if self.manual_pause:
            return {
                "allowed": False,
                "reason": self.manual_reason or "Trading is manually paused.",
                "kill_switch_active": True,
                "new_orders_blocked": True,
                "cancel_pending_orders": True,
                "manual_review_required": True,
                "risk_breach_events": (order_context or {}).get("risk_breach_events", []),
            }
        risk_events = (order_context or {}).get("risk_breach_events", [])
        if order_context and (order_context.get("risk_breach") or risk_events):
            return {
                "allowed": False,
                "reason": "Portfolio risk breach blocks new orders.",
                "kill_switch_active": True,
                "new_orders_blocked": True,
                "cancel_pending_orders": True,
                "manual_review_required": True,
                "risk_breach_events": risk_events,
            }
        return {
            "allowed": True,
            "reason": "Trading allowed.",
            "kill_switch_active": False,
            "new_orders_blocked": False,
            "cancel_pending_orders": False,
            "manual_review_required": False,
            "risk_breach_events": [],
        }

    def trigger_halt(self, reason: str, admin_id: int | str) -> dict[str, object]:
        self.manual_pause = True
        self.halted_at = datetime.now(UTC).isoformat()
        self.halted_by = str(admin_id)
        self.manual_reason = f"halted by {admin_id}: {reason}"
        return {
            "trading_allowed": False,
            "reason": self.manual_reason,
            "halted_at": self.halted_at,
            "halted_by": self.halted_by,
            "new_orders_blocked": True,
            "cancel_pending_orders": True,
            "manual_review_required": True,
        }

    def resume_trading(self, admin_id: int | str) -> dict[str, object]:
        self.manual_pause = False
        self.manual_reason = None
        self.halted_at = None
        self.halted_by = None
        return {
            "trading_allowed": True,
            "resumed_by": str(admin_id),
            "new_orders_blocked": False,
            "cancel_pending_orders": False,
        }

    def monitor_auto(
        self,
        volatility_zscore: float,
        correlation_spike: float,
        liquidity_drop: float,
    ) -> BlackSwanSignal:
        signal = self.detector.evaluate(volatility_zscore, correlation_spike, liquidity_drop)
        if signal.triggered and signal.severity == "critical":
            self.manual_pause = True
            self.halted_at = datetime.now(UTC).isoformat()
            self.halted_by = "auto_monitor"
            self.manual_reason = f"auto halt: {', '.join(signal.reasons)}"
        return signal
