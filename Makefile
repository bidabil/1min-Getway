# ============================================================
# Makefile - 1min-Gateway
# ============================================================

PYTHON ?= python3
IMAGE  ?= billelattafi/1min-gateway
export PYTHONPATH := src

.PHONY: help install dev test test-cov lint format typecheck check key build up down logs \
        monitoring-up monitoring-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[32m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime and development dependencies
	$(PYTHON) -m pip install -r requirements-dev.txt

dev: ## Run the gateway locally (reads .env)
	$(PYTHON) -m gateway

key: ## Create a gateway API key: make key NAME=my-agent
	$(PYTHON) -m gateway.cli create-key $(or $(NAME),agent)

test: ## Run the tests
	$(PYTHON) -m pytest

test-cov: ## Run the tests with coverage
	$(PYTHON) -m pytest --cov=src/gateway --cov-report=term-missing

lint: ## Lint and check formatting
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format: ## Format the code
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

typecheck: ## Static type checking (strict)
	$(PYTHON) -m mypy src

check: lint typecheck test-cov ## Everything CI runs

build: ## Build the Docker image
	docker build -t $(IMAGE):latest .

up: ## Start with Docker Compose
	docker compose up -d

down: ## Stop Docker Compose
	docker compose down

logs: ## Follow the gateway logs
	docker compose logs -f gateway

monitoring-up: ## Start Prometheus and Grafana
	docker compose -f docker-compose.monitoring.yml up -d

monitoring-down: ## Stop Prometheus and Grafana
	docker compose -f docker-compose.monitoring.yml down

clean: ## Remove caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov/

.DEFAULT_GOAL := help
