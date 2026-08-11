"""
Routage URL de l'application Finder-AI.

Structure :
  /                          — Page d'accueil / splash screen
  /app/                      — Workspace principal (authentification requise)
  /login/ /register/ /logout/  — Authentification
  /admin-dashboard/          — Tableau de bord administrateur (is_staff)
  /reset-password/…          — Réinitialisation du mot de passe (vues Django natives)

  /api/outils/               — Catalogue JSON + recherche + pagination
  /api/outils/<id>/avis/     — Dépôt d'avis
  /api/outils/proposer/      — Soumission d'un nouvel outil
  /api/outils/<id>/favoris/  — Toggle favori
  /api/projets/              — Liste et création de projets personnalisés
  /api/research/             — Recherche Web IA via Tavily
  /api/settings/             — Mise à jour du profil utilisateur
  /api/fichiers/upload/      — Téléversement d'un fichier de contexte
  /api/fichiers/             — Liste des fichiers de contexte
  /api/fichiers/<id>/        — Suppression d'un fichier de contexte
  /api/activer-plus/         — Activation du Plan Plus par code d'invitation

  /media/…                   — Fichiers médias (servi par Django en développement)
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path

from . import api_views, views

urlpatterns = [
    # ------------------------------------------------------------------
    # Vues HTML (navigation)
    # ------------------------------------------------------------------
    path("", views.landing, name="landing"),
    path("app/", views.liste_outils, name="liste_outils"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # ------------------------------------------------------------------
    # Réinitialisation du mot de passe (vues Django natives)
    # ------------------------------------------------------------------
    path(
        "reset-password/",
        auth_views.PasswordResetView.as_view(
            template_name="finder/password_reset.html"
        ),
        name="password_reset",
    ),
    path(
        "reset-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="finder/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset-password/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="finder/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset-password/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="finder/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # ------------------------------------------------------------------
    # API JSON — Catalogue, Avis, Favoris, Projets
    # ------------------------------------------------------------------
    path("api/outils/", api_views.api_outils_list, name="api_outils_list"),
    path("api/recherche/", api_views.api_recherche_workspace, name="api_recherche_workspace"),
    path(
        "api/outils/<int:outil_id>/avis/",
        api_views.api_ajouter_avis,
        name="api_ajouter_avis",
    ),
    path(
        "api/outils/proposer/",
        api_views.api_proposer_outil,
        name="api_proposer_outil",
    ),
    path(
        "api/outils/<int:outil_id>/favoris/",
        api_views.api_toggle_favoris,
        name="api_toggle_favoris",
    ),
    path("api/projets/", api_views.api_projets_list_create, name="api_projets_list_create"),

    # ------------------------------------------------------------------
    # API JSON — Recherche Web IA (Tavily)
    # ------------------------------------------------------------------
    path("api/research/", api_views.ResearchStartAPIView.as_view(), name="research_start"),
    path("api/quota/", api_views.api_quota, name="api_quota"),

    # ------------------------------------------------------------------
    # API JSON — Paramètres utilisateur
    # ------------------------------------------------------------------
    path("api/settings/", views.update_settings, name="update_settings"),

    # ------------------------------------------------------------------
    # API JSON — Gestion des fichiers de contexte (upload serveur)
    # ------------------------------------------------------------------
    path("api/fichiers/upload/", api_views.api_upload_fichier, name="api_upload_fichier"),
    path("api/fichiers/", api_views.api_liste_fichiers, name="api_liste_fichiers"),
    path(
        "api/fichiers/<int:fichier_id>/",
        api_views.api_supprimer_fichier,
        name="api_supprimer_fichier",
    ),

    # ------------------------------------------------------------------
    # API JSON — Plan Finder Plus (activation par code d'invitation)
    # ------------------------------------------------------------------
    path("api/activer-plus/", api_views.api_activer_plus, name="api_activer_plus"),
]

# En développement, Django sert lui-même les fichiers médias (MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
