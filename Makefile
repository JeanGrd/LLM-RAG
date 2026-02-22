.DEFAULT_GOAL := help

.PHONY: help install ingest reingest backend llama up down clean clean-data clean-all openwebui

BACKEND_VENV ?= .venv-backend
OPENWEBUI_VENV ?= .venv-openwebui

help:
	@echo "Targets:"
	@echo "  make install    Create venvs (.venv-backend, .venv-openwebui) and install deps"
	@echo "  make ingest     Build/update index (starts embed server if needed)"
	@echo "  make reingest   Reset index then ingest from scratch"
	@echo "  make backend    Start API only (expects running llama servers)"
	@echo "  make llama      Start chat + embed servers"
	@echo "  make up         Start chat + embed + backend + WebUI"
	@echo "  make down       Stop managed servers (chat, embed, backend, WebUI)"
	@echo "  make clean      Remove venvs and runtime pids/logs"
	@echo "  make clean-data Remove indices/cache/tmp/.openwebui (destroys search index)"
	@echo "  make clean-all  clean + clean-data"
	@echo "  make openwebui  Start Open WebUI (uses .venv-openwebui)"

install:
	./scripts/install.sh

ingest:
	./scripts/run/ingest.sh

reingest:
	./scripts/run/ingest.sh --full-rebuild

backend:
	./scripts/run/backend.sh

llama:
	./scripts/run/llama.sh

up:
	./scripts/run/up.sh

down:
	./scripts/run/down.sh

clean:
	rm -rf $(BACKEND_VENV) $(OPENWEBUI_VENV) .run

clean-data:
	rm -rf .openwebui .cache tmp data/indices

clean-all: clean clean-data

openwebui:
	./scripts/run/openwebui.sh
