"""
Django settings for config project.

Configuration "production-grade" :
  - Aucune clé en dur : toutes les valeurs sensibles proviennent de
    l'environnement (.env en dev, GCP Secret Manager / Cloud Run en prod).
  - Headers de sécurité de base activables via l'environnement.
  - Rate-limiting d'authentification (django-axes) activable en production.
"""

from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Chemins de base
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "testserver"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
    TAVILY_API_KEY=(str, ""),
    # Sécurité / HTTPS (valeurs par défaut sûres pour le dev local)
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    # Rate-limiting d'authentification (désactivé par défaut en dev)
    AXES_ENABLED=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Sécurité
# ---------------------------------------------------------------------------
# SECRET_KEY est OBLIGATOIRE : le serveur refuse de démarrer sans lui.
# Aucun fallback en dur dans le code (fail fast en production).
SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# Headers de sécurité de base
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# HTTPS derrière un load-balancer / Cloud Run
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")

# Cookies de session
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")

# HSTS (activé uniquement si SECURE_HSTS_SECONDS > 0)
SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

# ---------------------------------------------------------------------------
# Applications installées
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "axes",  # Rate-limiting des tentatives de connexion
    "finder",
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # AxesMiddleware DOIT être placé APRÈS AuthenticationMiddleware.
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Base de données — SQLite en développement, PostgreSQL en production
# via DATABASE_URL=postgres://user:pass@host:5432/dbname dans .env
# ---------------------------------------------------------------------------
DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    import dj_database_url  # type: ignore
    DATABASES = {"default": dj_database_url.config(default=DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # OPTIONS WAL activé dans FinderConfig.ready() pour la concurrence
        }
    }

# ---------------------------------------------------------------------------
# Clé primaire par défaut
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Validation des mots de passe
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Backends d'authentification — AxesStandaloneBackend trace les échecs sans
# intercepter l'authentification elle-même (ModelBackend reste l'authentifieur).
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "axes.backends.AxesStandaloneBackend",
]

# ---------------------------------------------------------------------------
# Rate-limiting d'authentification (django-axes)
# ---------------------------------------------------------------------------
AXES_ENABLED = env("AXES_ENABLED")
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = env.int("AXES_COOLOFF_TIME", default=2)  # en heures
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Casablanca"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques (CSS, JS, Images de l'interface)
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Fichiers médias (uploads utilisateurs : fichiers de contexte, pièces jointes)
# ---------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Clé API externe : Tavily (moteur de recherche IA)
# ---------------------------------------------------------------------------
TAVILY_API_KEY = env("TAVILY_API_KEY")

# ---------------------------------------------------------------------------
# Clé API externe : Gemini (résumé IA génératif)
# Modèle de clé hybride : clé personnelle (UserProfile.gemini_api_key) en
# priorité, sinon clé serveur réservée aux abonnés Finder Plus.
# ---------------------------------------------------------------------------
GEMINI_SERVER_API_KEY = env("GEMINI_SERVER_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-2.0-flash")

# ---------------------------------------------------------------------------
# Django REST Framework — Configuration globale
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ---------------------------------------------------------------------------
# Limites de téléversement de fichiers
# ---------------------------------------------------------------------------
# Taille maximale autorisée pour un fichier de contexte (10 Mo)
UPLOAD_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 Mo
# Extensions acceptées — les types rendables en ligne exécutables (svg, html,
# xml) sont exclus pour réduire la surface d'attaque (XSS stocké).
UPLOAD_ALLOWED_EXTENSIONS = {
    ".txt", ".pdf", ".py", ".js", ".ts", ".json", ".csv",
    ".md", ".css", ".yaml", ".yml",
    ".png", ".jpg", ".jpeg", ".gif",
}

# Taille maximale du corps des requêtes HTTP.
# Doit dépasser UPLOAD_MAX_SIZE_BYTES (le body multipart inclut le fichier).
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024  # 12 Mo
FILE_UPLOAD_MAX_MEMORY_SIZE = UPLOAD_MAX_SIZE_BYTES  # spool vers disque au-delà

# ---------------------------------------------------------------------------
# Planificateur de tâches d'arrière-plan (APScheduler)
# SCRAPER_ENABLED : désactiver en test pour éviter les effets de bord.
# ---------------------------------------------------------------------------
SCRAPER_ENABLED = env.bool("SCRAPER_ENABLED", default=False)
SCRAPER_TARGET_URL = env("SCRAPER_TARGET_URL", default="https://github.com/trending")
