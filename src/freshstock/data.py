"""Download verified source data and prepare a chronological M5 experiment."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RECORD_URL = "https://zenodo.org/api/records/12636070"
REQUIRED_FILES = ("sales_train_validation.csv", "calendar.csv", "sell_prices.csv")


def write_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def checksum(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_m5(output_dir: Path) -> dict:
    """Download the public Zenodo mirror, verify its checksum and extract only M5 inputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        response = client.get(RECORD_URL)
        response.raise_for_status()
        record = response.json()
        entry = next(f for f in record["files"] if f["key"] == "m5-forecasting-accuracy.zip")
        archive = output_dir / entry["key"]
        algorithm, expected = entry["checksum"].split(":", 1)
        if not archive.exists() or checksum(archive, algorithm) != expected:
            temporary = archive.with_suffix(".zip.part")
            with client.stream("GET", entry["links"]["self"]) as response:
                response.raise_for_status()
                with temporary.open("wb") as stream:
                    for chunk in response.iter_bytes(1024 * 1024):
                        stream.write(chunk)
            if checksum(temporary, algorithm) != expected:
                temporary.unlink(missing_ok=True)
                raise ValueError("Downloaded archive checksum does not match the source.")
            temporary.replace(archive)
    with zipfile.ZipFile(archive) as bundle:
        for filename in REQUIRED_FILES:
            candidates = [n for n in bundle.namelist() if Path(n).name == filename]
            if len(candidates) != 1:
                raise ValueError(f"Expected exactly one {filename} in the archive.")
            # Extract known filenames only; archive paths never determine output paths.
            with bundle.open(candidates[0]) as source, (output_dir / filename).open("wb") as target:
                shutil.copyfileobj(source, target)
    manifest = {
        "source": RECORD_URL,
        "title": record["metadata"]["title"],
        "mirror_license": record["metadata"].get("license"),
        "archive_checksum": entry["checksum"],
        "note": "Mirror metadata does not replace the original dataset terms.",
        "files": {name: checksum(output_dir / name) for name in REQUIRED_FILES},
    }
    write_json(output_dir / "source_manifest.json", manifest)
    return manifest


def prepare_m5(
    raw_dir: Path,
    output_dir: Path,
    store: str = "CA_1",
    products: int = 20,
    validation_days: int = 168,
    test_days: int = 168,
) -> dict:
    """Select products on training history only, then join a complete daily sales panel."""
    if products < 1 or validation_days < 1 or test_days < 1:
        raise ValueError("Product count and split lengths must be positive.")
    for filename in REQUIRED_FILES:
        if not (raw_dir / filename).is_file():
            raise FileNotFoundError(f"Missing {filename} in {raw_dir}. Run the download command.")

    pieces = []
    for chunk in pd.read_csv(raw_dir / REQUIRED_FILES[0], chunksize=2000):
        pieces.append(chunk[(chunk.store_id == store) & (chunk.cat_id == "FOODS")])
    wide = pd.concat(pieces, ignore_index=True)
    if wide.empty:
        raise ValueError(f"No food products found for store {store}.")
    day_columns = sorted(
        (column for column in wide if column.startswith("d_")),
        key=lambda column: int(column[2:]),
    )
    train_days = len(day_columns) - validation_days - test_days
    if train_days < 365:
        raise ValueError("At least 365 training days are required after reserving holdouts.")
    training_sales = wide[day_columns[:train_days]]
    if training_sales.isna().any().any() or (training_sales < 0).any().any():
        raise ValueError("Sales must be nonnegative and complete.")
    eligible = wide.loc[training_sales.sum(axis=1) > 0].copy()
    eligible["zero_fraction"] = (training_sales == 0).mean(axis=1)
    eligible = eligible.sort_values(["zero_fraction", "item_id"])
    # Spread selections across intermittency levels, not test-set performance.
    positions = np.linspace(0, len(eligible) - 1, min(products, len(eligible)), dtype=int)
    selected = eligible.iloc[positions]
    if selected.empty:
        raise ValueError("No products have positive training-period sales.")
    panel = selected.melt(
        id_vars=["item_id", "store_id", "dept_id"],
        value_vars=day_columns,
        var_name="d",
        value_name="sales",
    )
    calendar = pd.read_csv(raw_dir / "calendar.csv")
    panel = panel.merge(
        calendar[["d", "date", "wm_yr_wk", "event_name_1"]],
        on="d",
        how="left",
        validate="many_to_one",
    )
    prices = pd.read_csv(raw_dir / "sell_prices.csv")
    prices = prices[(prices.store_id == store) & prices.item_id.isin(selected.item_id)]
    panel = panel.merge(
        prices,
        on=["store_id", "item_id", "wm_yr_wk"],
        how="left",
        validate="many_to_one",
    )
    panel["date"] = pd.to_datetime(panel.date)
    panel["day_index"] = panel.d.str[2:].astype(int)
    panel["sales"] = panel.sales.astype(float)
    panel = panel.sort_values(["item_id", "date"]).reset_index(drop=True)
    if panel.date.isna().any() or panel.duplicated(["item_id", "date"]).any():
        raise ValueError("Invalid calendar mapping or duplicate product dates.")
    if panel.sales.isna().any() or (panel.sales < 0).any():
        raise ValueError("Sales must be complete and nonnegative.")
    panel["split"] = np.select(
        [
            panel.day_index <= train_days,
            panel.day_index <= train_days + validation_days,
        ],
        ["train", "validation"],
        default="test",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output_dir / "sales.parquet", index=False)
    dates = panel[["day_index", "date"]].drop_duplicates().set_index("day_index").date
    metadata = {
        "store": store,
        "products": selected.item_id.tolist(),
        "rows": len(panel),
        "train_end": dates.loc[train_days].date().isoformat(),
        "validation_end": dates.loc[train_days + validation_days].date().isoformat(),
        "test_end": dates.iloc[-1].date().isoformat(),
        "missing_price_fraction": float(panel.sell_price.isna().mean()),
        "source_checksums": {name: checksum(raw_dir / name) for name in REQUIRED_FILES},
        "selection": "Evenly spaced across training-period zero-sales fractions.",
        "demand_assumption": "Observed M5 sales are the demand proxy; stockouts are unobserved.",
    }
    write_json(output_dir / "metadata.json", metadata)
    return metadata
