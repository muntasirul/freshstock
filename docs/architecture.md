# FreshStock architecture

FreshStock is intentionally small at this stage. It uses a local SQLite database while keeping the data model compatible with PostgreSQL.

## Request flow

```text
React dashboard
    |
    | JSON over HTTP
    v
FastAPI application
    |
    | SQLAlchemy
    v
SQLite/PostgreSQL records
```

## Model flow

```text
M5 source files
    |
    v
prepare command
    |
    v
product-day parquet + metadata
    |
    v
origin-based features
    |
    v
LightGBM point and quantile models
    |
    v
metrics + test predictions + model artifact
    |
    v
dashboard and simulation API
```

## Temporal convention

At the close of day `t`, the application may use observations through day `t`. A horizon-`H` prediction targets days `t+1` through `t+H`.

Orders placed at the close of day `t` arrive at the start of day `t + lead_time`. A batch received on arrival day is usable immediately and expires before demand on `arrival + shelf_life`.

## Data integrity choices

- Sales records are unique by product and date.
- CSV imports are limited to whole-unit quantities and 2 MB.
- Conflicting imports are rejected rather than overwritten.
- Order drafts and inventory receipts use caller-supplied idempotency keys.
- Inventory movements are signed and append-only; batches define expiry windows.
- Model forecasts only apply when their forecast origin and horizon match the current data and product settings.

## Deferred production work

- Authentication and store authorization.
- Alembic migrations.
- Asynchronous workers and retries.
- PostgreSQL deployment and object storage.
- Supplier order submission.
- Drift and forecast staleness monitoring.
