"""
Service LLM (Gemini) — génération du « Résumé IA » de la recherche.

Modèle de clé hybride :
  1. Clé personnelle : `UserProfile.gemini_api_key` (masquée par l'API).
  2. Clé serveur     : `settings.GEMINI_SERVER_API_KEY`, réservée aux
     abonnés Finder Plus qui n'ont pas renseigné leur propre clé.
  3. Sinon           : `RequiresAPIKeyError`, convertie en 402 par l'API.

Les pannes externes de google.generativeai (timeout, clé invalide, quota)
ne remontent jamais : elles déclenchent un résumé de repli pour ne pas
faire échouer la recherche.
"""

from django.conf import settings


class RequiresAPIKeyError(Exception):
    """Aucune clé Gemini ne peut être résolue pour cet utilisateur."""


def _resoudre_cle_api(user) -> str:
    """
    Résout la clé Gemini à utiliser pour un utilisateur.

    Règles :
      1. La clé personnelle du profil prime toujours.
      2. Sinon, la clé serveur est utilisée uniquement pour les abonnés Plus.
      3. Sinon, `RequiresAPIKeyError` est levée.

    Le profil est relu depuis la base (pas le cache du lien inverse OneToOne)
    pour garantir une résolution à jour, y compris juste après une sauvegarde.
    """
    profile = None
    if user and getattr(user, "is_authenticated", False):
        from finder.models import UserProfile

        profile = UserProfile.objects.filter(user=user).first()

    cle_personnelle = (profile.gemini_api_key or "").strip() if profile else ""
    if cle_personnelle:
        return cle_personnelle

    if profile and profile.est_abonne_plus:
        cle_serveur = (getattr(settings, "GEMINI_SERVER_API_KEY", "") or "").strip()
        if cle_serveur:
            return cle_serveur

    raise RequiresAPIKeyError(
        "Aucune clé Gemini disponible : ajoutez votre clé dans les paramètres "
        "ou activez le Plan Finder Plus pour générer le résumé IA."
    )


def _construire_prompt(query: str, resultats: list[dict], style: str, langue: str) -> str:
    """Construit le prompt d'analyse des outils candidats pour Gemini."""
    lignes = []
    for i, outil in enumerate(resultats, start=1):
        nom = outil.get("nom") or "Outil sans nom"
        description = (outil.get("description") or "").strip()
        categorie = outil.get("categorie")
        if isinstance(categorie, dict):
            categorie = categorie.get("nom")
        score = outil.get("score_pertinence")

        extraits = [f"{i}. {nom}"]
        if categorie:
            extraits.append(f"[{categorie}]")
        if score is not None:
            extraits.append(f"(pertinence {float(score):.2f})")
        if description:
            extraits.append(f" — {description[:300]}")
        lignes.append(" ".join(extraits))

    liste = "\n".join(lignes) if lignes else "Aucun outil candidat."

    consignes = {
        "decision": "Privilégiez une recommandation directe et tranchée.",
        "detailed": "Analysez les forces et limites de chaque solution.",
        "balanced": "Proposez une vue équilibrée, claire et concise.",
    }.get(style, "Proposez une vue équilibrée, claire et concise.")

    if langue == "en":
        return (
            "You are Finder-AI, an expert assistant recommending AI tools.\n"
            f"User need: {query}\n"
            f"Candidate tools:\n{liste}\n"
            f"Write a concise synthesis in English. {consignes}\n"
            "Do not mention that you are an AI."
        )
    return (
        "Tu es Finder-AI, un assistant expert en recommandation d'outils IA.\n"
        f"Besoin exprimé par l'utilisateur : {query}\n"
        f"Outils candidats trouvés :\n{liste}\n"
        f"Rédige une synthèse claire et concise. {consignes}\n"
        "Ne mentionne pas que tu es une IA."
    )


def _generer_texte_gemini(cle: str, prompt: str) -> str:
    """
    Appelle l'API Gemini et retourne le texte généré (import différé du SDK).

    Un timeout explicite est transmis via request_options (certaines versions
    du SDK ne l'acceptent pas : on retombe alors sur l'appel simple).
    """
    import google.generativeai as genai

    genai.configure(api_key=cle)
    modele = genai.GenerativeModel(getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash"))

    try:
        reponse = modele.generate_content(prompt, request_options={"timeout": 45})
    except TypeError:
        reponse = modele.generate_content(prompt)

    return (reponse.text or "").strip()


def _resume_fallback(query: str, resultats: list[dict], langue: str) -> str:
    """Résumé de repli utilisé si l'appel Gemini échoue (jamais d'erreur 500)."""
    if not resultats:
        if langue == "en":
            return (
                f"No valid AI tool matched '{query}'. "
                "Try a more specific keyword or a broader search."
            )
        return (
            f"Aucun outil IA valide ne correspond à « {query} ». "
            "Essayez un mot-clé plus précis ou une recherche élargie."
        )

    premier = resultats[0]
    nom = premier.get("nom") or "un outil"
    nombre = len(resultats)
    if langue == "en":
        return (
            f"Finder AI recommends {nom} for '{query}', "
            f"among {nombre} relevant reference(s)."
        )
    return (
        f"Finder AI recommande {nom} pour « {query} », "
        f"parmi {nombre} référence(s) pertinente(s)."
    )


def generer_resume_recherche(
    query: str,
    resultats: list[dict],
    user,
    style: str = "balanced",
    langue: str = "fr",
) -> tuple[str, str]:
    """
    Génère le « Résumé IA » d'une recherche.

    Args:
        query     : Requête de l'utilisateur.
        resultats : Liste d'outils sérialisés (avec `nom`, `description`,
                    `categorie`, `score_pertinence`).
        user      : Utilisateur connecté (résolution de la clé Gemini).
        style     : Style de synthèse (decision | balanced | detailed).
        langue    : Langue de sortie (fr | en).

    Returns:
        Tuple `(texte, provenance)` avec provenance ∈ {"ia", "fallback"}.

    Raises:
        RequiresAPIKeyError : aucune clé Gemini résolvable. La levée est
        volontaire pour permettre à l'API de répondre 402 ; les pannes du
        SDK, elles, retournent silencieusement un résumé de repli.
    """
    cle = _resoudre_cle_api(user)

    prompt = _construire_prompt(query, resultats, style, langue)
    try:
        texte = _generer_texte_gemini(cle, prompt)
        if texte:
            return texte, "ia"
    except Exception:
        pass  # Timeout, clé invalide, quota… → repli sans faire crasher l'API

    return _resume_fallback(query, resultats, langue), "fallback"
