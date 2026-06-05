from pathlib import Path
from typing import Any


def train_model(
    features_df: Any,
    target_series: Any,
    output_path: str | Path = "model/xgb_model.json",
):
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit

    tscv = TimeSeriesSplit(n_splits=5)
    model = xgb.XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05)
    for train_idx, val_idx in tscv.split(features_df):
        x_train, x_val = features_df.iloc[train_idx], features_df.iloc[val_idx]
        y_train, y_val = target_series.iloc[train_idx], target_series.iloc[val_idx]
        model.fit(
            x_train,
            y_train,
            eval_set=[(x_val, y_val)],
            early_stopping_rounds=20,
            verbose=False,
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(output)
    return model


def explain_model(model: Any, features_df: Any) -> Any:
    import shap

    explainer = shap.TreeExplainer(model)
    return explainer.shap_values(features_df)
