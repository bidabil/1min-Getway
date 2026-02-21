
# --- STAGE 1: Builder ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# --- STAGE 2: Runtime (Image finale) ---
FROM python:3.12-slim

# Labels OCI standards
LABEL org.opencontainers.image.title="1min-Gateway"
LABEL org.opencontainers.image.description="Intelligent API Gateway for AI models (FastAPI)"
LABEL org.opencontainers.image.vendor="Billel Attafi"
LABEL org.opencontainers.image.source="https://github.com/billelattafi/1min-gateway"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/home/appuser/.local/bin:$PATH

WORKDIR /app

# Security updates for base image vulnerabilities
# Pending CVEs (no fix available yet in Debian):
# - CVE-2026-0861 (glibc): HIGH - memalign integer overflow. Low risk (no direct memalign usage)
# - CVE-2026-27171 (zlib): MEDIUM - CRC32 infinite loop DoS. Low risk (no CRC32 combine usage)
# - CVE-2025-14104 (util-linux): MEDIUM - setpwnam heap overread. Low risk (no SUID login-utils)
# - CVE-2025-7709 (sqlite3): MEDIUM - FTS5 integer overflow. Low risk (no FTS5 usage)
# This upgrade ensures we get security patches as soon as they're released.
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to fix CVE-2025-8869 (symlink extraction vulnerability)
RUN pip install --upgrade pip>=25.3

# Créer un utilisateur non-root AVANT de copier les fichiers
RUN useradd --create-home --shell /bin/bash appuser

# Copier les dépendances depuis le builder
COPY --from=builder /root/.local /home/appuser/.local

# Copier le code source avec les bonnes permissions
COPY --chown=appuser:appuser . .

# Créer le dossier de logs
RUN mkdir -p logs && chown -R appuser:appuser logs

# Passer à l'utilisateur non-root
USER appuser

# Healthcheck intégré (FastAPI)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:5001/', timeout=5)" || exit 1

EXPOSE 5001

# Utiliser uvicorn pour FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "1"]
