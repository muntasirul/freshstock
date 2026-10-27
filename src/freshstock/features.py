"""Forecast-origin features: information through close of day t, targets strictly after t."""

from __future__ import annotations

import pandas as pd

FEATURES = [
    "product_code",
    "day_of_week",
    "month",
    "day_index",
    "sales_today",
    "lag_7",
    "lag_14",
    "lag_28",
    "mean_7",
    "mean_28",
    "std_28",
    "zero_fraction_28",
    "latest_price",
]


def make_features(panel: pd.DataFrame, products: list[str], horizon: int = 2) -> pd.DataFrame:
    if not 1 <= horizon <= 7:
        raise ValueError("Supported protection horizons are one to seven days.")
    frame = panel.sort_values(["item_id", "date"]).copy()
    frame["date"] = pd.to_datetime(frame.date)
    frame["product_code"] = frame.item_id.map({item: i for i, item in enumerate(products)})
    if frame.product_code.isna().any():
        raise ValueError("The feature data contains products outside the training schema.")
    groups = frame.groupby("item_id", sort=False)
    frame["sales_today"] = frame.sales
    for lag in (7, 14, 28):
        frame[f"lag_{lag}"] = groups.sales.shift(lag)
    for window in (7, 28):
        frame[f"mean_{window}"] = groups.sales.transform(
            lambda values: values.rolling(window, min_periods=window).mean()
        )
    frame["std_28"] = groups.sales.transform(lambda values: values.rolling(28).std())
    frame["zero_fraction_28"] = groups.sales.transform(
        lambda values: values.eq(0).rolling(28).mean()
    )
    # Forward fill only. Future historical prices never backfill earlier origins.
    frame["latest_price"] = groups.sell_price.ffill()
    target_start = frame.date + pd.Timedelta(days=1)
    frame["day_of_week"] = target_start.dt.dayofweek
    frame["month"] = target_start.dt.month
    future_sales = pd.concat(
        [groups.sales.shift(-offset) for offset in range(1, horizon + 1)], axis=1
    )
    frame["target"] = future_sales.sum(axis=1, min_count=horizon)
    frame["target_end"] = frame.date + pd.Timedelta(days=horizon)
    frame["target_end_index"] = frame.day_index + horizon
    baseline_parts = []
    for offset in range(1, horizon + 1):
        matching_days = pd.concat(
            [groups.sales.shift(7 * week - offset) for week in range(1, 5)], axis=1
        )
        baseline_parts.append(matching_days.mean(axis=1))
    frame["baseline"] = pd.concat(baseline_parts, axis=1).sum(axis=1, min_count=horizon)
    # History validity is independent of target availability; latest origins remain for serving.
    return frame[frame.lag_28.notna()].reset_index(drop=True)
