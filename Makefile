
# ============================================================
# Makefile - 1min-Gateway (Optimisé)
# ============================================================

PYTHON := python3
IMAGE := billelattafi/1min-gateway

.PHONY: help install dev test lint format security check clean up down logs

help: ## 📖 Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[32m%-15s\033[0m %s\n", $$1, $$2}'

# --- SETUP ---
install: ## 🔧 Installation complète
	pip install -r requirements.txt
	pip install ruff pre-commit
	pre-commit install --hook-type commit-msg --hook-type pre-commit

# --- DÉVELOPPEMENT ---
dev: ## 🚀 Lance l'application
	$(PYTHON) main.py

# --- QUALITÉ ---
test: ## ✅ Lance les tests
	pytest tests/ -v

test-cov: ## 📊 Tests avec coverage
	pytest tests/ -v --cov=src --cov-report=html --cov-fail-under=75

lint: ## 🔍 Vérifie le code (Ruff)
	ruff check .

format: ## 🎨 Formate le code (Ruff)
	ruff format .
	ruff check --fix .

security: ## 🔒 Scan de sécurité
	ruff check --select S .

check: lint test ## ✅ Lint + Tests

# --- DOCKER ---
deploy: ## 🚀 Déploie sur un serveur distant (depuis le serveur)
	bash deploy.sh

monitoring-up: ## 📊 Lance Prometheus + Grafana
	docker compose -f docker-compose.monitoring.yml up -d

monitoring-down: ## ⏹️ Arrête Prometheus + Grafana
	docker compose -f docker-compose.monitoring.yml down

build: ## 🐳 Build l'image
	docker build -t $(IMAGE):latest .

up: ## 🚀 Lance l'infrastructure
	docker compose up -d

down: ## ⏹️ Arrête l'infrastructure
	docker compose down

logs: ## 📜 Affiche les logs
	docker compose logs -f 1min-gateway

# --- NETTOYAGE ---
clean: ## 🧹 Nettoie les caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov/

.DEFAULT_GOAL := help
