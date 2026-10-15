.PHONY: install test lint up down ingest
install:
	pip install -e ".[dev]"
test:
	pytest -q
lint:
	ruff check src tests
up:
	docker compose up -d
down:
	docker compose down
ingest:
	python -m surfline.cli ingest --source all
