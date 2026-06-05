from datetime import date

from backend.shared.models import CorporateActionEvent


def fetch_corporate_actions(symbol: str) -> list[CorporateActionEvent]:
    if symbol.upper() == "AAPL":
        return [
            CorporateActionEvent(
                symbol="AAPL",
                effective_date=date(2020, 8, 31),
                action_type="split",
                ratio=4.0,
                source="sample",
            )
        ]
    return []
