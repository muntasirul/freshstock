import pandas as pd
from fastapi.testclient import TestClient

from freshstock.api import create_app


def client(tmp_path):
    data_dir = tmp_path / "data"
    artifact_dir = tmp_path / "artifacts"
    data_dir.mkdir()
    artifact_dir.mkdir()
    pd.DataFrame(
        [
            {
                "item_id": "ITEM_A",
                "dept_id": "FOODS_1",
                "store_id": "CA_1",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=day),
                "day_index": day + 1,
                "sales": 2,
                "sell_price": 1.0,
            }
            for day in range(40)
        ]
    ).to_parquet(data_dir / "sales.parquet")
    return TestClient(
        create_app(
            database_url=f"sqlite:///{tmp_path}/test.db",
            data_dir=data_dir,
            artifact_dir=artifact_dir,
        )
    )


def test_overview_and_idempotent_draft_order(tmp_path):
    with client(tmp_path) as test_client:
        overview = test_client.get("/api/overview")
        assert overview.status_code == 200
        product = overview.json()["products"][0]
        assert product["source"] == "Seasonal baseline"
        payload = {
            "idempotency_key": "test-order-key-0001",
            "items": [{"product_id": "ITEM_A", "quantity": 4}],
        }
        first = test_client.post("/api/orders", json=payload)
        second = test_client.post("/api/orders", json=payload)
        assert first.status_code == second.status_code == 200
        assert first.json()["duplicate"] is False
        assert second.json()["duplicate"] is True


def test_sales_import_rejects_a_conflicting_existing_row(tmp_path):
    with client(tmp_path) as test_client:
        response = test_client.post(
            "/api/imports/sales",
            content=b"product_id,date,quantity\nITEM_A,2024-01-01,9\n",
            headers={"Content-Type": "text/csv"},
        )
        assert response.status_code == 409
