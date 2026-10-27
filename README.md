# FreshStock

A local-first inventory planning application for small food retailers. It uses historical demand forecasts, batch-level inventory assumptions, and ordering policies to create reviewable purchase recommendations.

The project is designed to demonstrate three skills together:

- **AI/ML engineering:** reproducible data preparation, LightGBM training, probabilistic forecasting, chronological evaluation, and model artifacts.
- **Data analysis:** SQL-backed product history, forecast metrics, and policy comparisons.
- **Software engineering:** FastAPI, SQLAlchemy, React with TypeScript, idempotent workflows, tests, and CI.

## Important data assumption

FreshStock currently uses historical sales from the public M5 dataset. Sales are used as a demand proxy. Actual stockouts, true demand, inventory levels, expiry dates and product-specific costs are not included in that source.

For that reason, opening stock, shelf life and cost parameters are explicit simulation assumptions. Any savings are simulated benchmark results, not measured real-world waste reduction.

## Current implemented scope

- Downloads and checksum-verifies the public Zenodo mirror of M5.
- Selects 20 food products from store `CA_1` using training-period characteristics.
- Trains two LightGBM cumulative-demand models:
  - a point forecast;
  - an 80% quantile forecast for a two-day protection horizon.
- Evaluates the models against a seasonal baseline on chronological validation and test periods.
- Simulates batch expiry, delivery lead time, unmet demand and inventory costs.
- Serves an authenticated-later local API and a React dashboard.
- Supports purchase-order drafts with idempotency keys.
- Supports a reviewable CSV import contract for daily sales.

Authentication, multi-store isolation, background workers and production deployment are planned in `FRESHSTOCK_PROJECT_PLAN.md`, but are not implemented yet.

## First measured result

Initial run with 20 products, a two-day cumulative target and 250 boosting iterations:

| Evaluation split | Model | MAE | WAPE | Extra result |
| --- | --- | ---: | ---: | --- |
| Validation | Seasonal baseline | 1.837 | 0.478 | - |
| Validation | LightGBM point | 1.692 | 0.441 | - |
| Validation | LightGBM 0.8 quantile | 1.940 | 0.505 | 0.702 coverage |
| Test | Seasonal baseline | 2.120 | 0.522 | - |
| Test | LightGBM point | 1.997 | 0.492 | - |
| Test | LightGBM 0.8 quantile | 2.672 | 0.658 | 0.816 coverage |

On the untouched test period, the point model's WAPE was about 5.8% lower than the seasonal baseline. The 0.8 quantile achieved about 81.6% observed coverage. These are aggregate results for the selected products and one initial model configuration.

## Repository layout

```text
apps/web/                  React dashboard
configs/                   Experiment settings
data/                      Ignored raw and processed data
artifacts/                 Ignored trained artifacts
docs/                      Architecture and model documentation
notebooks/                 Kaggle-ready training session
src/freshstock/            Backend, data and model code
tests/                     Focused backend and model tests
```

## Requirements

- Python 3.11 to 3.13 (the project pins 3.11 for local development).
- Node.js and npm.
- `uv` for Python dependency management.
- Optional: Docker/PostgreSQL later; the initial app uses local SQLite.

## Quick start

```bash
cd freshstock
uv sync --extra dev
npm ci --prefix apps/web
```

Download the data, prepare the selected store and train the initial models:

```bash
uv run freshstock download
uv run freshstock prepare
uv run freshstock train
```

Start the API:

```bash
uv run uvicorn freshstock.api:app --host 127.0.0.1 --port 8000
```

Start the dashboard in another terminal:

```bash
npm run dev --prefix apps/web
```

Open `http://127.0.0.1:5173`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

The database is local and first-party only:

```text
FRESHSTOCK_DATABASE_URL=sqlite:///data/freshstock.db
FRESHSTOCK_DATA_DIR=data/processed
FRESHSTOCK_ARTIFACT_DIR=artifacts/model
```

## Kaggle training session

The notebook in `notebooks/freshstock_m5_kaggle.ipynb` is designed for Kaggle:

1. Run `uv run freshstock package-kaggle` locally.
2. Upload `artifacts/freshstock-source.zip` as a private Kaggle dataset.
3. Attach that dataset to the notebook.
4. Enable internet access and run all cells.

See `docs/kaggle.md` for details.

## Verification

```bash
uv run pytest -q
uv run ruff check .
npm run build --prefix apps/web
```

The test suite currently covers forecast-origin feature correctness, inventory conservation and API idempotency/conflict behavior.

## Current limitations

- The current app is a local demo without authentication.
- The forecast uses observed sales as demand; it does not estimate censored demand.
- The current model has one validation block and no hyperparameter search yet.
- The simulator uses deterministic lead times and fixed cost assumptions.
- Current ordering recommendations do not reserve stock when a draft is saved.
- Expiry-aware ordering is represented in simulation assumptions, but the production recommendation remains a basic inventory-position policy.
- Product-level performance varies; aggregate results should not be claimed for every product.

## CV wording template

Use only after preserving the measured values that correspond to the final experiment:

> Built FreshStock, a full-stack demand forecasting and inventory planning application using LightGBM, FastAPI, React and SQLAlchemy. The trained model achieved [metric] on a chronological holdout, compared with [baseline], while an expiry-aware simulator evaluated [number] ordering policies under documented cost assumptions.

Do not describe simulated cost reduction as a retailer's measured savings.
