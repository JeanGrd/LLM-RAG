.DEFAULT_GOAL := help

.PHONY: help ingest reingest backend openwebui llama models

ifneq (,$(wildcard .env))
include .env
export
endif

help:
	@echo "Targets:"
	@echo "  make backend            Start backend (auto-ingest if index missing)"
	@echo "  make openwebui          Start Open WebUI connected to backend"
	@echo "  make llama              Start llama-server (LLAMA_MODEL or auto-pick)"
	@echo "  make models             List local GGUF files + remote /v1/models"
	@echo "  make ingest             Build/update index"
	@echo "  make reingest           Reset and rebuild index"

ingest:
	. .venv/bin/activate && python scripts/data/ingest.py

reingest:
	rm -rf data/indices/*
	. .venv/bin/activate && python scripts/data/ingest.py

backend:
	./scripts/run/backend.sh

openwebui:
	./scripts/run/openwebui.sh

llama:
	./scripts/run/llama_server.sh "$(LLAMA_MODEL)"

models:
	./scripts/run/llama_models.sh
