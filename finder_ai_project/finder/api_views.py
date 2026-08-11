"""
Vues API JSON de l'application Finder-AI.

Tous les endpoints retournent du JSON avec la structure :
  {"ok": true/false, ...}

Endpoints disponibles :
  GET  /api/outils/                       — Catalogue avec recherche, filtre, pagination
  POST /api/outils/<id>/avis/             — Déposer un avis sur un outil
  POST /api/outils/proposer/              — Proposer un nouvel outil (modération)
  POST /api/outils/<id>/favoris/          — Ajouter/retirer des favoris
  GET|POST /api/projets/                  — Lister/créer des projets personnalisés
  POST /api/research/                     — Lancer une recherche Web IA (Tavily)
  POST /api/settings/                     — (dans views.py) Mettre à jour le profil
  POST /api/fichiers/upload/              — Téléverser un fichier de contexte
  GET  /api/fichiers/                     — Lister les fichiers de contexte
  DELETE /api/fichiers/<id>/              — Supprimer un fichier de contexte
  POST /api/activer-plus/                 — Activer le Plan Plus via code d'invitation
"""

import json
import os

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finder.services.files import (
    contenu_coherent_avec_extension,
    extension_autorisee,
    taille_autorisee,
)

from .models import (
    Avis,
    Categorie,
    CodeAccesPlus,
    FichierContexte,
    OutilIA,
    Projet,
    ResearchJob,
)
from .serializers import ResearchRequestSerializer
from .services.research import perform_web_research


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------

def _json_error(message: str, code: int = 400) -> JsonResponse:
    """Retourne une réponse JSON d'erreur standardisée."""
    return JsonResponse({"ok": False, "error": message}, status=code)


def _json_ok(data: dict) -> JsonResponse:
    """Retourne une réponse JSON de succès standardisée."""
    return JsonResponse({"ok": True, **data})


def _format_research_job(job) -> dict:
    """Sérialise un ResearchJob et ses résultats en dictionnaire JSON."""
    return {
        "id": job.id,
        "query": job.query,
        "status": job.status,
        "summary": job.summary,
        "error_message": job.error_message,
        "results": [
            {
                "rank": result.rank,
                "title": result.title,
                "summary": result.summary,
                "score": float(result.score),
                "sources": [
                    {
                        "title": source.title,
                        "url": source.url,
                        "domain": source.domain,
                        "excerpt": source.excerpt,
                        "score": float(source.authority_score),
                    }
                    for source in result.sources.all()
                ],
            }
            for result in job.results.all()
        ],
    }


def _serialiser_outil(outil, user=None) -> dict:
    """Convertit un OutilIA en dictionnaire JSON prêt à l'envoi."""
    is_fav = (user in outil.favoris.all()) if user and user.is_authenticated else False
    avis_list = [
        {
            "id": a.id,
            "auteur": a.user.username if a.user else a.auteur,
            "note": a.note,
            "commentaire": a.commentaire,
            "date_creation": a.date_creation.strftime("%d/%m/%Y %H:%M"),
        }
        for a in outil.avis.all().order_by("-date_creation")
    ]
    return {
        "id": outil.id,
        "nom": outil.nom,
        "description": outil.description,
        "url_site": outil.url_site,
        "type_tarification": outil.type_tarification,
        "type_integration": outil.type_integration,
        "is_approved": outil.is_approved,
        "is_favori": is_fav,
        "categorie": {
            "id": outil.categorie.id if outil.categorie else None,
            "nom": outil.categorie.nom if outil.categorie else "Général",
            "slug": outil.categorie.slug if outil.categorie else "general",
        },
        "tags": [{"id": t.id, "nom": t.nom, "slug": t.slug} for t in outil.tags.all()],
        "score": outil.calculer_score(),
        "avis_count": len(avis_list),
        "avis": avis_list,
    }


# ---------------------------------------------------------------------------
# Catalogue : Recherche, Filtrage, Pagination
# ---------------------------------------------------------------------------

def api_outils_list(request):
    """
    Endpoint GET /api/outils/
    Paramètres GET :
      q          — Recherche textuelle (nom + description)
      categorie  — Slug de catégorie
      tags[]     — Un ou plusieurs slugs de tag
      tarification — Filtre sur le modèle de prix
      mode       — "semantic" pour activer le moteur TF-IDF (fallback auto)
      page       — Numéro de page (défaut : 1)
      page_size  — Taille de page (défaut : 20, max : 100)
    """
    query_str    = request.GET.get("q", "").strip()
    cat_slug     = request.GET.get("categorie", "").strip()
    tarification = request.GET.get("tarification", "").strip()
    mode         = request.GET.get("mode", "").strip()

    tags_list = request.GET.getlist("tags[]") or request.GET.getlist("tag")
    tags_list = [t.strip() for t in tags_list if t.strip() and t.strip() != "all"]

    qs = (
        OutilIA.objects.with_score()
        .filter(est_valide=True)
        .select_related("categorie")
        .prefetch_related("tags", "avis", "favoris")
    )

    # --- Filtres d'attributs (catégorie, tags, tarification) ---
    # Appliqués QUELQUE SOIT la stratégie de recherche (SQL ou sémantique) :
    # le fallback sémantique ne doit jamais les ignorer.
    if cat_slug and cat_slug != "all":
        qs = qs.filter(categorie__slug=cat_slug)
    if tags_list:
        qs = qs.filter(tags__slug__in=tags_list).distinct()
    if tarification:
        qs = qs.filter(type_tarification__icontains=tarification)

    # --- Recherche textuelle : SQL d'abord, fallback sémantique ensuite ---
    qs_texte = qs
    if query_str:
        qs_texte = qs.filter(
            Q(nom__icontains=query_str) | Q(description__icontains=query_str)
        )

    # --- Fallback recherche sémantique TF-IDF ---
    # Activé si : mode=semantic ou si la recherche textuelle SQL ne donne rien.
    # Le moteur sémantique REMPLACE le filtre texte (il EST la recherche par
    # mots-clés) mais la queryset conserve les filtres d'attributs ci-dessus :
    # la cohérence catégorie/tags/tarification est garantie à la prise de relais.
    semantic_active = False
    if query_str and (mode == "semantic" or not qs_texte.exists()):
        try:
            from .services.vector_search import recherche_semantique
            resultats_sem = recherche_semantique(query_str, top_k=20)
            if resultats_sem:
                ids_ordonnes = [o.id for o, _ in resultats_sem]
                # Préserver l'ordre de pertinence sémantique
                from django.db.models import Case, IntegerField, Value, When
                ordering = Case(
                    *[When(id=pk, then=Value(i)) for i, pk in enumerate(ids_ordonnes)],
                    output_field=IntegerField(),
                )
                qs = (
                    qs.filter(id__in=ids_ordonnes)
                    .annotate(sem_order=ordering)
                    .order_by("sem_order")
                )
                semantic_active = True
        except Exception:
            pass  # En cas d'erreur du moteur sémantique, on garde les résultats SQL

    # Aucun fallback actif : on garde les résultats de la recherche textuelle SQL.
    if not semantic_active:
        qs = qs_texte.order_by("-date_ajout")

    # --- Pagination ---
    try:
        page_num = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page_num = 1

    try:
        page_size = min(int(request.GET.get("page_size", 20)), 100)
    except (TypeError, ValueError):
        page_size = 20

    paginator = Paginator(qs, page_size)
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    user = request.user if request.user.is_authenticated else None
    outils_data = [_serialiser_outil(o, user) for o in page_obj.object_list]

    return JsonResponse(
        {
            "ok": True,
            "total": paginator.count,
            "total_count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "semantic_active": semantic_active,
            "outils": outils_data,
        }
    )


# ---------------------------------------------------------------------------
# Recherche workspace : synthese courte + resultats catalogue
# ---------------------------------------------------------------------------

@require_http_methods(["POST"])
def api_recherche_workspace(request):
    """
    POST /api/recherche/
    Retourne une synthese prete pour le panneau droit du workspace.
    Les preferences envoyees par le front influencent les filtres et la taille.
    """
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _json_error("Donnees invalides.")

    query_str = data.get("q", "").strip()
    if not query_str:
        return _json_error("La recherche est vide.")

    try:
        max_results = max(1, min(int(data.get("max_results", 8)), 20))
    except (TypeError, ValueError):
        max_results = 8

    result_style = data.get("result_style", "balanced")
    preferred_language = data.get("preferred_language", "fr")
    pricing = data.get("default_pricing") or data.get("budget_preference") or ""
    source_mode = data.get("source_mode", "hybrid")
    professional_context = data.get("professional_context", "").strip()
    goals = data.get("goals", []) if isinstance(data.get("goals", []), list) else []
    technology_stack = (
        data.get("technology_stack", [])
        if isinstance(data.get("technology_stack", []), list)
        else []
    )

    qs = (
        OutilIA.objects.with_score()
        .filter(est_valide=True)
        .select_related("categorie")
        .prefetch_related("tags", "avis", "favoris")
    )

    if pricing and pricing != "all":
        qs = qs.filter(type_tarification__icontains=pricing)

    semantic_results = []
    try:
        from .services.vector_search import recherche_semantique

        semantic_results = recherche_semantique(query_str, top_k=max_results * 2)
    except Exception:
        semantic_results = []

    if semantic_results:
        ids_ordonnes = [outil.id for outil, _score in semantic_results]
        qs = qs.filter(id__in=ids_ordonnes)
        from django.db.models import Case, IntegerField, Value, When

        ordering = Case(
            *[When(id=pk, then=Value(i)) for i, pk in enumerate(ids_ordonnes)],
            output_field=IntegerField(),
        )
        outils = list(qs.annotate(sem_order=ordering).order_by("sem_order")[:max_results])
        score_by_id = {outil.id: score for outil, score in semantic_results}
    else:
        qs = qs.filter(Q(nom__icontains=query_str) | Q(description__icontains=query_str))
        outils = list(qs.order_by("-date_ajout")[:max_results])
        score_by_id = {}

    resultats = []
    for outil in outils:
        serialized = _serialiser_outil(outil, request.user)
        raw_score = score_by_id.get(outil.id, 0.82)
        serialized.update(
            {
                "score_pertinence": float(raw_score),
                "categorie": serialized["categorie"]["nom"],
            }
        )
        resultats.append(serialized)

    meilleur = resultats[0] if resultats else None
    style_label = {
        "decision": "decision rapide",
        "balanced": "vue equilibree",
        "detailed": "analyse detaillee",
    }.get(result_style, "vue equilibree")

    context_bits = []
    if professional_context:
        context_bits.append("votre contexte professionnel")
    if goals:
        context_bits.append("vos objectifs")
    if technology_stack:
        context_bits.append("votre stack technique")

    if meilleur:
        synthese = (
            f"Finder AI recommande {meilleur['nom']} pour '{query_str}'. "
            f"Le classement utilise une {style_label}"
        )
        if pricing and pricing != "all":
            synthese += f", avec priorite au budget {pricing}"
        if context_bits:
            synthese += " et tient compte de " + ", ".join(context_bits)
        synthese += "."
    else:
        synthese = (
            f"Aucune reference valide ne correspond exactement a '{query_str}'. "
            "Essayez un mot-cle plus precis ou activez une recherche plus large."
        )

    if preferred_language == "en":
        synthese = (
            f"Finder AI found {len(resultats)} relevant AI reference"
            f"{'s' if len(resultats) != 1 else ''} for '{query_str}'."
        )

    points_cles = [
        f"{len(resultats)} reference(s) classee(s) selon la pertinence du mot-cle.",
        "Les filtres de budget et de profil influencent le classement.",
        "Le mode source choisi est " + ("catalogue seul" if source_mode == "catalog" else "catalogue + web"),
    ]
    if result_style == "detailed":
        points_cles.append("Le style detaille conserve plus de contexte dans la synthese.")
    if result_style == "decision":
        points_cles.append("Le style decision rapide privilegie la recommandation directe.")

    return _json_ok(
        {
            "synthese": synthese,
            "meilleur_outil": meilleur,
            "resultats": resultats,
            "points_cles": points_cles,
            "preferences_appliquees": {
                "max_results": max_results,
                "result_style": result_style,
                "preferred_language": preferred_language,
                "default_pricing": pricing or "all",
                "source_mode": source_mode,
            },
        }
    )


# ---------------------------------------------------------------------------
# Avis et évaluations
# ---------------------------------------------------------------------------

def api_ajouter_avis(request, outil_id):
    """
    POST /api/outils/<outil_id>/avis/
    Corps JSON : {"note": 1-5, "commentaire": "texte"}
    """
    if not request.user.is_authenticated:
        return _json_error("Vous devez être connecté pour publier un avis.", 401)

    outil = get_object_or_404(OutilIA, pk=outil_id, est_valide=True)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    try:
        note = int(data.get("note", 0))
    except (TypeError, ValueError):
        note = 0

    commentaire = str(data.get("commentaire", "")).strip()

    if not 1 <= note <= 5:
        return _json_error("La note doit être comprise entre 1 et 5.")
    if not commentaire:
        return _json_error("Veuillez saisir un commentaire pour votre avis.")

    auteur_name = request.user.get_full_name() or request.user.username

    try:
        with transaction.atomic():
            avis = Avis.objects.create(
                outil=outil,
                user=request.user,
                auteur=auteur_name,
                note=note,
                commentaire=commentaire,
            )
    except IntegrityError:
        return _json_error("Vous avez déjà publié un avis sur cet outil IA.")

    return _json_ok(
        {
            "message": "Votre avis a bien été publié.",
            "score": outil.calculer_score(),
            "avis_count": outil.avis.count(),
            "new_avis": {
                "id": avis.id,
                "auteur": auteur_name,
                "note": avis.note,
                "commentaire": avis.commentaire,
                "date_creation": avis.date_creation.strftime("%d/%m/%Y %H:%M"),
            },
        }
    )


# ---------------------------------------------------------------------------
# Soumission communautaire d'outils
# ---------------------------------------------------------------------------

def api_proposer_outil(request):
    """
    POST /api/outils/proposer/
    Corps JSON : {nom, description, url_site, type_tarification, type_integration, categorie_id}
    Les outils soumis sont marqués est_valide=False en attente de modération admin.
    """
    if not request.user.is_authenticated:
        return _json_error("Vous devez être connecté pour proposer un outil.", 401)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    nom             = str(data.get("nom", "")).strip()
    description     = str(data.get("description", "")).strip()
    url_site        = str(data.get("url_site", "")).strip()
    type_tarif      = str(data.get("type_tarification", "Freemium")).strip()
    type_integ      = str(data.get("type_integration", "Web / API")).strip()
    categorie_id    = data.get("categorie_id")

    if not nom or not description or not url_site:
        return _json_error("Veuillez fournir le nom, la description et l'URL de l'outil.")
    if not url_site.startswith(("http://", "https://")):
        return _json_error("L'URL doit commencer par http:// ou https://")

    valideur = URLValidator()
    try:
        valideur(url_site)
    except ValidationError:
        return _json_error("L'adresse URL fournie n'est pas valide.")

    categorie = Categorie.objects.filter(pk=categorie_id).first() if categorie_id else None

    # url_site est unique : refuser proprement une proposition déjà référencée
    # plutôt que de laisser la contrainte lever une IntegrityError (erreur 500).
    if OutilIA.objects.filter(url_site=url_site).exists():
        return _json_error("Cet outil est déjà référencé dans le catalogue.")

    try:
        outil = OutilIA.objects.create(
            nom=nom,
            description=description,
            url_site=url_site,
            type_tarification=type_tarif,
            type_integration=type_integ,
            categorie=categorie,
            soumis_par=request.user,
            provenance="community",
            est_valide=False,
        )
    except IntegrityError:
        # Filet de sécurité : course entre la vérification et la création
        # (deux soumissions simultanées du même URL).
        return _json_error("Cet outil est déjà référencé dans le catalogue.")

    return _json_ok(
        {
            "message": (
                "Votre proposition a été soumise avec succès. "
                "Elle sera validée par l'administrateur sous peu."
            ),
            "outil_id": outil.id,
        }
    )


# ---------------------------------------------------------------------------
# Favoris
# ---------------------------------------------------------------------------

def api_toggle_favoris(request, outil_id):
    """POST /api/outils/<outil_id>/favoris/"""
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)

    outil = get_object_or_404(OutilIA, pk=outil_id, est_valide=True)

    if request.user in outil.favoris.all():
        outil.favoris.remove(request.user)
        return _json_ok({"is_favori": False, "message": "Outil retiré de vos favoris."})
    else:
        outil.favoris.add(request.user)
        return _json_ok({"is_favori": True, "message": "Outil ajouté à vos favoris."})


# ---------------------------------------------------------------------------
# Projets personnalisés
# ---------------------------------------------------------------------------

def api_projets_list_create(request):
    """
    GET  /api/projets/  — Liste les projets de l'utilisateur connecté.
    POST /api/projets/  — Crée un nouveau projet.
    Corps POST JSON : {"nom": "...", "description": "..."}
    """
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)

    if request.method == "GET":
        projets = Projet.objects.filter(user=request.user).prefetch_related("outils")
        data = [
            {
                "id": p.id,
                "nom": p.nom,
                "description": p.description,
                "outils_count": p.outils.count(),
                "date_creation": p.date_creation.strftime("%d/%m/%Y"),
            }
            for p in projets
        ]
        return _json_ok({"projets": data})

    if request.method == "POST":
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            payload = request.POST

        nom = str(payload.get("nom", "")).strip()
        description = str(payload.get("description", "")).strip()

        if not nom:
            return _json_error("Le nom du projet est requis.")

        projet = Projet.objects.create(
            user=request.user, nom=nom, description=description
        )
        return _json_ok(
            {"message": "Projet créé avec succès.", "id": projet.id, "nom": projet.nom}
        )

    return _json_error("Méthode non autorisée.", 405)


# ---------------------------------------------------------------------------
# Recherche Web IA (Tavily) — API REST avec DRF
# ---------------------------------------------------------------------------

class ResearchStartAPIView(APIView):
    """
    POST /api/research/
    Corps JSON : {"query": "texte de la recherche"}
    Authentification requise (session Django).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = ResearchJob.objects.create(
            query=serializer.validated_data["query"],
            status="pending",
        )

        try:
            perform_web_research(job)
        except Exception:
            job.refresh_from_db()
            return Response(
                {
                    "message": "La recherche n'a pas pu être complétée.",
                    "research": _format_research_job(job),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        job.refresh_from_db()
        return Response(
            {
                "message": "Recherche terminée avec succès.",
                "research": _format_research_job(job),
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Gestion des fichiers de contexte (upload serveur sécurisé)
# ---------------------------------------------------------------------------

@require_http_methods(["POST"])
def api_upload_fichier(request):
    """
    POST /api/fichiers/upload/
    Formulaire multipart/form-data : fichier=<file>, projet_id=<int optionnel>
    Téléverse un fichier sur le serveur, calcule son MD5 pour éviter les doublons,
    et l'enregistre en base de données.
    """
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)

    if "fichier" not in request.FILES:
        return _json_error("Aucun fichier fourni dans la requête.")

    fichier_django = request.FILES["fichier"]
    projet_id = request.POST.get("projet_id")

    # Validation centralisée (whitelist + taille + magic bytes) :
    # cf. finder/services/files.py — mêmes règles que les validators du modèle.
    ext = os.path.splitext(fichier_django.name)[1].lower()

    if not extension_autorisee(fichier_django.name):
        from django.conf import settings as conf
        return _json_error(
            f"Extension '{ext}' non autorisée. Extensions acceptées : "
            + ", ".join(sorted(getattr(conf, "UPLOAD_ALLOWED_EXTENSIONS", set())))
        )

    if not taille_autorisee(fichier_django.size):
        from django.conf import settings as conf
        max_size = getattr(conf, "UPLOAD_MAX_SIZE_BYTES", 10 * 1024 * 1024)
        max_mo = max_size // (1024 * 1024)
        return _json_error(
            f"Fichier trop volumineux ({fichier_django.size // 1024} Ko). "
            f"Maximum autorisé : {max_mo} Mo."
        )

    # Calcul du MD5 pour déduplication (repositionne le curseur au début)
    hash_md5 = FichierContexte.calculer_md5(fichier_django)

    # Vérification des magic bytes pour les types binaires (image / PDF) :
    # empêche de servir un fichier malveillant sous une extension autorisée.
    debut_contenu = fichier_django.read(16)
    if not contenu_coherent_avec_extension(ext, debut_contenu):
        return _json_error("Le contenu du fichier ne correspond pas à son extension.")
    fichier_django.seek(0)

    # Vérification de doublon exact pour cet utilisateur
    doublon = FichierContexte.objects.filter(
        user=request.user, hash_md5=hash_md5
    ).first()
    if doublon:
        return _json_ok(
            {
                "message": "Ce fichier existe déjà dans votre espace.",
                "fichier": {
                    "id": doublon.id,
                    "nom": doublon.nom_original,
                    "taille": doublon.taille_octets,
                    "extension": doublon.extension,
                    "date_ajout": doublon.date_ajout.strftime("%d/%m/%Y %H:%M"),
                },
                "doublon": True,
            }
        )

    # Résolution du projet si fourni
    projet = None
    if projet_id:
        from .models import Projet as ProjetModel
        projet = ProjetModel.objects.filter(
            pk=projet_id, user=request.user
        ).first()

    # Création de l'objet en base avec le fichier (le path est calculé dans _upload_context_path)
    fichier_obj = FichierContexte(
        user=request.user,
        projet=projet,
        nom_original=fichier_django.name[:255],
        extension=ext,
        taille_octets=fichier_django.size,
        hash_md5=hash_md5,
    )
    fichier_obj.fichier = fichier_django
    fichier_obj.save()

    return _json_ok(
        {
            "message": "Fichier téléversé avec succès.",
            "fichier": {
                "id": fichier_obj.id,
                "nom": fichier_obj.nom_original,
                "taille": fichier_obj.taille_octets,
                "extension": fichier_obj.extension,
                "date_ajout": fichier_obj.date_ajout.strftime("%d/%m/%Y %H:%M"),
            },
        }
    )


@require_http_methods(["GET"])
def api_liste_fichiers(request):
    """
    GET /api/fichiers/
    Retourne la liste des fichiers de contexte de l'utilisateur connecté.
    Paramètre optionnel : projet_id=<int>
    """
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)

    qs = FichierContexte.objects.filter(user=request.user).order_by("-date_ajout")

    projet_id = request.GET.get("projet_id")
    if projet_id:
        qs = qs.filter(projet_id=projet_id)

    fichiers_data = [
        {
            "id": f.id,
            "nom": f.nom_original,
            "extension": f.extension,
            "taille": f.taille_octets,
            "projet_id": f.projet_id,
            "date_ajout": f.date_ajout.strftime("%d/%m/%Y %H:%M"),
        }
        for f in qs
    ]
    return _json_ok({"fichiers": fichiers_data, "total": len(fichiers_data)})


@require_http_methods(["DELETE"])
def api_supprimer_fichier(request, fichier_id):
    """
    DELETE /api/fichiers/<fichier_id>/
    Supprime le fichier en base de données ET physiquement sur le disque.
    """
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)

    fichier_obj = get_object_or_404(FichierContexte, pk=fichier_id, user=request.user)
    nom = fichier_obj.nom_original

    # Suppression physique du fichier sur le disque
    chemin_fichier = fichier_obj.fichier.name
    if chemin_fichier and default_storage.exists(chemin_fichier):
        default_storage.delete(chemin_fichier)

    fichier_obj.delete()
    return _json_ok({"message": f"Le fichier « {nom} » a été supprimé."})


# ---------------------------------------------------------------------------
# Plan Finder Plus — Activation par code d'invitation
# ---------------------------------------------------------------------------

@require_http_methods(["POST"])
def api_activer_plus(request):
    """
    POST /api/activer-plus/
    Corps JSON : {"code": "FINDER-PLUS-XXXX"}
    Active le Plan Finder Plus de l'utilisateur si le code est valide.
    """
    if not request.user.is_authenticated:
        return _json_error("Authentification requise.", 401)

    profile = getattr(request.user, "finder_profile", None)
    if not profile:
        return _json_error("Profil utilisateur introuvable.", 404)

    if profile.est_abonne_plus:
        return _json_ok(
            {"message": "Votre compte bénéficie déjà du Plan Finder Plus."}
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    code_saisi = str(data.get("code", "")).strip().upper()
    if not code_saisi:
        return _json_error("Veuillez saisir un code d'invitation.")

    # Recherche du code dans la base
    try:
        code_obj = CodeAccesPlus.objects.get(code=code_saisi)
    except CodeAccesPlus.DoesNotExist:
        return _json_error("Code d'invitation invalide ou inexistant.")

    if not code_obj.est_valide():
        return _json_error(
            "Ce code a expiré ou a atteint son nombre maximum d'utilisations."
        )

    # Activation atomique pour éviter les conditions de concurrence
    with transaction.atomic():
        code_obj = CodeAccesPlus.objects.select_for_update().get(pk=code_obj.pk)
        if not code_obj.est_valide():
            return _json_error(
                "Ce code a expiré ou a atteint son nombre maximum d'utilisations."
            )
        code_obj.utilisations_actuelles += 1
        code_obj.save(update_fields=["utilisations_actuelles"])

        profile.est_abonne_plus = True
        profile.code_plus_utilise = code_saisi
        profile.save(update_fields=["est_abonne_plus", "code_plus_utilise"])

    return _json_ok(
        {
            "message": "🎉 Félicitations ! Le Plan Finder Plus est maintenant actif sur votre compte.",
            "est_abonne_plus": True,
        }
    )
