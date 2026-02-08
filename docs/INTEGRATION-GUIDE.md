# 🚀 Guide d'Intégration Complet - 1min-Gateway

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Installation pas-à-pas](#installation-pas-à-pas)
- [Structure des fichiers](#structure-des-fichiers)
- [Configuration GitHub](#configuration-github)
- [Premier commit et release](#premier-commit-et-release)
- [Workflow quotidien](#workflow-quotidien)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

Tu disposes maintenant d'un écosystème DevOps complet avec :

```
Local Development          GitHub Actions              Production
─────────────────         ────────────────            ──────────────
Pre-commit hooks    →     CI/CD Pipeline       →      Docker Registry
  │                         │                            │
  ├─ Commitlint             ├─ Tests                     ├─ Docker Hub
  ├─ Black/Flake8           ├─ Security Scan             └─ GHCR
  ├─ isort                  ├─ Semantic Release
  └─ Bandit                 └─ Multi-arch Build    →    Watchtower
                                                          Auto-deploy
```

---

## 📦 Installation pas-à-pas

### Étape 1 : Backup de ton code actuel

```bash
# Sauvegarde ton travail actuel
git stash
# OU
git commit -m "🚧 WIP: Before DevOps setup"
```

### Étape 2 : Placement des nouveaux fichiers

**Voici exactement où mettre chaque fichier :**

```bash
# Structure de ton projet
1min-gateway/
├── .github/
│   ├── workflows/
│   │   ├── ci-cd.yml                          # ✅ GARDER (déjà bon)
│   │   └── dependabot-auto-merge.yml          # ⚠️ REMPLACER par dependabot-auto-merge-fixed.yml
│   └── dependabot.yml                         # ✅ GARDER (déjà bon)
│
├── .pre-commit-config.yaml                    # 🔄 REMPLACER
├── .releaserc.json                            # 🔄 REMPLACER
├── commitlint.config.js                       # ➕ NOUVEAU FICHIER
├── config.json                                # ❌ SUPPRIMER ou renommer en .czrc
├── Makefile                                   # 🔄 REMPLACER
│
├── docker-compose.yml                         # ✅ GARDER
├── Dockerfile                                 # ✅ GARDER
├── requirements.txt                           # ✅ GARDER
├── main.py                                    # ✅ GARDER
└── ... (reste de ton code)
```

### Étape 3 : Commandes d'installation

```bash
# 1. Retour à la racine de ton projet
cd /chemin/vers/1min-gateway

# 2. Supprimer config.json (inutile)
rm config.json

# 3. Remplacer .releaserc.json
cp /chemin/téléchargements/.releaserc.json .

# 4. Remplacer .pre-commit-config.yaml
cp /chemin/téléchargements/.pre-commit-config.yaml .

# 5. Ajouter commitlint.config.js (nouveau)
cp /chemin/téléchargements/commitlint.config.js .

# 6. Remplacer dependabot-auto-merge.yml
cp /chemin/téléchargements/dependabot-auto-merge-fixed.yml .github/workflows/dependabot-auto-merge.yml

# 7. Remplacer Makefile
cp /chemin/téléchargements/Makefile .

# 8. Installer les dépendances
make install
```

### Étape 4 : Créer les fichiers additionnels

**1. `.secrets.baseline` (pour detect-secrets)**

```bash
make setup-secrets
```

**2. `pyproject.toml` (pour Bandit config)**

```bash
cat > pyproject.toml << 'EOF'
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv", "logs"]
skips = ["B101", "B601"]

[tool.black]
line-length = 100
target-version = ['py312']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | venv
  | logs
  | __pycache__
)/
'''

[tool.isort]
profile = "black"
line_length = 100
EOF
```

**3. Vérifier que `requirements.txt` contient tout**

```bash
# Ajouter si manquant :
cat >> requirements.txt << 'EOF'

# Development tools
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
bandit>=1.7.5
pre-commit>=3.0.0
EOF
```

---

## ⚙️ Configuration GitHub

### 1. Secrets GitHub à configurer

Va dans **Settings → Secrets and variables → Actions** et ajoute :

| Secret | Valeur | Où le trouver |
|--------|--------|---------------|
| `DOCKER_USERNAME` | `billelattafi` | Ton username Docker Hub |
| `DOCKER_PASSWORD` | `dckr_pat_xxxxx` | [Créer un token](https://hub.docker.com/settings/security) |
| `CODECOV_TOKEN` | (optionnel) | [codecov.io](https://codecov.io) pour couverture de code |

### 2. Branch Protection

**Settings → Branches → Add rule**

```
Branch name pattern: main

☑️ Require a pull request before merging
   ☑️ Require approvals: 1
   ☑️ Dismiss stale reviews

☑️ Require status checks to pass before merging
   ☑️ Require branches to be up to date
   Sélectionner: "test" (obligatoire)

☑️ Do not allow bypassing the above settings

☑️ Allow auto-merge
```

### 3. Activer Dependabot

**Settings → Code security → Dependabot**

```
☑️ Dependabot alerts: Enabled
☑️ Dependabot security updates: Enabled
☑️ Dependabot version updates: Enabled (fichier dependabot.yml détecté automatiquement)
```

---

## 🎯 Premier commit et release

### Test 1 : Vérifier les hooks locaux

```bash
# Créer un fichier de test
echo "print('test')" > test_commit.py

# Essayer de commiter (devrait être formaté automatiquement)
git add test_commit.py
git commit -m "✨ feat(Core): Add test file"

# Si pre-commit échoue, corrige les erreurs et recommite
git add .
git commit -m "✨ feat(Core): Add test file"
```

### Test 2 : Premier push (sans release)

```bash
# Commit sans emoji de release
git commit -m "📝 docs: Update README"
git push origin main

# Résultat attendu :
# ✅ Tests passent
# ⏭️ Semantic Release : Aucune version créée (type "docs")
# ⏭️ Build & Push : Skippé (pas de release)
```

### Test 3 : Première vraie release

```bash
# Commit qui déclenche une release
git commit -m "✨ feat(Gateway): Add health endpoint"
git push origin main

# Résultat attendu :
# ✅ Tests passent
# 🎉 Semantic Release : v1.0.0 créée
# 🐳 Build & Push : Image taguée 1.0.0 + latest
# 🔒 Cosign : Images signées
# 📦 CHANGELOG.md généré
```

**Vérifier le résultat :**

1. Va sur **GitHub → Actions** → Voir le workflow
2. Va sur **GitHub → Releases** → v1.0.0 devrait être là
3. Va sur **Docker Hub** → Tags → `1.0.0` et `latest`
4. Va sur **Security → Code scanning** → Résultats Trivy

---

## 🔄 Workflow quotidien

### Développement de feature

```bash
# 1. Créer une branche
git checkout -b feat/nouvelle-feature

# 2. Coder
# ... édite tes fichiers ...

# 3. Tester localement
make test
make lint

# 4. Commiter (les hooks vérifient automatiquement)
make commit
# OU
git add .
git commit -m "✨ feat(Core): Ma nouvelle feature"

# 5. Push et créer une PR
git push origin feat/nouvelle-feature
# → Créer la PR sur GitHub

# 6. Attendre les checks CI/CD
# → Tests s'exécutent automatiquement
# → Build de validation (sans push)

# 7. Merger la PR
# → Semantic Release calcule la version
# → Image Docker buildée et poussée
# → Watchtower déploie automatiquement
```

### Gestion des PRs Dependabot

**Scénario 1 : Patch de sécurité**

```
Lundi 09:00 → PR créée : "⬆️ chore(deps): Bump fastapi 0.109.0 → 0.109.1"
Lundi 09:15 → Tests passent
Lundi 09:16 → Auto-merge automatique ✅
```

**Scénario 2 : Mise à jour mineure production**

```
Lundi 09:00 → PR créée : "⬆️ chore(deps): Bump pydantic 2.5.0 → 2.6.0"
Lundi 09:15 → Tests passent
Lundi 09:16 → Approuvée automatiquement, mais PAS mergée ⏸️
Action : Tu review et merge manuellement
```

**Scénario 3 : Mise à jour majeure**

```
Lundi 09:00 → PR créée : "⬆️ chore(deps): Bump fastapi 0.109.0 → 1.0.0"
Lundi 09:15 → Tests passent
Lundi 09:16 → Approuvée avec commentaire "⚠️ MAJOR UPDATE" ⏸️
Action :
  1. Lis les release notes de FastAPI 1.0.0
  2. Teste localement : git checkout dependabot/pip/...
  3. Merge si OK
```

### Créer une release manuelle

```bash
# Si tu veux forcer une release sans nouveau code
make release

# Ou directement
git commit --allow-empty -m "🚀 chore(release): Trigger new version"
git push origin main
```

---

## 🐛 Troubleshooting

### Problème 1 : Pre-commit hooks échouent

**Symptôme** :

```
[INFO] Initializing environment for ...
[ERROR] black failed with exit code 1
```

**Solution** :

```bash
# Installer les dépendances manquantes
make install

# Ou réinstaller les hooks
pre-commit clean
pre-commit install --install-hooks --hook-type commit-msg --hook-type pre-commit

# Tester manuellement
pre-commit run --all-files
```

### Problème 2 : Commitlint rejette mes commits

**Symptôme** :

```
⧗   input: ✨ Add feature
✖   subject may not be empty [subject-empty]
```

**Cause** : Le format n'est pas reconnu.

**Solution** : Utilise le bon format

```bash
# ❌ Mauvais
git commit -m "✨ Add feature"

# ✅ Bon
git commit -m "✨ feat(Core): Add feature"
#              ^    ^     ^    ^
#              │    │     │    └─ Description
#              │    │     └────── Scope (optionnel mais recommandé)
#              │    └──────────── Type (feat, fix, etc.)
#              └───────────────── Gitmoji
```

### Problème 3 : Semantic Release ne crée pas de version

**Symptôme** : Push sur main mais pas de release créée.

**Causes possibles** :

1. **Type de commit ignoré** : `docs`, `style`, `chore` ne créent pas de releases
2. **Pas de plugin installé** : Vérifier que `semantic-release-gitmoji` est dans CI/CD

**Solution** :

```yaml
# Dans .github/workflows/ci-cd.yml
- name: Semantic Release
  uses: cycjimmy/semantic-release-action@v4
  with:
    extra_plugins: |
      semantic-release-gitmoji
      @semantic-release/changelog
      @semantic-release/git
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Problème 4 : Dependabot auto-merge ne fonctionne pas

**Diagnostic** :

```bash
# Vérifier les logs du workflow
gh run list --workflow=dependabot-auto-merge.yml
gh run view <run-id> --log
```

**Checklist** :

- [ ] "Allow auto-merge" activé dans Settings → General
- [ ] Branch protection configurée (require status check "test")
- [ ] Workflow `dependabot-auto-merge.yml` présent
- [ ] `checkName: "test"` (pas "build-and-push")

### Problème 5 : Docker build échoue en CI/CD

**Symptôme** :

```
Error: buildx failed with: ERROR: failed to solve: process "/bin/sh -c pip install ..."
```

**Solution** :

```bash
# Tester le build localement
make docker-build

# Si ça marche localement, vérifier :
# 1. Secrets Docker configurés dans GitHub
# 2. Dockerfile utilise bien python:3.12-slim
# 3. requirements.txt accessible

# Forcer un rebuild sans cache
make docker-build-no-cache
```

### Problème 6 : Watchtower ne met pas à jour

**Symptôme** : Nouvelle image poussée mais container pas mis à jour.

**Diagnostic** :

```bash
# Vérifier les logs Watchtower
docker logs watchtower

# Vérifier le label sur le container
docker inspect 1min-gateway | grep watchtower
```

**Solution** :

```yaml
# Dans docker-compose.yml, vérifier :
1min-gateway:
  labels:
    - "com.centurylinklabs.watchtower.enable=true"  # ✅ Doit être présent
```

---

## 📊 Commandes utiles quotidiennes

```bash
# Développement
make dev              # Lancer l'app
make test             # Tests
make lint             # Vérifier le code
make format           # Formater le code
make commit           # Commit interactif

# Docker local
make docker-build     # Build l'image
make docker-run       # Run en standalone
make docker-logs      # Voir les logs

# Docker Compose
make up               # Tout lancer
make down             # Tout arrêter
make logs-gateway     # Logs du gateway
make restart          # Redémarrer

# CI/CD
make release          # Forcer une release
make ci-full          # Simuler CI en local

# Maintenance
make clean            # Nettoyer Python
make clean-docker     # Nettoyer Docker
make update           # Mettre à jour dépendances
```

---

## 🎓 Ressources additionnelles

### Documentation officielle

- **Semantic Release** : <https://semantic-release.gitbook.io/>
- **Gitmoji** : <https://gitmoji.dev/>
- **Commitlint** : <https://commitlint.js.org/>
- **Pre-commit** : <https://pre-commit.com/>
- **Dependabot** : <https://docs.github.com/en/code-security/dependabot>

### Cheatsheets créées pour toi

- `CI-CD-CHEATSHEET.md` → Commandes CI/CD
- `CI-CD-DOCUMENTATION.md` → Doc complète CI/CD
- `DEPENDABOT-DOCUMENTATION.md` → Doc complète Dependabot

---

## ✅ Checklist finale

Avant de commit le setup complet :

- [ ] Tous les fichiers placés aux bons endroits
- [ ] `make install` exécuté sans erreur
- [ ] Secrets GitHub configurés (DOCKER_USERNAME, DOCKER_PASSWORD)
- [ ] Branch protection activée
- [ ] Dependabot activé
- [ ] Test commit local réussi
- [ ] Première release testée

**Commandes de vérification finale** :

```bash
# 1. Vérifier l'installation
make version

# 2. Tester les hooks
make pre-commit

# 3. Tester les tests
make test

# 4. Vérifier Docker
make docker-build
```

---

**Setup terminé ! Ton projet est maintenant 100% production-ready.** 🎉

Pour toute question, consulte les documentations ou ouvre une issue sur GitHub !
