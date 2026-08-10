"""
Configuration de l'interface d'administration Django pour Finder-AI.

Tous les modèles de l'application sont enregistrés ici avec des options
adaptées à la gestion quotidienne (filtres, recherche, champs modifiables).
"""

from django.contrib import admin

from .models import (
    Avis,
    Categorie,
    CodeAccesPlus,
    FichierContexte,
    OutilIA,
    Projet,
    ResearchJob,
    ResearchResult,
    ScraperLog,
    Source,
    Tag,
    UserProfile,
)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "slug")
    prepopulated_fields = {"slug": ("nom",)}
    search_fields = ("nom",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "slug")
    prepopulated_fields = {"slug": ("nom",)}
    search_fields = ("nom",)


@admin.register(OutilIA)
class OutilIAAdmin(admin.ModelAdmin):
    list_display = (
        "id", "nom", "categorie", "type_tarification",
        "type_integration", "provenance", "est_valide", "soumis_par", "date_ajout",
    )
    list_filter = (
        "est_valide", "provenance", "categorie", "type_tarification", "type_integration"
    )
    search_fields = ("nom", "description", "url_site")
    list_editable = ("est_valide",)
    readonly_fields = ("date_ajout", "modified_at")
    filter_horizontal = ("tags", "favoris")


# ---------------------------------------------------------------------------
# Avis
# ---------------------------------------------------------------------------

@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = ("id", "outil", "auteur", "user", "note", "date_creation")
    list_filter = ("note", "date_creation")
    search_fields = ("auteur", "commentaire", "outil__nom")
    readonly_fields = ("date_creation",)


# ---------------------------------------------------------------------------
# Projets
# ---------------------------------------------------------------------------

@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "user", "date_creation")
    search_fields = ("nom", "user__username")
    readonly_fields = ("date_creation",)
    filter_horizontal = ("outils",)


# ---------------------------------------------------------------------------
# Journal de scraping
# ---------------------------------------------------------------------------

@admin.register(ScraperLog)
class ScraperLogAdmin(admin.ModelAdmin):
    list_display = ("id", "date_execution", "total_extraits", "temps_execution")
    readonly_fields = ("date_execution", "total_extraits", "temps_execution", "erreurs")

    def has_add_permission(self, request):
        return False  # Les logs sont créés automatiquement, jamais manuellement


# ---------------------------------------------------------------------------
# Recherche Web IA
# ---------------------------------------------------------------------------

@admin.register(ResearchJob)
class ResearchJobAdmin(admin.ModelAdmin):
    list_display = ("id", "query", "status", "created_at", "completed_at")
    list_filter = ("status", "created_at")
    search_fields = ("query",)
    readonly_fields = ("created_at", "completed_at")

    def has_add_permission(self, request):
        return False


@admin.register(ResearchResult)
class ResearchResultAdmin(admin.ModelAdmin):
    list_display = ("rank", "title", "score", "research_job", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "summary")
    ordering = ("research_job", "rank")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("title", "domain", "authority_score", "research_result", "published_at")
    list_filter = ("domain", "published_at")
    search_fields = ("title", "domain", "url")

    def has_add_permission(self, request):
        return False


# ---------------------------------------------------------------------------
# Profils utilisateurs
# ---------------------------------------------------------------------------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user", "full_name", "job_role", "organization",
        "result_style", "est_abonne_plus", "created_at",
    )
    list_filter = ("job_role", "result_style", "preferred_language", "est_abonne_plus")
    search_fields = ("user__username", "full_name", "organization")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Fichiers de contexte
# ---------------------------------------------------------------------------

@admin.register(FichierContexte)
class FichierContexteAdmin(admin.ModelAdmin):
    list_display = ("id", "nom_original", "user", "extension", "taille_octets", "date_ajout")
    list_filter = ("extension", "date_ajout")
    search_fields = ("nom_original", "user__username")
    readonly_fields = ("date_ajout", "hash_md5", "taille_octets", "extension")

    def has_add_permission(self, request):
        return False  # Les fichiers sont créés uniquement via l'API upload


# ---------------------------------------------------------------------------
# Codes d'accès Plan Plus
# ---------------------------------------------------------------------------

@admin.register(CodeAccesPlus)
class CodeAccesPlusAdmin(admin.ModelAdmin):
    list_display = (
        "code", "description", "max_utilisations",
        "utilisations_actuelles", "est_actif", "date_expiration",
    )
    list_filter = ("est_actif",)
    search_fields = ("code", "description")
    readonly_fields = ("date_creation", "utilisations_actuelles")
