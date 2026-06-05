import pickle
from pathlib import Path


def train_regime_model(
    features_path: str | Path = "market_features.csv",
    output_path: str | Path = "models/market_regime_hmm.pkl",
):
    from hmmlearn import hmm
    import pandas as pd

    features = pd.read_csv(features_path)
    model = hmm.GaussianHMM(n_components=3, covariance_type="full")
    model.fit(features.values)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file:
        pickle.dump(model, file)
    return model


if __name__ == "__main__":
    train_regime_model()
