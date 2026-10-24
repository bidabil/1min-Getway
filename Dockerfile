# --- STAGE 1: dependencies ---
FROM python:3.14-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- STAGE 2: runtime ---
FROM python:3.14-slim

ARG VERSION="0.0.0"
ARG COMMIT="unknown"

LABEL org.opencontainers.image.title="1min-Gateway"
LABEL org.opencontainers.image.description="OpenAI- and Anthropic-compatible gateway and MCP server for 1min.ai"
LABEL org.opencontainers.image.source="https://github.com/bidabil/1min-Getway"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${COMMIT}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    APP_COMMIT="${COMMIT}" \
    PORT=5001 \
    WORKERS=1

# pip is not needed at runtime; removing it also removes its CVEs from the image.
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser \
    && python -m pip uninstall --yes pip

COPY --from=builder /install /usr/local
# Code is owned by root and read-only for the runtime user.
COPY src/ /app/src/

# Numeric UID (appuser) so the host and orchestrators can resolve it.
USER 1000
WORKDIR /app
EXPOSE 5001

# An uncaught exception exits with status 1, which marks the container unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; port = os.environ.get('PORT', '5001'); urllib.request.urlopen('http://127.0.0.1:' + port + '/health', timeout=4)"]

# `exec` makes uvicorn PID 1 so it receives SIGTERM and shuts down gracefully.
# FORWARDED_ALLOW_IPS lists the reverse proxies whose X-Forwarded-* headers are trusted.
CMD ["sh", "-c", "exec uvicorn gateway.main:app --host 0.0.0.0 --port \"$PORT\" --workers \"$WORKERS\" --proxy-headers --no-access-log --timeout-graceful-shutdown 30"]
