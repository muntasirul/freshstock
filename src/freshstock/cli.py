"""Command-line entry points shared by local development and Kaggle."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from freshstock.data import download_m5, prepare_m5


def package_kaggle(root: Path) -> Path:
    output = root / "artifacts" / "freshstock-source.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for folder in ("src", "configs"):
            for path in sorted((root / folder).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                    archive.write(path, path.relative_to(root))
        archive.write(root / "pyproject.toml", "pyproject.toml")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshStock data and training workflow")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="Download and verify the public M5 mirror")
    download.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    prepare = commands.add_parser("prepare", help="Prepare a store with chronological splits")
    prepare.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    prepare.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    prepare.add_argument("--store", default="CA_1")
    prepare.add_argument("--products", type=int, default=20)
    prepare.add_argument("--validation-days", type=int, default=168)
    prepare.add_argument("--test-days", type=int, default=168)
    trainer = commands.add_parser("train", help="Train and evaluate cumulative-demand models")
    trainer.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    trainer.add_argument("--output-dir", type=Path, default=Path("artifacts/model"))
    trainer.add_argument("--horizon", type=int, default=2)
    trainer.add_argument("--quantile", type=float, default=0.8)
    trainer.add_argument("--iterations", type=int, default=250)
    trainer.add_argument("--seed", type=int, default=42)
    commands.add_parser("package-kaggle", help="Create a small source bundle for Kaggle")
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "download":
        result = download_m5(**args)
    elif command == "prepare":
        result = prepare_m5(**args)
    elif command == "train":
        from freshstock.forecasting import train

        result = train(**args)
    else:
        result = {"archive": str(package_kaggle(Path.cwd()))}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
