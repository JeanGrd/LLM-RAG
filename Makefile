.PHONY: setup ingest reindex api test lint open-webui open-webui-down open-webui-reset ollama-list ollama-pull

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

open-webui:
	./scripts/compose.sh -f docker-compose.open-webui.yml up -d

open-webui-down:
	./scripts/compose.sh -f docker-compose.open-webui.yml down

open-webui-reset:
	./scripts/compose.sh -f docker-compose.open-webui.yml down -v
	./scripts/compose.sh -f docker-compose.open-webui.yml up -d

ollama-list:
	docker exec llm-rag-ollama ollama list

ollama-pull:
	test -n "$(MODEL)" || (echo "Usage: make ollama-pull MODEL=qwen3:4b" && exit 1)
	docker exec llm-rag-ollama ollama pull $(MODEL)
