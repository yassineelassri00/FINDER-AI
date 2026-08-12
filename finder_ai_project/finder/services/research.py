from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from finder.models import ResearchResult, Source


# ---------------------------------------------------------------------------
# Gating Plan Finder Plus — la recherche web (Tavily) est réservée aux Plus.
# ---------------------------------------------------------------------------

def utilisateur_a_acces_web(user) -> bool:
    """True si l'utilisateur peut déclencher une recherche web (Plan Plus)."""
    if not user or not user.is_authenticated:
        return False
    profile = getattr(user, "finder_profile", None)
    return bool(profile and profile.est_abonne_plus)


# ---------------------------------------------------------------------------
# Recherche web Tavily sans écriture en base (mode Hybride / Web du workspace)
# ---------------------------------------------------------------------------

def rechercher_web_tavily(query: str, max_results: int = 6) -> list[dict]:
    """
    Interroge le moteur Tavily et retourne des résultats structurés.

    Contrairement à `perform_web_research`, cette fonction ne touche pas la
    base de données : elle sert directement la réponse JSON du workspace.

    Returns:
        Liste de dicts : {title, url, domain, content, score}.
    """
    from tavily import TavilyClient  # Import différé : app démarrable sans SDK

    client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    response = client.search(
        query=query,
        search_depth="basic",
        max_results=max_results,
        topic="general",
        include_answer=False,
        include_raw_content=False,
        include_usage=True,
    )

    resultats = []
    for item in response.get("results", []):
        url = item.get("url") or ""
        content = item.get("content") or "Aucun extrait disponible."
        domain = urlparse(url).netloc.removeprefix("www.") or "Source inconnue"
        resultats.append(
            {
                "title": (item.get("title") or "Résultat sans titre")[:300],
                "url": url,
                "domain": domain[:255],
                "content": content,
                "score": float(item.get("score", 0) or 0),
            }
        )
    return resultats


def perform_web_research(job):
    """
    Recherche plusieurs sources Web avec Tavily, puis enregistre
    les résultats classés et leurs références dans la base de données.
    """
    # Gating : la recherche web est strictement réservée au Plan Finder Plus.
    if not utilisateur_a_acces_web(job.user):
        job.status = "failed"
        job.error_message = "Plan Finder Plus requis pour la recherche web."
        job.save(update_fields=["status", "error_message"])
        raise PermissionError("Plan Finder Plus requis pour la recherche web.")

    job.status = "searching"
    job.error_message = ""
    job.save(update_fields=["status", "error_message"])

    try:
        # Import différé : l'application reste démarrable même si le client de recherche
        # externe doit être réparé ou mis à jour indépendamment de l'interface.
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.TAVILY_API_KEY)

        response = client.search(
            query=job.query,
            search_depth="basic",
            max_results=6,
            topic="general",
            include_answer=False,
            include_raw_content=False,
            include_usage=True,
        )

        results = response.get("results", [])

        # Si cette recherche est relancée, supprime seulement ses anciens résultats.
        job.results.all().delete()

        for rank, item in enumerate(results, start=1):
            title = item.get("title") or f"Résultat {rank}"
            url = item.get("url") or ""
            content = item.get("content") or "Aucun extrait disponible."
            score = Decimal(str(item.get("score", 0))).quantize(Decimal("0.01"))
            domain = urlparse(url).netloc.removeprefix("www.") or "Source inconnue"

            research_result = ResearchResult.objects.create(
                research_job=job,
                rank=rank,
                title=title[:300],
                summary=content,
                score=score,
            )

            Source.objects.create(
                research_result=research_result,
                title=title[:500],
                url=url,
                domain=domain[:255],
                excerpt=content,
                authority_score=score,
            )

        job.summary = (
            f"{len(results)} source(s) trouvée(s) et classée(s) "
            f"pour la recherche : {job.query}"
        )
        job.status = "completed"
        job.completed_at = timezone.now()
        job.save(update_fields=["summary", "status", "completed_at"])

        return job

    except Exception as error:
        job.status = "failed"
        job.error_message = str(error)
        job.save(update_fields=["status", "error_message"])
        raise
