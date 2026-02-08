# --- STAGE 1: Builder ---
FROM python:3.14-slim AS builder

# Désactiver le cache pip pour gagner de la place et éviter les fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# On installe build-essential uniquement ici pour compiler les dépendances (tiktoken, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances dans un dossier utilisateur pour faciliter le transfert
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# --- STAGE 2: Runtime (Image finale) ---
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

# On récupère uniquement les bibliothèques compilées de l'étape précédente
COPY --from=builder /root/.local /root/.local

# Copie du code source
COPY . .

# Gestion des logs (création du dossier et permissions)
RUN mkdir -p logs && chmod 777 logs

# Expose le port de l'application
EXPOSE 5001

# Utilisation d'un utilisateur non-root pour la sécurité (optionnel mais conseillé)
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser

CMD ["python", "main.py"]
