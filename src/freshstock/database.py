"""Initial local database. PostgreSQL is supported through the SQLAlchemy URL."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    department: Mapped[str] = mapped_column(String)
    store: Mapped[str] = mapped_column(String)
    lead_time: Mapped[int] = mapped_column(Integer, default=2)
    shelf_life: Mapped[int] = mapped_column(Integer, default=7)


class Sale(Base):
    __tablename__ = "sales_daily"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)


class Batch(Base):
    __tablename__ = "inventory_batches"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    received_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date] = mapped_column(Date)


class Movement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("inventory_batches.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String)


class Order(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    items_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def make_engine(url: str):
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    Base.metadata.create_all(engine)
    return engine


def seed_database(engine, data_dir: Path) -> None:
    """Load prepared M5 data once; synthetic inventory is explicitly a demo assumption."""
    with Session(engine) as session:
        if session.scalar(select(Product.id).limit(1)) is not None:
            return
        path = data_dir / "sales.parquet"
        if not path.exists():
            return
        panel = pd.read_parquet(path)
        last_day = panel.date.max().date()
        for item_id, group in panel.groupby("item_id"):
            last = group.sort_values("date").iloc[-1]
            session.add(Product(id=item_id, department=last.dept_id, store=last.store_id))
        session.flush()
        sales = [
            {
                "product_id": row.item_id,
                "date": row.date.date(),
                "quantity": float(row.sales),
                "price": None if pd.isna(row.sell_price) else float(row.sell_price),
            }
            for row in panel.itertuples()
        ]
        session.execute(Sale.__table__.insert(), sales)
        for item_id, group in panel.groupby("item_id"):
            quantity = int(group.sort_values("date").tail(7).sales.mean() * 2)
            batch_id = f"demo-{item_id}"
            session.add(
                Batch(
                    id=batch_id,
                    product_id=item_id,
                    received_date=last_day,
                    expiry_date=last_day + pd.Timedelta(days=7),
                )
            )
            session.flush()
            session.add(
                Movement(id=f"seed-{item_id}", batch_id=batch_id, quantity=quantity, reason="demo")
            )
        session.commit()
