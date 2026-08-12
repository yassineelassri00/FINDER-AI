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
  - validation du type MIME RÉEL du fichier (lecture de l'en-tête), pas
    seulement de l'extension :
      * types binaires connus (image/PDF) : contrôle strict des magic bytes,
      * types texte/code : rejet de tout balisage HTML/SVG/XML/script déguisé
        (XSS stocké), quelle que soit l'extension déclarée.
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
    max_size = getattr(settings, "UPLOAD_MAX_SIZE_BYTES", 5 * 1024 * 1024)
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

# Marqueurs de balisage rendable par le navigateur. Un fichier déclaré
# texte/code ne doit JAMAIS en commencer par un : cela signale un
# HTML/SVG/XML/script déguisé (XSS stocké), même sous extension "autorisée".
_MARQUEURS_MARKUP: tuple[bytes, ...] = (
    b"<!doctype",
    b"<!DOCTYPE",
    b"<html",
    b"<head",
    b"<body",
    b"<svg",
    b"<script",
    b"<iframe",
    b"<object",
    b"<embed",
    b"<?xml",
    b"<!entity",
)


def contenu_coherent_avec_extension(extension: str, debut_contenu: bytes) -> bool:
    """
    Vérifie que le type MIME réel (en-tête du fichier) correspond à l'extension.

    - Types binaires connus (image/PDF) : contrôle strict des magic bytes
      (empêche de faire passer un binaire malveillant sous une extension
      autorisée).
    - Types texte/code : le contenu ne doit pas être du balisage
      HTML/SVG/XML/script déguisé (défense en profondeur contre l'XSS stocké).
    """
    signature = _MAGIC_BYTES.get(extension.lower())
    if signature is not None:
        return debut_contenu.startswith(signature)
    return not _est_markup(debut_contenu)


def _est_markup(debut_contenu: bytes) -> bool:
    """Détecte un balisage HTML/SVG/XML/script au début du contenu réel."""
    en_tete = debut_contenu.lstrip()[:1024].lower()
    return any(en_tete.startswith(m) for m in _MARQUEURS_MARKUP)


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
