class LstmForecaster:
    def fit(self, rows: list[dict]) -> None:
        self.rows_seen = len(rows)

    def predict(self, horizon: int) -> list[float]:
        return [0.0 for _ in range(horizon)]

