from datetime import date


HIGH_IMPACT_EVENTS = {"earnings", "fda_decision", "regulatory_ruling"}
MEDIUM_IMPACT_EVENTS = {"ex_dividend", "investor_day", "product_launch", "macro_release"}


def evaluate_event_risk(
    symbol: str,
    events: list[dict] | None = None,
    as_of: date | None = None,
) -> dict[str, object]:
    today = as_of or date.today()
    upcoming = []
    for event in events or []:
        event_date = event.get("date")
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        if not isinstance(event_date, date):
            continue
        days_until = (event_date - today).days
        if 0 <= days_until <= 14:
            event_type = str(event.get("type", "unknown"))
            impact = "high" if event_type in HIGH_IMPACT_EVENTS else "medium"
            if event_type in MEDIUM_IMPACT_EVENTS:
                impact = "medium"
            upcoming.append(
                {
                    "type": event_type,
                    "date": event_date.isoformat(),
                    "days_until": days_until,
                    "impact": impact,
                    "source": event.get("source", "calendar"),
                    "confidence": float(event.get("confidence", 0.8)),
                }
            )

    high_impact = any(event["impact"] == "high" for event in upcoming)
    medium_impact = bool(upcoming) and not high_impact
    size_multiplier = 0.5 if high_impact else 0.8 if medium_impact else 1.0
    action = (
        "reduce_size_or_hedge"
        if high_impact
        else "flag_for_review"
        if medium_impact
        else "standard_risk_limits"
    )
    return {
        "symbol": symbol.upper(),
        "upcoming_events": sorted(upcoming, key=lambda item: item["days_until"]),
        "action": action,
        "size_multiplier": size_multiplier,
        "position_size_multiplier": size_multiplier,
        "block_new_automation": high_impact,
        "hedge_recommendation": (
            "buy_protective_put_or_reduce_delta"
            if high_impact
            else "monitor_event_and_avoid_size_increase"
            if medium_impact
            else "none"
        ),
        "event_risk_protocol": {
            "flag": bool(upcoming),
            "reduce": high_impact,
            "hedge": high_impact,
            "block_new_automation": high_impact,
            "review_required": bool(upcoming),
        },
        "blocked_reason": (
            "upcoming_high_impact_event"
            if high_impact
            else None
        ),
        "rationale": (
            "Upcoming high-impact event requires reduced size or hedge before automated execution."
            if high_impact
            else "Upcoming medium-impact event should be reviewed before increasing exposure."
            if medium_impact
            else "No near-term high-impact event detected."
        ),
    }
