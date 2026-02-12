.PHONY: setup ingest reindex api quick-backend quick-openwebui quick test lint

setup:
	python3.11 -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e . --no-build-isolation

ingest:
	. .venv/bin/activate && python scripts/data/ingest.py

reindex:
	rm -rf data/indices/*
	. .venv/bin/activate && python scripts/data/ingest.py

api:
	. .venv/bin/activate && python scripts/app/run_api.py

quick:
quick-backend:
	./scripts/run_quick_backend.sh

quick-openwebui:
	./scripts/run_quick_openwebui.sh

test:
	. .venv/bin/activate && pytest

lint:
	. .venv/bin/activate && ruff check src tests
