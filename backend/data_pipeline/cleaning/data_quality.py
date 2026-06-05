from datetime import datetime, timedelta, timezone
from typing import Any


def _as_row_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "model_dump"):
        return row.model_dump()
    return dict(row)


def _coerce_timestamp(value: Any) -> datetime | None:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    if isinstance(value, datetime):
        return value
    return None


def validate_rows(
    rows: list[dict],
    as_of: datetime | None = None,
    stale_after: timedelta = timedelta(days=30),
    outlier_return_threshold: float = 0.5,
) -> dict[str, object]:
    reference = as_of or datetime.now(timezone.utc)
    errors = 0
    stale = 0
    missing = 0
    outliers = 0
    lookahead = 0
    reasons: list[dict[str, object]] = []
    previous_close_by_symbol: dict[str, float] = {}
    for index, raw_row in enumerate(rows):
        row = _as_row_dict(raw_row)
        row_reasons: list[str] = []
        is_tick = row.get("stream") == "price:ticks"
        if is_tick:
            if row.get("price") is None:
                missing += 1
                row_reasons.append("missing_price")
            if float(row.get("price", 0) or 0) <= 0:
                errors += 1
                row_reasons.append("non_positive_price")
        else:
            if row.get("open") is None or row.get("close") is None:
                missing += 1
                row_reasons.append("missing_open_or_close")
            if any(float(row.get(field, 0) or 0) < 0 for field in ("open", "high", "low", "close", "volume")):
                errors += 1
                row_reasons.append("negative_market_value")
            if float(row.get("volume", 0) or 0) == 0:
                stale += 1
                row_reasons.append("zero_volume")
            if row.get("high") is not None and row.get("low") is not None and float(row["high"]) < float(row["low"]):
                outliers += 1
                row_reasons.append("high_below_low")
            if row.get("high") is not None and row.get("open") is not None and float(row["high"]) < float(row["open"]):
                outliers += 1
                row_reasons.append("high_below_open")
            if row.get("low") is not None and row.get("close") is not None and float(row["low"]) > float(row["close"]):
                outliers += 1
                row_reasons.append("low_above_close")
            close = float(row.get("close", 0) or 0)
            symbol = str(row.get("symbol", "")).upper()
            previous_close = previous_close_by_symbol.get(symbol)
            if previous_close and close:
                absolute_return = abs(close - previous_close) / max(previous_close, 1e-9)
                if absolute_return > outlier_return_threshold:
                    outliers += 1
                    row_reasons.append("large_close_to_close_move")
            if symbol and close:
                previous_close_by_symbol[symbol] = close

        timestamp = _coerce_timestamp(row.get("timestamp"))
        if timestamp is None:
            missing += 1
            row_reasons.append("missing_timestamp")
            reasons.append({"row": index, "reasons": row_reasons})
            continue
        if timestamp and timestamp > reference:
            lookahead += 1
            row_reasons.append("lookahead_timestamp")
        if timestamp and reference - timestamp > stale_after:
            stale += 1
            row_reasons.append("stale_timestamp")
        if row_reasons:
            reasons.append({"row": index, "symbol": row.get("symbol"), "reasons": row_reasons})
    total_errors = errors + stale + missing + outliers + lookahead
    return {
        "rows_checked": len(rows),
        "errors": errors,
        "missing": missing,
        "stale": stale,
        "outliers": outliers,
        "lookahead": lookahead,
        "blocked": total_errors > 0,
        "reasons": reasons,
    }


def quality_gate_or_raise(rows: list[dict], as_of: datetime | None = None) -> dict[str, object]:
    report = validate_rows(rows, as_of=as_of)
    if report["blocked"]:
        raise ValueError(f"quality gate blocked dataset: {report}")
    return report


def run_data_quality_checks(rows: list[dict] | None = None, db=None) -> dict[str, object]:
    if rows is not None:
        return validate_rows(rows)
    return validate_rows([])
