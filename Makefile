.PHONY: install dev test lint demo
install:
	python -m pip install -e '.[dev]'
dev:
	uvicorn atlas.api:app --reload
lint:
	ruff check src tests
test:
	pytest -q
demo:
	python -m atlas.cli seed
	uvicorn atlas.api:app --reload
