"""
Moteur de recherche sémantique vectorielle — 100 % gratuit, aucune dépendance externe.

Stratégie :
  1. TF-IDF maison (Term Frequency-Inverse Document Frequency) calculé en Python pur.
  2. Similarité cosinus calculée manuellement sans numpy ni bibliothèque IA payante.
  3. L'index est construit en mémoire au premier appel et invalidé dès qu'un outil est
     ajouté ou modifié (via le signal post_save sur OutilIA).

Usage :
  from finder.services.vector_search import recherche_semantique
  resultats = recherche_semantique("outil pour générer du code Python", top_k=5)
  # → Liste de (OutilIA, score_float) triée par pertinence décroissante
"""

import math
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Index en mémoire (singleton par processus Python)
# ---------------------------------------------------------------------------

_index: Optional[dict] = None  # dict avec "idf", "tf_idf_matrix", "outils"

# Bonus appliqué au score de similarité quand un outil correspond au profil
# utilisateur (stack technique + objectifs). Une correspondance totale peut
# ajouter jusqu'à 25 % au score, le tout plafonné à 1.0.
BONUS_PROFIL = 0.25


def _tokenizer(texte: str) -> list[str]:
    """Découpe un texte en tokens minuscules, sans ponctuation ni stopwords courants."""
    STOPWORDS_FR_EN = {
        "de", "du", "le", "la", "les", "un", "une", "des", "en", "et", "ou",
        "à", "au", "avec", "pour", "sur", "par", "dans", "que", "qui", "est",
        "the", "a", "an", "of", "in", "to", "for", "and", "or", "is", "on",
        "it", "be", "as", "at", "by", "we", "an",
    }
    tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9]+", texte.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS_FR_EN]


def _construire_document(outil) -> str:
    """Construit le texte représentatif d'un outil pour l'indexation."""
    parties = [
        outil.nom,
        outil.description,
        outil.categorie.nom if outil.categorie else "",
        outil.type_tarification,
        outil.type_integration,
        " ".join(t.nom for t in outil.tags.all()),
    ]
    return " ".join(p for p in parties if p)


def _calculer_tfidf(corpus: list[list[str]]) -> tuple[dict, list[dict]]:
    """
    Calcule l'IDF global et les vecteurs TF-IDF de chaque document.

    Retourne :
      idf        : {terme: valeur_idf}
      tf_vectors : [{terme: valeur_tf_idf}, ...]
    """
    N = len(corpus)
    if N == 0:
        return {}, []

    # Fréquences de documents (DF)
    df: dict[str, int] = {}
    for tokens in corpus:
        for terme in set(tokens):
            df[terme] = df.get(terme, 0) + 1

    # IDF avec lissage logarithmique (évite la division par zéro)
    idf = {terme: math.log((N + 1) / (freq + 1)) + 1 for terme, freq in df.items()}

    # Vecteurs TF-IDF normalisés
    tf_vectors = []
    for tokens in corpus:
        tf: dict[str, float] = {}
        if tokens:
            for terme in tokens:
                tf[terme] = tf.get(terme, 0) + 1
            total = len(tokens)
            vecteur = {terme: (count / total) * idf.get(terme, 0) for terme, count in tf.items()}
        else:
            vecteur = {}
        # Normalisation L2
        norme = math.sqrt(sum(v * v for v in vecteur.values())) or 1.0
        tf_vectors.append({terme: val / norme for terme, val in vecteur.items()})

    return idf, tf_vectors


def _similarite_cosinus(vec_a: dict, vec_b: dict) -> float:
    """Calcule la similarité cosinus entre deux vecteurs TF-IDF sous forme de dicts."""
    termes_communs = set(vec_a) & set(vec_b)
    if not termes_communs:
        return 0.0
    produit = sum(vec_a[t] * vec_b[t] for t in termes_communs)
    norme_a = math.sqrt(sum(v * v for v in vec_a.values())) or 1.0
    norme_b = math.sqrt(sum(v * v for v in vec_b.values())) or 1.0
    return produit / (norme_a * norme_b)


# ---------------------------------------------------------------------------
# Personnalisation du classement par profil utilisateur (Plan Finder-AI)
# ---------------------------------------------------------------------------

def _tokens_profil(profil) -> set[str]:
    """
    Extrait les tokens significatifs du profil utilisateur.

    Sources : stack technique, objectifs (goals) et contexte professionnel.
    """
    if profil is None:
        return set()

    parties = []
    for champ in ("technology_stack", "goals"):
        valeurs = getattr(profil, champ, None)
        if isinstance(valeurs, list):
            parties.append(" ".join(str(v) for v in valeurs))
    contexte = getattr(profil, "professional_context", "") or ""
    if isinstance(contexte, str):
        parties.append(contexte)

    return set(_tokenizer(" ".join(parties)))


def _bonus_personnalisation(outil, tokens_profil: set[str]) -> float:
    """
    Multiplicateur ≥ 1.0 si l'outil correspond au profil utilisateur.

    Retourne 1.0 (aucun bonus) si le profil est vide ou si l'outil ne partage
    aucun token avec lui.
    """
    if not tokens_profil:
        return 1.0

    tokens_outil = set(_tokenizer(_construire_document(outil)))
    correspondances = tokens_profil & tokens_outil
    if not correspondances:
        return 1.0

    ratio = len(correspondances) / len(tokens_profil)
    return 1.0 + (BONUS_PROFIL * ratio)


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def invalider_index():
    """Invalide l'index en mémoire (appelé par signal post_save sur OutilIA)."""
    global _index
    _index = None


def _construire_index():
    """Construit ou reconstruit l'index TF-IDF depuis la base de données."""
    global _index
    from finder.models import OutilIA

    outils = list(
        OutilIA.objects.filter(est_valide=True)
        .select_related("categorie")
        .prefetch_related("tags")
    )

    if not outils:
        _index = {"idf": {}, "tf_idf_matrix": [], "outils": []}
        return

    corpus_raw = [_construire_document(o) for o in outils]
    corpus_tokens = [_tokenizer(doc) for doc in corpus_raw]
    idf, tf_vectors = _calculer_tfidf(corpus_tokens)

    _index = {
        "idf": idf,
        "tf_idf_matrix": tf_vectors,
        "outils": outils,
    }


def recherche_semantique(requete: str, top_k: int = 5, profil=None) -> list[tuple]:
    """
    Recherche les outils IA les plus pertinents pour une requête en langage naturel.

    Args:
        requete : Texte de la requête utilisateur.
        top_k   : Nombre maximum de résultats à retourner.
        profil  : UserProfile optionnel — les outils correspondant à la stack
                  technique ou aux objectifs de l'utilisateur reçoivent un
                  bonus de pertinence (personnalisation du classement).

    Returns:
        Liste de tuples (OutilIA, score) triée par pertinence décroissante.
        Le score est une valeur flottante entre 0.0 et 1.0.
    """
    if _index is None:
        _construire_index()

    if not _index["outils"]:
        return []

    # Vectorisation de la requête dans le même espace que le corpus
    tokens_requete = _tokenizer(requete)
    if not tokens_requete:
        return []

    tf_requete: dict[str, float] = {}
    for terme in tokens_requete:
        tf_requete[terme] = tf_requete.get(terme, 0) + 1
    total = len(tokens_requete)
    idf = _index["idf"]
    vecteur_requete = {
        terme: (count / total) * idf.get(terme, 0)
        for terme, count in tf_requete.items()
    }
    norme = math.sqrt(sum(v * v for v in vecteur_requete.values())) or 1.0
    vecteur_requete = {t: v / norme for t, v in vecteur_requete.items()}

    # Personnalisation : bonus de classement selon le profil utilisateur.
    tokens_profil = _tokens_profil(profil)

    # Calcul de la similarité avec chaque outil (score plafonné à 1.0)
    scores = []
    for i, vec in enumerate(_index["tf_idf_matrix"]):
        outil = _index["outils"][i]
        base = _similarite_cosinus(vecteur_requete, vec)
        if base <= 0.0:
            continue
        bonus = _bonus_personnalisation(outil, tokens_profil)
        scores.append((outil, min(1.0, base * bonus)))

    # Tri décroissant et filtre des scores nuls
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
