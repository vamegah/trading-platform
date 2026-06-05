from datetime import date, timedelta


class EarningsScanner:
    async def update_events(self, symbols: list[str] | None = None) -> list[dict]:
        return [
            {
                "symbol": symbol.upper(),
                "event_type": "EARNINGS",
                "event_date": date.today() + timedelta(days=14),
            }
            for symbol in (symbols or [])
        ]

    async def flag_positions_with_upcoming_events(self, positions: list[dict]) -> list[dict]:
        today = date.today()
        soon = today + timedelta(days=7)
        warnings = []
        for position in positions:
            event_date = position.get("event_date")
            if event_date and today <= event_date <= soon:
                warnings.append(
                    {
                        "symbol": position["symbol"].upper(),
                        "suggestion": "Consider reducing size or hedging before event risk.",
                    }
                )
        return warnings
