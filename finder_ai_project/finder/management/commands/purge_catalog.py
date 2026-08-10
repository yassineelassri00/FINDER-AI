"""Commande de gestion : purge les outils IA hors catalogue.

Le catalogue officiel (provenance="catalogue") est la seule source de
données « sûre » du workspace. Les entrées issues du robot de scraping
ou proposées par la communauté polluent la démo : cette commande permet
de les retirer proprement.

Usage :
    python manage.py purge_catalog --all-unseeded        # supprime tout sauf le catalogue
    python manage.py purge_catalog --provenance scraper  # supprime uniquement les outils scrapés
    python manage.py purge_catalog --all-unseeded --keep-validated  # conserve les outils validés
"""

from django.core.management.base import BaseCommand

from finder.models import OutilIA


class Command(BaseCommand):
    help = "Supprime les outils IA qui ne font pas partie du catalogue officiel."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all-unseeded",
            action="store_true",
            help="Supprimer tous les outils sauf ceux du catalogue officiel.",
        )
        parser.add_argument(
            "--provenance",
            choices=["scraper", "community"],
            help="Supprimer uniquement les outils de cette provenance.",
        )
        parser.add_argument(
            "--keep-validated",
            action="store_true",
            help="Conserver les outils validés par l'administrateur.",
        )

    def handle(self, *args, **options):
        queryset = OutilIA.objects.none()

        if options["all_unseeded"]:
            queryset = OutilIA.objects.exclude(provenance="catalogue")
        elif options["provenance"]:
            queryset = OutilIA.objects.filter(provenance=options["provenance"])
        else:
            self.stdout.write(self.style.WARNING(
                "Aucun critère fourni. Utilisez --all-unseeded ou --provenance."
            ))
            return

        if options["keep_validated"]:
            queryset = queryset.filter(est_valide=False)

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Rien à purger : aucun outil ne correspond."))
            return

        queryset.delete()
        restants = OutilIA.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"{total} outil(s) supprimé(s). Il reste {restants} outil(s) en base.")
        )
