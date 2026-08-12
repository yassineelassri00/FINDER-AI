# syntax=docker/dockerfile:1
#
# Image de production Finder-AI (Django + gunicorn + whitenoise).
#
#  - Image de base Python slim récente (3.13).
#  - Build en 2 étapes : le builder installe les dépendances, le runtime
#    ne contient que le nécessaire (pas d'outils de compilation).
#  - Exécution en utilisateur système non privilégié (UID 1000) : jamais root.
#  - L'image ne contient ni .env, ni base SQLite, ni venv (voir .dockerignore).
#
# L'utilisateur est chargé d'injecter l'environnement au lancement
# (compose, Secret Manager / Cloud Run) : SECRET_KEY, DATABASE_URL, etc.

# ═══════════════════════════════════════════════════════════════════════════
# Stage 1 — builder : venv isolé avec les dépendances Python
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip wheel \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ═══════════════════════════════════════════════════════════════════════════
# Stage 2 — runtime : image finale minimale, non root
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Port HTTP écouté par gunicorn — surchargé par Cloud Run (PORT).
    PORT="8000"

# libpq : binaire natif requis par psycopg 3 ; tzdata : fuseau "Africa/Casablanca".
RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 tzdata \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur système dédié, non privilégié.
RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=1000:1000 . .

# Dossiers en écriture pour l'utilisateur applicatif (collectstatic).
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R 1000:1000 /app/staticfiles /app/media

USER appuser

EXPOSE 8000

# collectstatic au démarrage (les env. sont injectées à l'exécution), puis
# gunicorn : threads pour les I/O bloquantes (APIs IA, scraping), recyclage
# régulier des workers (--max-requests), logs access/error sur stdout.
# Exec : gunicorn remplace le shell pour recevoir directement les signaux.
CMD ["sh", "-c", "python manage.py collectstatic --noinput \
    && exec gunicorn config.wsgi:application \
         --bind 0.0.0.0:${PORT:-8000} \
         --workers ${WEB_CONCURRENCY:-2} \
         --threads 4 \
         --timeout 30 \
         --max-requests 1000 \
         --max-requests-jitter 100 \
         --access-logfile - \
         --error-logfile - \
         --log-level info"]
