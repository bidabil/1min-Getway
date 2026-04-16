# Audit par Zones — 1min-Gateway

## Principe

Chaque zone = périmètre isolé = un seul prompt d'audit ciblé.
Moins de contexte chargé → meilleure détection de code mort, variables inutiles, doublons.

Outil recommandé : `vulture src/ --min-confidence 70`

---

## Zones

### Zone 1 — Contrat public
**Fichiers :**
- `src/__init__.py`
- `src/infrastructure/__init__.py`
- `src/api/schemas.py`

**Question clé :** Tout ce qui est exporté dans `__all__` est-il vraiment importé ailleurs ?

**Résultat :** _(à remplir)_

---

### Zone 2 — Config & Bootstrap
**Fichiers :**
- `src/config.py`
- `src/api/app.py`
- `main.py`

**Question clé :** Variables lues mais jamais consommées ? Middleware configuré mais sans effet ?

**Résultat :**
- `SECRET_KEY` supprimée — définie et validée mais jamais utilisée par l'application (supprimé commit `4590c1c`)

---

### Zone 3 — Domaine (logique métier pure)
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

### Zone 4 — Infrastructure (services externes)
**Fichiers :**
- `src/infrastructure/one_min_client.py`
- `src/infrastructure/asset_service.py`
- `src/infrastructure/api_key_validator.py`
- `src/infrastructure/token_service.py`
- `src/infrastructure/model_cache.py`
- `src/infrastructure/network_service.py`
- `src/infrastructure/error_service.py`

**Question clé :** Fonctions dupliquées avec `routes.py` ? Code jamais appelé par la couche API ?

**Résultat :** _(à remplir)_

---

### Zone 5 — Transversal (métriques, logs, circuit breaker)
**Fichiers :**
- `src/infrastructure/metrics.py` (374 lignes)
- `src/infrastructure/logging_config.py`
- `src/infrastructure/circuit_breaker.py`
- `src/infrastructure/rate_limiter.py`
- `src/infrastructure/health_service.py`
- `src/infrastructure/webhooks.py` (403 lignes)

**Question clé :** Métriques enregistrées mais jamais exposées ? Webhooks ou hooks morts ?

**Résultat :** _(à remplir)_

---

### Zone 6 — Adapters & Glue code
**Fichiers :**
- `src/adapters/openai_adapter.py`
- `src/application/use_cases.py`
- `src/container.py`

**Question clé :** Adapters bypassés directement par `routes.py` ? Use cases sans appelant ?

**Résultat :** _(à remplir)_

---

## Prompt type pour chaque zone

```
Audite uniquement ces fichiers : [liste de la zone].
Cherche :
- fonctions définies mais jamais appelées
- variables définies mais jamais lues
- imports non utilisés
- exports dans __all__ jamais importés ailleurs
- doublons avec routes.py
Ne touche pas aux autres fichiers.
```

---

## Historique des audits

| Date | Zone | Résumé | Commit |
|------|------|--------|--------|
| 2026-04-16 | Zone 2 | Suppression `SECRET_KEY` inutilisée | `4590c1c` |
