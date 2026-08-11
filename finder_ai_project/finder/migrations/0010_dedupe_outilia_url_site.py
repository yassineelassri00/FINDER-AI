"""
Migration de données : dédoublonnage des OutilIA avant la contrainte unique.

Cette étape de nettoyage s'exécute OBLIGATOIREMENT avant la migration 0011 qui
applique `unique=True` sur OutilIA.url_site : une contrainte unique échoue si
des doublons subsistent.

Pour chaque groupe d'outils partageant la même URL, on conserve une entrée
canonique et on rattache ses dépendances (Avis, Projets, Favoris, Tags) avant
de supprimer les doublons.

IMPORTANT — exécution en production :
    python manage.py migrate finder 0010
    # (les doublons sont fusionnés, rien n'est perdu)
    python manage.py migrate finder 0011
    # (la contrainte unique est appliquée sur des données propres)
"""

from django.db import migrations
from django.db.models import Count


def _choisir_canonique(groupe):
    """Retourne l'outil conservé pour un groupe partageant la même url_site.

    Critères, par ordre de priorité :
      1. outil validé (est_valide=True),
      2. provenance 'catalogue' (source de référence),
      3. id le plus ancien (stabilité des références).
    """
    valides = [o for o in groupe if o.est_valide]
    if valides:
        catalogue = [o for o in valides if o.provenance == "catalogue"]
        if catalogue:
            return min(catalogue, key=lambda o: o.id)
        return min(valides, key=lambda o: o.id)
    catalogue = [o for o in groupe if o.provenance == "catalogue"]
    if catalogue:
        return min(catalogue, key=lambda o: o.id)
    return min(groupe, key=lambda o: o.id)


def _fusionner_avis(duplicata, canonique, Avis):
    """Déplace les avis du duplicata vers l'outil canonique.

    Respecte la contrainte unique (outil, user) : si l'utilisateur a déjà noté
    l'outil canonique, on conserve la note la plus élevée.
    """
    for avis in Avis.objects.filter(outil_id=duplicata.pk):
        existant = None
        if avis.user_id:
            existant = Avis.objects.filter(
                outil_id=canonique.pk, user_id=avis.user_id
            ).first()
        if existant is None:
            avis.outil_id = canonique.pk
            avis.save()
        elif avis.note > existant.note:
            existant.note = avis.note
            existant.commentaire = avis.commentaire
            existant.save()
            avis.delete()
        else:
            avis.delete()


def dedupliquer_outils_url_site(apps, schema_editor):
    """Fusionne les outils partageant la même URL, puis supprime les doublons."""
    OutilIA = apps.get_model("finder", "OutilIA")
    Avis = apps.get_model("finder", "Avis")

    groupes_doublons = (
        OutilIA.objects.values("url_site")
        .annotate(nombre=Count("id"))
        .filter(nombre__gt=1)
    )

    for entree in groupes_doublons:
        groupe = list(OutilIA.objects.filter(url_site=entree["url_site"]))
        canonique = _choisir_canonique(groupe)

        for duplicata in (o for o in groupe if o.pk != canonique.pk):
            # 1) Avis : déplacement / fusion (contrainte unique outil+user)
            _fusionner_avis(duplicata, canonique, Avis)

            # 2) Projets : rattacher l'outil canonique, retirer le doublon
            for projet in duplicata.projets.all():
                projet.outils.add(canonique)
                projet.outils.remove(duplicata)

            # 3) Favoris : transférer les utilisateurs
            for utilisateur in duplicata.favoris.all():
                canonique.favoris.add(utilisateur)

            # 4) Tags : transférer les étiquettes
            canonique.tags.add(*duplicata.tags.all())

            # 5) Suppression du doublon (les m2m résiduelles partent en cascade)
            duplicata.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("finder", "0009_outilia_provenance"),
    ]

    operations = [
        migrations.RunPython(dedupliquer_outils_url_site, migrations.RunPython.noop),
    ]
