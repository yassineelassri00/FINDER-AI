"""
Modèles de données de l'application Finder-AI.

Hiérarchie :
  Categorie / Tag  ──►  OutilIA  ──►  Avis
  User             ──►  UserProfile (onboarding + abonnement)
  User             ──►  Projet (collections d'outils)
  User             ──►  FichierContexte (uploads serveur)
  ResearchJob      ──►  ResearchResult  ──►  Source
  ScraperLog       (journal des exécutions du robot)
  CodeAccesPlus    (codes d'invitation pour Plan Plus gratuit)
"""

import hashlib
import os

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg

from django.conf import settings as django_settings


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------

def _upload_context_path(instance, filename):
    """Calcule un chemin d'enregistrement propre pour les fichiers de contexte."""
    ext = os.path.splitext(filename)[1].lower()
    # Nom de fichier = hash MD5 de l'original pour éviter les doublons et les
    # caractères dangereux dans les noms de fichiers.
    safe_name = f"{instance.hash_md5}{ext}"
    return f"uploads/context/{instance.user.id}/{safe_name}"


def _upload_attachment_path(instance, filename):
    """Calcule un chemin d'enregistrement pour les pièces jointes de recherche."""
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"{instance.hash_md5}{ext}"
    return f"uploads/attachments/{instance.user.id}/{safe_name}"


# ---------------------------------------------------------------------------
# Catalogue : Catégorie et Tag
# ---------------------------------------------------------------------------

class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.nom


class Tag(models.Model):
    nom = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


# ---------------------------------------------------------------------------
# Outil IA (cœur du catalogue)
# ---------------------------------------------------------------------------

class OutilIA(models.Model):
    PROVENANCE_CHOICES = [
        ("catalogue", "Catalogue officiel"),
        ("scraper", "Robot de scraping"),
        ("community", "Communauté"),
    ]

    nom = models.CharField(max_length=200)
    description = models.TextField()
    url_site = models.URLField()
    type_tarification = models.CharField(max_length=100)
    type_integration = models.CharField(max_length=100)
    date_ajout = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    provenance = models.CharField(
        max_length=20,
        choices=PROVENANCE_CHOICES,
        default="catalogue",
        verbose_name="Provenance de l'outil",
        help_text="Origine de l'entrée : catalogue officiel, robot de scraping ou communauté.",
        db_index=True,
    )
    est_valide = models.BooleanField(
        default=True,
        verbose_name="Est validé par l'admin",
        db_index=True,
    )
    soumis_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outils_soumis",
    )
    favoris = models.ManyToManyField(User, related_name="outils_favoris", blank=True)
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.SET_NULL,
        null=True,
        related_name="outils",
        db_index=True,
    )
    tags = models.ManyToManyField(Tag, related_name="outils", blank=True)

    class Meta:
        ordering = ["-date_ajout"]
        verbose_name = "Outil IA"
        verbose_name_plural = "Outils IA"

    # ------------------------------------------------------------------
    # Propriété d'alias pour compatibilité avec les tests existants
    # ------------------------------------------------------------------

    @property
    def is_approved(self):
        return self.est_valide

    @is_approved.setter
    def is_approved(self, val):
        self.est_valide = val

    # ------------------------------------------------------------------
    # Score moyen basé sur les avis
    # ------------------------------------------------------------------

    def calculer_score(self):
        """Retourne la note moyenne (0.0 si aucun avis)."""
        resultat = self.avis.aggregate(moyenne=Avg("note"))["moyenne"]
        return round(resultat, 1) if resultat is not None else 0.0

    def __str__(self):
        return self.nom


# ---------------------------------------------------------------------------
# Avis et évaluations
# ---------------------------------------------------------------------------

class Avis(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="avis", null=True, blank=True
    )
    auteur = models.CharField(max_length=100)
    note = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    outil = models.ForeignKey(OutilIA, on_delete=models.CASCADE, related_name="avis")

    class Meta:
        # Un utilisateur ne peut noter qu'une seule fois le même outil
        unique_together = ("outil", "user")
        ordering = ["-date_creation"]

    def __str__(self):
        nom_auteur = self.user.username if self.user else self.auteur
        return f"Avis de {nom_auteur} sur {self.outil.nom}"


# ---------------------------------------------------------------------------
# Projets personnalisés (collections d'outils)
# ---------------------------------------------------------------------------

class Projet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projets")
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    outils = models.ManyToManyField(OutilIA, related_name="projets", blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Projet"

    def __str__(self):
        return f"Projet '{self.nom}' de {self.user.username}"


# ---------------------------------------------------------------------------
# Journal du robot de Web Scraping
# ---------------------------------------------------------------------------

class ScraperLog(models.Model):
    date_execution = models.DateTimeField(auto_now_add=True)
    total_extraits = models.IntegerField(default=0)
    temps_execution = models.FloatField(
        default=0.0, help_text="Durée d'exécution en secondes"
    )
    erreurs = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-date_execution"]
        verbose_name = "Journal de scraping"
        verbose_name_plural = "Journaux de scraping"

    def __str__(self):
        return f"Scraping du {self.date_execution.strftime('%Y-%m-%d %H:%M')}"


# ---------------------------------------------------------------------------
# Recherche Web IA (Tavily) — Jobs et résultats
# ---------------------------------------------------------------------------

class ResearchJob(models.Model):
    STATUS_CHOICES = [
        ("pending",   "En attente"),
        ("searching", "Recherche en cours"),
        ("ranking",   "Classement en cours"),
        ("completed", "Terminé"),
        ("failed",    "Échec"),
    ]

    query = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    summary = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tâche de recherche"

    def __str__(self):
        return f"{self.query} — {self.status}"


class ResearchResult(models.Model):
    research_job = models.ForeignKey(
        ResearchJob, on_delete=models.CASCADE, related_name="results"
    )
    rank = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=300)
    summary = models.TextField()
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rank"]
        verbose_name = "Résultat de recherche"

    def __str__(self):
        return f"#{self.rank} — {self.title}"


class Source(models.Model):
    research_result = models.ForeignKey(
        ResearchResult, on_delete=models.CASCADE, related_name="sources"
    )
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000)
    domain = models.CharField(max_length=255)
    excerpt = models.TextField(blank=True)
    published_at = models.DateField(null=True, blank=True)
    authority_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    retrieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-authority_score"]

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Profil utilisateur (onboarding + abonnement)
# ---------------------------------------------------------------------------

class UserProfile(models.Model):
    RESULT_STYLE_CHOICES = [
        ("decision",  "Décision rapide"),
        ("balanced",  "Vue équilibrée"),
        ("detailed",  "Analyse détaillée"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="finder_profile"
    )
    full_name = models.CharField(max_length=150)
    organization = models.CharField(max_length=150, blank=True)
    job_role = models.CharField(max_length=100)
    experience_level = models.CharField(max_length=50, blank=True)
    goals = models.JSONField(default=list, blank=True)
    research_sources = models.JSONField(default=list, blank=True)
    technology_stack = models.JSONField(default=list, blank=True)
    budget_preference = models.CharField(max_length=50, blank=True)
    professional_context = models.TextField(blank=True)
    gemini_api_key = models.CharField(max_length=255, blank=True)
    search_preferences = models.JSONField(default=dict, blank=True)
    ui_preferences = models.JSONField(default=dict, blank=True)
    result_style = models.CharField(
        max_length=20, choices=RESULT_STYLE_CHOICES, default="balanced"
    )
    preferred_language = models.CharField(max_length=10, default="fr")
    watch_frequency = models.CharField(max_length=30, default="on_demand")
    onboarding_completed = models.BooleanField(default=True)

    # --- Abonnement Finder Plus (activé par code d'invitation, gratuit) ---
    est_abonne_plus = models.BooleanField(
        default=False,
        verbose_name="Abonné Finder Plus",
        help_text="Activé via un code d'invitation gratuit.",
    )
    code_plus_utilise = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Code Plus utilisé",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil Finder-AI de {self.user.username}"


# ---------------------------------------------------------------------------
# Fichiers de contexte (uploads serveur sécurisés)
# ---------------------------------------------------------------------------

def _validate_extension(value):
    """Valide que l'extension du fichier est dans la liste autorisée."""
    from finder.services.files import extension_autorisee

    if not extension_autorisee(value.name):
        allowed = sorted(getattr(django_settings, "UPLOAD_ALLOWED_EXTENSIONS", set()))
        raise ValidationError(
            f"Extension '{os.path.splitext(value.name)[1].lower()}' non autorisée. "
            f"Extensions acceptées : " + ", ".join(allowed)
        )


def _validate_taille(value):
    """Valide que le fichier ne dépasse pas la taille maximale autorisée."""
    from finder.services.files import taille_autorisee

    max_size = getattr(django_settings, "UPLOAD_MAX_SIZE_BYTES", 10 * 1024 * 1024)
    if not taille_autorisee(value.size):
        max_mo = max_size // (1024 * 1024)
        raise ValidationError(
            f"Le fichier est trop volumineux ({value.size // 1024} Ko). "
            f"Taille maximale autorisée : {max_mo} Mo."
        )


class FichierContexte(models.Model):
    """Fichier téléversé par un utilisateur et associé à ses projets de recherche."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="fichiers_contexte"
    )
    projet = models.ForeignKey(
        Projet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fichiers",
        help_text="Projet auquel ce fichier est associé (facultatif).",
    )
    nom_original = models.CharField(
        max_length=255, help_text="Nom original du fichier avant téléversement."
    )
    fichier = models.FileField(
        upload_to=_upload_context_path,
        validators=[_validate_extension, _validate_taille],
    )
    extension = models.CharField(max_length=20)
    taille_octets = models.BigIntegerField(default=0)
    hash_md5 = models.CharField(
        max_length=32,
        blank=True,
        help_text="Hash MD5 du contenu — empêche les doublons.",
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_ajout"]
        verbose_name = "Fichier de contexte"
        verbose_name_plural = "Fichiers de contexte"

    def __str__(self):
        return f"{self.nom_original} ({self.user.username})"

    @classmethod
    def calculer_md5(cls, fichier_django):
        """Calcule le MD5 d'un InMemoryUploadedFile sans le lire deux fois."""
        md5 = hashlib.md5()
        for chunk in fichier_django.chunks():
            md5.update(chunk)
        fichier_django.seek(0)
        return md5.hexdigest()


# ---------------------------------------------------------------------------
# Codes d'accès gratuits au Plan Finder Plus
# ---------------------------------------------------------------------------

class CodeAccesPlus(models.Model):
    """Code d'invitation permettant d'activer gratuitement le Plan Finder Plus."""

    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Description interne (ex: 'Lot stage EMSI 2026').",
    )
    max_utilisations = models.PositiveIntegerField(
        default=1,
        help_text="Nombre maximum d'activations autorisées pour ce code.",
    )
    utilisations_actuelles = models.PositiveIntegerField(default=0)
    est_actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Laisser vide pour un code sans date d'expiration.",
    )

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Code d'accès Plus"
        verbose_name_plural = "Codes d'accès Plus"

    def est_valide(self):
        """Retourne True si le code peut encore être utilisé."""
        from django.utils import timezone

        if not self.est_actif:
            return False
        if self.utilisations_actuelles >= self.max_utilisations:
            return False
        if self.date_expiration and timezone.now() > self.date_expiration:
            return False
        return True

    def __str__(self):
        return f"{self.code} ({self.utilisations_actuelles}/{self.max_utilisations})"
