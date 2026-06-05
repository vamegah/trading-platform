from backend.services.agents.fundamentals_agent.financial_model import fair_value_score


def analyze_fundamentals(symbol: str) -> dict[str, object]:
    normalized_symbol = symbol.upper()
    score = fair_value_score(symbol)
    beneish_m_score = -2.45 + (0.2 if normalized_symbol.startswith("N") else 0.0)
    cash_flow_quality = round(min(score + 0.08, 0.95), 4)
    accounting_red_flags = []
    red_flag_explanations = []
    if beneish_m_score > -1.78:
        accounting_red_flags.append("beneish_m_score_above_manipulation_threshold")
        red_flag_explanations.append(
            "Beneish M-Score is above the common manipulation-risk threshold, so accounting quality is penalized."
        )
    return {
        "symbol": normalized_symbol,
        "agent": "fundamentals",
        "score": score,
        "factors": {
            "filing_quality": round(score, 4),
            "transcript_tone": 0.58,
            "valuation": round(max(0.0, 1 - score / 2), 4),
            "cash_flow_quality": cash_flow_quality,
            "beneish_m_score": beneish_m_score,
        },
        "red_flags": accounting_red_flags,
        "red_flag_explanations": red_flag_explanations,
        "evidence": [
            {
                "type": "10-k",
                "source": "sample_sec_filings",
                "snapshot_id": f"{normalized_symbol}-10k-latest",
                "url": f"https://www.sec.gov/edgar/search/#/{normalized_symbol}",
            },
            {
                "type": "earnings_transcript",
                "source": "sample_transcripts",
                "snapshot_id": f"{normalized_symbol}-call-latest",
                "url": f"internal://transcripts/{normalized_symbol}/latest",
            },
        ],
        "summary": "Fundamental analysis combines filings, transcript tone, valuation, cash flow quality, and Beneish red flags.",
    }
