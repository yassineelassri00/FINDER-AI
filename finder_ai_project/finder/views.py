"""
Vues HTML de l'application Finder-AI.

Vues disponibles :
  landing()         — Page d'accueil / splash screen (auth.html)
  login_view()      — Connexion utilisateur
  register_view()   — Inscription avec création du profil complet
  logout_view()     — Déconnexion
  liste_outils()    — Workspace principal Finder-AI (authentification requise)
  update_settings() — Endpoint AJAX de mise à jour du profil
  admin_dashboard() — Tableau de bord de modération (is_staff uniquement)

Gestionnaires d'erreurs globaux :
  handler_404()     — Page / réponse JSON pour les routes introuvables
  handler_500()     — Page / réponse JSON pour les erreurs serveur internes
"""

import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Avis, Categorie, OutilIA, Tag, UserProfile


# ---------------------------------------------------------------------------
# Normalisation des préférences d'inscription
# ---------------------------------------------------------------------------
# Le formulaire d'onboarding envoie les multi-sélections (cases à cocher)
# sous forme d'une chaîne jointe par des virgules (ex. "discover,evaluate").
# Ces helpers découpent cette chaîne en une vraie liste Python et alignent
# les valeurs de l'onboarding sur le vocabulaire utilisé par les paramètres.

def _split_multi(values):
    """Transforme une valeur multi-champs en liste propre et dédoublonnée.

    Accepte une chaîne "a,b,c" ou une liste (getlist), découpe sur les
    virgules, nettoie les espaces, ignore les vides et limite à 12 éléments.
    """
    if isinstance(values, (list, tuple)):
        items = []
        for value in values:
            items.extend(str(value).split(","))
    else:
        items = str(values or "").split(",")

    result = []
    for item in items:
        item = item.strip()
        if item and item not in result:
            result.append(item)
    return result[:12]


def _normaliser_goals(values):
    """Aligne les objectifs de l'onboarding sur les catégories des paramètres."""
    mapping = {
        "discover": "research",
        "evaluate": "research",
        "build": "code",
        "watch": "watch",
    }
    result = []
    for value in _split_multi(values):
        canonical = mapping.get(value, value)
        if canonical and canonical not in result:
            result.append(canonical)
    return result[:12]


def _normaliser_budget(value):
    """Traduit la préférence budgétaire de l'onboarding en libellé des paramètres."""
    mapping = {
        "free": "Gratuit",
        "freemium": "Freemium",
        "paid": "Payant",
        "enterprise": "Payant",
    }
    valeur = (value or "").strip()
    return mapping.get(valeur, valeur)


def _normaliser_style(value):
    """Traduit le style de réponse ("expert" n'existe pas dans les paramètres)."""
    valeur = (value or "balanced").strip()
    return "detailed" if valeur == "expert" else (valeur or "balanced")


def _normaliser_langue(value):
    """Traduit la langue libre de l'onboarding en code (fr/en)."""
    valeur = (value or "").strip().lower()
    if "anglais" in valeur or "english" in valeur or valeur == "en":
        return "en"
    return "fr"


def _normaliser_frequence(value):
    """Traduit le rythme de veille de l'onboarding en code des paramètres."""
    valeur = (value or "").strip().lower()
    if "quotidien" in valeur or valeur == "daily":
        return "daily"
    if "hebdomadaire" in valeur or valeur == "weekly":
        return "weekly"
    if "mensuel" in valeur or valeur == "monthly":
        return "weekly"
    return "on_demand"


def _normaliser_job_role(value):
    """Aligne le métier libre de l'onboarding sur les options des paramètres."""
    valeur = (value or "").strip().lower()
    if "front" in valeur:
        return "frontend"
    if "back" in valeur:
        return "backend"
    if "full" in valeur:
        return "fullstack"
    if any(k in valeur for k in ("machine", "data", "ml", " ai")):
        return "ai_engineer"
    if any(k in valeur for k in ("product", "manager", "chef de projet", "lead", "cto")):
        return "product"
    if any(k in valeur for k in ("devops", "sre", "cloud")):
        return "backend"
    if "architecte" in valeur:
        return "fullstack"
    return (value or "").strip() or "other"


# ---------------------------------------------------------------------------
# Page d'accueil / splash screen
# ---------------------------------------------------------------------------

def landing(request):
    """
    Page d'entrée publique.
    Affiche toujours le splash screen (auth.html), qu'il soit connecté ou non.
    Le template adapte son contenu selon `already_authenticated`.
    """
    return render(
        request,
        "finder/auth.html",
        {"already_authenticated": request.user.is_authenticated},
    )


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

@require_http_methods(["POST"])
def login_view(request):
    """Traite le formulaire de connexion (POST uniquement)."""
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    user = authenticate(request, username=username, password=password)

    if user is None:
        messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
        return redirect("landing")

    login(request, user)
    return redirect("liste_outils")


@require_http_methods(["POST"])
def register_view(request):
    """
    Traite le formulaire d'inscription (POST uniquement).
    Crée l'utilisateur et son profil complet dans une transaction atomique.
    """
    full_name             = request.POST.get("full_name", "").strip()
    username              = request.POST.get("username", "").strip()
    email                 = request.POST.get("email", "").strip().lower()
    password              = request.POST.get("password", "")
    password_confirmation = request.POST.get("password_confirmation", "")

    # --- Validations ---
    if not all([full_name, username, email, password]):
        messages.error(request, "Complétez vos informations d'identité pour créer le compte.")
        return redirect("landing")
    if password != password_confirmation:
        messages.error(request, "Les deux mots de passe ne correspondent pas.")
        return redirect("landing")
    if len(password) < 8:
        messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
        return redirect("landing")
    if User.objects.filter(email=email).exists():
        messages.error(request, "Cette adresse e-mail est déjà associée à un compte.")
        return redirect("landing")

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": full_name,
                    "organization": request.POST.get("organization", "").strip(),
                    "job_role": _normaliser_job_role(request.POST.get("job_role", "")),
                    "experience_level": request.POST.get("experience_level", "").strip(),
                    "goals": _normaliser_goals(request.POST.getlist("goals")),
                    "research_sources": _split_multi(request.POST.getlist("research_sources")),
                    "technology_stack": _split_multi(request.POST.getlist("technology_stack")),
                    "budget_preference": _normaliser_budget(
                        request.POST.get("budget_preference", "")
                    ),
                    "result_style": _normaliser_style(
                        request.POST.get("result_style", "balanced")
                    ),
                    "preferred_language": _normaliser_langue(
                        request.POST.get("preferred_language", "")
                    ),
                    "watch_frequency": _normaliser_frequence(
                        request.POST.get("watch_frequency", "")
                    ),
                }
            )
    except IntegrityError:
        messages.error(
            request,
            "Ce nom d'utilisateur est déjà utilisé. Choisissez-en un autre.",
        )
        return redirect("landing")

    # backend explicite : plusieurs backends configurés (ModelBackend + AxesStandaloneBackend)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "Votre espace Finder-AI est prêt.")
    return redirect("liste_outils")


@require_http_methods(["POST"])
def logout_view(request):
    """Déconnecte l'utilisateur et redirige vers la page d'accueil."""
    logout(request)
    return redirect("landing")


# ---------------------------------------------------------------------------
# Workspace principal
# ---------------------------------------------------------------------------

@login_required
def liste_outils(request):
    """
    Vue principale du Workspace Finder-AI.
    Passe au template les outils validés, les catégories, les tags et le profil.
    La recherche et le filtrage réels se font via l'API JSON /api/outils/.
    """
    outils = (
        OutilIA.objects.filter(est_valide=True)
        .select_related("categorie")
        .prefetch_related("tags", "avis")
    )
    categories = Categorie.objects.all()
    tags = Tag.objects.all()
    profile = getattr(request.user, "finder_profile", None)

    return render(
        request,
        "finder/liste_outils.html",
        {
            "outils": outils,
            "categories": categories,
            "tags": tags,
            "profile": profile,
        },
    )


# ---------------------------------------------------------------------------
# Mise à jour du profil utilisateur (endpoint AJAX)
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def update_settings(request):
    """
    GET  /api/settings/  — Retourne les préférences NON sensibles du profil.
    POST /api/settings/  — Corps JSON : {"section": "profil"|"preferences", ...}
    Sauvegarde les paramètres du profil et des préférences en base de données.
    """
    # GET : la clé API Gemini n'est JAMAIS renvoyée au client (ni en HTML,
    # ni en JSON) : elle ne transite plus jamais vers le navigateur (Bug S4).
    # Elle ne peut être ni lue ni affichée : uniquement remplacée (voir POST).
    if request.method == "GET":
        profile = getattr(request.user, "finder_profile", None)
        return JsonResponse(
            {
                "ok": True,
                "est_abonne_plus": bool(profile and profile.est_abonne_plus),
                "search_preferences": profile.search_preferences if profile else {},
                "ui_preferences": profile.ui_preferences if profile else {},
            }
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ok": False, "error": "Données invalides."}, status=400)

    section = data.get("section", "")
    profile = getattr(request.user, "finder_profile", None)

    if section == "profil":
        full_name    = data.get("full_name", "").strip()
        email        = data.get("email", "").strip().lower()
        organization = data.get("organization", "").strip()
        job_role     = data.get("job_role", "")
        preferred_language = data.get("preferred_language", "")
        professional_context = data.get("professional_context", "").strip()
        valid_languages = {"fr", "en"}

        if email and email != request.user.email:
            if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                return JsonResponse(
                    {"ok": False, "error": "Cet email est déjà utilisé."}, status=409
                )
            request.user.email = email
            request.user.save(update_fields=["email"])

        if profile:
            if full_name:
                profile.full_name = full_name
            if organization is not None:
                profile.organization = organization
            if job_role:
                profile.job_role = job_role
            if preferred_language in valid_languages:
                profile.preferred_language = preferred_language
            profile.professional_context = professional_context
            profile.save(
                update_fields=[
                    "full_name",
                    "organization",
                    "job_role",
                    "preferred_language",
                    "professional_context",
                ]
            )

        return JsonResponse(
            {
                "ok": True,
                "message": "Profil mis à jour.",
                "full_name": profile.full_name if profile else full_name,
            }
        )

    if section == "preferences":
        result_style       = data.get("result_style", "")
        preferred_language = data.get("preferred_language", "")
        budget_preference  = data.get("budget_preference", "")
        watch_frequency    = data.get("watch_frequency", "")
        gemini_api_key     = data.get("gemini_api_key", "").strip()
        goals              = data.get("goals", [])
        research_sources   = data.get("research_sources", [])
        technology_stack   = data.get("technology_stack", [])
        search_preferences = data.get("search_preferences", {})
        ui_preferences     = data.get("ui_preferences", {})
        valid_styles    = {"decision", "balanced", "detailed"}
        valid_languages = {"fr", "en"}
        valid_budget    = {"", "all", "Gratuit", "Freemium", "Payant", "Open-source", "Open-Source"}
        valid_frequency = {"on_demand", "daily", "weekly"}

        def _clean_list(value):
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()][:12]

        def _clean_dict(value):
            return value if isinstance(value, dict) else {}

        if profile:
            if result_style in valid_styles:
                profile.result_style = result_style
            if preferred_language in valid_languages:
                profile.preferred_language = preferred_language
            if budget_preference in valid_budget:
                profile.budget_preference = budget_preference
            if watch_frequency in valid_frequency:
                profile.watch_frequency = watch_frequency
            profile.goals = _clean_list(goals)
            profile.research_sources = _clean_list(research_sources)
            profile.technology_stack = _clean_list(technology_stack)
            profile.search_preferences = _clean_dict(search_preferences)
            profile.ui_preferences = _clean_dict(ui_preferences)
            # S4 : la clé Gemini n'est mise à jour QUE si une nouvelle valeur
            # est saisie — un champ vide ne doit jamais écraser la clé stockée.
            update_fields = [
                "result_style",
                "preferred_language",
                "budget_preference",
                "watch_frequency",
                "goals",
                "research_sources",
                "technology_stack",
                "search_preferences",
                "ui_preferences",
            ]
            if gemini_api_key:
                profile.gemini_api_key = gemini_api_key
                update_fields.append("gemini_api_key")
            profile.save(update_fields=update_fields)

        return JsonResponse({"ok": True, "message": "Préférences mises à jour."})

    return JsonResponse({"ok": False, "error": "Section inconnue."}, status=400)


# ---------------------------------------------------------------------------
# Tableau de bord Administrateur (modération)
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(lambda u: u.is_staff, login_url="landing")
def admin_dashboard(request):
    """
    Vue d'administration avec contrôle d'accès strict (RBAC is_staff).
    Permet la validation ou le refus des outils proposés par la communauté.
    """
    if request.method == "POST":
        action   = request.POST.get("action")
        outil_id = request.POST.get("outil_id")

        if action and outil_id:
            outil = get_object_or_404(OutilIA, pk=outil_id)

            if action == "valider":
                outil.est_valide = True
                outil.save()
                messages.success(
                    request,
                    f"L'outil « {outil.nom} » a été validé et publié au catalogue.",
                )
            elif action == "refuser":
                nom = outil.nom
                outil.delete()
                messages.info(
                    request,
                    f"La proposition d'outil « {nom} » a été refusée et supprimée.",
                )

        return redirect("admin_dashboard")

    # with_score() : pré-calcule la moyenne des avis (le template affiche
    # o.calculer_score par outil — évite une requête par ligne, soit N+1).
    outils_en_attente = (
        OutilIA.objects.with_score().filter(est_valide=False).order_by("-date_ajout")
    )
    outils_valides = (
        OutilIA.objects.with_score()
        .filter(est_valide=True)
        .order_by("-date_ajout")[:15]
    )

    return render(
        request,
        "finder/admin_dashboard.html",
        {
            "outils_en_attente": outils_en_attente,
            "outils_valides": outils_valides,
            "total_outils": OutilIA.objects.count(),
            "total_valides": OutilIA.objects.filter(est_valide=True).count(),
            "total_attente": outils_en_attente.count(),
            "total_avis": Avis.objects.count(),
        },
    )


# ---------------------------------------------------------------------------
# Gestionnaires d'erreurs globaux
# ---------------------------------------------------------------------------

def handler_404(request, exception=None):
    """
    Gestionnaire global pour les erreurs 404 (route introuvable).
    - Retourne du JSON si le client attend du JSON (API).
    - Retourne une page HTML sinon.
    """
    if request.headers.get("Accept", "").startswith("application/json") or \
       request.path.startswith("/api/"):
        return JsonResponse(
            {"ok": False, "error": "Ressource introuvable (404)."},
            status=404,
        )
    return render(request, "finder/404.html", status=404)


def handler_500(request):
    """
    Gestionnaire global pour les erreurs 500 (erreur interne du serveur).
    - Retourne du JSON si le client attend du JSON (API).
    - Retourne une page HTML sinon.
    """
    if request.headers.get("Accept", "").startswith("application/json") or \
       request.path.startswith("/api/"):
        return JsonResponse(
            {"ok": False, "error": "Erreur interne du serveur (500). Veuillez réessayer."},
            status=500,
        )
    return render(request, "finder/500.html", status=500)
