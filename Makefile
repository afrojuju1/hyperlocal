SHELL := /bin/bash

API_DIR := apps/api
WEB_DIR := apps/web
API_BASE_URL ?= http://localhost:18000
DATABASE_URL ?= postgresql+psycopg://hyperlocal:hyperlocal@localhost:55432/hyperlocal

.DEFAULT_GOAL := help

.PHONY: help setup up down logs dev api worker web db-init db-reset check check-api check-web smoke generate clean clean-output

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Hyperlocal commands:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install API and web dependencies
	cd $(API_DIR) && uv sync
	cd $(WEB_DIR) && bun install

up: ## Start the Docker stack
	docker compose up -d --build

down: ## Stop the Docker stack
	docker compose down

logs: ## Follow Docker stack logs
	docker compose logs -f

dev: up ## Start the normal local dev stack

api: ## Run the FastAPI app locally
	cd $(API_DIR) && PYTHONPATH=src uv run uvicorn hyperlocal.api.main:app --host 0.0.0.0 --port 8000 --reload

worker: ## Run the creative worker locally
	cd $(API_DIR) && PYTHONPATH=src uv run scripts/run_creative_worker.py

web: ## Run the Next.js app locally
	cd $(WEB_DIR) && bun run dev

db-init: ## Apply the SQL schema to the configured database
	psql "$(DATABASE_URL)" -f $(API_DIR)/sql/schema.sql

db-reset: ## Drop and recreate the local database schema, with confirmation
	@read -p "Reset local database schema? Type RESET to continue: " confirm; \
	if [[ "$$confirm" != "RESET" ]]; then echo "Aborted."; exit 1; fi
	psql "$(DATABASE_URL)" -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
	psql "$(DATABASE_URL)" -f $(API_DIR)/sql/schema.sql

check: check-api check-web ## Run the full quality gate

check-api: ## Run API tests and compile checks
	cd $(API_DIR) && PYTHONPATH=src uv run python -m unittest discover -s tests
	cd $(API_DIR) && PYTHONPATH=src uv run python -m compileall src/hyperlocal scripts tests

check-web: ## Run frontend lint and production build
	cd $(WEB_DIR) && bun run lint
	cd $(WEB_DIR) && bun run build

smoke: ## Run stack health checks
	cd $(API_DIR) && PYTHONPATH=src uv run scripts/check_stack.py

generate: ## Enqueue a sample creative run against the local API
	curl -sS -X POST "$(API_BASE_URL)/api/v1/creative-runs" \
		-H "Content-Type: application/json" \
		--data-binary @examples/creative-run-smoothie.json
	@printf "\n"

clean: ## Remove local caches only
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf $(WEB_DIR)/.next $(WEB_DIR)/tsconfig.tsbuildinfo

clean-output: ## Remove generated output, with confirmation
	@read -p "Delete generated output? Type DELETE to continue: " confirm; \
	if [[ "$$confirm" != "DELETE" ]]; then echo "Aborted."; exit 1; fi
	rm -rf output $(API_DIR)/output
