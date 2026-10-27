.PHONY: setup download prepare train test api web package-kaggle
setup:
	uv sync --extra dev
	npm ci --prefix apps/web
download:
	uv run freshstock download
prepare:
	uv run freshstock prepare --raw-dir data/raw --output-dir data/processed
train:
	uv run freshstock train --data-dir data/processed --output-dir artifacts/model
test:
	uv run pytest
	uv run ruff check .
	npm run build --prefix apps/web
api:
	uv run uvicorn freshstock.api:app --host 127.0.0.1 --port 8000
web:
	npm run dev --prefix apps/web -- --host 127.0.0.1
package-kaggle:
	uv run freshstock package-kaggle
