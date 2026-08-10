from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from finder.models import ResearchResult, Source


def perform_web_research(job):
    """
    Recherche plusieurs sources Web avec Tavily, puis enregistre
    les résultats classés et leurs références dans la base de données.
    """
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
