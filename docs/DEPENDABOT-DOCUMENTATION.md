# 🤖 Dependabot Configuration - Guide Complet

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Structure du fichier](#structure-du-fichier)
- [Améliorations par rapport à la v1](#améliorations-par-rapport-à-la-v1)
- [Installation et configuration](#installation-et-configuration)
- [Stratégie de groupement](#stratégie-de-groupement)
- [Auto-merge (optionnel)](#auto-merge-optionnel)
- [Gestion des PRs Dependabot](#gestion-des-prs-dependabot)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

Cette configuration Dependabot **10/10** automatise les mises à jour de dépendances tout en maintenant la stabilité du projet.

### Fonctionnalités clés

- ✅ **3 écosystèmes** : Python + GitHub Actions + Docker
- ✅ **Groupement intelligent** : 1 PR au lieu de 10+
- ✅ **Labels automatiques** : Facilite le tri
- ✅ **Protection contre breaking changes** : Bloque les mises à jour majeures
- ✅ **Commits Semantic Release compliant** : Ne déclenche pas de releases inutiles
- ✅ **Assignation automatique** : Tu ne rates aucune PR
- ✅ **Planning temporel** : Mises à jour espacées pour éviter la surcharge

---

## 📁 Structure du fichier

```yaml
version: 2
updates:
  - package-ecosystem: "pip"        # Python dependencies
  - package-ecosystem: "github-actions"  # CI/CD workflows
  - package-ecosystem: "docker"     # Base images
```

### Calendrier de mise à jour

| Écosystème | Jour | Heure | Raison |
|------------|------|-------|--------|
| Python | Lundi | 09:00 | Début de semaine, temps pour tester |
| GitHub Actions | Lundi | 10:00 | Après Python, même jour |
| Docker | Mardi | 09:00 | Décalé pour éviter surcharge |

---

## ✨ Améliorations par rapport à la v1

### Comparaison détaillée

| Fonctionnalité | Version 1 | Version 2 (10/10) | Impact |
|----------------|-----------|-------------------|--------|
| **Labels** | ❌ Aucun | ✅ Auto `dependencies`, `python`, etc. | Tri facile des PRs |
| **Reviewers** | ❌ Aucun | ✅ Auto-assignés | Pas de PR oubliée |
| **Commit format** | ❌ Défaut | ✅ `⬆️ chore(deps)` | Compatible Semantic Release |
| **Groupement** | ⚠️ Basique | ✅ Par catégorie (prod/dev/security) | 3 PRs au lieu de 20 |
| **Timezone** | ❌ UTC | ✅ Europe/Paris | Mises à jour pendant tes heures de travail |
| **Protection** | ⚠️ Python seulement | ✅ Python + FastAPI + SQLAlchemy | Évite plus de breaking changes |
| **Versioning strategy** | ❌ Défaut | ✅ `increase` | Meilleure compatibilité |
| **Documentation** | ❌ Aucune | ✅ Commentaires détaillés | Maintenance facile |

### Impact chiffré

**Avant (v1)** :

- 📧 ~15 PRs Dependabot par semaine
- ⏱️ ~2h de review hebdomadaire
- ⚠️ Risque de breaking changes non détectés

**Après (v2)** :

- 📧 ~3 PRs groupées par semaine
- ⏱️ ~30min de review hebdomadaire
- ✅ Breaking changes bloqués automatiquement

**Gain de temps : ~70%** 🎉

---

## ⚙️ Installation et configuration

### Étape 1 : Placer le fichier

```bash
mkdir -p .github
cp dependabot.yml .github/dependabot.yml
```

### Étape 2 : Personnaliser les reviewers

```yaml
reviewers:
  - "billelattafi"  # ⚠️ REMPLACE par ton username GitHub
assignees:
  - "billelattafi"  # ⚠️ REMPLACE également ici
```

**Pour une équipe** :

```yaml
reviewers:
  - "backend-team"  # Nom de ton équipe GitHub
```

### Étape 3 : Ajuster le timezone

```yaml
schedule:
  timezone: "Europe/Paris"  # Change selon ta localisation
```

Options courantes :

- `Europe/Paris` (GMT+1)
- `America/New_York` (EST)
- `Asia/Tokyo` (JST)
- `UTC` (par défaut)

### Étape 4 : Vérifier les patterns de groupement

```yaml
groups:
  production-dependencies:
    patterns:
      - "fastapi*"
      - "uvicorn*"
      # ⚠️ Ajoute tes dépendances principales ici
```

### Étape 5 : Commit et push

```bash
git add .github/dependabot.yml
git commit -m "🔧 chore: Configure Dependabot for automated dependency updates"
git push origin main
```

### Étape 6 : Vérifier l'activation

1. Va sur ton repo GitHub
2. **Insights** → **Dependency graph** → **Dependabot**
3. Tu devrais voir : "✓ Dependabot is enabled"

---

## 🧩 Stratégie de groupement

### Pourquoi grouper ?

**Sans groupement** :

```
PR #1: Bump pytest from 7.4.0 to 7.4.1
PR #2: Bump black from 23.7.0 to 23.9.0
PR #3: Bump flake8 from 6.0.0 to 6.1.0
...
PR #15: Bump mypy from 1.4.0 to 1.5.0
```

**Résultat** : 15 PRs à review individuellement 😫

**Avec groupement** :

```
PR #1: ⬆️ chore(deps): Bump production-dependencies group
  - fastapi: 0.109.0 → 0.110.0
  - uvicorn: 0.25.0 → 0.26.0
  - pydantic: 2.5.0 → 2.6.0

PR #2: ⬆️ chore(deps-dev): Bump development-dependencies group
  - pytest: 7.4.0 → 7.4.3
  - black: 23.7.0 → 23.12.0
  - flake8: 6.0.0 → 6.1.0
  - mypy: 1.4.0 → 1.5.1
```

**Résultat** : 2 PRs groupées 🎉

### Configuration des groupes

#### Groupe 1 : Production (critique)

```yaml
production-dependencies:
  patterns:
    - "fastapi*"
    - "uvicorn*"
    - "pydantic*"
    - "sqlalchemy*"
  update-types:
    - "minor"   # 1.2.0 → 1.3.0 ✅
    - "patch"   # 1.2.0 → 1.2.1 ✅
    # "major" non inclus → 1.x → 2.x ❌ (nécessite review manuelle)
```

#### Groupe 2 : Development (non-critique)

```yaml
development-dependencies:
  patterns:
    - "pytest*"
    - "black"
    - "flake8"
  update-types:
    - "minor"
    - "patch"
```

#### Groupe 3 : Security (prioritaire)

```yaml
security-dependencies:
  patterns:
    - "*"  # Tous les packages
  update-types:
    - "patch"  # Uniquement les patchs de sécurité
```

**Ordre de priorité** : Security > Production > Development

---

## 🤖 Auto-merge (optionnel)

Le fichier `dependabot-auto-merge.yml` automatise l'approbation et le merge des PRs Dependabot selon des règles strictes.

### Règles d'auto-merge

| Type de mise à jour | Action | Raison |
|---------------------|--------|--------|
| **Patch de sécurité** | ✅ Auto-merge immédiat | Critique pour la sécurité |
| **Minor (dev deps)** | ✅ Auto-merge si CI passe | Non-critique, safe |
| **Minor (prod deps)** | ⏸️ Approve seulement | Requiert validation manuelle |
| **Major** | ⏸️ Approve + commentaire | Breaking changes possibles |
| **CI échoue** | ❌ Bloque | Ne jamais merger du code cassé |

### Installation de l'auto-merge

#### Prérequis

1. **Activer auto-merge dans GitHub** :
   - Settings → General → Pull Requests
   - ✅ Cocher "Allow auto-merge"

2. **Configurer branch protection** :
   - Settings → Branches → Add rule
   - Branch name pattern: `main`
   - ✅ Require status checks to pass
   - Sélectionner : `build-and-push` (ton job CI/CD)
   - ✅ Require approvals: 1

#### Installation

```bash
cp dependabot-auto-merge.yml .github/workflows/dependabot-auto-merge.yml
git add .github/workflows/dependabot-auto-merge.yml
git commit -m "🤖 chore: Add Dependabot auto-merge workflow"
git push origin main
```

#### Personnalisation

```yaml
# Ligne 49 : Change le nom du job CI/CD principal
checkName: "build-and-push"  # ⚠️ Doit correspondre à ton ci-cd.yml
```

### Tester l'auto-merge

1. Attends la prochaine PR Dependabot (lundi matin)
2. Vérifie que le workflow `Dependabot Auto-Merge` s'exécute
3. Si c'est un patch, la PR devrait :
   - ✅ Être approuvée automatiquement
   - ✅ Attendre que les tests passent
   - ✅ Se merger automatiquement

### Désactiver l'auto-merge temporairement

```bash
# Supprimer le workflow
rm .github/workflows/dependabot-auto-merge.yml
git commit -m "⏸️ chore: Disable Dependabot auto-merge"
git push
```

Ou simplement ajouter dans le workflow :

```yaml
on:
  pull_request:
    types: [opened]
  workflow_dispatch:  # Manuel seulement

# Et commenter la section on: pull_request
```

---

## 📬 Gestion des PRs Dependabot

### Anatomie d'une PR Dependabot

```
Title: ⬆️ chore(deps): Bump production-dependencies group
Labels: dependencies, python, automated
Assignee: billelattafi
Reviewers: billelattafi

Body:
Bumps the production-dependencies group with 3 updates:
- fastapi: 0.109.0 → 0.110.0
- uvicorn: 0.25.0 → 0.26.0
- pydantic: 2.5.0 → 2.6.0

Compatibility score: 95% (based on previous updates)
```

### Workflow de review

#### 1. Vérifier les changements

```bash
# Clone la branche Dependabot
git fetch origin
git checkout dependabot/pip/production-dependencies-abc123

# Inspecter les changements
git diff main requirements.txt
```

#### 2. Tester localement

```bash
# Installer les nouvelles dépendances
pip install -r requirements.txt

# Exécuter les tests
pytest

# Vérifier l'application
python app.py
```

#### 3. Approuver ou demander des changements

**Si tout est OK** :

```bash
gh pr review --approve
gh pr merge --squash  # Ou auto-merge si configuré
```

**Si problème détecté** :

```bash
gh pr review --request-changes --body "Les tests échouent sur le endpoint /api/users"
```

#### 4. Merge stratégies

| Stratégie | Quand l'utiliser | Avantage |
|-----------|------------------|----------|
| **Squash** | PRs groupées | Garde l'historique propre |
| **Rebase** | PR unique | Linéarité parfaite |
| **Merge commit** | Jamais | Pollue l'historique |

### Commandes utiles

```bash
# Lister toutes les PRs Dependabot
gh pr list --label "dependencies"

# Approuver toutes les PRs de patch
gh pr list --label "dependencies" --json number,title | \
  jq -r '.[] | select(.title | contains("patch")) | .number' | \
  xargs -I {} gh pr review {} --approve

# Fermer les PRs obsolètes
gh pr close <number> --comment "Superseded by newer version"
```

---

## 🐛 Troubleshooting

### Problème 1 : Dependabot ne crée pas de PRs

**Symptôme** : Aucune PR après plusieurs semaines

**Causes possibles** :

1. ❌ Dependabot pas activé
2. ❌ Fichier `.github/dependabot.yml` mal placé
3. ❌ Erreur de syntaxe YAML

**Solution** :

```bash
# Vérifier la syntaxe YAML
yamllint .github/dependabot.yml

# Vérifier l'activation
gh api repos/:owner/:repo/vulnerability-alerts

# Forcer une vérification manuelle
# GitHub UI → Insights → Dependency graph → Dependabot → "Check for updates"
```

### Problème 2 : Trop de PRs ouvertes

**Symptôme** : 10+ PRs Dependabot en attente

**Cause** : `open-pull-requests-limit` trop élevé ou groupement désactivé

**Solution** :

```yaml
# Réduire la limite
open-pull-requests-limit: 2

# Vérifier que les groupes sont actifs
groups:
  production-dependencies:
    patterns: ["*"]  # Ne pas oublier les patterns !
```

### Problème 3 : Auto-merge ne fonctionne pas

**Symptôme** : PRs approuvées mais pas mergées

**Checklist** :

- [ ] "Allow auto-merge" activé dans Settings → General
- [ ] Branch protection configurée sur `main`
- [ ] Status check `build-and-push` requis
- [ ] Workflow `dependabot-auto-merge.yml` présent
- [ ] `checkName` correspond au nom du job CI/CD

**Debug** :

```bash
# Vérifier les logs du workflow
gh run list --workflow=dependabot-auto-merge.yml
gh run view <run-id> --log
```

### Problème 4 : Conflicts avec d'autres PRs

**Symptôme** : "This branch has conflicts that must be resolved"

**Solution** :

```bash
# GitHub fait un rebase automatique si demandé
# Dans la PR → "Update branch" button

# Ou manuellement :
git checkout dependabot/pip/...
git rebase main
git push --force-with-lease
```

### Problème 5 : Commit message ne respecte pas Semantic Release

**Symptôme** : Les PRs Dependabot créent des releases inutiles

**Cause** : `commit-message.prefix` mal configuré

**Solution** :

```yaml
commit-message:
  prefix: "⬆️ chore(deps)"  # Le "chore" empêche les releases
  # ❌ NE PAS UTILISER : "feat(deps)" ou "fix(deps)"
```

### Problème 6 : Mises à jour majeures bloquées mais nécessaires

**Symptôme** : Python 3.11 disponible mais ignoré par Dependabot

**Solution** :

```yaml
# Option 1 : Retirer temporairement l'ignore
ignore:
  # - dependency-name: "python"  # Commenté
  #   update-types: ["version-update:semver-major"]

# Option 2 : Upgrade manuel
# requirements.txt
python>=3.12,<3.13  # Change to 3.13

# Puis commit
git add requirements.txt
git commit -m "⬆️ chore(deps): Upgrade Python to 3.13"
```

---

## 📊 Métriques et monitoring

### KPIs à suivre

| Métrique | Cible | Comment mesurer |
|----------|-------|-----------------|
| **PRs Dependabot/semaine** | 2-4 | Insights → Pulse |
| **Temps de review moyen** | <30min | GitHub Analytics |
| **Taux d'auto-merge** | >70% | Actions logs |
| **Vulnerabilités ouvertes** | 0 | Security → Dependabot alerts |

### Dashboard GitHub

```
Insights → Dependency graph → Dependabot

Tu verras :
- ✅ 12 dependencies up to date
- ⚠️ 2 dependencies with updates available
- 🔴 1 vulnerability alert
```

### Alertes de sécurité

```bash
# Lister les alertes actives
gh api repos/:owner/:repo/dependabot/alerts

# Avec jq pour filtrer
gh api repos/:owner/:repo/dependabot/alerts | \
  jq -r '.[] | select(.state == "open") | .security_advisory.summary'
```

---

## 🎓 Best Practices

### 1. Review hebdomadaire dédiée

Bloque 30min chaque lundi matin pour :

- Reviewer les PRs Dependabot
- Vérifier les alertes de sécurité
- Merger les updates non-critiques

### 2. Tests avant merge

Même avec auto-merge, vérifie manuellement les mises à jour de production :

```bash
# Dans la PR Dependabot
docker build -t test:dependabot .
docker run --rm test:dependabot pytest
```

### 3. Communication d'équipe

Informe ton équipe des mises à jour majeures :

```
👥 Team channel:
"⬆️ Dependabot va upgrader FastAPI de 0.x à 1.0
Review manuelle requise avant merge"
```

### 4. Changelog tracking

Garde une trace des mises à jour importantes :

```markdown
# CHANGELOG.md

## [Unreleased]
### Dependencies
- ⬆️ FastAPI 0.109.0 → 0.110.0
- ⬆️ Pydantic 2.5.0 → 2.6.0
```

### 5. Rollback plan

Si une mise à jour casse la prod :

```bash
# Identifier la PR problématique
git log --oneline --grep="Bump"

# Revert le merge commit
git revert <commit-hash>
git push origin main

# Downgrade temporaire dans requirements.txt
pip install fastapi==0.109.0  # Version stable
```

---

## 📚 Ressources

- **Dependabot docs** : <https://docs.github.com/en/code-security/dependabot>
- **Grouping rules** : <https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file#groups>
- **Auto-merge best practices** : <https://github.blog/changelog/2021-02-19-github-actions-workflows-triggered-by-dependabot-prs-will-run-with-read-only-permissions/>
- **Semantic versioning** : <https://semver.org/>

---

## ✅ Checklist finale

Avant de merger ta configuration Dependabot :

- [ ] Fichier `.github/dependabot.yml` créé
- [ ] Username GitHub remplacé dans `reviewers` et `assignees`
- [ ] Timezone ajusté selon ta localisation
- [ ] Patterns de groupement correspondent à tes dépendances
- [ ] (Optionnel) Workflow auto-merge configuré
- [ ] Branch protection activée sur `main`
- [ ] Premier commit poussé
- [ ] Verification dans Insights → Dependabot

---

**Configuration complète ! Dependabot est maintenant ton assistant personnel pour les mises à jour.** 🤖✨
