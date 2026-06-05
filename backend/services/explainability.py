from backend.services.signal_orchestrator.orchestrator import generate_signal


async def generate_explanation(symbol: str) -> dict[str, object]:
    signal = await generate_signal(symbol)
    contributions = signal.get("explainability", {}).get("feature_attributions", {})
    return {
        "symbol": symbol.upper(),
        "signal": signal["signal"],
        "confidence": signal["confidence"],
        "feature_contributions": contributions,
        "top_drivers": signal.get("explainability", {}).get("top_drivers", []),
        "plain_language_risks": signal.get("explainability", {}).get("plain_language_risks", []),
        "model": "interpretable_signal_scaffold",
    }
