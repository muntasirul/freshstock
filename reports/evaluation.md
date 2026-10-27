# Initial experiment report

## Scope

- Store: M5 `CA_1`
- Products: 20 selected food-category products
- Target: two-day cumulative sales
- Horizon and ordering convention: an order generated at the close of day `t` covers days `t+1` and `t+2`
- Quantile model: 0.8
- Boosting iterations: 250
- Seed: 42

## Chronological holdout results

| Split | Model | MAE | WAPE | Pinball loss | Coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| Validation | Seasonal baseline | 1.837 | 0.478 | - | - |
| Validation | LightGBM point | 1.692 | 0.441 | - | - |
| Validation | LightGBM 0.8 quantile | 1.940 | 0.505 | 0.751 | 0.702 |
| Test | Seasonal baseline | 2.120 | 0.522 | - | - |
| Test | LightGBM point | 1.997 | 0.492 | - | - |
| Test | LightGBM 0.8 quantile | 2.672 | 0.658 | 0.783 | 0.816 |

The test-period point model reduced WAPE from 0.522 to 0.492, about 5.8% relative improvement. The quantile is intentionally conservative and should not be compared with point forecasts through MAE or WAPE alone.

## Initial policy simulation

Settings: two-day deterministic lead time, seven-day shelf life, unit cost 1, holding cost 0.02 per unit-day, disposal cost 0.1 and lost-sale penalty 2. A 14-day warm-up is excluded from reported metrics.

| Policy | Simulated cost | Fill rate | Expired units | Unmet units | Closing / in transit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seasonal baseline | 7,981.46 | 76.1% | 126 | 1,494 | 43 / 61 |
| LightGBM point | 7,900.48 | 77.6% | 138 | 1,398 | 42 / 63 |
| LightGBM 0.8 quantile | 7,448.12 | 88.4% | 274 | 723 | 68 / 79 |

The point policy lowered simulated cost by about 1.0% while raising fill rate by about 1.5 percentage points. The quantile policy lowered simulated cost further and raised service substantially, while generating more expired and remaining stock. These values are sensitive to the assumed lost-sale penalty and shelf life.

## Interpretation

This result supports further work on probabilistic ordering, but it does not yet support a real-world savings claim. Product-level forecasts vary; see `artifacts/model/metrics.json` for the full per-product table.

## Known issues to address next

- Add rolling validation folds and a controlled parameter search.
- Build a true shelf-life-aware recommendation, not only a stock target.
- Test sensitivity across lead time, shelf life and cost assumptions.
- Add uncertainty around paired policy differences rather than comparing aggregate totals alone.
- Persist simulation runs and forecast snapshots in the application database.
