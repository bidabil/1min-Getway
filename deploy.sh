#!/usr/bin/env bash
# ==============================================================================
# deploy.sh - install or update 1min-Gateway on a Linux server with Docker.
# Works when piped:  curl -fsSL <url>/deploy.sh | bash
# Re-running it updates the image and keeps the existing configuration.
# ==============================================================================
set -euo pipefail

IMAGE="${GATEWAY_IMAGE:-billelattafi/1min-gateway:latest}"
CONTAINER="1min-gateway"
DEPLOY_DIR="${DEPLOY_DIR:-$HOME/1min-gateway}"
ENV_FILE="$DEPLOY_DIR/.env"
BIND="${GATEWAY_BIND:-127.0.0.1}"
PORT="${GATEWAY_PORT:-5001}"

info()  { printf '\033[0;32m[INFO]\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m[WARN]\033[0m %s\n' "$1"; }
fail()  { printf '\033[0;31m[ERROR]\033[0m %s\n' "$1" >&2; exit 1; }

# Prompts read the terminal, not stdin (stdin is the script itself under curl | bash).
ask() {
    local prompt="$1" answer=""
    if [[ -r /dev/tty ]]; then
        read -r -p "$prompt" answer < /dev/tty || true
    fi
    printf '%s' "$answer"
}

ask_secret() {
    local prompt="$1" answer=""
    if [[ -r /dev/tty ]]; then
        read -r -s -p "$prompt" answer < /dev/tty || true
        printf '\n' > /dev/tty
    fi
    printf '%s' "$answer"
}

DOCKER=(docker)

ensure_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        info "Installing Docker (get.docker.com)..."
        curl -fsSL https://get.docker.com | sudo sh
        sudo systemctl enable --now docker
    fi
    if ! docker info >/dev/null 2>&1; then
        # The current shell is not (yet) in the docker group: use sudo for this run.
        DOCKER=(sudo docker)
        "${DOCKER[@]}" info >/dev/null 2>&1 || fail "Cannot talk to the Docker daemon."
    fi
}

configure() {
    mkdir -p "$DEPLOY_DIR"
    if [[ -f "$ENV_FILE" ]]; then
        info "Keeping the existing configuration in $ENV_FILE"
        return
    fi

    local api_key="${ONE_MIN_API_KEY:-}"
    [[ -n "$api_key" ]] || api_key="$(ask_secret '1min.ai API key (input hidden): ')"
    [[ -n "$api_key" ]] || fail "A 1min.ai API key is required (or set ONE_MIN_API_KEY before running)."

    local agent_name
    agent_name="$(ask 'Name of the first agent key [agent]: ')"
    agent_name="${agent_name:-agent}"

    info "Generating a gateway key for '$agent_name'..."
    local key_output gateway_key key_entry
    key_output="$("${DOCKER[@]}" run --rm "$IMAGE" python -m gateway.cli create-key "$agent_name")"
    gateway_key="$(printf '%s\n' "$key_output" | awk '/^ *gw-/ {print $1; exit}')"
    key_entry="$(printf '%s\n' "$key_output" | awk -v n="$agent_name:" 'index($1, n) == 1 {print $1; exit}')"
    [[ -n "$gateway_key" && -n "$key_entry" ]] || fail "Could not generate a gateway key."

    umask 077
    cat > "$ENV_FILE" <<EOF
ONE_MIN_API_KEY=$api_key
GATEWAY_API_KEYS=$key_entry
LOG_FORMAT=json
RATE_LIMIT_RPM=60
EOF
    chmod 600 "$ENV_FILE"
    info "Configuration written to $ENV_FILE"
    printf '\n  Gateway API key for %s (shown once, store it safely):\n    %s\n\n' "$agent_name" "$gateway_key"
}

deploy() {
    info "Pulling $IMAGE..."
    "${DOCKER[@]}" pull "$IMAGE"

    if "${DOCKER[@]}" ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
        info "Replacing the running container..."
        "${DOCKER[@]}" rm -f "$CONTAINER" >/dev/null
    fi

    "${DOCKER[@]}" run -d \
        --name "$CONTAINER" \
        --restart unless-stopped \
        --env-file "$ENV_FILE" \
        -p "$BIND:$PORT:5001" \
        --read-only --tmpfs /tmp \
        --cap-drop ALL --security-opt no-new-privileges:true \
        "$IMAGE" >/dev/null

    info "Waiting for the gateway to become healthy..."
    for _ in $(seq 1 30); do
        if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
            info "1min-Gateway is running on $BIND:$PORT"
            return
        fi
        sleep 2
    done
    "${DOCKER[@]}" logs --tail 40 "$CONTAINER" || true
    fail "The gateway did not become healthy."
}

summary() {
    cat <<EOF

  OpenAI base URL     http://127.0.0.1:$PORT/v1
  Anthropic base URL  http://127.0.0.1:$PORT
  MCP endpoint        http://127.0.0.1:$PORT/mcp
  Readiness           curl http://127.0.0.1:$PORT/ready

  The gateway listens on $BIND only. To reach it from other machines, put a reverse
  proxy with TLS in front of it (e.g. Caddy: 'reverse_proxy 127.0.0.1:$PORT'), so API
  keys never travel in clear text. Add keys: docker run --rm $IMAGE python -m gateway.cli create-key NAME
  then append the printed entry to GATEWAY_API_KEYS in $ENV_FILE and re-run this script.

EOF
}

ensure_docker
configure
deploy
summary
