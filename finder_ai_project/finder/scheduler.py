"""
Planificateur de tâches d'arrière-plan Finder-AI.

Utilise APScheduler (BackgroundScheduler) pour exécuter le robot de Web Scraping
automatiquement à heure fixe, sans bloquer le serveur web.

Le planificateur est démarré depuis FinderConfig.ready() uniquement si
SCRAPER_ENABLED=True dans les paramètres. Il n'est jamais lancé pendant
les commandes `manage.py test`, `migrate` ou `makemigrations`.

Tâches planifiées :
  - run_scheduled_scraping() : chaque jour à 02h00 (configurable)
"""

import logging

logger = logging.getLogger(__name__)


def run_scheduled_scraping():
    """
    Tâche exécutée automatiquement par APScheduler.
    Lance le robot FinderScraper sur l'URL configurée dans SCRAPER_TARGET_URL.
    Enregistre le résultat dans ScraperLog et signale toute erreur dans les logs.
    """
    from django.conf import settings
    from finder.scraper import FinderScraper

    url = getattr(settings, "SCRAPER_TARGET_URL", "https://github.com/trending")
    logger.info("[Scheduler] Démarrage automatique du scraping sur : %s", url)

    try:
        scraper = FinderScraper(url_cible=url)
        log = scraper.lancer()
        logger.info(
            "[Scheduler] Scraping terminé : %d outils en %.2fs. Erreurs : %d",
            log.total_extraits,
            log.temps_execution,
            len(scraper.erreurs),
        )
    except Exception as exc:
        logger.error("[Scheduler] Échec du scraping automatique : %s", exc, exc_info=True)


def demarrer_planificateur():
    """
    Initialise et démarre le BackgroundScheduler d'APScheduler.
    Ajoute la tâche de scraping nocturne (02h00 tous les jours).
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from django.conf import settings
    except ImportError:
        logger.warning(
            "[Scheduler] APScheduler n'est pas installé. "
            "Installez-le avec : pip install apscheduler==3.10.4"
        )
        return

    scheduler = BackgroundScheduler(timezone="Africa/Casablanca")

    scheduler.add_job(
        func=run_scheduled_scraping,
        trigger=CronTrigger(hour=2, minute=0),  # Tous les jours à 02h00
        id="scraping_nocturne",
        name="Scraping automatique Finder-AI",
        replace_existing=True,
        misfire_grace_time=3600,  # Tolérance de 1h si le serveur était arrêté
    )

    scheduler.start()
    logger.info("[Scheduler] Planificateur démarré. Scraping nocturne à 02h00.")
