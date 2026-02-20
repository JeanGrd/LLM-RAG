.DEFAULT_GOAL := help

.PHONY: help ingest reingest backend openwebui llama models up down doctor

ifneq (,$(wildcard .env))
include .env
export
endif

help:
	@echo "Targets:"
	@echo "  make backend            Start backend (ingest is manual)"
	@echo "  make openwebui          Start Open WebUI connected to backend"
	@echo "  make llama              Start llama-server (LLAMA_MODEL or auto-pick)"
	@echo "  make models             List local GGUF files + remote /v1/models"
	@echo "  make up                 Start chat llama + embed llama + backend + Open WebUI"
	@echo "  make down               Stop stack started by make up"
	@echo "  make doctor             Run local diagnostics (venv, GGUF, endpoints)"
	@echo "  make ingest             Build/update index (auto-start embeddings server if needed)"
	@echo "  make reingest           Force full rebuild: reset index then ingest from scratch"

ingest:
	./scripts/run/ingest.sh

reingest:
	./scripts/run/ingest.sh --full-rebuild

backend:
	./scripts/run/backend.sh

openwebui:
	./scripts/run/openwebui.sh

llama:
	./scripts/run/llama_server.sh "$(LLAMA_MODEL)"

models:
	./scripts/run/llama_models.sh

up:
	./scripts/run/up.sh

down:
	./scripts/run/down.sh

doctor:
	./scripts/run/doctor.sh
