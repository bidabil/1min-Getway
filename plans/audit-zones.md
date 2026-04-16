# Audit par Zones — 1min-Gateway

## Principe

Chaque zone = périmètre isolé = un seul prompt d'audit ciblé.
Moins de contexte chargé → meilleure détection de code mort, variables inutiles, doublons.

Outil recommandé pour le code Python : `vulture src/ --min-confidence 70`

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
- `tests/test_adapters/`
- `tests/test_application/`
- `tests/test_domain/`
- `tests/test_error_service.py`
- `tests/test_infrastructure/`
- `tests/test_integration/`

**Question clé :** Fixtures définies dans conftest jamais utilisées par un test ? Deux conftest pour une seule app ? Tests qui ne testent rien (assert trivial) ?

**Résultat :** _(à remplir)_

---

## Zones Infrastructure & CI/CD

### Zone I1 — Docker
**Fichiers :**
- `Dockerfile`
- `docker-compose.yml` (200 lignes)
- `docker-compose.monitoring.yml`
- `.dockerignore`

**Question clé :** Services définis dans compose jamais utilisés en prod ? Variables d'env dans compose redondantes avec `config.py` ? Étapes du Dockerfile dupliquées ou inutiles ?

**Résultat :** _(à remplir)_

---

### Zone I2 — GitHub Actions CI
**Fichiers :**
- `.github/workflows/ci.yml` (396 lignes)
- `.github/workflows/ci-build.yml` (279 lignes)
- `.github/workflows/ci-security.yml` (205 lignes)

**Question clé :** Steps dupliqués entre workflows ? Jobs qui tournent mais dont le résultat n'est jamais utilisé ? Variables d'env définies mais non consommées dans le job ?

**Résultat :** _(à remplir)_

---

### Zone I3 — GitHub Actions CD
**Fichiers :**
- `.github/workflows/cd-production.yml` (514 lignes — le plus gros)
- `.github/workflows/cd-staging.yml` (255 lignes)
- `.github/workflows/dependabot-auto-merge.yml` (243 lignes)

**Question clé :** Logique dupliquée entre staging et production ? Steps dans dependabot-auto-merge qui n'ont plus de sens ? Secrets référencés mais non configurés dans GitHub ?

**Résultat :** _(à remplir)_

---

### Zone I4 — Release & Deploy
**Fichiers :**
- `deploy.sh` (234 lignes)
- `.releaserc.json`
- `commitlint.config.js` (178 lignes)
- `Makefile`

**Question clé :** Targets Makefile sans appelant ? Variables dans `deploy.sh` jamais réutilisées ? Rules commitlint en conflit avec `.releaserc.json` ?

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
- `.env` _(ne pas committer)_

**Question clé :** Dépendances dans `requirements.txt` jamais importées dans `src/` ? Hooks pre-commit qui font doublon avec CI ? Config tool dans `pyproject.toml` pour un outil non installé ?

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

**Question clé :** Docs qui décrivent des variables/endpoints supprimés ? `SECRET_KEY` encore mentionnée dans les guides ? Prometheus scrape des métriques que l'app n'expose plus ?

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
