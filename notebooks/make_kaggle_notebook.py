"""Generate the Kaggle-ready FreshStock training notebook."""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
notebook = nbf.v4.new_notebook(
    cells=[
        nbf.v4.new_markdown_cell(
            """# FreshStock: M5 cumulative-demand training

This Kaggle session downloads a checksum-verified public mirror of the M5 dataset,
prepares a selected store, and trains LightGBM point and quantile models.

**Evaluation convention:** information through the close of day `t` predicts total demand
for days `t+1` through `t+H`. Chronological validation and test windows are kept separate.

**Data assumption:** observed sales are used as a demand proxy. True stockouts and inventory
levels are not present in M5."""
        ),
        nbf.v4.new_markdown_cell(
            """## Attach the project source

Run `uv run freshstock package-kaggle` locally, upload `artifacts/freshstock-source.zip`
as a private Kaggle dataset named `freshstock-source`, and attach it to this notebook.
Alternatively, keep this notebook inside the repository for local execution."""
        ),
        nbf.v4.new_code_cell(
            """import subprocess
import sys
from pathlib import Path

KAGGLE_INPUT = Path('/kaggle/input/freshstock-source')
LOCAL_ROOT = Path.cwd().parent if (Path.cwd().parent / 'src/freshstock').exists() else Path.cwd()

if KAGGLE_INPUT.exists():
    bundles = sorted(KAGGLE_INPUT.glob('*.zip'))
    if not bundles:
        raise FileNotFoundError('Attach a Kaggle dataset containing freshstock-source.zip.')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', str(bundles[-1])], check=True)
elif (LOCAL_ROOT / 'pyproject.toml').exists() and (LOCAL_ROOT / 'src/freshstock').exists():
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '-e', str(LOCAL_ROOT)], check=True)
else:
    raise FileNotFoundError('Project source not found. Attach freshstock-source.zip or run inside the repository.')

subprocess.run(
    [sys.executable, '-m', 'pip', 'install', '-q', 'pandas>=2.2', 'numpy>=1.26', 'pyarrow>=17', 'scikit-learn>=1.5', 'lightgbm>=4.5', 'joblib>=1.4', 'httpx>=0.27'],
    check=True,
)
print('FreshStock source is ready.')"""
        ),
        nbf.v4.new_markdown_cell("## Configure the experiment"),
        nbf.v4.new_code_cell(
            """from pathlib import Path

WORK_DIR = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd() / 'kaggle-output'
RAW_DIR = WORK_DIR / 'data/raw'
PROCESSED_DIR = WORK_DIR / 'data/processed'
MODEL_DIR = WORK_DIR / 'artifacts/model'

STORE = 'CA_1'
PRODUCT_COUNT = 20
VALIDATION_DAYS = 168
TEST_DAYS = 168
HORIZON = 2
QUANTILE = 0.8
ITERATIONS = 250
SEED = 42

print({'work_dir': str(WORK_DIR), 'store': STORE, 'horizon': HORIZON})"""
        ),
        nbf.v4.new_markdown_cell(
            """## Download and prepare M5

The downloader verifies the Zenodo archive checksum and extracts only the files used by this
experiment. Keep raw data out of source control."""
        ),
        nbf.v4.new_code_cell(
            """from freshstock.data import download_m5, prepare_m5

manifest = download_m5(RAW_DIR)
metadata = prepare_m5(
    raw_dir=RAW_DIR,
    output_dir=PROCESSED_DIR,
    store=STORE,
    products=PRODUCT_COUNT,
    validation_days=VALIDATION_DAYS,
    test_days=TEST_DAYS,
)
manifest, metadata"""
        ),
        nbf.v4.new_markdown_cell("## Train point and quantile models"),
        nbf.v4.new_code_cell(
            """from freshstock.forecasting import train

report = train(
    data_dir=PROCESSED_DIR,
    output_dir=MODEL_DIR,
    horizon=HORIZON,
    quantile=QUANTILE,
    iterations=ITERATIONS,
    seed=SEED,
)
report['metrics']"""
        ),
        nbf.v4.new_markdown_cell(
            """## Inspect held-out predictions

Aggregate improvement does not mean every product improved. Review product-level results
before making a CV or portfolio claim."""
        ),
        nbf.v4.new_code_cell(
            """import pandas as pd

predictions = pd.read_parquet(MODEL_DIR / 'test_predictions.parquet')
predictions.head()"""
        ),
        nbf.v4.new_code_cell(
            """summary = pd.DataFrame(report['per_product'])
summary['point_wape'] = summary['point'].map(lambda value: value['wape'])
summary['baseline_wape'] = summary['baseline'].map(lambda value: value['wape'])
summary[['item_id', 'point_wape', 'baseline_wape']].sort_values('point_wape')"""
        ),
        nbf.v4.new_markdown_cell("## Package the experiment output"),
        nbf.v4.new_code_cell(
            """import json
import shutil

artifact_zip = shutil.make_archive(str(WORK_DIR / 'freshstock-experiment'), 'zip', MODEL_DIR)
print(f'Wrote {artifact_zip}')
print(json.dumps(report['metrics'], indent=2))"""
        ),
        nbf.v4.new_markdown_cell(
            """## Interpretation notes

- Lower MAE and WAPE indicate better cumulative demand estimates.
- Quantile coverage should be evaluated against the requested quantile; coverage around 80%
  is expected for the initial `QUANTILE = 0.8` setting.
- Inventory savings require the separate simulator in `freshstock.inventory`; forecast quality
  alone does not establish better ordering outcomes.
- Describe results as benchmark/simulation findings unless real retailer data is used."""
        ),
    ],
    metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
)
nbf.write(notebook, ROOT / "freshstock_m5_kaggle.ipynb")
print(ROOT / "freshstock_m5_kaggle.ipynb")
