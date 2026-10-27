# Model card: cumulative demand forecasting

## Model

- Algorithm: LightGBM gradient-boosted trees.
- Outputs:
  - cumulative point demand over a two-day horizon;
  - cumulative 80% demand quantile over the same horizon.
- Inputs: product identity, calendar fields, lagged sales, rolling history, zero-sales rate and latest known price.
- Artifact: `artifacts/model/model.joblib`.
- Metrics: `artifacts/model/metrics.json`.

## Data

- Source: M5 Forecasting Accuracy dataset, public Zenodo mirror at record 12636070.
- Store: `CA_1`.
- Products: 20 selected food-category products.
- Selection method: evenly spaced across training-period zero-sales fractions.
- Target: total observed sales over days `t+1` and `t+2`.

## Evaluation protocol

Training, validation and test data are separated chronologically:

- Training ends: 2015-05-24.
- Validation ends: 2015-11-08.
- Test ends: 2016-04-24.

Model rows whose target window crosses a boundary are excluded from that split. Hyperparameters are fixed before the held-out test evaluation. The fitted model is refit through validation before final scoring.

## Initial result

| Split | Model | MAE | WAPE | Notes |
| --- | --- | ---: | ---: | --- |
| Validation | Seasonal baseline | 1.837 | 0.478 | Baseline comparison |
| Validation | LightGBM point | 1.692 | 0.441 | Lower error |
| Validation | LightGBM 0.8 quantile | 1.940 | 0.505 | 0.702 coverage |
| Test | Seasonal baseline | 2.120 | 0.522 | Baseline comparison |
| Test | LightGBM point | 1.997 | 0.492 | About 5.8% WAPE improvement |
| Test | LightGBM 0.8 quantile | 2.672 | 0.658 | 0.816 coverage |

## Limitations

- Observed sales are a demand proxy, not measured unconstrained demand.
- Product-level results vary and some products are easier for the baseline.
- Cumulative target windows overlap, so test errors are not independent daily samples.
- The initial run has one chronological validation block and no rolling cross-validation.
- Future scheduled prices are not used; only the latest known price is carried forward.
- Recommendations remain a basic inventory-position policy; forecast improvement does not guarantee better inventory cost.

## Appropriate use

Use the model to compare forecast policies and generate reviewable purchase targets under documented assumptions. Do not use it to claim real waste savings or automatically purchase stock.
