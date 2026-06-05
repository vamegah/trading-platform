class CryptoSentimentBert:
    def score(self, text: str) -> dict[str, float | str]:
        score = 0.55 if text else 0.0
        return {"label": "neutral_positive" if score >= 0.5 else "neutral", "score": score}

