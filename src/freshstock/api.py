"""Local single-store API. Authentication and production deployment are later milestones."""

from __future__ import annotations

import io
import json
import math
import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from freshstock.database import Batch, Movement, Order, Product, Sale, make_engine, seed_database
from freshstock.inventory import Scenario, simulate


class ProductUpdate(BaseModel):
    lead_time: int = Field(ge=1, le=7)
    shelf_life: int = Field(ge=1, le=90)


class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=100000)


class OrderRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    items: list[OrderItem] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Each product must appear once in an order.")
        return self


class ReceiptRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    product_id: str
    quantity: int = Field(ge=1, le=100000)
    received_date: date
    expiry_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.expiry_date <= self.received_date:
            raise ValueError("Expiry must be later than receipt.")
        return self


class SimulationRequest(BaseModel):
    shelf_life: int = Field(default=7, ge=1, le=90)
    lost_sale_penalty: float = Field(default=2, ge=0, le=1000, allow_inf_nan=False)


def create_app(
    database_url: str | None = None,
    data_dir: Path | None = None,
    artifact_dir: Path | None = None,
) -> FastAPI:
    data_dir = data_dir or Path(os.getenv("FRESHSTOCK_DATA_DIR", "data/processed"))
    artifact_dir = artifact_dir or Path(os.getenv("FRESHSTOCK_ARTIFACT_DIR", "artifacts/model"))

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine = make_engine(
            database_url or os.getenv("FRESHSTOCK_DATABASE_URL", "sqlite:///data/freshstock.db")
        )
        seed_database(engine, data_dir)
        application.state.engine = engine
        yield
        engine.dispose()

    application = FastAPI(title="FreshStock", version="0.1.0", lifespan=lifespan)

    def load_report():
        path = artifact_dir / "metrics.json"
        return json.loads(path.read_text()) if path.exists() else None

    def current_snapshot(session: Session) -> dict:
        products = session.scalars(select(Product).order_by(Product.id)).all()
        as_of = session.scalar(select(func.max(Sale.date)))
        if not products or as_of is None:
            return {"as_of": None, "products": [], "forecast_source": "unavailable"}
        sales = session.execute(
            select(Sale).where(Sale.date >= as_of - timedelta(days=34))
        ).scalars().all()
        quantities = {(sale.product_id, sale.date): sale.quantity for sale in sales}
        forecast_file = artifact_dir / "latest_forecasts.json"
        forecasts = (
            {row["item_id"]: row for row in json.loads(forecast_file.read_text())}
            if forecast_file.exists()
            else {}
        )
        balances = session.execute(
            select(Batch.product_id, func.sum(Movement.quantity))
            .join(Movement, Movement.batch_id == Batch.id)
            .where(Batch.received_date <= as_of, Batch.expiry_date > as_of)
            .group_by(Batch.product_id)
        ).all()
        stock = dict(balances)
        result = []
        for product in products:
            baseline = sum(
                sum(
                    quantities.get(
                        (product.id, as_of + timedelta(days=offset - 7 * week)), 0
                    )
                    for week in range(1, 5)
                )
                / 4
                for offset in range(1, product.lead_time + 1)
            )
            forecast = forecasts.get(product.id)
            valid = (
                forecast
                and forecast["origin"] == as_of.isoformat()
                and forecast["horizon"] == product.lead_time
            )
            target = forecast["quantile_value"] if valid else baseline
            point = forecast["point"] if valid else baseline
            on_hand = stock.get(product.id, 0)
            average = sum(
                quantities.get((product.id, as_of - timedelta(days=offset)), 0)
                for offset in range(7)
            ) / 7
            result.append(
                {
                    "id": product.id,
                    "department": product.department,
                    "store": product.store,
                    "lead_time": product.lead_time,
                    "shelf_life": product.shelf_life,
                    "on_hand": on_hand,
                    "daily_average": average,
                    "forecast": point,
                    "target_stock": target,
                    "order_quantity": max(0, math.ceil(target - on_hand)),
                    "days_cover": on_hand / average if average else None,
                    "source": "LightGBM" if valid else "Seasonal baseline",
                    "quantile": forecast["quantile"] if valid else None,
                    "explanation": (
                        f"{product.lead_time}-day cumulative demand target, less usable inventory. "
                        "Draft orders do not reserve stock. Expiry-aware ordering is not yet applied."
                    ),
                }
            )
        return {"as_of": as_of.isoformat(), "products": result}

    @application.get("/api/health")
    def health():
        return {"status": "ok", "mode": "local-demo"}

    @application.get("/api/overview")
    def overview():
        with Session(application.state.engine) as session:
            snapshot = current_snapshot(session)
            report = load_report()
            as_of = date.fromisoformat(snapshot["as_of"]) if snapshot["as_of"] else None
            history = []
            if as_of:
                rows = session.execute(
                    select(Sale.date, func.sum(Sale.quantity))
                    .where(Sale.date >= as_of - timedelta(days=55))
                    .group_by(Sale.date)
                    .order_by(Sale.date)
                )
                history = [{"date": day.isoformat(), "sales": quantity} for day, quantity in rows]
            products = snapshot["products"]
            return {
                **snapshot,
                "history": history,
                "metrics": report["metrics"] if report else None,
                "model_version": report["model_version"] if report else None,
                "model_horizon": report["horizon"] if report else None,
                "summary": {
                    "products": len(products),
                    "stock_units": sum(product["on_hand"] for product in products),
                    "suggested_units": sum(product["order_quantity"] for product in products),
                    "reorder_count": sum(product["order_quantity"] > 0 for product in products),
                },
                "notice": (
                    "Historical M5 sales. Starting inventory and cost assumptions are simulated. "
                    "Recommendations refer to the displayed historical date."
                ),
            }

    @application.get("/api/products/{product_id}/history")
    def product_history(product_id: str):
        with Session(application.state.engine) as session:
            if session.get(Product, product_id) is None:
                raise HTTPException(404, "Product not found.")
            rows = session.scalars(
                select(Sale).where(Sale.product_id == product_id).order_by(Sale.date.desc()).limit(90)
            ).all()
            return [
                {"date": row.date.isoformat(), "sales": row.quantity}
                for row in reversed(rows)
            ]

    @application.patch("/api/products/{product_id}")
    def update_product(product_id: str, payload: ProductUpdate):
        with Session(application.state.engine) as session:
            product = session.get(Product, product_id)
            if product is None:
                raise HTTPException(404, "Product not found.")
            product.lead_time = payload.lead_time
            product.shelf_life = payload.shelf_life
            session.commit()
            return {"status": "updated", "product_id": product_id}

    @application.get("/api/orders")
    def orders():
        with Session(application.state.engine) as session:
            rows = session.scalars(select(Order).order_by(Order.created_at.desc())).all()
            return [
                {
                    "id": row.id,
                    "status": row.status,
                    "items": json.loads(row.items_json),
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]

    @application.post("/api/orders")
    def save_order(payload: OrderRequest):
        content = json.dumps(
            sorted([item.model_dump() for item in payload.items], key=lambda item: item["product_id"]),
            sort_keys=True,
        )
        with Session(application.state.engine) as session:
            existing = session.get(Order, payload.idempotency_key)
            if existing:
                if existing.items_json != content:
                    raise HTTPException(409, "Idempotency key already belongs to another payload.")
                return {"id": existing.id, "status": existing.status, "duplicate": True}
            for item in payload.items:
                if session.get(Product, item.product_id) is None:
                    raise HTTPException(422, f"Unknown product: {item.product_id}")
            session.add(Order(id=payload.idempotency_key, items_json=content, status="draft"))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.get(Order, payload.idempotency_key)
                if existing is None or existing.items_json != content:
                    raise HTTPException(409, "Conflicting concurrent order.") from None
                return {"id": existing.id, "status": existing.status, "duplicate": True}
            return {"id": payload.idempotency_key, "status": "draft", "duplicate": False}

    @application.post("/api/inventory/receipts")
    def receive_inventory(payload: ReceiptRequest):
        with Session(application.state.engine) as session:
            if session.get(Product, payload.product_id) is None:
                raise HTTPException(422, "Unknown product.")
            existing = session.get(Movement, payload.idempotency_key)
            if existing:
                batch = session.get(Batch, existing.batch_id)
                if (
                    batch.product_id != payload.product_id
                    or batch.received_date != payload.received_date
                    or batch.expiry_date != payload.expiry_date
                    or existing.quantity != payload.quantity
                ):
                    raise HTTPException(409, "Idempotency key already belongs to another receipt.")
                return {"status": "received", "duplicate": True}
            session.add(
                Batch(
                    id=payload.idempotency_key,
                    product_id=payload.product_id,
                    received_date=payload.received_date,
                    expiry_date=payload.expiry_date,
                )
            )
            session.flush()
            session.add(
                Movement(
                    id=payload.idempotency_key,
                    batch_id=payload.idempotency_key,
                    quantity=payload.quantity,
                    reason="receipt",
                )
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "Concurrent receipt. Retry with the same key.") from None
            return {"status": "received", "duplicate": False}

    @application.post("/api/imports/sales")
    async def import_sales(request: Request):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 2 * 1024 * 1024:
                raise HTTPException(413, "CSV imports are limited to 2 MB.")
        try:
            frame = pd.read_csv(io.BytesIO(body))
            if not {"product_id", "date", "quantity"}.issubset(frame.columns):
                raise ValueError("Required columns: product_id, date, quantity.")
            if frame.empty or len(frame) > 10000:
                raise ValueError("An import must contain between 1 and 10,000 rows.")
            frame["date"] = pd.to_datetime(frame.date, format="%Y-%m-%d", errors="raise").dt.date
            frame["quantity"] = pd.to_numeric(frame.quantity, errors="raise")
            if frame[["product_id", "date", "quantity"]].isna().any().any():
                raise ValueError("Required values cannot be empty.")
            if any(
                not math.isfinite(value) or value < 0 or value != int(value)
                for value in frame.quantity
            ):
                raise ValueError("Quantities must be finite, nonnegative whole units.")
            if frame.duplicated(["product_id", "date"]).any():
                raise ValueError("Duplicate product/date pairs in this file.")
        except (ValueError, UnicodeError, pd.errors.ParserError) as error:
            raise HTTPException(422, str(error)) from error
        with Session(application.state.engine) as session:
            inserted = skipped = 0
            for row in frame.itertuples():
                if session.get(Product, row.product_id) is None:
                    raise HTTPException(422, f"Unknown product: {row.product_id}")
                existing = session.get(Sale, (row.product_id, row.date))
                if existing:
                    if existing.quantity != row.quantity:
                        raise HTTPException(409, f"Conflicting sale: {row.product_id}, {row.date}")
                    skipped += 1
                else:
                    session.add(
                        Sale(product_id=row.product_id, date=row.date, quantity=row.quantity)
                    )
                    inserted += 1
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "Concurrent import conflict; retry the same CSV.") from None
            return {
                "inserted": inserted,
                "skipped": skipped,
                "note": "Imports update sales history only. They do not decrement demo stock.",
            }

    @application.post("/api/simulations")
    def run_simulation(payload: SimulationRequest):
        report = load_report()
        predictions_path = artifact_dir / "test_predictions.parquet"
        if not report or not predictions_path.exists():
            raise HTTPException(409, "Train a model before running historical comparisons.")
        predictions = pd.read_parquet(predictions_path)
        results = []
        for name, column in (
            ("Seasonal baseline", "baseline"),
            ("LightGBM point", "point_prediction"),
            ("LightGBM quantile", "quantile_prediction"),
        ):
            runs = [
                simulate(
                    group.sort_values("date").sales.tolist(),
                    group.sort_values("date")[column].tolist(),
                    Scenario(
                        lead_time=report["horizon"],
                        shelf_life=payload.shelf_life,
                        lost_sale_penalty=payload.lost_sale_penalty,
                    ),
                )
                for _, group in predictions.groupby("item_id")
            ]
            total_demand = sum(run["fulfilled_units"] + run["unmet_units"] for run in runs)
            results.append(
                {
                    "policy": name,
                    "cost": sum(run["cost"] for run in runs),
                    "fill_rate": (
                        sum(run["fulfilled_units"] for run in runs) / total_demand
                        if total_demand else None
                    ),
                    "expired_units": sum(run["expired_units"] for run in runs),
                    "unmet_units": sum(run["unmet_units"] for run in runs),
                    "closing_units": sum(run["closing_units"] for run in runs),
                    "outstanding_units": sum(run["outstanding_units"] for run in runs),
                }
            )
        return {
            "results": results,
            "lead_time": report["horizon"],
            "shelf_life": payload.shelf_life,
            "notice": (
                "Historical simulation with 14 warm-up days. Unit cost 1, holding cost 0.02, "
                "disposal cost 0.1; all costs are assumed cost units. "
                "Changing assumptions explores the test set, not a new independent evaluation."
            ),
        }

    return application


app = create_app()
