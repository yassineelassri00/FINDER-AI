"""
Service de validation des fichiers téléversés (Finder-AI).

Centralise les règles de sécurité applicables aux uploads afin qu'elles
soient partagées par :
  - les validators des champs du modèle (FichierContexte.fichier),
  - la vue API /api/fichiers/upload/.

Les fonctions retournent un tuple (booléen, message d'erreur) pour rester
découplées du framework (le modèle lève ValidationError, l'API renvoie
un JsonResponse 400).

Durcissement appliqué :
  - whitelist d'extensions (les types rendables exécutables — svg, html,
    xml — sont exclus : vecteur d'XSS stocké),
  - limite de taille,
  - vérification des magic bytes pour les types binaires (image/PDF) afin
    d'empêcher de faire passer un fichier malveillant sous une extension
    autorisée.
"""

from django.conf import settings


def extension_autorisee(nom_fichier: str) -> bool:
    """Vérifie que l'extension du fichier figure dans la whitelist."""
    if not nom_fichier:
        return False
    extension = _extraire_extension(nom_fichier)
    autorisees = getattr(settings, "UPLOAD_ALLOWED_EXTENSIONS", set())
    return extension in autorisees


def taille_autorisee(taille_octets: int) -> bool:
    """Vérifie que la taille du fichier ne dépasse pas la limite configurée."""
    max_size = getattr(settings, "UPLOAD_MAX_SIZE_BYTES", 10 * 1024 * 1024)
    return isinstance(taille_octets, int) and 0 <= taille_octets <= max_size


# Signatures binaires (magic bytes) des types à contrôle renforcé.
# Un fichier déclaré .png/.jpg/.gif/.pdf doit commencer par ces octets.
_MAGIC_BYTES: dict[str, bytes] = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".gif": b"GIF8",
    ".pdf": b"%PDF-",
}


def contenu_coherent_avec_extension(extension: str, debut_contenu: bytes) -> bool:
    """
    Vérifie les magic bytes pour les types binaires connus.

    Les types non répertoriés (texte, code, données) ne sont pas vérifiés :
    leur contenu est inoffensif par définition et leur usage est la raison
    d'être de l'application (fichiers de contexte pour développeurs).
    """
    signature = _MAGIC_BYTES.get(extension.lower())
    if signature is None:
        return True
    return debut_contenu.startswith(signature)


def message_erreur(ok: bool, message: str) -> str | None:
    """Normalise le message d'erreur pour la levée (None si succès)."""
    return None if ok else message


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _extraire_extension(nom_fichier: str) -> str:
    """Retourne l'extension en minuscules, avec le point."""
    import os

    return os.path.splitext(nom_fichier)[1].lower()
