.PHONY: setup ingest reindex api test lint

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e .

ingest:
	. .venv/bin/activate && python scripts/ingest.py

reindex:
	rm -rf data/indices/*
	. .venv/bin/activate && python scripts/ingest.py

api:
	. .venv/bin/activate && python scripts/run_api.py

test:
	. .venv/bin/activate && pytest

lint:
	. .venv/bin/activate && ruff check src tests
