"""Train cumulative-demand models with purged chronological holdouts."""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_pinball_loss

from freshstock.data import write_json
from freshstock.features import FEATURES, make_features


def metrics(actual: np.ndarray, predicted: np.ndarray, quantile: float | None = None) -> dict:
    denominator = float(np.sum(actual))
    result = {
        "mae": float(mean_absolute_error(actual, predicted)),
        "wape": float(np.abs(actual - predicted).sum() / denominator) if denominator else None,
    }
    if quantile is not None:
        result["pinball_loss"] = float(mean_pinball_loss(actual, predicted, alpha=quantile))
        result["observed_quantile_coverage"] = float(np.mean(actual <= predicted))
    return result


def train(
    data_dir: Path,
    output_dir: Path,
    horizon: int = 2,
    quantile: float = 0.8,
    iterations: int = 250,
    seed: int = 42,
) -> dict:
    if not 0 < quantile < 1 or iterations < 1:
        raise ValueError("Quantile must be between zero and one; iterations must be positive.")
    metadata = json.loads((data_dir / "metadata.json").read_text())
    panel = pd.read_parquet(data_dir / "sales.parquet")
    features = make_features(panel, metadata["products"], horizon)
    train_end = pd.Timestamp(metadata["train_end"])
    validation_end = pd.Timestamp(metadata["validation_end"])
    training = features[features.target.notna() & (features.target_end <= train_end)]
    validation = features[
        features.target.notna()
        & (features.date >= train_end)
        & (features.target_end <= validation_end)
    ]
    test = features[features.target.notna() & (features.date >= validation_end)].copy()
    if any(frame.empty for frame in (training, validation, test)):
        raise ValueError("Chronological splits must each contain complete target windows.")
    output_dir.mkdir(parents=True, exist_ok=True)
    parameters = {
        "n_estimators": iterations,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_child_samples": 30,
        "reg_lambda": 1.0,
        "random_state": seed,
        "n_jobs": 2,
        "verbosity": -1,
        "deterministic": True,
        "force_col_wise": True,
    }
    evaluation = {"validation": {}, "test": {}}
    fitted = {}
    refit = features[features.target.notna() & (features.target_end <= validation_end)]
    for name, objective in (("point", "regression"), ("quantile", "quantile")):
        model = LGBMRegressor(
            **parameters,
            objective=objective,
            **({"alpha": quantile} if name == "quantile" else {}),
        )
        model.fit(training[FEATURES], training.target)
        prediction = np.maximum(0, model.predict(validation[FEATURES]))
        evaluation["validation"][name] = metrics(
            validation.target.to_numpy(), prediction, quantile if name == "quantile" else None
        )
        # Hyperparameters are fixed before test evaluation; refit sees validation labels only.
        model.fit(refit[FEATURES], refit.target)
        fitted[name] = model
        test[f"{name}_prediction"] = np.maximum(0, model.predict(test[FEATURES]))
        evaluation["test"][name] = metrics(
            test.target.to_numpy(),
            test[f"{name}_prediction"].to_numpy(),
            quantile if name == "quantile" else None,
        )
    for name, split in (("validation", validation), ("test", test)):
        evaluation[name]["seasonal_baseline"] = metrics(
            split.target.to_numpy(), split.baseline.to_numpy()
        )
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    latest = features.groupby("item_id", sort=False).tail(1).copy()
    latest["point_prediction"] = np.maximum(0, fitted["point"].predict(latest[FEATURES]))
    latest["quantile_prediction"] = np.maximum(0, fitted["quantile"].predict(latest[FEATURES]))
    forecast = []
    for row in latest.itertuples():
        forecast.append(
            {
                "item_id": row.item_id,
                "origin": row.date.date().isoformat(),
                "horizon": horizon,
                "point": float(row.point_prediction),
                "quantile": quantile,
                "quantile_value": float(row.quantile_prediction),
                "model_version": version,
            }
        )
    test[
        ["item_id", "date", "sales", "target", "baseline", "point_prediction", "quantile_prediction"]
    ].to_parquet(output_dir / "test_predictions.parquet", index=False)
    per_product = []
    for item_id, group in test.groupby("item_id"):
        per_product.append(
            {
                "item_id": item_id,
                "point": metrics(group.target.to_numpy(), group.point_prediction.to_numpy()),
                "baseline": metrics(group.target.to_numpy(), group.baseline.to_numpy()),
            }
        )
    report = {
        "model_version": version,
        "horizon": horizon,
        "quantile": quantile,
        "seed": seed,
        "iterations": iterations,
        "features": FEATURES,
        "training_rows": len(training),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "data": metadata,
        "metrics": evaluation,
        "per_product": per_product,
        "versions": {"python": platform.python_version(), "lightgbm": lightgbm.__version__},
        "limitations": [
            "Historical sales are a demand proxy, not measured unconstrained demand.",
            "One chronological validation block; no hyperparameter search or rolling folds yet.",
            "Cumulative target windows overlap; errors are not independent daily observations.",
            "Fixed model parameters during the test period; features update at each origin.",
            "Latest forecasts are based on the end of historical M5 data, not today's date.",
        ],
    }
    joblib.dump(
        {"models": fitted, "features": FEATURES, "products": metadata["products"], "horizon": horizon},
        output_dir / "model.joblib",
    )
    write_json(output_dir / "metrics.json", report)
    write_json(output_dir / "latest_forecasts.json", forecast)
    return report
