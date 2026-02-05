# 🚀 CI/CD Quick Reference - Cheatsheet

## 📦 Déclencher une release

### Patch Release (1.2.3 → 1.2.4)

```bash
git commit -m "🐛 fix: Correction bug authentification"
git push origin main
```

### Minor Release (1.2.3 → 1.3.0)

```bash
git commit -m "✨ feat: Ajout export CSV"
git push origin main
```

### Major Release (1.2.3 → 2.0.0)

```bash
git commit -m "💥 BREAKING CHANGE: API v2 incompatible avec v1"
git push origin main
```

### Pas de release (documentation, style, etc.)

```bash
git commit -m "📝 docs: Update README"
git commit -m "🎨 style: Format code"
git commit -m "♻️ refactor: Simplify function"
# → Aucune version créée, pas de build Docker
```

---

## 🏷️ Gitmojis pour Semantic Release

| Gitmoji | Type | Impact | Exemple |
|---------|------|--------|---------|
| ✨ `:sparkles:` | `feat` | **Minor** | ✨ feat: Nouvelle API endpoint |
| 🐛 `:bug:` | `fix` | **Patch** | 🐛 fix: Résolution crash au démarrage |
| 💥 `:boom:` | Breaking | **Major** | 💥 BREAKING CHANGE: Suppression API v1 |
| 🔒 `:lock:` | `security` | **Patch** | 🔒 security: Patch CVE-2024-1234 |
| ⚡ `:zap:` | `perf` | **Patch** | ⚡ perf: Cache Redis pour /users |
| 📝 `:memo:` | `docs` | Aucun | 📝 docs: Ajout guide API |
| 🎨 `:art:` | `style` | Aucun | 🎨 style: Format avec black |
| ♻️ `:recycle:` | `refactor` | Aucun | ♻️ refactor: Extract auth logic |
| ✅ `:white_check_mark:` | `test` | Aucun | ✅ test: Add unit tests for parser |
| 🔧 `:wrench:` | `chore` | Aucun | 🔧 chore: Update dependencies |

---

## 🐳 Vérifier les images publiées

### Docker Hub

```bash
# Lister les tags
curl -s https://hub.docker.com/v2/repositories/billelattafi/1min-gateway/tags | jq -r '.results[].name'

# Pull une version spécifique
docker pull billelattafi/1min-gateway:1.2.3
docker pull billelattafi/1min-gateway:latest
```

### GitHub Container Registry (GHCR)

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull
docker pull ghcr.io/ton-username/1min-gateway:1.2.3
```

---

## 🔐 Vérifier la signature Cosign

### Installation Cosign

```bash
# macOS
brew install cosign

# Linux
wget https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
```

### Vérifier une image

```bash
cosign verify \
  --certificate-identity-regexp=".*" \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  billelattafi/1min-gateway:latest

# Si OK, tu verras :
# ✓ Verification for billelattafi/1min-gateway:latest --
# The following checks were performed on each of these signatures:
#   - The cosign claims were validated
#   - Existence of the claims in the transparency log was verified offline
```

---

## 🛡️ Consulter les vulnérabilités

### Dans GitHub

1. Va sur `ton-repo` → **Security**
2. Clique **Code scanning alerts**
3. Filtre par `Trivy`

### Localement avec Trivy

```bash
# Installation
brew install trivy  # macOS
# ou
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy

# Scan d'une image
trivy image billelattafi/1min-gateway:latest

# Scan avec seuil critique uniquement
trivy image --severity CRITICAL,HIGH billelattafi/1min-gateway:latest
```

---

## 🔍 Débugger un workflow échoué

### 1. Voir les logs détaillés

```bash
# Dans GitHub Actions
Actions → Workflow échoué → Job échoué → Expand all steps
```

### 2. Re-exécuter un job spécifique

```bash
# Interface GitHub
Actions → Workflow échoué → "Re-run failed jobs"
```

### 3. Activer le mode debug

```yaml
# Dans ton workflow, ajoute temporairement :
- name: Debug info
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "Release published: ${{ needs.release.outputs.new_release_published }}"
    echo "Release version: ${{ needs.release.outputs.new_release_version }}"
```

### 4. Tester le build localement

```bash
# Reproduire le build Docker
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag test:local \
  .

# Reproduire les tests
pip install -r requirements.txt pytest
pytest
```

---

## 📊 Monitoring des resources GitHub Actions

### Vérifier les minutes consommées

```bash
# Dans GitHub
Settings → Billing and plans → Plans and usage
```

### Optimiser la consommation

```yaml
# Désactiver temporairement les builds ARM64
platforms: linux/amd64  # Au lieu de linux/amd64,linux/arm64

# Désactiver le cache (si problèmes)
cache-from: ""  # Supprime type=gha
cache-to: ""
```

---

## 🚨 Rollback d'une release

### Méthode 1 : Tag une ancienne version

```bash
# Trouver le dernier commit stable
git log --oneline

# Re-tag manuellement
git tag -f v1.2.3 abc1234
git push origin v1.2.3 --force

# L'image v1.2.3 reste disponible sur Docker Hub
docker pull billelattafi/1min-gateway:1.2.3
```

### Méthode 2 : Revert le commit

```bash
# Annuler le dernier commit (crée un nouveau commit inverse)
git revert HEAD
git push origin main

# → Déclenche un nouveau build avec patch version
```

### Méthode 3 : Restaurer latest manuellement

```bash
# Pull une ancienne version
docker pull billelattafi/1min-gateway:1.2.3

# Re-tag comme latest
docker tag billelattafi/1min-gateway:1.2.3 billelattafi/1min-gateway:latest

# Push
docker push billelattafi/1min-gateway:latest
```

---

## 🧪 Tester avant de merger une PR

### 1. Build l'image localement

```bash
git checkout feat/ma-feature
docker build -t test:pr .
docker run -p 8080:8080 test:pr
```

### 2. Vérifier que les tests passent

```bash
pytest --cov=.
```

### 3. Vérifier le scan de sécurité

```bash
docker build -t test:scan .
trivy image --severity CRITICAL,HIGH test:scan
```

---

## 💡 Tips & Tricks

### Forcer une release sans changement de code

```bash
git commit --allow-empty -m "🚀 chore(release): Force rebuild"
git push origin main
```

### Voir les images multi-arch

```bash
docker buildx imagetools inspect billelattafi/1min-gateway:latest

# Résultat :
# Name:      billelattafi/1min-gateway:latest
# MediaType: application/vnd.docker.distribution.manifest.list.v2+json
# Digest:    sha256:abc123...
#
# Manifests:
#   Name:      linux/amd64
#   Digest:    sha256:def456...
#
#   Name:      linux/arm64
#   Digest:    sha256:ghi789...
```

### Nettoyer les anciennes images GitHub

```bash
# Via GitHub Packages UI
Packages → 1min-gateway → Package settings → Delete old versions
```

### Accélérer les tests en local

```bash
# Utiliser le cache pip
pip install --cache-dir ~/.cache/pip -r requirements.txt

# Exécuter seulement les tests modifiés
pytest --lf  # Last failed
pytest --ff  # Failed first
```

---

## 📞 Ressources utiles

- **Semantic Release** : <https://semantic-release.gitbook.io/>
- **Gitmoji Guide** : <https://gitmoji.dev/>
- **Docker Buildx** : <https://docs.docker.com/buildx/>
- **Cosign** : <https://docs.sigstore.dev/cosign/>
- **Trivy** : <https://aquasecurity.github.io/trivy/>
- **GitHub Actions** : <https://docs.github.com/actions>

---

## 🆘 Support

**Problème avec le workflow ?**

1. Vérifie les logs dans Actions
2. Consulte la [documentation complète](./CI-CD-DOCUMENTATION.md)
3. Ouvre une issue GitHub avec :
   - Le lien vers le workflow échoué
   - Les logs d'erreur
   - Ta configuration `.releaserc.json`

---

**Happy shipping! 🚢**
