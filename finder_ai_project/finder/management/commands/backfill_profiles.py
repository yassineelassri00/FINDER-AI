"""
Commande de management — Rattrapage des UserProfile manquants (Bug B7).

Parcourt tous les comptes `User` existants et crée un `UserProfile` minimal
pour ceux qui n'en possèdent pas encore.

Corrige définitivement l'erreur 404 "Profil utilisateur introuvable" qui
survenait sur /api/activer-plus/ (et ailleurs) pour les comptes créés avant
l'introduction du signal `post_save` de création de profil.

Usage :
  python manage.py backfill_profiles
  python manage.py backfill_profiles --dry-run
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from finder.models import UserProfile


class Command(BaseCommand):
    help = (
        "Crée un UserProfile pour chaque User qui n'en possède pas encore "
        "(corrige l'erreur 404 de l'activation du Plan Plus)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les comptes concernés sans rien créer en base.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        users_sans_profil = (
            User.objects.filter(finder_profile__isnull=True)
            .order_by("id")
            .distinct()
        )

        total = users_sans_profil.count()
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Aucun compte sans profil : la base est déjà saine."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(f"{total} compte(s) sans profil trouvé(s).")
        )

        if options["dry_run"]:
            for user in users_sans_profil.iterator():
                self.stdout.write(
                    f"  - #{user.pk} {user.username} ({user.email or 'sans email'})"
                )
            self.stdout.write(
                self.style.WARNING(
                    "Mode --dry-run : aucune modification n'a été effectuée."
                )
            )
            return

        crees = 0
        with transaction.atomic():
            for user in users_sans_profil.iterator():
                # Filet de sécurité : ignore les profils créés entre-temps.
                if UserProfile.objects.filter(user=user).exists():
                    continue
                nom = f"{user.first_name} {user.last_name}".strip() or user.username
                UserProfile.objects.create(
                    user=user,
                    full_name=nom,
                    job_role="other",
                    onboarding_completed=True,
                )
                crees += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{crees} profil(s) créé(s) avec succès "
                f"(compteur de recherches initialisé à "
                f"{UserProfile._meta.get_field('recherches_restantes').default})."
            )
        )
