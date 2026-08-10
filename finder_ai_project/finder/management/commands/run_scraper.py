from django.core.management.base import BaseCommand
from finder.scraper import FinderScraper


class Command(BaseCommand):
    help = "Exécute le robot de Web Scraping Finder-AI pour extraire des outils IA depuis une URL cible."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            default="https://github.com/trending",
            help="L'URL cible à visiter et analyser.",
        )

    def handle(self, *args, **options):
        url = options["url"]
        self.stdout.write(self.style.SUCCESS(f"Démarrage du robot de scraping sur : {url}"))

        scraper = FinderScraper(url_cible=url)
        log = scraper.lancer()

        if scraper.erreurs:
            self.stdout.write(self.style.WARNING(f"Exécution terminée avec {len(scraper.erreurs)} avertissement(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Succès ! {log.total_extraits} outils traités en {log.temps_execution}s."))
