from datetime import datetime, timezone
from typing import Any


class TradeJournal:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def log_trade(self, trade: dict[str, Any], signal: dict[str, Any] | None = None) -> dict[str, Any]:
        signal = signal or {}
        attribution = self.attribute_trade(trade, signal)
        entry = {
            "journal_id": f"journal-{len(self.entries) + 1}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trade": trade,
            "signal_source": signal.get("source", "signal_orchestrator"),
            "symbol": signal.get("symbol", trade.get("symbol")),
            "model_version_id": signal.get("model_version_id") or trade.get("model_version_id"),
            "data_snapshot_id": signal.get("data_snapshot_id") or trade.get("data_snapshot_id"),
            "trade_tags": self._trade_tags(trade, signal),
            "attribution": attribution,
        }
        self.entries.append(entry)
        return entry

    def attribute_trade(self, trade: dict[str, Any], signal: dict[str, Any]) -> dict[str, Any]:
        confidence = float(signal.get("confidence", 0.0))
        factors = (
            signal.get("factor_exposures")
            or signal.get("agent_outputs", {}).get("factor_tagging", {}).get("factor_exposures", {})
        )
        factor_score = round(sum(float(value) for value in factors.values()), 4) if factors else 0.0
        side = str(trade.get("action") or trade.get("side") or "BUY").upper()
        cost = float(trade.get("cost", 0.0))
        gross_notional = max(float(trade.get("gross_notional", 0.0)), 1.0)
        return {
            "selection_skill": round(confidence * 0.45, 4),
            "timing_skill": round((confidence - 0.5) * 0.25, 4),
            "factor_contribution": factor_score,
            "execution_drag": round(-cost, 4),
            "execution_drag_bps": round((cost / gross_notional) * -10000, 4),
            "side": side,
            "factor_breakdown": {key: round(float(value), 4) for key, value in factors.items()},
            "source_breakdown": {
                "selection": round(confidence * 0.45, 4),
                "timing": round((confidence - 0.5) * 0.25, 4),
                "factor": factor_score,
                "execution": round(-cost, 4),
            },
        }

    def list_entries(self) -> list[dict[str, Any]]:
        return self.entries

    def _trade_tags(self, trade: dict[str, Any], signal: dict[str, Any]) -> list[str]:
        tags = ["paper" if trade.get("paper_account_id") else "live"]
        if signal.get("signal"):
            tags.append(f"signal:{str(signal['signal']).lower()}")
        if trade.get("precheck", {}).get("allowed") is True:
            tags.append("prechecked")
        if trade.get("estimated_transaction_cost"):
            tags.append("costed")
        if signal.get("model_version_id"):
            tags.append("model_versioned")
        if signal.get("data_snapshot_id"):
            tags.append("snapshot_linked")
        return tags


journal = TradeJournal()
