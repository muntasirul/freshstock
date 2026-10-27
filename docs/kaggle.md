# Kaggle workflow

The repository notebook is intended to run in a Kaggle notebook session without editing code.

## One-time source package

From the repository root:

```bash
uv run freshstock package-kaggle
```

This creates `artifacts/freshstock-source.zip`, a small source bundle containing `src/`, `configs/` and `pyproject.toml`.

Upload that ZIP as a private Kaggle dataset. A dataset name such as `freshstock-source` is easiest because the notebook expects it at `/kaggle/input/freshstock-source`.

## Data source

The notebook downloads the public M5 mirror directly from Zenodo:

```text
https://zenodo.org/api/records/12636070
```

Kaggle internet access must be enabled for this download. Review the original dataset terms and the mirror metadata before use.

## Running the session

1. Upload `notebooks/freshstock_m5_kaggle.ipynb` to Kaggle.
2. Attach the private `freshstock-source` dataset.
3. Enable internet access.
4. Run all cells.

The notebook installs the source bundle, downloads M5, prepares a selected store, trains point and quantile models, and writes reproducible output under `/kaggle/working`.

## Reproducibility controls

- Zenodo archive checksum is verified before extraction.
- Product selection uses training-period statistics only.
- Chronological validation and test boundaries are fixed.
- Feature creation uses observations through the forecast origin.
- The training seed, horizon and iteration count are explicit variables.
- Metrics and prediction rows are saved for inspection.

## Output

The final cells show aggregate and per-product metrics, preview test predictions and write a ZIP artifact that can be downloaded from Kaggle.
