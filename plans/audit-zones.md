# Audit par Zones — 1min-Gateway

## Principe

Chaque zone = périmètre isolé = un seul prompt d'audit ciblé.
Moins de contexte chargé → meilleure détection de code mort, variables inutiles, doublons.

Outil recommandé pour le code Python : `vulture src/ --min-confidence 70`

---

## Index — tous les fichiers du projet

### Racine

| Fichier | Zone |
|---------|------|
| `Dockerfile` | I1 — Docker |
| `docker-compose.yml` | I1 — Docker |
| `docker-compose.monitoring.yml` | I1 — Docker |
| `.dockerignore` | I1 — Docker |
| `.github/workflows/ci.yml` | I2 — CI |
| `.github/workflows/ci-build.yml` | I2 — CI |
| `.github/workflows/ci-security.yml` | I2 — CI |
| `.github/workflows/cd-production.yml` | I3 — CD |
| `.github/workflows/cd-staging.yml` | I3 — CD |
| `.github/workflows/dependabot-auto-merge.yml` | I3 — CD |
| `.github/dependabot.yml` | I3 — CD |
| `deploy.sh` | I4 — Release/Deploy |
| `Makefile` | I4 — Release/Deploy |
| `.releaserc.json` | I4 — Release/Deploy |
| `commitlint.config.js` | I4 — Release/Deploy |
| `pyproject.toml` | I5 — Config projet |
| `requirements.txt` | I5 — Config projet |
| `requirements-dev.txt` | I5 — Config projet |
| `.pre-commit-config.yaml` | I5 — Config projet |
| `.editorconfig` | I5 — Config projet |
| `.env.example` | I5 — Config projet |
| `README.md` | I6 — Documentation |
| `monitoring/prometheus.yml` | I6 — Documentation |
| `docs/API_PARAMETERS.md` | I6 — Documentation |
| `docs/AUDIT.md` | I6 — Documentation |
| `docs/CI-CD-CHEATSHEET.md` | I6 — Documentation |
| `docs/CI-CD-DOCUMENTATION.md` | I6 — Documentation |
| `docs/CONTRIBUTING.md` | I6 — Documentation |
| `docs/DEPENDABOT-DOCUMENTATION.md` | I6 — Documentation |
| `docs/ENV-DOCKER-GUIDE.md` | I6 — Documentation |
| `docs/INTEGRATION-GUIDE.md` | I6 — Documentation |
| `docs/index.md` | I6 — Documentation |
| `docs/FUNDING.yml` | I6 — Documentation |
| `main.py` | P2 — Config & Bootstrap |
| `printedcolors.py` | P6 — Adapters & Glue |
| `plans/audit-zones.md` | _(méta — hors audit)_ |
| `plans/improvements-plan.md` | _(méta — hors audit)_ |
| `.env` | _(secrets — ne jamais auditer)_ |
| `.gitignore` | _(méta git — hors audit)_ |
| `LICENSE` | _(immuable — hors audit)_ |

### Source Python `src/`

| Fichier | Zone |
|---------|------|
| `src/__init__.py` | P1 — Contrat public |
| `src/infrastructure/__init__.py` | P1 — Contrat public |
| `src/api/schemas.py` | P1 — Contrat public |
| `src/config.py` | P2 — Config & Bootstrap |
| `src/api/app.py` | P2 — Config & Bootstrap |
| `src/api/__init__.py` | P2 — Config & Bootstrap |
| `src/domain/models.py` | P3 — Domaine |
| `src/domain/ports.py` | P3 — Domaine |
| `src/domain/services/chat_service.py` | P3 — Domaine |
| `src/domain/conversation_service.py` | P3 — Domaine |
| `src/domain/model_provider.py` | P3 — Domaine |
| `src/domain/image_mapper.py` | P3 — Domaine |
| `src/infrastructure/one_min_client.py` | P4 — Infra services |
| `src/infrastructure/asset_service.py` | P4 — Infra services |
| `src/infrastructure/api_key_validator.py` | P4 — Infra services |
| `src/infrastructure/token_service.py` | P4 — Infra services |
| `src/infrastructure/model_cache.py` | P4 — Infra services |
| `src/infrastructure/network_service.py` | P4 — Infra services |
| `src/infrastructure/error_service.py` | P4 — Infra services |
| `src/infrastructure/adapters/one_min_asset_adapter.py` | P4 — Infra services |
| `src/infrastructure/adapters/one_min_conversation_adapter.py` | P4 — Infra services |
| `src/infrastructure/adapters/token_adapter.py` | P4 — Infra services |
| `src/infrastructure/metrics.py` | P5 — Transversal |
| `src/infrastructure/logging_config.py` | P5 — Transversal |
| `src/infrastructure/circuit_breaker.py` | P5 — Transversal |
| `src/infrastructure/rate_limiter.py` | P5 — Transversal |
| `src/infrastructure/health_service.py` | P5 — Transversal |
| `src/infrastructure/webhooks.py` | P5 — Transversal |
| `src/adapters/openai_adapter.py` | P6 — Adapters & Glue |
| `src/application/use_cases.py` | P6 — Adapters & Glue |
| `src/container.py` | P6 — Adapters & Glue |
| `src/api/routes.py` | P6 — Adapters & Glue |

### Tests `tests/`

| Fichier | Zone |
|---------|------|
| `tests/conftest.py` | P7 — Tests |
| `tests/conftest_fastapi.py` | P7 — Tests |
| `tests/test_adapters/test_openai_adapter.py` | P7 — Tests |
| `tests/test_application/test_use_cases.py` | P7 — Tests |
| `tests/test_domain/test_chat_service.py` | P7 — Tests |
| `tests/test_domain/test_conversation_service.py` | P7 — Tests |
| `tests/test_domain/test_model_provider.py` | P7 — Tests |
| `tests/test_domain/test_ports.py` | P7 — Tests |
| `tests/test_error_service.py` | P7 — Tests |
| `tests/test_infrastructure/test_adapters.py` | P7 — Tests |
| `tests/test_infrastructure/test_api_key_validator.py` | P7 — Tests |
| `tests/test_infrastructure/test_asset_service.py` | P7 — Tests |
| `tests/test_infrastructure/test_circuit_breaker.py` | P7 — Tests |
| `tests/test_infrastructure/test_health_service.py` | P7 — Tests |
| `tests/test_infrastructure/test_logging_config.py` | P7 — Tests |
| `tests/test_infrastructure/test_metrics.py` | P7 — Tests |
| `tests/test_infrastructure/test_network_service.py` | P7 — Tests |
| `tests/test_infrastructure/test_one_min_client.py` | P7 — Tests |
| `tests/test_infrastructure/test_rate_limiter.py` | P7 — Tests |
| `tests/test_infrastructure/test_token_service.py` | P7 — Tests |
| `tests/test_infrastructure/test_webhooks.py` | P7 — Tests |
| `tests/test_integration/test_api_endpoints.py` | P7 — Tests |
| `tests/test_integration/test_circuit_breaker_integration.py` | P7 — Tests |
| `tests/test_adapters/__init__.py` | _(vide — ignorable)_ |
| `tests/test_domain/__init__.py` | _(vide — ignorable)_ |
| `tests/test_infrastructure/__init__.py` | _(vide — ignorable)_ |

---

## Zones Python (code source)

### Zone P1 — Contrat public
**Fichiers :** `src/__init__.py` · `src/infrastructure/__init__.py` · `src/api/schemas.py`

**Question clé :** Tout ce qui est dans `__all__` est-il vraiment importé ailleurs ?

**Résultat :**
- `src/__init__.py` : façade complète jamais consommée — tous les imports se font directement vers les modules (`from src.config import ...`, pas `from src import ...`)
- `src/__init__.py` l.4 : `stream_response`, `transform_response` exportés mais jamais utilisés (logique dupliquée dans `routes.py`)
- `src/__init__.py` l.17 : `handle_options_request`, `set_response_headers` exportés mais jamais utilisés applicativement
- `src/infrastructure/__init__.py` l.8-9 : `upload_image_to_1min`, `create_1min_conversation` exportés mais jamais importés via ce module
- `src/api/schemas.py` : classes Pydantic (`MessageContent`, `ChatCompletionChoice`, etc.) non importées en code — intentionnel pour la doc OpenAPI

---

### Zone P2 — Config & Bootstrap
**Fichiers :** `src/config.py` · `src/api/app.py` · `src/api/__init__.py` · `main.py`

**Question clé :** Variables lues mais jamais consommées ? Middleware sans effet ?

**Résultat :**
- `src/config.py` l.74-76 : `RATELIMIT_STORAGE_URL` définie, jamais utilisée (SlowAPI utilise le backend en mémoire par défaut)
- `src/config.py` l.78 : `RATELIMIT_MODELS_LIST` définie, jamais utilisée (pas de limite par modèle implémentée)
- `src/config.py` l.89 : `LOG_FILE` définie, ignorée — `app.py` l.97 hardcode `"logs/api.log"`
- `SECRET_KEY` supprimée — commit `4590c1c`

---

### Zone P3 — Domaine (logique métier pure)
**Fichiers :** `src/domain/` (6 fichiers)

**Question clé :** Classes ou méthodes définies mais jamais appelées en dehors du domaine ?

**Résultat :**
- `src/domain/image_mapper.py` l.9 : `format_image_generation_response()` jamais appelée nulle part
- `src/domain/conversation_service.py` l.11 : paramètre `messages` accepté mais jamais utilisé dans le corps
- `src/domain/services/chat_service.py` l.110 : paramètre `params` dans `_resolve_session_id()` jamais utilisé
- `src/domain/conversation_service.py` et `model_provider.py` : exportées dans `__init__.py` mais jamais appelées en code métier (uniquement façade)

---

### Zone P4 — Infrastructure services externes
**Fichiers :** `src/infrastructure/one_min_client.py` + 9 autres

**Question clé :** Fonctions dupliquées avec `routes.py` ? Adapters jamais instanciés par le container ?

**Résultat :**
- `src/infrastructure/one_min_client.py` l.45 : `class CircuitBreaker` — doublon exact avec `src/infrastructure/circuit_breaker.py` (le vrai CB utilisé)
- `src/infrastructure/one_min_client.py` l.22 : `get_retry_session()` + variable `_session` globale — jamais utilisées en dehors du fichier
- `src/infrastructure/one_min_client.py` l.89 : `_get_safe_payload()` jamais appelée
- `src/infrastructure/api_key_validator.py` l.87 : `validate_format_only()` jamais appelée
- `src/infrastructure/network_service.py` l.62 : `create_json_response()` jamais appelée
- **CRITIQUE** : `src/adapters/openai_adapter.py` l.19-169 : `transform_response()` et `stream_response()` entièrement dupliquées dans `routes.py` (`_transform_response` l.580, `_handle_streaming` l.456) — l'adapter n'est jamais appelé

---

### Zone P5 — Transversal (métriques, logs, circuit breaker)
**Fichiers :** `src/infrastructure/metrics.py` (374 l.) · `webhooks.py` (403 l.) + 4 autres

**Question clé :** Métriques enregistrées mais jamais exposées ? Webhooks ou handlers morts ?

**Résultat :**
- `src/infrastructure/metrics.py` l.258-303 : 6 métriques/compteurs définis (`REQUEST_COUNT`, `REQUEST_DURATION`, `ACTIVE_REQUESTS`, `MODEL_REQUESTS`, `CACHE_HITS`, `CACHE_MISSES`) — jamais incrémentés
- `src/infrastructure/metrics.py` l.306-369 : 5 fonctions d'enveloppe (`track_request`, `track_model_request`, `track_cache_hit`, `track_cache_miss`, `timed`) jamais appelées
- `src/infrastructure/webhooks.py` l.395 : `trigger_event()` jamais appelée depuis `routes.py` ou `app.py`
- `src/infrastructure/webhooks.py` l.192-235 : méthodes `enable()`, `disable()`, `trigger()` jamais invoquées
- `src/infrastructure/rate_limiter.py` l.126 : `set_custom_limit()` jamais appelée
- `src/infrastructure/rate_limiter.py` l.317 : `cleanup_expired()` jamais appelée
- `src/infrastructure/logging_config.py` l.206 : classe `RequestLogger` jamais instanciée
- `src/infrastructure/health_service.py` l.213 : bloc `if APP_ENV == "production": pass` — code mort

---

### Zone P6 — Adapters & Glue code
**Fichiers :** `src/api/routes.py` · `src/adapters/openai_adapter.py` · `src/application/use_cases.py` · `src/container.py` · `printedcolors.py`

**Question clé :** Adapters bypassés directement par `routes.py` ? `printedcolors.py` encore utilisé ?

**Résultat :**
- `printedcolors.py` : jamais importé dans `src/` ni `main.py` — fichier mort à supprimer
- `src/adapters/openai_adapter.py` l.19 : `transform_response()` jamais appelée — `routes.py` redéfinit `_transform_response()` l.580
- `src/adapters/openai_adapter.py` l.93 : `stream_response()` jamais appelée — `routes.py` implémente le streaming inline
- `src/container.py` l.47 : propriété `chat_service` exposée mais jamais utilisée directement

---

### Zone P7 — Tests
**Fichiers :** `tests/conftest.py` · `tests/conftest_fastapi.py` · 23 fichiers de tests

**Question clé :** Fixtures mortes ? Double conftest ? Asserts triviaux ?

**Résultat :**
- `tests/conftest_fastapi.py` : **doublon à supprimer** — quasi-identique à `conftest.py`, jamais explicitement importé, `conftest.py` est plus complet
- `tests/conftest.py` l.268 : fixture `mock_1min_error_response` jamais utilisée dans aucun test
- `tests/conftest.py` l.307 : fixture `mock_routes_requests_post` jamais utilisée dans aucun test
- `tests/test_adapters/test_openai_adapter.py` l.9 : `Mock` importé, jamais utilisé (seulement `MagicMock`)
- `tests/test_integration/test_api_endpoints.py` l.85, 93, 142 : assertions `in [200, 400, 500, 503, 504]` sans mock — trop larges, pas de vérification réelle
- `tests/test_integration/test_circuit_breaker_integration.py` l.72, 114 : assertions conditionnelles `if mock_post.called` affaiblissent la vérification

---

## Zones Infrastructure & CI/CD

### Zone I1 — Docker
**Fichiers :** `Dockerfile` · `docker-compose.yml` · `docker-compose.monitoring.yml` · `.dockerignore`

**Question clé :** Services compose inutilisés ? Variables redondantes ? Dockerfile redondant ?

**Résultat :**
- `Dockerfile` l.5-6 : `PYTHONDONTWRITEBYTECODE` et `PYTHONUNBUFFERED` définis dans le stage builder — inutiles, redéfinis identiquement l.33-34 dans le stage runtime
- `docker-compose.yml` l.127 : `SUBSET_OF_ONE_MIN_PERMITTED_MODELS` avec valeurs par défaut hardcodées (`mistral-nemo,gpt-4o-mini,deepseek-chat`) — incohérent avec `config.py` qui a `""` comme défaut
- `docker-compose.yml` l.131-132 : `MEMCACHED_HOST` et `MEMCACHED_PORT` — mêmes valeurs que les defaults de `config.py`, redondant
- `docker-compose.yml` l.186 : volume `memcached-data` commenté — memcached stateless, données perdues au redémarrage, décision à documenter
- `.dockerignore` : `plans/` et `monitoring/` absents — devraient être exclus du contexte de build

---

### Zone I2 — GitHub Actions CI
**Fichiers :** `ci.yml` (396 l.) · `ci-build.yml` (279 l.) · `ci-security.yml` (205 l.)

**Question clé :** Steps dupliqués ? Variables inutilisées ? Artefacts orphelins ?

**Résultat :**
- `ci-security.yml` l.39 : `RUFF_VERSION: "0.8.0"` défini au niveau workflow, jamais consommé dans ce fichier (utilisé dans `ci.yml` seulement)
- `ci-security.yml` l.154 : artefact `dependency-scan-results` uploadé mais jamais consommé par un autre job
- `ci-security.yml` l.203 : artefact `scorecard-results` uploadé mais jamais consommé par un autre job
- Duplication `setup-python` + `cache:pip` entre `ci.yml` et `ci-security.yml` — architecture intentionnelle mais non factorisée

---

### Zone I3 — GitHub Actions CD
**Fichiers :** `cd-production.yml` (514 l.) · `cd-staging.yml` (255 l.) · `dependabot-auto-merge.yml` (243 l.)

**Question clé :** Logique dupliquée staging/prod ? Steps obsolètes ? Secrets manquants ?

**Résultat :**
- `cd-production.yml` l.51-62 / `cd-staging.yml` l.111-119 : bloc Docker login GHCR copié-collé — candidat à une composite action
- `cd-production.yml` l.148-165 / `cd-staging.yml` l.182-219 : blocs health check dupliqués entre staging et prod
- `dependabot-auto-merge.yml` l.207-229 : job `notify` sans effet réel (logs seulement, pas de webhook/mail)
- `dependabot-auto-merge.yml` l.212 : condition `if: always() && github.actor == 'dependabot[bot]'` — redondante avec le filtre du job parent
- **Secrets à vérifier** dans `cd-production.yml` : `PRODUCTION_SSH_HOST`, `PRODUCTION_SSH_USER`, `PRODUCTION_SSH_KEY`, `PRODUCTION_SSH_PORT` — doivent exister dans Settings → Secrets

---

### Zone I4 — Release & Deploy
**Fichiers :** `deploy.sh` (234 l.) · `.releaserc.json` · `commitlint.config.js` (178 l.) · `Makefile`

**Question clé :** Variables mortes ? Targets inutilisés ? Conflits commitlint/release ?

**Résultat :**
- `Makefile` : `test-cov`, `check`, `format`, `security`, `build`, `monitoring-up/down` — jamais appelés depuis CI (le CI redéfinit les commandes directement sans passer par `make`)
- `commitlint.config.js` l.39-52 : `scope-enum` restreint à 9 valeurs PascalCase, mais `.releaserc.json` l.9 accepte n'importe quel scope via `headerPattern` — incohérence potentielle
- `deploy.sh` : aucune variable ni fonction morte — tout est utilisé ✅

---

### Zone I5 — Config projet & qualité
**Fichiers :** `pyproject.toml` · `requirements*.txt` · `.pre-commit-config.yaml` · `.env.example`

**Question clé :** Dépendances inutilisées ? Hooks doublons ? Config d'outil mort ?

**Résultat :**
- `requirements.txt` l.29-30 : `limits[memcached]` et `pymemcache` jamais importés dans `src/`
- `requirements.txt` l.32 : `coloredlogs` jamais importé dans `src/` — logging utilise le module standard
- `requirements-dev.txt` l.9 : `filelock` jamais utilisé dans `tests/`
- `requirements-dev.txt` : `pytest-timeout`, `pytest-benchmark`, `pytest-randomly` absents mais installés manuellement dans `ci.yml` l.216 — incohérence local vs CI
- `pyproject.toml` l.32-50 : sections `[tool.black]` et `[tool.isort]` — outils remplacés par Ruff, configuration morte
- `pyproject.toml` l.129-139 : section `[tool.bandit]` — remplacé par Ruff rules `S`, configuration morte
- `pyproject.toml` l.142-155 : section `[tool.mypy]` — mypy absent de `requirements*.txt`, installé ad-hoc dans CI
- `.env.example` : 9 variables obsolètes (`ONE_MIN_API_URL`, `APP_NAME`, `DOCKER_USER`, `DOCKER_TOKEN`, `LOG_FORMAT`, `SECRET_KEY`, `CORS_ALLOW_CREDENTIALS`, `DOCKER_IMAGE_NAME`, `DOCKER_BUILDKIT`)
- `.pre-commit-config.yaml` + `ci.yml` : `ruff check` et `ruff format` dupliqués exactement

---

### Zone I6 — Documentation
**Fichiers :** `README.md` · `docs/` (10 fichiers) · `monitoring/prometheus.yml`

**Question clé :** Variables supprimées encore documentées ? Fonctionnalités inexistantes documentées ?

**Résultat :**
- `docs/ENV-DOCKER-GUIDE.md` l.44 / `docs/AUDIT.md` l.64,132,211 / `.env.example` l.88 : `SECRET_KEY` encore documentée — variable supprimée en `4590c1c`
- `docs/API_PARAMETERS.md` l.138-149 : section "Image Generation" documentée avec paramètres (`content_type: IMAGE_GENERATOR`, `n`, `size`, `aspect_ratio`) — **fonctionnalité inexistante** dans `routes.py` et `schemas.py`
- `docs/API_PARAMETERS.md` : endpoints `/webhooks/*` (6 routes dans `routes.py` l.216-263) non documentés
- `docs/ENV-DOCKER-GUIDE.md` l.52 vs `docs/CI-CD-DOCUMENTATION.md` l.59 : `DOCKER_USER` vs `DOCKER_USERNAME` — noms incohérents entre docs
- `docs/index.md` l.134 : `Last updated: 2024` — obsolète
- `monitoring/prometheus.yml` scrape `/metrics` : endpoint existant dans `routes.py` l.144 ✅

---

## Prompt type pour chaque zone

```
Audite uniquement ces fichiers : [liste de la zone].
Cherche :
- code / steps / variables définis mais jamais utilisés
- doublons avec d'autres fichiers du projet
- références à des variables/secrets/endpoints supprimés
- configuration pour des outils non installés ou non appelés
Ne charge pas d'autres fichiers. Liste chaque problème avec le fichier et la ligne.
```

---

## Historique des audits

| Date | Zone | Résumé | Commit |
|------|------|--------|--------|
| 2026-04-16 | P2 | Suppression `SECRET_KEY` inutilisée | `4590c1c` |
| 2026-04-16 | I5/I6 | `SECRET_KEY` retirée de `ci.yml` et `deploy.sh` | `4590c1c` |
| 2026-04-16 | Toutes | Audit complet 13 zones — résultats consolidés | _(ce commit)_ |
