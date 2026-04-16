#!/usr/bin/env bash
# ==============================================================================
# deploy.sh - 1min-Gateway Server Deployment Script
# ==============================================================================
# Usage: bash deploy.sh
# Requirements: Ubuntu/Debian server (fresh or existing)
# ==============================================================================

set -euo pipefail

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Config ---
IMAGE="billelattafi/1min-gateway:latest"
CONTAINER_NAME="1min-gateway"
PORT="5001"
ENV_FILE="$HOME/.env-1min-gateway"
LOG_DIR="$HOME/1min-gateway/logs"

log_info()    { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_section() { echo -e "\n${BLUE}==> $1${NC}"; }

# ==============================================================================
# 1. DOCKER INSTALLATION
# ==============================================================================
install_docker() {
    log_section "Vérification de Docker"

    if command -v docker &>/dev/null; then
        log_info "Docker déjà installé : $(docker --version)"
    else
        log_info "Installation de Docker..."
        sudo apt-get update -qq
        sudo apt-get install -y ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
            | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
            https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
            | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update -qq
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        sudo systemctl enable --now docker
        sudo usermod -aG docker "$USER"
        log_info "Docker installé avec succès"
    fi
}

# ==============================================================================
# 2. ENVIRONMENT CONFIGURATION
# ==============================================================================
configure_env() {
    log_section "Configuration de l'environnement"

    if [[ -f "$ENV_FILE" ]]; then
        log_warn "Fichier .env existant détecté : $ENV_FILE"
        read -rp "  Voulez-vous le reconfigurer ? [y/N] " answer
        [[ "$answer" =~ ^[Yy]$ ]] || { log_info "Configuration existante conservée."; return; }
    fi

    echo ""
    log_info "Entrez vos paramètres de configuration :"
    echo ""

    # API Key (obligatoire)
    while true; do
        read -rp "  ONE_MIN_AI_API_KEY (1min.ai) : " api_key
        [[ -n "$api_key" ]] && break
        log_error "La clé API est obligatoire."
    done

    # Models filter
    read -rp "  Filtrer les modèles ? [y/N] : " filter_models
    if [[ "$filter_models" =~ ^[Yy]$ ]]; then
        read -rp "  Modèles autorisés (ex: gpt-4o-mini,deepseek-chat) : " permitted_models
        permit_only="True"
    else
        permitted_models="mistral-nemo,gpt-4o-mini,deepseek-chat"
        permit_only="False"
    fi

    # CORS
    read -rp "  Domaines CORS autorisés (laisser vide = tous) : " cors_origins

    # Generate secret key
    secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # Write .env file
    cat > "$ENV_FILE" << EOF
# ==============================================================================
# 1min-Gateway - Configuration
# Généré le $(date '+%Y-%m-%d %H:%M:%S')
# ==============================================================================

# 1min.ai API
ONE_MIN_AI_API_KEY=${api_key}
ONE_MIN_API_URL=https://api.1min.ai/api/features
ONE_MIN_CONVERSATION_API_STREAMING_URL=https://api.1min.ai/api/features/stream
ONE_MIN_ASSET_URL=https://api.1min.ai/api/assets

# Sécurité
DEBUG=False
CORS_ORIGINS=${cors_origins}
CORS_ALLOW_CREDENTIALS=True

# Serveur
PORT=5001
LOG_LEVEL=INFO
LOG_FORMAT=json

# Modèles
PERMIT_MODELS_FROM_SUBSET_ONLY=${permit_only}
SUBSET_OF_ONE_MIN_PERMITTED_MODELS=${permitted_models}

# Rate limiting
RATELIMIT_ENABLED=True
RATELIMIT_DEFAULT=500 per minute
RATELIMIT_MODELS_LIST=20 per minute

# Memcached (désactivé en mode simple)
MEMCACHED_HOST=localhost
MEMCACHED_PORT=11211
EOF

    chmod 600 "$ENV_FILE"
    log_info "Fichier .env créé : $ENV_FILE"
}

# ==============================================================================
# 3. DEPLOY CONTAINER
# ==============================================================================
deploy_container() {
    log_section "Déploiement du container"

    # Create log directory
    mkdir -p "$LOG_DIR"

    # Stop existing container if running
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_info "Arrêt du container existant..."
        docker stop "$CONTAINER_NAME" &>/dev/null || true
        docker rm "$CONTAINER_NAME" &>/dev/null || true
    fi

    # Pull latest image
    log_info "Pull de l'image depuis Docker Hub..."
    docker pull "$IMAGE"

    # Run container
    log_info "Démarrage du container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p "${PORT}:${PORT}" \
        --env-file "$ENV_FILE" \
        -v "${LOG_DIR}:/app/logs" \
        "$IMAGE"

    log_info "Container démarré : $CONTAINER_NAME"
}

# ==============================================================================
# 4. HEALTH CHECK
# ==============================================================================
health_check() {
    log_section "Vérification de santé"

    log_info "Attente du démarrage (15s)..."
    sleep 15

    if curl -sf "http://localhost:${PORT}/" &>/dev/null; then
        log_info "Gateway opérationnel !"
        echo ""
        curl -s "http://localhost:${PORT}/" | python3 -m json.tool 2>/dev/null || true
    else
        log_error "Le gateway ne répond pas. Vérifiez les logs :"
        docker logs "$CONTAINER_NAME" --tail 30
        exit 1
    fi
}

# ==============================================================================
# 5. SUMMARY
# ==============================================================================
print_summary() {
    PUBLIC_IP=$(curl -sf ifconfig.me 2>/dev/null || echo "IP inconnue")

    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}  Déploiement réussi !${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo -e "  URL locale  : http://localhost:${PORT}"
    echo -e "  URL publique: http://${PUBLIC_IP}:${PORT}"
    echo ""
    echo -e "  Configuration client AI :"
    echo -e "    API Base URL : http://${PUBLIC_IP}:${PORT}"
    echo -e "    API Key      : (ta clé ONE_MIN_AI_API_KEY)"
    echo ""
    echo -e "  Commandes utiles :"
    echo -e "    Logs    : docker logs -f ${CONTAINER_NAME}"
    echo -e "    Stop    : docker stop ${CONTAINER_NAME}"
    echo -e "    Update  : docker pull ${IMAGE} && docker restart ${CONTAINER_NAME}"
    echo -e "    Status  : docker ps"
    echo ""
    echo -e "${YELLOW}  ⚠️  Pense à ouvrir le port ${PORT} dans le firewall GCP${NC}"
    echo ""
}

# ==============================================================================
# MAIN
# ==============================================================================
main() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  1min-Gateway - Script de déploiement${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""

    install_docker
    configure_env
    deploy_container
    health_check
    print_summary
}

main "$@"
