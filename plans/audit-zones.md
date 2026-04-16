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
**Fichiers :**
- `src/__init__.py`
- `src/infrastructure/__init__.py`
- `src/api/schemas.py`

**Question clé :** Tout ce qui est dans `__all__` est-il vraiment importé ailleurs ?

**Résultat :** _(à remplir)_

---

### Zone P2 — Config & Bootstrap
**Fichiers :**
- `src/config.py`
- `src/api/app.py`
- `src/api/__init__.py`
- `main.py`

**Question clé :** Variables lues mais jamais consommées ? Middleware sans effet ?

**Résultat :**
- `SECRET_KEY` supprimée — définie et validée mais jamais utilisée (commit `4590c1c`)

---

### Zone P3 — Domaine (logique métier pure)
**Fichiers :**
- `src/domain/models.py`
- `src/domain/ports.py`
- `src/domain/services/chat_service.py`
- `src/domain/conversation_service.py`
- `src/domain/model_provider.py`
- `src/domain/image_mapper.py`

**Question clé :** Classes ou méthodes définies mais jamais appelées en dehors du domaine ?

**Résultat :** _(à remplir)_

---

### Zone P4 — Infrastructure services externes
**Fichiers :**
- `src/infrastructure/one_min_client.py` (239 lignes)
- `src/infrastructure/asset_service.py`
- `src/infrastructure/api_key_validator.py`
- `src/infrastructure/token_service.py`
- `src/infrastructure/model_cache.py`
- `src/infrastructure/network_service.py`
- `src/infrastructure/error_service.py`
- `src/infrastructure/adapters/one_min_asset_adapter.py`
- `src/infrastructure/adapters/one_min_conversation_adapter.py`
- `src/infrastructure/adapters/token_adapter.py`

**Question clé :** Fonctions dupliquées avec `routes.py` ? Adapters jamais instanciés par le container ?

**Résultat :** _(à remplir)_

---

### Zone P5 — Transversal (métriques, logs, circuit breaker)
**Fichiers :**
- `src/infrastructure/metrics.py` (374 lignes)
- `src/infrastructure/logging_config.py`
- `src/infrastructure/circuit_breaker.py`
- `src/infrastructure/rate_limiter.py`
- `src/infrastructure/health_service.py`
- `src/infrastructure/webhooks.py` (403 lignes)

**Question clé :** Métriques enregistrées mais jamais exposées ? Webhooks ou handlers morts ?

**Résultat :** _(à remplir)_

---

### Zone P6 — Adapters & Glue code
**Fichiers :**
- `src/api/routes.py` (655 lignes)
- `src/adapters/openai_adapter.py`
- `src/application/use_cases.py`
- `src/container.py`
- `printedcolors.py`

**Question clé :** Adapters bypassés directement par `routes.py` ? `printedcolors.py` encore utilisé ?

**Résultat :** _(à remplir)_

---

### Zone P7 — Tests
**Fichiers :**
- `tests/conftest.py`
- `tests/conftest_fastapi.py`
- `tests/test_adapters/test_openai_adapter.py`
- `tests/test_application/test_use_cases.py`
- `tests/test_domain/test_chat_service.py`
- `tests/test_domain/test_conversation_service.py`
- `tests/test_domain/test_model_provider.py`
- `tests/test_domain/test_ports.py`
- `tests/test_error_service.py`
- `tests/test_infrastructure/test_adapters.py`
- `tests/test_infrastructure/test_api_key_validator.py`
- `tests/test_infrastructure/test_asset_service.py`
- `tests/test_infrastructure/test_circuit_breaker.py`
- `tests/test_infrastructure/test_health_service.py`
- `tests/test_infrastructure/test_logging_config.py`
- `tests/test_infrastructure/test_metrics.py`
- `tests/test_infrastructure/test_network_service.py`
- `tests/test_infrastructure/test_one_min_client.py`
- `tests/test_infrastructure/test_rate_limiter.py`
- `tests/test_infrastructure/test_token_service.py`
- `tests/test_infrastructure/test_webhooks.py`
- `tests/test_integration/test_api_endpoints.py`
- `tests/test_integration/test_circuit_breaker_integration.py`

**Question clé :** Fixtures dans conftest jamais utilisées ? Deux conftest pour une seule app ? Tests avec assert trivial ?

**Résultat :** _(à remplir)_

---

## Zones Infrastructure & CI/CD

### Zone I1 — Docker
**Fichiers :**
- `Dockerfile`
- `docker-compose.yml` (200 lignes)
- `docker-compose.monitoring.yml`
- `.dockerignore`

**Question clé :** Services compose jamais utilisés en prod ? Variables d'env redondantes avec `config.py` ? Étapes Dockerfile dupliquées ?

**Résultat :** _(à remplir)_

---

### Zone I2 — GitHub Actions CI
**Fichiers :**
- `.github/workflows/ci.yml` (396 lignes)
- `.github/workflows/ci-build.yml` (279 lignes)
- `.github/workflows/ci-security.yml` (205 lignes)

**Question clé :** Steps dupliqués entre workflows ? Jobs dont le résultat n'est jamais utilisé ? Variables d'env définies mais non consommées ?

**Résultat :** _(à remplir)_

---

### Zone I3 — GitHub Actions CD
**Fichiers :**
- `.github/workflows/cd-production.yml` (514 lignes — le plus gros)
- `.github/workflows/cd-staging.yml` (255 lignes)
- `.github/workflows/dependabot-auto-merge.yml` (243 lignes)
- `.github/dependabot.yml`

**Question clé :** Logique dupliquée entre staging et prod ? Steps dependabot obsolètes ? Secrets référencés mais absents de GitHub ?

**Résultat :** _(à remplir)_

---

### Zone I4 — Release & Deploy
**Fichiers :**
- `deploy.sh` (234 lignes)
- `.releaserc.json`
- `commitlint.config.js` (178 lignes)
- `Makefile`

**Question clé :** Targets Makefile sans appelant ? Variables `deploy.sh` jamais réutilisées ? Rules commitlint en conflit avec `.releaserc.json` ?

**Résultat :** _(à remplir)_

---

### Zone I5 — Config projet & qualité
**Fichiers :**
- `pyproject.toml` (208 lignes)
- `requirements.txt`
- `requirements-dev.txt`
- `.pre-commit-config.yaml`
- `.editorconfig`
- `.env.example`

**Question clé :** Dépendances jamais importées dans `src/` ? Hooks pre-commit qui doublonnent le CI ? Config d'outil non installé dans `pyproject.toml` ?

**Résultat :** _(à remplir)_

---

### Zone I6 — Documentation
**Fichiers :**
- `README.md`
- `docs/AUDIT.md`
- `docs/CI-CD-CHEATSHEET.md`
- `docs/CI-CD-DOCUMENTATION.md`
- `docs/CONTRIBUTING.md`
- `docs/DEPENDABOT-DOCUMENTATION.md`
- `docs/ENV-DOCKER-GUIDE.md`
- `docs/INTEGRATION-GUIDE.md`
- `docs/API_PARAMETERS.md`
- `docs/index.md`
- `docs/FUNDING.yml`
- `monitoring/prometheus.yml`

**Question clé :** Docs décrivant des variables/endpoints supprimés ? Prometheus scrape des métriques que l'app n'expose plus ?

**Résultat :**
- `docs/ENV-DOCKER-GUIDE.md` et `docs/AUDIT.md` mentionnent encore `SECRET_KEY` supprimée

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
| 2026-04-16 | I5/I6 | `SECRET_KEY` retirée de `ci.yml` et `deploy.sh`, encore dans docs | `4590c1c` |
