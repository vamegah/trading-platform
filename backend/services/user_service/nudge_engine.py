class NudgeEngine:
    PANIC_SELL_THRESHOLD = -0.05
    FOMO_BUY_THRESHOLD = 3

    async def analyze_user_activity(self, user_id: str, recent_orders: list[dict] | None = None) -> list[dict]:
        orders = recent_orders or []
        nudges: list[dict] = []
        sells = [order for order in orders if order.get("side") == "SELL"]
        buys = [order for order in orders if order.get("side") == "BUY"]
        if len(sells) > 2:
            nudges.append(
                {
                    "user_id": user_id,
                    "event_type": "PANIC_SELL",
                    "severity": "medium",
                    "message": self.format_message("PANIC_SELL"),
                    "evidence": {
                        "sell_orders": len(sells),
                        "threshold": 2,
                        "behavior": "multiple recent sell orders",
                    },
                    "dismissible": True,
                }
            )
        if len(buys) >= self.FOMO_BUY_THRESHOLD:
            nudges.append(
                {
                    "user_id": user_id,
                    "event_type": "FOMO_BUY",
                    "severity": "low",
                    "message": self.format_message("FOMO_BUY"),
                    "evidence": {
                        "buy_orders": len(buys),
                        "threshold": self.FOMO_BUY_THRESHOLD,
                        "behavior": "rapid repeated buying",
                    },
                    "dismissible": True,
                }
            )
        return nudges

    def format_message(self, event_type: str) -> str:
        if event_type == "PANIC_SELL":
            return "Review your plan before selling into a sharp drawdown."
        if event_type == "FOMO_BUY":
            return "Multiple quick buys can increase concentration risk."
        return "Review your trading plan and risk limits."
