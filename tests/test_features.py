import pandas as pd

from freshstock.features import make_features


def synthetic_panel(days=60):
    rows = []
    for day in range(days):
        rows.append(
            {
                "item_id": "ITEM",
                "dept_id": "TEST",
                "store_id": "STORE",
                "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=day),
                "day_index": day + 1,
                "sales": day + 1,
                "sell_price": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_features_use_history_through_forecast_origin():
    features = make_features(synthetic_panel(), ["ITEM"], horizon=2)
    row = features.loc[features.day_index == 35].iloc[0]
    assert row.sales_today == 35
    assert row.lag_7 == 28
    assert row.mean_7 == sum(range(29, 36)) / 7
    # Targets t+1 and t+2 use matching weekdays at t-6 and t-5.
    assert row.baseline == ((29 + 22 + 15 + 8) / 4) + ((30 + 23 + 16 + 9) / 4)
    assert row.target == 36 + 37
