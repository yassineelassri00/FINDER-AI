"""
Configuration de l'application Finder-AI.

Ce fichier accomplit trois tâches au démarrage du serveur :
  1. Active le mode WAL (Write-Ahead Logging) de SQLite pour autoriser les lectures
     et écritures simultanées sans verrouillage de la base.
  2. Connecte les signaux Django nécessaires (invalidation de l'index sémantique
     lorsqu'un outil est ajouté ou modifié).
  3. Lance le planificateur de tâches d'arrière-plan (APScheduler) pour l'exécution
     automatique du robot de Web Scraping, uniquement si SCRAPER_ENABLED=True
     dans les paramètres et si le processus n'est pas celui de la commande
     `manage.py migrate` ou `manage.py test` (évite les effets de bord en CI).
"""

import os

from django.apps import AppConfig


class FinderConfig(AppConfig):
    name = "finder"
    verbose_name = "Finder-AI"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # ----------------------------------------------------------------
        # 1. Connexion des signaux
        # ----------------------------------------------------------------
        self._connecter_signaux()

        # ----------------------------------------------------------------
        # 2. WAL mode sur SQLite (ignoré pour PostgreSQL)
        # ----------------------------------------------------------------
        self._activer_wal()

        # ----------------------------------------------------------------
        # 3. Planificateur d'arrière-plan (désactivé en test et en migration)
        # ----------------------------------------------------------------
        self._demarrer_planificateur()

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _connecter_signaux(self):
        """Importe le module de signaux afin d'enregistrer les écouteurs."""
        try:
            from finder import signals  # noqa: F401
        except ImportError:
            pass

    def _activer_wal(self):
        """Active le mode WAL sur la base SQLite pour la concurrence."""
        from django.conf import settings
        from django.db import connection

        db_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
        if "sqlite3" not in db_engine:
            return  # PostgreSQL / MySQL : WAL non applicable

        try:
            connection.ensure_connection()
            connection.connection.execute("PRAGMA journal_mode=WAL;")
            connection.connection.execute("PRAGMA synchronous=NORMAL;")
            connection.connection.execute("PRAGMA cache_size=-16000;")  # ~16 Mo de cache
        except Exception:
            # Ne jamais faire planter le serveur à cause d'un PRAGMA
            pass

    def _demarrer_planificateur(self):
        """Lance APScheduler si SCRAPER_ENABLED=True et hors contexte de test/migration."""
        from django.conf import settings

        if not getattr(settings, "SCRAPER_ENABLED", False):
            return

        # Ne pas lancer le planificateur dans les processus annexes Django
        # (manage.py test, migrate, makemigrations, etc.)
        running_cmd = os.environ.get("DJANGO_MANAGEMENT_COMMAND", "")
        skip_commands = {"test", "migrate", "makemigrations", "shell", "collectstatic"}
        if running_cmd in skip_commands:
            return

        # Éviter le double démarrage en mode rechargement automatique (DEBUG)
        if os.environ.get("RUN_MAIN") != "true" and settings.DEBUG:
            return

        try:
            from finder.scheduler import demarrer_planificateur
            demarrer_planificateur()
        except Exception:
            # Le planificateur ne doit jamais empêcher le serveur de démarrer
            pass
