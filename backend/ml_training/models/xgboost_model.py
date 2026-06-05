class XgboostRanker:
    def fit(self, rows: list[dict]) -> None:
        self.rows_seen = len(rows)

    def score(self, features: dict[str, float]) -> float:
        return round(sum(features.values()) / max(len(features), 1), 4)

