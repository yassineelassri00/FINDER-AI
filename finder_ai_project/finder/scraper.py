import random
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from finder.models import Categorie, OutilIA, ScraperLog

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class FinderScraper:
    """Robot de web scraping d'outils IA avec rotation d'en-têtes et mesure de performance."""

    def __init__(self, url_cible):
        self.url_cible = url_cible
        self.outils_ajoutes = 0
        self.outils_mis_a_jour = 0
        self.erreurs = []
        self.start_time = None
        self.temps_execution = 0.0

    def get_random_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def recuperer_page(self):
        """Télécharge le HTML de la page cible avec rotation d'en-tête."""
        try:
            reponse = requests.get(
                self.url_cible,
                headers=self.get_random_headers(),
                timeout=15,
            )
            reponse.raise_for_status()
            return reponse.text
        except requests.RequestException as e:
            self.erreurs.append(f"Erreur HTTP sur {self.url_cible} : {str(e)}")
            return None

    def extraire_donnees(self, html):
        """Analyse le HTML et extrait les informations d'outils IA."""
        soup = BeautifulSoup(html, "html.parser")

        # Recherche flexible d'éléments représentant des cartes d'outils
        articles = (
            soup.find_all("article")
            or soup.find_all("div", class_=["card", "tool-card", "item", "product-card"])
            or soup.find_all("li", class_=["tool", "item"])
        )

        if not articles:
            # Recherche générique par blocs contenant des titres H2/H3 et liens
            headings = soup.find_all(["h2", "h3"])
            for h in headings:
                parent = h.find_parent(["div", "section", "article", "li"])
                if parent and parent not in articles:
                    articles.append(parent)

        for article in articles:
            try:
                # Extraction du nom (h2, h3, h4 ou strong)
                heading_el = article.find(["h1", "h2", "h3", "h4", "strong"])
                if not heading_el:
                    continue
                nom = heading_el.get_text().strip()
                # Nettoie les sauts de ligne et espaces multiples
                # (ex: "proprietaire /\n\n      repo" -> "proprietaire / repo")
                nom = re.sub(r"\s+", " ", nom).strip()
                if not nom or len(nom) > 200:
                    continue

                # Extraction de la description (p ou span)
                desc_el = article.find("p") or article.find("span", class_=["desc", "description", "summary"])
                description = desc_el.get_text().strip() if desc_el else f"Outil IA {nom} extrait par le robot Finder-AI."
                description = re.sub(r"\s+", " ", description).strip()[:1000]

                # Extraction du lien URL (balise a)
                link_el = article.find("a", href=True)
                url = link_el["href"] if link_el else self.url_cible
                if not url.startswith("http"):
                    # URL relative -> absolue
                    url = urljoin(self.url_cible, url)

                # Détection facultative de tarification / catégorie
                text_content = article.get_text().lower()
                type_tarification = "Gratuit" if "free" in text_content or "gratuit" in text_content else "Freemium"
                if "payant" in text_content or "paid" in text_content or "pricing" in text_content:
                    type_tarification = "Payant"

                self.sauvegarder_outil(
                    nom=nom,
                    description=description,
                    url=url,
                    type_tarification=type_tarification,
                    texte_analyse=text_content,
                )
            except Exception as e:
                self.erreurs.append(f"Erreur d'extraction d'élément : {str(e)}")

    # Mots-clés simples permettant d'affecter une catégorie du catalogue.
    CATEGORIE_KEYWORDS = {
        "assistant-de-code": [
            "code", "ide", "copilot", "éditeur", "editor", "repository",
            "programming", "developer tool", "coding",
        ],
        "data": [
            "data", "ml", "machine learning", "dataset", "analytics",
            "notebook", "python", "tensorflow", "pytorch",
        ],
        "automatisation": [
            "automation", "workflow", "pipeline", "integration",
            "bot", "no-code", "low-code", "agent",
        ],
        "recherche": [
            "search", "recherche", "research", "llm", "language model",
            "chatbot", "question answering", "gpt",
        ],
        "design": [
            "design", "image", "video", "audio", "génération", "generation",
            "creative", "art", "music",
        ],
    }

    @staticmethod
    def detecter_categorie(texte_analyse, categorie_defaut):
        """Choisit une catégorie existante du catalogue en fonction du contenu."""
        if not texte_analyse:
            return categorie_defaut
        for slug, mots_cles in FinderScraper.CATEGORIE_KEYWORDS.items():
            if any(mot in texte_analyse for mot in mots_cles):
                categorie = Categorie.objects.filter(slug=slug).first()
                if categorie:
                    return categorie
        return categorie_defaut

    def sauvegarder_outil(self, nom, description, url, type_tarification="Freemium", texte_analyse=""):
        """Enregistre ou met à jour l'outil dans la base de données Django."""
        cat_def, _ = Categorie.objects.get_or_create(
            slug="general",
            defaults={"nom": "Général"},
        )
        categorie = self.detecter_categorie(texte_analyse, cat_def)

        outil, cree = OutilIA.objects.update_or_create(
            url_site=url,
            defaults={
                "nom": nom,
                "description": description,
                "type_tarification": type_tarification,
                "type_integration": "Web / API",
                "categorie": categorie,
                "provenance": "scraper",
                "est_valide": False,  # modéré par l'admin avant publication
            },
        )
        if cree:
            self.outils_ajoutes += 1
        else:
            self.outils_mis_a_jour += 1

    def lancer(self):
        """Exécute le scraping, calcule le temps d'exécution et génère le log."""
        self.start_time = time.time()
        print(f"Lancement du scraping autonome sur {self.url_cible}...")

        html = self.recuperer_page()
        if html:
            self.extraire_donnees(html)

        self.temps_execution = round(time.time() - self.start_time, 2)
        total_traites = self.outils_ajoutes + self.outils_mis_a_jour

        log = ScraperLog.objects.create(
            total_extraits=total_traites,
            temps_execution=self.temps_execution,
            erreurs="\n".join(self.erreurs) if self.erreurs else "Aucune erreur",
        )

        print(f"Scraping terminé en {self.temps_execution}s : {self.outils_ajoutes} ajoutés, {self.outils_mis_a_jour} mis à jour.")
        return log