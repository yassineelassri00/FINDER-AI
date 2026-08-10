"""
Signaux Django pour l'application Finder-AI.

Signaux déclarés :
  - post_save sur OutilIA : invalide l'index sémantique en mémoire lorsqu'un
    outil est créé ou modifié, afin que la prochaine recherche reconstruise un
    index à jour.
  - post_save sur User    : crée automatiquement un UserProfile vide lorsqu'un
    utilisateur est créé directement via l'interface Django Admin (les inscriptions
    via le formulaire de l'application créent déjà le profil dans register_view).
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="finder.OutilIA")
def invalider_index_semantique(sender, instance, **kwargs):
    """
    Invalide l'index TF-IDF en mémoire après toute modification d'un OutilIA.
    La prochaine requête de recherche sémantique reconstruira automatiquement
    l'index depuis la base de données.
    """
    try:
        from finder.services.vector_search import invalider_index
        invalider_index()
    except Exception:
        # Ne jamais faire planter une sauvegarde d'outil à cause du cache
        pass


@receiver(post_save, sender=User)
def creer_profil_utilisateur_admin(sender, instance, created, **kwargs):
    """
    Crée un UserProfile minimal lorsqu'un compte est créé depuis l'Admin Django.
    (Le formulaire d'inscription de l'application crée le profil complet dans
    register_view — ce signal gère uniquement les comptes créés via Admin.)
    """
    if not created:
        return

    from finder.models import UserProfile

    if not UserProfile.objects.filter(user=instance).exists():
        UserProfile.objects.create(
            user=instance,
            full_name=f"{instance.first_name} {instance.last_name}".strip()
            or instance.username,
            job_role="other",
        )
