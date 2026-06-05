class SentimentBert:
    def score(self, text: str) -> float:
        return 0.5 if text else 0.0

