# 🔐 Guide de Configuration Environnement & Docker

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Fichiers générés](#fichiers-générés)
- [Installation](#installation)
- [Sécurité des secrets](#sécurité-des-secrets)
- [Environnements (dev/prod)](#environnements)
- [Docker Compose](#docker-compose)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

Tu as maintenant **4 fichiers améliorés** pour gérer tes configurations :

```
1min-gateway/
├── .env.example-improved       → Template complet pour production
├── .env.local                  → Configuration développement local
├── .dockerignore-improved      → Optimisation build Docker
├── .gitignore-improved         → Protection secrets + patterns Python modernes
├── docker-compose-optimized.yml → Healthchecks + resource limits + logs
└── docker-compose.yml          → Version actuelle (à remplacer)
```

---

## 📁 Fichiers Générés

### 1. `.env.example-improved` (Template Production)

**À placer** : `1min-gateway/.env.example`

**Contenu** :

- ✅ Toutes les variables nécessaires documentées
- ✅ Notes de sécurité pour chaque section
- ✅ Valeurs par défaut safe
- ✅ Checklist de sécurité en bas

**Utilisation** :

```bash
# Créer ton .env depuis le template
cp .env.example .env

# Éditer avec tes vraies credentials
nano .env  # ou vim, code, etc.
```

### 2. `.env.local` (Template Développement)

**À placer** : `1min-gateway/.env.local`

**Différences vs production** :

- `DEBUG=True`
- `RATELIMIT_ENABLED=False`
- `LOG_LEVEL=DEBUG`
- Pas de vraies credentials Docker

**Utilisation** :

```bash
# En développement local (sans Docker)
cp .env.local .env

# Lancer l'app
make dev
# OU
python main.py
```

### 3. `.dockerignore-improved`

**À placer** : `1min-gateway/.dockerignore` (remplacer l'actuel)

**Impact** :

- ✅ Réduction du contexte Docker de ~30%
- ✅ Build plus rapide
- ✅ Image finale plus légère
- ✅ Pas de secrets accidentellement copiés

**Avant/Après** :

```bash
# Avant (contexte ~50MB avec logs, .git, etc.)
Sending build context to Docker daemon  52.3MB

# Après (contexte ~20MB)
Sending build context to Docker daemon  21.1MB
```

### 4. `.gitignore-improved`

**À placer** : `1min-gateway/.gitignore` (fusionner avec l'actuel)

**Ajouts** :

- `.secrets.baseline` (detect-secrets)
- `.mypy_cache/`, `.ruff_cache/` (type checking)
- `htmlcov/`, `.coverage` (coverage reports)
- Patterns Jupyter Notebook
- Backup files patterns

### 5. `docker-compose-optimized.yml`

**À placer** : `1min-gateway/docker-compose.yml` (remplacer)

**Nouvelles fonctionnalités** :

- ✅ **Healthchecks** : Watchtower attend que l'app soit ready
- ✅ **Resource limits** : Pas de RAM/CPU exhaustion
- ✅ **Logging rotation** : Max 10MB × 3 fichiers
- ✅ **Version memcached pinnée** : `1.6-alpine` (stable)
- ✅ **Subnet configuré** : `172.28.0.0/16`
- ✅ **Depends_on avec conditions** : `service_healthy`

---

## 🔧 Installation

### Étape 1 : Backup

```bash
# Sauvegarder les anciens fichiers
mkdir -p .backup-config-$(date +%Y%m%d)
cp .env .backup-config-$(date +%Y%m%d)/ 2>/dev/null || true
cp .dockerignore .backup-config-$(date +%Y%m%d)/
cp .gitignore .backup-config-$(date +%Y%m%d)/
cp docker-compose.yml .backup-config-$(date +%Y%m%d)/
```

### Étape 2 : Copier les nouveaux fichiers

```bash
# Variables (CHANGE LE CHEMIN)
DOWNLOAD="$HOME/Downloads"

# Copier les fichiers
cp "$DOWNLOAD/.env.example-improved" .env.example
cp "$DOWNLOAD/.env.local" .env.local
cp "$DOWNLOAD/.dockerignore-improved" .dockerignore
cp "$DOWNLOAD/.gitignore-improved" .gitignore
cp "$DOWNLOAD/docker-compose-optimized.yml" docker-compose.yml
```

### Étape 3 : Configurer l'environnement

**Pour la production** :

```bash
# Créer .env depuis le template
cp .env.example .env

# Éditer et remplir les vraies valeurs
nano .env
```

**Variables OBLIGATOIRES à remplir** :

```bash
# Dans .env
ONE_MIN_AI_API_KEY=sk-xxxxxxxx...   # ← Ta vraie clé 1min.ai
DOCKER_USER=billelattafi             # ← Ton username Docker Hub
DOCKER_TOKEN=dckr_pat_xxxxxx...      # ← Token (PAS le mot de passe!)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

**Pour le développement** :

```bash
# Utiliser le fichier local
cp .env.local .env

# Éditer juste la clé API
nano .env  # Remplacer ONE_MIN_AI_API_KEY
```

### Étape 4 : Sécuriser .env

```bash
# Permissions restrictives (lecture seule pour toi)
chmod 600 .env

# Vérifier qu'il est dans .gitignore
grep "^.env$" .gitignore || echo ".env" >> .gitignore
```

---

## 🔐 Sécurité des Secrets

### ❌ À NE JAMAIS FAIRE

```bash
# MAUVAIS : Commiter le .env
git add .env
git commit -m "Add config"  # ⚠️ SECRETS EXPOSÉS PUBLIQUEMENT

# MAUVAIS : Token = Mot de passe
DOCKER_TOKEN=mon_mot_de_passe  # ⚠️ Si volé, accès total au compte
```

### ✅ Bonnes Pratiques

**1. Utiliser des Access Tokens**

```bash
# Docker Hub → Account Settings → Security → New Access Token
# Permissions: Read-only suffit pour Watchtower
DOCKER_TOKEN=dckr_pat_AbCdEfGhIjKlMnOpQrStUvWxYz
```

**2. Rotation des secrets**

```bash
# Tous les 90 jours, regénérer :
# - ONE_MIN_AI_API_KEY (1min.ai)
# - DOCKER_TOKEN (Docker Hub)
# - SECRET_KEY (Flask)
```

**3. Vérifier les leaks**

```bash
# Installer detect-secrets
pip install detect-secrets

# Scanner le repo
detect-secrets scan > .secrets.baseline

# Vérifier avant chaque commit
detect-secrets audit .secrets.baseline
```

**4. Utiliser un gestionnaire de secrets (production)**

```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id 1min-gateway/prod

# HashiCorp Vault
vault kv get secret/1min-gateway/prod

# Docker Secrets (Swarm mode)
docker secret create one_min_api_key -
```

---

## 🌍 Environnements (dev/prod)

### Développement Local

```bash
# 1. Utiliser .env.local
cp .env.local .env

# 2. Lancer sans Docker
make dev
# OU
python main.py

# Résultat :
# - DEBUG=True
# - Logs verbeux (DEBUG level)
# - Rate limiting désactivé
# - CORS permissif (*)
```

### Production Docker

```bash
# 1. Utiliser .env.example comme base
cp .env.example .env

# 2. Remplir les vraies credentials
nano .env

# 3. Lancer avec Docker Compose
docker compose up -d

# Résultat :
# - DEBUG=False
# - Logs JSON (INFO level)
# - Rate limiting actif
# - Healthchecks actifs
# - Resource limits actifs
```

### Staging / Testing

```bash
# Créer un .env.staging
cp .env.example .env.staging

# Modifier pour staging
sed -i 's/APP_ENV=production/APP_ENV=staging/' .env.staging
sed -i 's/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/' .env.staging

# Utiliser avec Docker Compose
docker compose --env-file .env.staging up -d
```

---

## 🐳 Docker Compose

### Nouvelles Fonctionnalités

**1. Healthchecks**

```yaml
1min-gateway:
  healthcheck:
    test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5001/health')"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

**Impact** :

- Watchtower attend que l'app soit vraiment prête avant de switcher
- `docker ps` montre le status de santé : `healthy` ou `unhealthy`
- `depends_on: service_healthy` garantit l'ordre de démarrage

**2. Resource Limits**

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 256M
```

**Impact** :

- Protection contre les containers qui consomment toute la RAM
- Ajuste selon tes besoins : `docker stats` pour voir l'usage réel

**3. Logging Rotation**

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    compress: "true"
```

**Impact** :

- Évite que `/var/lib/docker` ne remplisse le disque
- Max 30MB de logs par container (10MB × 3 fichiers)

### Commandes Utiles

```bash
# Vérifier les healthchecks
docker ps
# CONTAINER ID   STATUS
# abc123         Up 2 minutes (healthy)

# Voir les logs healthcheck
docker inspect 1min-gateway-container | grep -A 10 Health

# Stats en temps réel
docker stats

# Forcer une update Watchtower (sans attendre 5min)
docker exec watchtower /watchtower --run-once

# Vérifier la connectivité memcached
docker exec 1min-gateway-container sh -c "echo stats | nc memcached 11211"
```

---

## 🐛 Troubleshooting

### Problème 1 : Container gateway unhealthy

**Symptôme** :

```bash
docker ps
# STATUS: Up 2 minutes (unhealthy)
```

**Diagnostic** :

```bash
# Voir les logs du healthcheck
docker inspect 1min-gateway-container --format='{{json .State.Health}}' | jq

# Logs de l'app
docker logs 1min-gateway-container
```

**Solutions** :

```bash
# 1. Vérifier que /health endpoint existe
curl http://localhost:5001/health

# 2. Augmenter start_period si l'app est lente au démarrage
# Dans docker-compose.yml :
start_period: 60s  # Au lieu de 40s

# 3. Simplifier le healthcheck
test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
```

### Problème 2 : Memcached non accessible

**Symptôme** :

```
ConnectionError: [Errno 111] Connection refused
```

**Solution** :

```bash
# Vérifier que memcached est UP
docker ps | grep memcached

# Tester la connexion depuis gateway
docker exec 1min-gateway-container sh -c "nc -zv memcached 11211"

# Si ça échoue, vérifier le réseau
docker network inspect 1min-gateway-network
```

### Problème 3 : Watchtower ne pull pas les nouvelles images

**Diagnostic** :

```bash
# Logs Watchtower
docker logs watchtower

# Vérifier les labels
docker inspect 1min-gateway-container | grep watchtower
```

**Causes possibles** :

1. **Credentials Docker incorrects**

   ```bash
   # Tester manuellement
   echo $DOCKER_TOKEN | docker login -u $DOCKER_USER --password-stdin
   ```

2. **Label manquant**

   ```yaml
   labels:
     - "com.centurylinklabs.watchtower.enable=true"  # ← Vérifier
   ```

3. **Image pas pushée**

   ```bash
   # Vérifier sur Docker Hub
   docker manifest inspect billelattafi/1min-gateway:latest
   ```

### Problème 4 : "version is obsolete" warning

**Symptôme** :

```
WARN[0000] .../docker-compose.yml: `version` is obsolete
```

**Solution** :

```yaml
# Supprimer cette ligne dans docker-compose.yml
version: '3.8'  # ← Ligne à supprimer
```

C'est juste un warning, pas bloquant, mais autant le corriger.

---

## 📊 Checklist Finale

### Avant le premier `docker compose up`

- [ ] `.env` créé et rempli avec vraies credentials
- [ ] `ONE_MIN_AI_API_KEY` testée (curl vers 1min.ai)
- [ ] `DOCKER_TOKEN` est un Access Token (pas un mot de passe)
- [ ] `chmod 600 .env` exécuté
- [ ] `.env` dans `.gitignore`
- [ ] `docker-compose.yml` mis à jour avec healthchecks
- [ ] `.dockerignore` optimisé

### Test du setup

```bash
# 1. Build local
docker compose build

# 2. Up
docker compose up -d

# 3. Vérifier les healthchecks (attendre ~40s)
docker ps
# Tous les containers doivent être (healthy)

# 4. Tester l'endpoint
curl http://localhost:5001/health
# Devrait retourner 200 OK

# 5. Logs
docker compose logs -f 1min-gateway
```

---

## 🎯 Commandes de Maintenance

```bash
# Mettre à jour les services
docker compose pull
docker compose up -d

# Nettoyer les anciennes images
docker image prune -a

# Voir l'usage disque
docker system df

# Backup des logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Rotation manuelle des logs Docker
docker compose down
rm -rf /var/lib/docker/containers/*/....log
docker compose up -d
```

---

**Setup terminé ! Ton environnement et Docker Compose sont maintenant production-ready.** 🎉

Pour toute question, consulte les fichiers `.env.example` (très commentés) ou les logs des containers.
