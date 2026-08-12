"""
Django settings for config project.

Configuration "production-grade" :
  - Aucune clé en dur : toutes les valeurs sensibles proviennent de
    l'environnement (.env en dev, GCP Secret Manager / Cloud Run en prod).
  - SECRET_KEY obligatoire : fail-fast (ImproperlyConfigured) sans lui.
  - DEBUG dynamique via .env ; démarrage refusé si DEBUG=True en production.
  - Headers de sécurité, cookies sécurisés et HSTS activables via
    l'environnement (et forcés en production).
  - Rate-limiting d'authentification (django-axes) + throttling API (DRF).
  - Logging structuré vers la console pour tracer l'activité en production.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# ---------------------------------------------------------------------------
# Chemins de base
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ENVIRONMENT=(str, "development"),
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

def _verifier_secret_key(valeur: str) -> str:
    """Lève ImproperlyConfigured si SECRET_KEY est vide/absente (fail fast)."""
    if not valeur:
        raise ImproperlyConfigured(
            "SECRET_KEY est introuvable dans l'environnement (.env ou Secret "
            "Manager). Le serveur refuse de démarrer sans lui : aucun fallback "
            "en dur dans le code."
        )
    return valeur


def _verifier_mode_production(environment: str, debug: bool) -> None:
    """Interdit DEBUG=True en production : fuite de secrets et de stack traces."""
    if environment == "production" and debug:
        raise ImproperlyConfigured(
            "DEBUG=True est strictement interdit en environnement de "
            "production (fuite d'informations sensibles et traces de "
            "débogage). Passez DEBUG=False dans le .env / Secret Manager."
        )


def _force_https_production(environment: str, valeur_env: bool) -> bool:
    """En production, la sécurité HTTPS est incontournable : on force True."""
    if environment == "production":
        return True
    return valeur_env


def _choisir_email_backend(host_smtp: str) -> str:
    """Backend SMTP si un hôte est fourni, sinon repli sur la console."""
    if host_smtp:
        return "django.core.mail.backends.smtp.EmailBackend"
    return "django.core.mail.backends.console.EmailBackend"


SECRET_KEY = _verifier_secret_key(env("SECRET_KEY"))

ENVIRONMENT = env("ENVIRONMENT").strip().lower()
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# Fail-fast : DEBUG=True est interdit en production.
_verifier_mode_production(ENVIRONMENT, DEBUG)

# Headers de sécurité de base
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# HTTPS derrière un load-balancer / Cloud Run
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _force_https_production(ENVIRONMENT, env("SECURE_SSL_REDIRECT"))

# Cookies de session
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = _force_https_production(ENVIRONMENT, env("SESSION_COOKIE_SECURE"))
CSRF_COOKIE_SECURE = _force_https_production(ENVIRONMENT, env("CSRF_COOKIE_SECURE"))

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
    # Whitenoise DOIT venir immédiatement après SecurityMiddleware pour
    # servir les fichiers statiques compressés (gzip/brotli) en production.
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
# Base de données — PostgreSQL en production via DATABASE_URL
# (ex : postgres://user:pass@host:5432/dbname). Sans DATABASE_URL, repli
# transparent sur la base SQLite locale : le développement et les tests
# continuent de fonctionner sans aucune configuration supplémentaire.
# ---------------------------------------------------------------------------
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{(BASE_DIR / 'db.sqlite3').as_posix()}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}
# DATABASE_URL défini mais vide (cas du .env de développement) : dj-database-url
# retourne alors {} — on retombe explicitement sur SQLite.
if not DATABASES["default"]:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # OPTIONS WAL activé dans FinderConfig.ready() pour la concurrence
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
# En production, la protection anti-force-brute est incontournable : on force
# AXES_ENABLED=True même si le .env l'omet par erreur.
AXES_ENABLED = env("AXES_ENABLED") or ENVIRONMENT == "production"
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = env.int("AXES_COOLOFF_TIME", default=2)  # en heures
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]

# ---------------------------------------------------------------------------
# Logging — journalisation structurée vers la console (stdout/stderr).
# Niveau INFO pour Django, WARNING pour les requêtes HTTP.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "axes": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

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

# Whitenoise : compression gzip/brotli + cache-busting par hash de contenu.
# En développement (DEBUG=True) le manifeste n'est pas requis : Django sert
# les fichiers via le runserver, le comportement reste identique.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# Fichiers immuables (noms hashés) : cache navigateur long sans risque.
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 30  # 30 jours

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
    # Throttling global (S2) : limite les abus sur l'API (brute force, DoS).
    # S'applique aux vues DRF — ex. /api/research/.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "100/min",
    },
}

# ---------------------------------------------------------------------------
# Limites de téléversement de fichiers
# ---------------------------------------------------------------------------
# Taille maximale autorisée pour un fichier de contexte (5 Mo)
UPLOAD_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 Mo
# Extensions acceptées — les types rendables en ligne exécutables (svg, html,
# xml) sont exclus pour réduire la surface d'attaque (XSS stocké).
UPLOAD_ALLOWED_EXTENSIONS = {
    ".txt", ".pdf", ".py", ".js", ".ts", ".json", ".csv",
    ".md", ".css", ".yaml", ".yml",
    ".png", ".jpg", ".jpeg", ".gif",
}

# Taille maximale du corps des requêtes HTTP (5 Mo de fichier + overhead
# multipart) : bloque les dénis de service par corps de requête géants (S2).
# Doit dépasser UPLOAD_MAX_SIZE_BYTES (le body multipart inclut le fichier).
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # 6 Mo
FILE_UPLOAD_MAX_MEMORY_SIZE = UPLOAD_MAX_SIZE_BYTES  # spool vers disque au-delà

# ---------------------------------------------------------------------------
# Messagerie — SMTP si configuré, sinon repli sur la console (S3).
# Sans SMTP, la réinitialisation de mot de passe reste fonctionnelle : l'e-mail
# est affiché dans les logs au lieu d'échouer silencieusement.
# ---------------------------------------------------------------------------
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_BACKEND = _choisir_email_backend(EMAIL_HOST)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Finder AI <noreply@finder-ai.local>")

# ---------------------------------------------------------------------------
# Planificateur de tâches d'arrière-plan (APScheduler)
# SCRAPER_ENABLED : désactiver en test pour éviter les effets de bord.
# ---------------------------------------------------------------------------
SCRAPER_ENABLED = env.bool("SCRAPER_ENABLED", default=False)
SCRAPER_TARGET_URL = env("SCRAPER_TARGET_URL", default="https://github.com/trending")
