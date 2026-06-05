from backend.ml_training.models.xgboost_model import XgboostRanker
from backend.shared.data_lake import record_data_lake_edge


def train(rows: list[dict]) -> dict[str, object]:
    model = XgboostRanker()
    model.fit(rows)
    return {
        "model": "xgboost_ranker",
        "rows_seen": len(rows),
        "status": "trained",
        "database_edge": record_data_lake_edge("ml_pipeline_model_training", "read_write", "feature_store"),
    }
