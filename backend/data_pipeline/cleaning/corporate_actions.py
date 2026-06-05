from backend.shared.models import CorporateActionEvent, OHLCVBar


def adjust_for_corporate_actions(
    bars: list[OHLCVBar],
    actions: list[CorporateActionEvent],
) -> list[OHLCVBar]:
    adjusted = [(bar, {bar.symbol.upper()}) for bar in bars]
    for action in sorted(actions, key=lambda item: item.effective_date):
        action_symbol = action.symbol.upper()
        if action.action_type == "split" and action.ratio and action.ratio > 0:
            adjusted = [
                (
                    bar.model_copy(
                        update={
                            "open": bar.open / action.ratio,
                            "high": bar.high / action.ratio,
                            "low": bar.low / action.ratio,
                            "close": bar.close / action.ratio,
                            "adjusted_close": (bar.adjusted_close or bar.close) / action.ratio,
                            "volume": bar.volume * action.ratio,
                        }
                    ),
                    aliases,
                )
                if action_symbol in aliases and bar.timestamp.date() < action.effective_date
                else (bar, aliases)
                for bar, aliases in adjusted
            ]
        elif action.action_type == "dividend" and action.cash_amount:
            adjusted = [
                (
                    bar.model_copy(
                        update={"adjusted_close": max((bar.adjusted_close or bar.close) - action.cash_amount, 0)}
                    ),
                    aliases,
                )
                if action_symbol in aliases and bar.timestamp.date() < action.effective_date
                else (bar, aliases)
                for bar, aliases in adjusted
            ]
        elif action.action_type == "symbol_change" and action.new_symbol:
            adjusted = [
                (
                    bar.model_copy(update={"symbol": action.new_symbol.upper()}),
                    aliases | {action.new_symbol.upper()},
                )
                if action_symbol in aliases and bar.timestamp.date() >= action.effective_date
                else (bar, aliases)
                for bar, aliases in adjusted
            ]
    return [bar for bar, _aliases in adjusted]
