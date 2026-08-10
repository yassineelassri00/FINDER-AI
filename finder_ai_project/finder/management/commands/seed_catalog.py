"""Commande de gestion : charge le catalogue officiel d'outils IA.

Usage :
    python manage.py seed_catalog [--no-tags]

Le catalogue vit dans finder/data/catalog.json et est idempotent :
relancer la commande met à jour les entrées existantes (par URL) sans
créer de doublons. Les outils du catalogue sont marqués
provenance="catalogue" et est_valide=True par défaut.
"""

import json
import os

from django.core.management.base import BaseCommand

from finder.models import Categorie, OutilIA, Tag

CHEMIN_CATALOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "catalog.json",
)


class Command(BaseCommand):
    help = "Charge ou met à jour le catalogue officiel d'outils IA depuis catalog.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-tags",
            action="store_true",
            help="Ne pas recréer/synchroniser les tags du catalogue.",
        )

    def handle(self, *args, **options):
        if not os.path.exists(CHEMIN_CATALOG):
            self.stderr.write(self.style.ERROR(f"Catalogue introuvable : {CHEMIN_CATALOG}"))
            return

        with open(CHEMIN_CATALOG, encoding="utf-8") as fh:
            data = json.load(fh)

        categories_data = data.get("categories", [])
        outils_data = data.get("tools", [])
        sync_tags = not options["no_tags"]

        # --- Catégories ---
        categories = {}
        for cat in categories_data:
            obj, _ = Categorie.objects.get_or_create(
                slug=cat["slug"], defaults={"nom": cat["nom"]}
            )
            if obj.nom != cat["nom"]:
                obj.nom = cat["nom"]
                obj.save(update_fields=["nom"])
            categories[cat["slug"]] = obj
        self.stdout.write(
            self.style.SUCCESS(f"Catégories prêtes : {len(categories)} ({', '.join(sorted(categories))})")
        )

        # --- Tags ---
        tags = {}
        if sync_tags:
            slugs_tags = set()
            for outil in outils_data:
                slugs_tags.update(outil.get("tags", []))
            for slug in sorted(slugs_tags):
                obj, _ = Tag.objects.get_or_create(slug=slug, defaults={"nom": slug})
                tags[slug] = obj
            self.stdout.write(self.style.SUCCESS(f"Tags synchronisés : {len(tags)}"))

        # --- Outils ---
        ajoutes = 0
        maj = 0
        for entree in outils_data:
            nom = entree["nom"]
            url = entree["url_site"]
            categorie = categories.get(entree.get("categorie", "general"))
            defaults = {
                "nom": nom,
                "description": entree.get("description", ""),
                "type_tarification": entree.get("type_tarification", "Freemium"),
                "type_integration": entree.get("type_integration", "Web / API"),
                "categorie": categorie,
                "provenance": "catalogue",
                "est_valide": entree.get("est_valide", True),
            }
            outil, cree = OutilIA.objects.update_or_create(
                url_site=url, defaults=defaults
            )
            if sync_tags and tags:
                outil.tags.set([tags[s] for s in entree.get("tags", []) if s in tags])
            if cree:
                ajoutes += 1
            else:
                maj += 1

        total = OutilIA.objects.filter(provenance="catalogue").count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogue terminé : {ajoutes} ajouté(s), {maj} mis à jour, "
                f"{total} outil(s) de provenance « catalogue » en base."
            )
        )
