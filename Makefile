# ============================================================
# Makefile - 1min-Gateway Project
# ============================================================
# Commandes principales pour le développement et le déploiement
# Usage: make <command>
# Aide: make help
# ============================================================

# --- VARIABLES ---
PYTHON := python3
PIP := pip
DOCKER_IMAGE := billelattafi/1min-gateway
DOCKER_TAG := latest
COMPOSE_FILE := docker-compose.yml

# Couleurs pour l'output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
NC := \033[0m # No Color

# --- HELP ---
.PHONY: help
help: ## 📖 Affiche cette aide
	@echo "$(CYAN)════════════════════════════════════════$(NC)"
	@echo "$(CYAN)  1min-Gateway - Commandes Disponibles$(NC)"
	@echo "$(CYAN)════════════════════════════════════════$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# --- SETUP ---
.PHONY: install
install: ## 🔧 Installe les dépendances et configure les hooks
	@echo "$(BLUE)📦 Installation des dépendances Python...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(BLUE)🔧 Installation des outils de développement...$(NC)"
	$(PIP) install pre-commit black flake8 isort pytest pytest-cov bandit
	@echo "$(BLUE)🪝 Installation des pre-commit hooks...$(NC)"
	pre-commit install --hook-type commit-msg
	pre-commit install --hook-type pre-commit
	@echo "$(GREEN)✅ Setup terminé. Prêt à coder !$(NC)"

.PHONY: install-ci
install-ci: ## 📦 Installation pour CI/CD (sans hooks)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt pytest pytest-cov

.PHONY: update
update: ## ⬆️ Met à jour toutes les dépendances
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r requirements.txt
	pre-commit autoupdate
	@echo "$(GREEN)✅ Dépendances mises à jour$(NC)"

# --- DÉVELOPPEMENT ---
.PHONY: dev
dev: ## 🚀 Lance l'application en mode développement
	@echo "$(BLUE)🚀 Lancement de 1min-Gateway...$(NC)"
	$(PYTHON) main.py

.PHONY: dev-watch
dev-watch: ## 👀 Lance l'application avec auto-reload (watchdog)
	@echo "$(BLUE)👀 Mode watch activé (Ctrl+C pour arrêter)$(NC)"
	watchmedo auto-restart --directory=./ --pattern='*.py' --recursive -- $(PYTHON) main.py

# --- TESTS ---
.PHONY: test
test: ## ✅ Lance les tests unitaires
	@echo "$(BLUE)🧪 Exécution des tests...$(NC)"
	export PYTHONPATH=. && pytest -v

.PHONY: test-cov
test-cov: ## 📊 Lance les tests avec couverture de code
	@echo "$(BLUE)📊 Tests avec couverture...$(NC)"
	export PYTHONPATH=. && pytest --cov=. --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✅ Rapport de couverture généré dans htmlcov/index.html$(NC)"

.PHONY: test-watch
test-watch: ## 🔄 Lance les tests en mode watch
	export PYTHONPATH=. && pytest-watch

# --- CODE QUALITY ---
.PHONY: lint
lint: ## 🔍 Vérifie la qualité du code (flake8 + black)
	@echo "$(BLUE)🔍 Analyse du code...$(NC)"
	black --check .
	flake8 . --max-line-length=100 --extend-ignore=E203,W503
	isort --check-only --profile black .
	@echo "$(GREEN)✅ Code conforme aux standards$(NC)"

.PHONY: format
format: ## 🎨 Formate automatiquement le code
	@echo "$(BLUE)🎨 Formatage du code...$(NC)"
	black .
	isort --profile black .
	@echo "$(GREEN)✅ Code formaté$(NC)"

.PHONY: security
security: ## 🔒 Scan de sécurité avec Bandit
	@echo "$(BLUE)🔒 Scan de sécurité...$(NC)"
	bandit -r . -x ./tests,./venv,./logs
	@echo "$(GREEN)✅ Aucune vulnérabilité détectée$(NC)"

.PHONY: check
check: lint security test ## ✅ Vérifie tout (lint + security + tests)
	@echo "$(GREEN)✅ Toutes les vérifications passées !$(NC)"

# --- PRE-COMMIT ---
.PHONY: pre-commit
pre-commit: ## 🪝 Exécute manuellement tous les pre-commit hooks
	pre-commit run --all-files

.PHONY: pre-commit-update
pre-commit-update: ## ⬆️ Met à jour les versions des hooks
	pre-commit autoupdate

# --- COMMITS ---
.PHONY: commit
commit: ## 💬 Fait un commit interactif avec gitmoji (via commitify)
	@command -v commitify >/dev/null 2>&1 || \
		{ echo "$(RED)❌ commitify non installé. Installation: npm i -g commitify$(NC)"; exit 1; }
	npx commitify

.PHONY: commit-quick
commit-quick: ## ⚡ Commit rapide avec message passé en argument (ex: make commit-quick MSG="fix: bug")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)❌ Usage: make commit-quick MSG=\"votre message\"$(NC)"; \
		exit 1; \
	fi
	git add .
	git commit -m "$(MSG)"

# --- DOCKER ---
.PHONY: docker-build
docker-build: ## 🐳 Build l'image Docker (multi-stage)
	@echo "$(BLUE)🐳 Build de l'image Docker...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✅ Image construite: $(DOCKER_IMAGE):$(DOCKER_TAG)$(NC)"

.PHONY: docker-build-no-cache
docker-build-no-cache: ## 🔄 Build Docker sans cache
	@echo "$(BLUE)🔄 Build sans cache...$(NC)"
	docker build --no-cache -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

.PHONY: docker-run
docker-run: ## ▶️ Lance le container Docker en standalone
	@echo "$(BLUE)▶️ Démarrage du container...$(NC)"
	docker run -d -p 5001:5001 --name 1min-gateway --env-file .env $(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: docker-stop
docker-stop: ## ⏹️ Arrête et supprime le container
	docker stop 1min-gateway 2>/dev/null || true
	docker rm 1min-gateway 2>/dev/null || true

.PHONY: docker-logs
docker-logs: ## 📜 Affiche les logs du container
	docker logs -f 1min-gateway

.PHONY: docker-shell
docker-shell: ## 🐚 Ouvre un shell dans le container
	docker exec -it 1min-gateway /bin/sh

.PHONY: docker-scan
docker-scan: ## 🔍 Scan de sécurité de l'image avec Trivy
	@command -v trivy >/dev/null 2>&1 || \
		{ echo "$(RED)❌ Trivy non installé. Voir: https://aquasecurity.github.io/trivy/$(NC)"; exit 1; }
	trivy image --severity HIGH,CRITICAL $(DOCKER_IMAGE):$(DOCKER_TAG)

# --- DOCKER COMPOSE ---
.PHONY: up
up: ## 🚀 Lance l'infrastructure complète (docker-compose up)
	@echo "$(BLUE)🚀 Démarrage de l'infrastructure...$(NC)"
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Infrastructure démarrée$(NC)"
	@echo "$(CYAN)📊 Vérifier les logs: make logs$(NC)"

.PHONY: down
down: ## ⏹️ Arrête tous les conteneurs
	@echo "$(YELLOW)⏹️ Arrêt de l'infrastructure...$(NC)"
	docker compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✅ Infrastructure arrêtée$(NC)"

.PHONY: restart
restart: down up ## 🔄 Redémarre l'infrastructure

.PHONY: logs
logs: ## 📜 Affiche les logs de tous les services
	docker compose -f $(COMPOSE_FILE) logs -f

.PHONY: logs-gateway
logs-gateway: ## 📜 Affiche les logs du gateway uniquement
	docker compose -f $(COMPOSE_FILE) logs -f 1min-gateway

.PHONY: ps
ps: ## 📊 Liste les conteneurs en cours d'exécution
	docker compose -f $(COMPOSE_FILE) ps

.PHONY: pull
pull: ## ⬇️ Pull la dernière version de l'image
	docker compose -f $(COMPOSE_FILE) pull

.PHONY: update-deploy
update-deploy: pull restart ## 🔄 Met à jour et redéploie (pull + restart)
	@echo "$(GREEN)✅ Déploiement mis à jour !$(NC)"

# --- RELEASE ---
.PHONY: release
release: ## 🚀 Déclenche une release manuelle (commit vide)
	@echo "$(YELLOW)🚀 Déclenchement d'une release...$(NC)"
	git commit --allow-empty -m "🚀 chore(release): Trigger new version"
	git push origin main
	@echo "$(GREEN)✅ Release déclenchée ! Voir GitHub Actions$(NC)"

.PHONY: changelog
changelog: ## 📝 Génère le CHANGELOG.md (local)
	@echo "$(BLUE)📝 Génération du changelog...$(NC)"
	npx conventional-changelog-cli -p gitmoji -i CHANGELOG.md -s
	@echo "$(GREEN)✅ Changelog généré$(NC)"

# --- NETTOYAGE ---
.PHONY: clean
clean: ## 🧹 Supprime les fichiers temporaires et caches
	@echo "$(BLUE)🧹 Nettoyage...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/ dist/ build/
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

.PHONY: clean-docker
clean-docker: ## 🐳 Nettoie les ressources Docker inutilisées
	@echo "$(YELLOW)🐳 Nettoyage Docker...$(NC)"
	docker system prune -af --volumes
	@echo "$(GREEN)✅ Docker nettoyé$(NC)"

.PHONY: clean-all
clean-all: clean clean-docker ## 🧹 Nettoyage complet (Python + Docker)

# --- UTILITAIRES ---
.PHONY: requirements
requirements: ## 📋 Génère requirements.txt depuis l'environnement actuel
	$(PIP) freeze > requirements.txt
	@echo "$(GREEN)✅ requirements.txt mis à jour$(NC)"

.PHONY: env-check
env-check: ## 🔍 Vérifie les variables d'environnement
	@echo "$(BLUE)🔍 Vérification de l'environnement...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ Fichier .env manquant$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Fichier .env présent$(NC)"
	@grep -v '^#' .env | grep -v '^$$' | wc -l | xargs echo "Variables configurées:"

.PHONY: setup-secrets
setup-secrets: ## 🔐 Crée un fichier .secrets.baseline pour detect-secrets
	@if [ ! -f .secrets.baseline ]; then \
		echo "$(BLUE)🔐 Création du baseline secrets...$(NC)"; \
		detect-secrets scan > .secrets.baseline; \
		echo "$(GREEN)✅ Baseline créé$(NC)"; \
	else \
		echo "$(YELLOW)⚠️ Baseline déjà existant$(NC)"; \
	fi

.PHONY: version
version: ## 📌 Affiche les versions des outils
	@echo "$(CYAN)═══════════════════════════════$(NC)"
	@echo "$(CYAN)  Versions des outils$(NC)"
	@echo "$(CYAN)═══════════════════════════════$(NC)"
	@echo "Python:       $$($(PYTHON) --version)"
	@echo "Docker:       $$(docker --version)"
	@echo "Docker Compose: $$(docker compose version)"
	@echo "Pre-commit:   $$(pre-commit --version 2>/dev/null || echo 'Non installé')"
	@echo "Trivy:        $$(trivy --version 2>/dev/null || echo 'Non installé')"

.PHONY: health
health: ## 🏥 Vérifie l'état de santé de l'application
	@echo "$(BLUE)🏥 Vérification de l'état de santé...$(NC)"
	@curl -f http://localhost:5001/health || echo "$(RED)❌ Application non accessible$(NC)"

# --- CI/CD ---
.PHONY: ci-test
ci-test: install-ci test ## 🔄 Simule le pipeline CI (tests)

.PHONY: ci-full
ci-full: install-ci lint security test docker-build ## 🔄 Simule le pipeline CI complet

# --- DEFAULT ---
.DEFAULT_GOAL := help
