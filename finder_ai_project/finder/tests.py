"""
Suite de tests unitaires complète pour l'application Finder-AI.

Organisation :
  ModelTestCase        — Tests des modèles ORM et de leurs méthodes
  ViewTestCase         — Tests des vues HTML (authentification, navigation)
  APITestCase          — Tests des endpoints API JSON
  FichierContexteTestCase — Tests de l'upload et de la gestion des fichiers
  PlusPlanTestCase     — Tests de l'activation du Plan Finder Plus
  RechercheSemantiqueTestCase — Tests du moteur TF-IDF
  ScraperTestCase      — Tests du robot de Web Scraping
"""

import json
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from finder.models import (
    Avis,
    Categorie,
    CodeAccesPlus,
    FichierContexte,
    OutilIA,
    Projet,
    ScraperLog,
    Tag,
    UserProfile,
)
from finder.scraper import FinderScraper
from finder.services.vector_search import (
    _tokenizer,
    invalider_index,
    recherche_semantique,
)


# ---------------------------------------------------------------------------
# Configuration partagée de test : répertoire média temporaire
# ---------------------------------------------------------------------------

import tempfile, os
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


# ===========================================================================
# 1. Tests des modèles ORM
# ===========================================================================

class ModelTestCase(TestCase):
    """Tests unitaires pour la couche Modèles ORM et méthodes associées."""

    def setUp(self):
        self.user  = User.objects.create_user(username="testuser",  password="password123")
        self.user2 = User.objects.create_user(username="testuser2", password="password123")
        self.categorie = Categorie.objects.create(nom="Traitement du langage", slug="nlp")
        self.tag1 = Tag.objects.create(nom="Open-Source", slug="open-source")
        self.tag2 = Tag.objects.create(nom="API REST",    slug="api-rest")

        self.outil = OutilIA.objects.create(
            nom="ChatGPT",
            description="Agent conversationnel d'OpenAI",
            url_site="https://chatgpt.com",
            type_tarification="Freemium",
            type_integration="Web / API",
            categorie=self.categorie,
            est_valide=True,
        )
        self.outil.tags.add(self.tag1, self.tag2)

    def test_calculer_score_sans_avis(self):
        self.assertEqual(self.outil.calculer_score(), 0)

    def test_calculer_score_avec_avis(self):
        Avis.objects.create(outil=self.outil, user=self.user,  auteur="U1", note=5, commentaire="Excellent !")
        Avis.objects.create(outil=self.outil, user=self.user2, auteur="U2", note=4, commentaire="Très bon !")
        self.assertEqual(self.outil.calculer_score(), 4.5)

    def test_calculer_score_reutilise_annotation(self):
        """with_score() doit pré-calculer score_moyen sans requête par outil."""
        Avis.objects.create(outil=self.outil, user=self.user, auteur="U1", note=5, commentaire="Excellent !")
        outil_annote = OutilIA.objects.with_score().get(pk=self.outil.pk)
        self.assertTrue(hasattr(outil_annote, "score_moyen"))
        self.assertEqual(outil_annote.calculer_score(), 5.0)

    def test_url_site_unique(self):
        """url_site doit être unique : une deuxième entrée lève IntegrityError."""
        with self.assertRaises(IntegrityError):
            OutilIA.objects.create(
                nom="ChatGPT doublon",
                description="Copie du même outil",
                url_site="https://chatgpt.com",  # même URL que self.outil
                type_tarification="Freemium",
                type_integration="Web / API",
                categorie=self.categorie,
                est_valide=True,
            )

    def test_unique_together_avis(self):
        Avis.objects.create(outil=self.outil, user=self.user, auteur="U1", note=5, commentaire="Premier avis.")
        with self.assertRaises(IntegrityError):
            Avis.objects.create(outil=self.outil, user=self.user, auteur="U1", note=3, commentaire="Doublon interdit.")

    def test_scraper_log_creation(self):
        log = ScraperLog.objects.create(total_extraits=5, temps_execution=2.5, erreurs="Aucune erreur")
        self.assertEqual(log.total_extraits, 5)
        self.assertEqual(log.temps_execution, 2.5)

    def test_is_approved_property(self):
        """La propriété is_approved est un alias de est_valide."""
        self.assertTrue(self.outil.is_approved)
        self.outil.is_approved = False
        self.assertFalse(self.outil.est_valide)

    def test_code_acces_plus_validite(self):
        """Un code épuisé ne doit pas être considéré comme valide."""
        code = CodeAccesPlus.objects.create(code="TEST-PLUS", max_utilisations=1, utilisations_actuelles=1)
        self.assertFalse(code.est_valide())

    def test_code_acces_plus_valide(self):
        """Un code disponible doit être considéré comme valide."""
        code = CodeAccesPlus.objects.create(code="VALID-PLUS", max_utilisations=5, utilisations_actuelles=2)
        self.assertTrue(code.est_valide())

    def test_userprofile_est_abonne_plus_default(self):
        """Le statut abonné Plus est False par défaut."""
        UserProfile.objects.update_or_create(user=self.user, defaults={"full_name": "Test", "job_role": "dev"})
        profile = UserProfile.objects.get(user=self.user)
        self.assertFalse(profile.est_abonne_plus)


# ===========================================================================
# 2. Tests des vues HTML (authentification)
# ===========================================================================

class ViewTestCase(TestCase):
    """Tests unitaires pour les vues HTML d'authentification et de navigation."""

    def setUp(self):
        self.client   = Client()
        self.username = "yassine"
        self.password = "password123!"
        self.user = User.objects.create_user(
            username=self.username, email="yassine@example.com", password=self.password
        )
        UserProfile.objects.update_or_create(user=self.user, defaults={"full_name": "Yassine El Assri", "job_role": "Développeur"})

    def test_landing_page(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finder AI")

    def test_login_success(self):
        response = self.client.post(reverse("login"), {"username": self.username, "password": self.password})
        self.assertRedirects(response, reverse("liste_outils"))

    def test_login_failure(self):
        response = self.client.post(reverse("login"), {"username": self.username, "password": "mauvais"})
        self.assertRedirects(response, reverse("landing"))

    def test_register_success(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Nouveau Dev",
                "username": "newdev",
                "email": "newdev@example.com",
                "password": "password123!",
                "password_confirmation": "password123!",
                "job_role": "Full-Stack",
            },
        )
        self.assertRedirects(response, reverse("liste_outils"))
        self.assertTrue(User.objects.filter(username="newdev").exists())

    def test_liste_outils_login_required(self):
        """L'accès au workspace doit être refusé aux visiteurs non connectés."""
        response = self.client.get(reverse("liste_outils"))
        self.assertEqual(response.status_code, 302)

    def test_liste_outils_authenticated(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("liste_outils"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yassine El Assri")


# ===========================================================================
# 3. Tests des API JSON
# ===========================================================================

class APITestCase(TestCase):
    """Tests unitaires pour les endpoints API JSON."""

    def setUp(self):
        self.client    = Client()
        self.user      = User.objects.create_user(username="devuser", password="password123")
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={"full_name": "Dev User", "job_role": "fullstack"},
        )
        self.categorie = Categorie.objects.create(nom="Génération d'image", slug="image-gen")
        self.tag       = Tag.objects.create(nom="Gratuit", slug="gratuit")
        self.outil     = OutilIA.objects.create(
            nom="Midjourney",
            description="Génération d'images par IA",
            url_site="https://midjourney.com",
            type_tarification="Payant",
            type_integration="Web / Discord",
            categorie=self.categorie,
            est_valide=True,
        )
        self.outil.tags.add(self.tag)

    def test_api_outils_list(self):
        self.client.login(username="devuser", password="password123")
        response = self.client.get(reverse("api_outils_list") + "?categorie=image-gen")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["outils"][0]["nom"], "Midjourney")

    def test_api_settings_preferences_saved(self):
        """Les paramètres de recherche doivent être sauvegardés en base."""
        self.client.login(username="devuser", password="password123")
        response = self.client.post(
            reverse("update_settings"),
            data=json.dumps(
                {
                    "section": "preferences",
                    "result_style": "detailed",
                    "preferred_language": "fr",
                    "budget_preference": "Payant",
                    "watch_frequency": "weekly",
                    "goals": ["research", "design"],
                    "research_sources": ["official_docs", "github"],
                    "technology_stack": ["python", "django"],
                    "search_preferences": {
                        "max_results": 5,
                        "source_mode": "hybrid",
                        "include_web": True,
                    },
                    "ui_preferences": {
                        "theme": "oled",
                        "viewMode": "grid",
                    },
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.finder_profile.refresh_from_db()
        self.assertEqual(self.user.finder_profile.result_style, "detailed")
        self.assertEqual(self.user.finder_profile.budget_preference, "Payant")
        self.assertEqual(self.user.finder_profile.search_preferences["max_results"], 5)
        self.assertEqual(self.user.finder_profile.ui_preferences["theme"], "oled")

    def test_api_recherche_workspace_respects_preferences(self):
        """La recherche workspace doit appliquer le budget et la limite utilisateur."""
        self.client.login(username="devuser", password="password123")
        response = self.client.post(
            reverse("api_recherche_workspace"),
            data=json.dumps(
                {
                    "q": "generation images",
                    "max_results": 1,
                    "result_style": "decision",
                    "preferred_language": "fr",
                    "default_pricing": "Payant",
                    "source_mode": "catalog",
                    "goals": ["design"],
                    "technology_stack": ["python"],
                    "professional_context": "Projet Django de recommandation IA",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertLessEqual(len(data["resultats"]), 1)
        self.assertEqual(data["preferences_appliquees"]["default_pricing"], "Payant")

    def test_api_recherche_decremente_le_quota(self):
        """Chaque recherche consomme une unité du compteur serveur."""
        self.client.login(username="devuser", password="password123")
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.recherches_restantes, 3)

        response = self.client.post(
            reverse("api_recherche_workspace"),
            data=json.dumps({"q": "generation images"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recherches_restantes"], 2)

        profile.refresh_from_db()
        self.assertEqual(profile.recherches_restantes, 2)

    def test_api_recherche_quota_epuise_429(self):
        """Une recherche avec quota épuisé doit renvoyer 429 Too Many Requests."""
        self.client.login(username="devuser", password="password123")
        profile = UserProfile.objects.get(user=self.user)
        profile.recherches_restantes = 0
        profile.save()

        response = self.client.post(
            reverse("api_recherche_workspace"),
            data=json.dumps({"q": "generation images"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()["ok"])

    def test_api_recherche_quota_illimite_pour_abonne_plus(self):
        """Un abonné Finder Plus ignore le compteur (pas de 429, pas de décrément)."""
        self.client.login(username="devuser", password="password123")
        profile = UserProfile.objects.get(user=self.user)
        profile.est_abonne_plus = True
        profile.recherches_restantes = 0
        profile.save()

        response = self.client.post(
            reverse("api_recherche_workspace"),
            data=json.dumps({"q": "generation images"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        profile.refresh_from_db()
        self.assertEqual(profile.recherches_restantes, 0)

    def test_api_quota_renvoie_le_compteur_reel(self):
        """GET /api/quota/ expose le compteur serveur (pas de localStorage)."""
        self.client.login(username="devuser", password="password123")
        response = self.client.get(reverse("api_quota"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["recherches_restantes"], 3)
        self.assertEqual(data["limit"], 3)
        self.assertFalse(data["limit_reached"])
        self.assertFalse(data["est_abonne_plus"])

    def test_api_settings_get_ne_divulgue_pas_la_cle_gemini(self):
        """S4 : la clé Gemini ne doit jamais transiter vers le client."""
        self.client.login(username="devuser", password="password123")
        profile = UserProfile.objects.get(user=self.user)
        profile.gemini_api_key = "AIzaSy-SECRET-TEST-KEY"
        profile.save()

        response = self.client.get(reverse("update_settings"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("gemini_api_key", response.json())
        self.assertNotIn("AIzaSy-SECRET-TEST-KEY", response.content.decode())

    def test_api_settings_champ_vide_ne_ecrase_pas_la_cle(self):
        """S4 : sauvegarder les préférences sans clé ne doit pas effacer la clé."""
        self.client.login(username="devuser", password="password123")
        profile = UserProfile.objects.get(user=self.user)
        profile.gemini_api_key = "AIzaSy-KEY-EXISTANTE"
        profile.save()

        response = self.client.post(
            reverse("update_settings"),
            data=json.dumps(
                {"section": "preferences", "result_style": "balanced"}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.gemini_api_key, "AIzaSy-KEY-EXISTANTE")

        # Une NOUVELLE clé saisie remplace bien l'ancienne.
        response = self.client.post(
            reverse("update_settings"),
            data=json.dumps(
                {
                    "section": "preferences",
                    "result_style": "balanced",
                    "gemini_api_key": "AIzaSy-NOUVELLE-CLE",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.gemini_api_key, "AIzaSy-NOUVELLE-CLE")

    def test_api_outils_list_sem_fallback(self):
        """La recherche sémantique TF-IDF doit s'activer si la requête SQL ne donne rien."""
        self.client.login(username="devuser", password="password123")
        invalider_index()
        response = self.client.get(
            reverse("api_outils_list") + "?q=generation+images&mode=semantic"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

    def test_api_outils_list_sem_fallback_respecte_filtres(self):
        """Le fallback sémantique doit préserver les filtres catégorie/tags/tarif."""
        autre_categorie = Categorie.objects.create(nom="Art", slug="art")
        OutilIA.objects.create(
            nom="Stable Diffusion",
            description="générer des visuels artistiques",
            url_site="https://stability.ai",
            type_tarification="Gratuit",
            type_integration="Web / API",
            categorie=autre_categorie,
            est_valide=True,
        )
        self.client.login(username="devuser", password="password123")
        invalider_index()

        # Requête qui ne matche pas en SQL mais oui en sémantique, avec filtre catégorie.
        response = self.client.get(
            reverse("api_outils_list")
            + "?q=g%C3%A9n%C3%A9rer+des+images&mode=semantic&categorie=image-gen"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["semantic_active"])
        # Seul Midjourney (catégorie image-gen) doit être retourné : le filtre
        # catégorie reste appliqué même lorsque le moteur sémantique prend le relais.
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["outils"][0]["nom"], "Midjourney")

    def test_api_proposer_outil_doublon_url(self):
        """Proposer un outil dont l'URL existe déjà doit être refusé (pas de 500)."""
        self.client.login(username="devuser", password="password123")
        response = self.client.post(
            reverse("api_proposer_outil"),
            data=json.dumps(
                {
                    "nom": "Midjourney bis",
                    "description": "Doublon",
                    "url_site": "https://midjourney.com",  # déjà référencé
                    "type_tarification": "Payant",
                    "type_integration": "Web / Discord",
                    "categorie_id": self.categorie.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_api_ajouter_avis(self):
        self.client.login(username="devuser", password="password123")
        url = reverse("api_ajouter_avis", kwargs={"outil_id": self.outil.id})
        response = self.client.post(
            url,
            data=json.dumps({"note": 5, "commentaire": "Super rendu d'image !"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["score"], 5.0)

    def test_api_avis_note_invalide(self):
        """Une note hors de [1,5] doit être rejetée."""
        self.client.login(username="devuser", password="password123")
        url = reverse("api_ajouter_avis", kwargs={"outil_id": self.outil.id})
        response = self.client.post(
            url,
            data=json.dumps({"note": 6, "commentaire": "Note invalide."}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_api_proposer_outil(self):
        self.client.login(username="devuser", password="password123")
        response = self.client.post(
            reverse("api_proposer_outil"),
            data=json.dumps(
                {
                    "nom": "Claude 3.5 Sonnet",
                    "description": "Modèle d'IA avancé par Anthropic",
                    "url_site": "https://anthropic.com",
                    "type_tarification": "Freemium",
                    "type_integration": "Web / API",
                    "categorie_id": self.categorie.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        nouveau = OutilIA.objects.get(nom="Claude 3.5 Sonnet")
        self.assertFalse(nouveau.est_valide)  # Doit être en attente de modération
        self.assertEqual(nouveau.soumis_par, self.user)

    def test_api_toggle_favoris(self):
        self.client.login(username="devuser", password="password123")
        url = reverse("api_toggle_favoris", kwargs={"outil_id": self.outil.id})
        res1 = self.client.post(url)
        self.assertTrue(res1.json()["is_favori"])
        res2 = self.client.post(url)
        self.assertFalse(res2.json()["is_favori"])

    def test_api_projets_list_create(self):
        self.client.login(username="devuser", password="password123")
        url = reverse("api_projets_list_create")
        res_create = self.client.post(
            url,
            data=json.dumps({"nom": "Mon Projet R&D", "description": "Sélection d'outils IA"}),
            content_type="application/json",
        )
        self.assertTrue(res_create.json()["ok"])
        res_list = self.client.get(url)
        data = res_list.json()
        self.assertEqual(len(data["projets"]), 1)
        self.assertEqual(data["projets"][0]["nom"], "Mon Projet R&D")

    def test_password_reset_views(self):
        res = self.client.get(reverse("password_reset"))
        self.assertEqual(res.status_code, 200)
        res_done = self.client.get(reverse("password_reset_done"))
        self.assertEqual(res_done.status_code, 200)

    def test_admin_dashboard_moderation(self):
        staff = User.objects.create_user(username="staff", password="password123", is_staff=True)
        self.client.login(username="staff", password="password123")
        outil_pend = OutilIA.objects.create(
            nom="Outil En Attente", description="Test", url_site="https://example.com",
            type_tarification="Gratuit", type_integration="Web", est_valide=False,
        )
        url_admin = reverse("admin_dashboard")
        res_get = self.client.get(url_admin)
        self.assertEqual(res_get.status_code, 200)
        # Validation de l'outil
        self.client.post(url_admin, data={"action": "valider", "outil_id": outil_pend.id})
        outil_pend.refresh_from_db()
        self.assertTrue(outil_pend.est_valide)


# ===========================================================================
# 4. Tests de l'upload de fichiers
# ===========================================================================

@override_settings(
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    UPLOAD_MAX_SIZE_BYTES=5 * 1024 * 1024,
    UPLOAD_ALLOWED_EXTENSIONS={".txt", ".pdf", ".py", ".json"},
)
class FichierContexteTestCase(TestCase):
    """Tests de l'endpoint d'upload, liste et suppression de fichiers de contexte."""

    def setUp(self):
        self.client = Client()
        self.user   = User.objects.create_user(username="fileuser", password="password123")
        UserProfile.objects.update_or_create(user=self.user, defaults={"full_name": "File User", "job_role": "dev"})

    def _upload(self, content=b"contenu de test", name="test.txt"):
        """Helpers : téléverse un fichier via l'API et retourne la réponse."""
        self.client.login(username="fileuser", password="password123")
        fichier = SimpleUploadedFile(name, content, content_type="text/plain")
        return self.client.post(
            reverse("api_upload_fichier"),
            {"fichier": fichier},
            format="multipart",
        )

    def test_upload_succes(self):
        response = self._upload()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(FichierContexte.objects.filter(user=self.user).count(), 1)

    def test_upload_extension_non_autorisee(self):
        response = self._upload(name="virus.exe", content=b"malware")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_upload_doublon_md5(self):
        """Uploader deux fois le même fichier doit retourner ok=True sans doublon."""
        self._upload(content=b"contenu unique")
        response = self._upload(content=b"contenu unique")
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data.get("doublon", False))
        # Un seul fichier doit exister en base
        self.assertEqual(FichierContexte.objects.filter(user=self.user).count(), 1)

    def test_liste_fichiers(self):
        self._upload()
        self.client.login(username="fileuser", password="password123")
        response = self.client.get(reverse("api_liste_fichiers"))
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["total"], 1)

    def test_supprimer_fichier(self):
        self._upload()
        fichier_obj = FichierContexte.objects.get(user=self.user)
        self.client.login(username="fileuser", password="password123")
        response = self.client.delete(
            reverse("api_supprimer_fichier", kwargs={"fichier_id": fichier_obj.id})
        )
        self.assertTrue(response.json()["ok"])
        self.assertEqual(FichierContexte.objects.filter(user=self.user).count(), 0)

    def test_upload_non_authentifie(self):
        fichier = SimpleUploadedFile("test.txt", b"contenu", content_type="text/plain")
        response = self.client.post(
            reverse("api_upload_fichier"),
            {"fichier": fichier},
            format="multipart",
        )
        self.assertEqual(response.status_code, 401)


# ===========================================================================
# 5. Tests du Plan Finder Plus
# ===========================================================================

class PlusPlanTestCase(TestCase):
    """Tests de l'activation du Plan Finder Plus par code d'invitation."""

    def setUp(self):
        self.client = Client()
        self.user   = User.objects.create_user(username="plususer", password="password123")
        UserProfile.objects.update_or_create(user=self.user, defaults={"full_name": "Plus User", "job_role": "dev"})

    def test_activation_code_valide(self):
        CodeAccesPlus.objects.create(code="FINDER-PLUS-2026", max_utilisations=10)
        self.client.login(username="plususer", password="password123")
        response = self.client.post(
            reverse("api_activer_plus"),
            data=json.dumps({"code": "FINDER-PLUS-2026"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["est_abonne_plus"])
        # Vérification en base
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.est_abonne_plus)
        # Le compteur d'utilisations doit être incrémenté
        code = CodeAccesPlus.objects.get(code="FINDER-PLUS-2026")
        self.assertEqual(code.utilisations_actuelles, 1)

    def test_activation_code_invalide(self):
        self.client.login(username="plususer", password="password123")
        response = self.client.post(
            reverse("api_activer_plus"),
            data=json.dumps({"code": "CODE-INEXISTANT"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_activation_code_epuise(self):
        CodeAccesPlus.objects.create(
            code="CODE-EPUISE", max_utilisations=1, utilisations_actuelles=1
        )
        self.client.login(username="plususer", password="password123")
        response = self.client.post(
            reverse("api_activer_plus"),
            data=json.dumps({"code": "CODE-EPUISE"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_deja_abonne(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.est_abonne_plus = True
        profile.save()
        CodeAccesPlus.objects.create(code="EXTRA-CODE", max_utilisations=10)
        self.client.login(username="plususer", password="password123")
        response = self.client.post(
            reverse("api_activer_plus"),
            data=json.dumps({"code": "EXTRA-CODE"}),
            content_type="application/json",
        )
        self.assertTrue(response.json()["ok"])
        # Le code ne doit pas être consommé
        code = CodeAccesPlus.objects.get(code="EXTRA-CODE")
        self.assertEqual(code.utilisations_actuelles, 0)


# ===========================================================================
# 6. Tests du moteur de recherche sémantique TF-IDF
# ===========================================================================

class RechercheSemantiqueTestCase(TestCase):
    """Tests du moteur TF-IDF Python pur."""

    def setUp(self):
        invalider_index()
        self.categorie = Categorie.objects.create(nom="Image", slug="image")
        self.outil1 = OutilIA.objects.create(
            nom="DALL-E",
            description="Génération d'images par intelligence artificielle OpenAI",
            url_site="https://openai.com/dall-e",
            type_tarification="Payant",
            type_integration="API",
            categorie=self.categorie,
            est_valide=True,
        )
        self.outil2 = OutilIA.objects.create(
            nom="GitHub Copilot",
            description="Assistant de génération de code pour les développeurs",
            url_site="https://github.com/features/copilot",
            type_tarification="Payant",
            type_integration="IDE",
            categorie=self.categorie,
            est_valide=True,
        )

    def test_tokenizer_stopwords(self):
        tokens = _tokenizer("un outil pour générer des images")
        self.assertNotIn("un", tokens)
        self.assertNotIn("pour", tokens)
        self.assertNotIn("des", tokens)
        self.assertIn("outil", tokens)
        self.assertIn("générer", tokens)

    def test_recherche_retourne_resultats(self):
        resultats = recherche_semantique("génération images IA")
        self.assertIsInstance(resultats, list)

    def test_recherche_pertinence_images(self):
        """DALL-E doit apparaître dans les résultats pour une recherche sur les images."""
        resultats = recherche_semantique("créer des images avec IA")
        ids = [o.id for o, _ in resultats]
        self.assertIn(self.outil1.id, ids)

    def test_recherche_pertinence_code(self):
        """GitHub Copilot doit apparaître pour une recherche sur la génération de code."""
        resultats = recherche_semantique("générer du code automatiquement")
        ids = [o.id for o, _ in resultats]
        self.assertIn(self.outil2.id, ids)

    def test_recherche_vide(self):
        resultats = recherche_semantique("")
        self.assertEqual(resultats, [])


# ===========================================================================
# 7. Tests du robot de Web Scraping
# ===========================================================================

class ScraperTestCase(TestCase):
    """Tests du robot de Web Scraping autonome FinderScraper."""

    def test_scraper_execution(self):
        scraper = FinderScraper(url_cible="https://httpbin.org/html")
        log = scraper.lancer()
        self.assertIsNotNone(log)
        self.assertGreaterEqual(log.temps_execution, 0.0)
        self.assertTrue(ScraperLog.objects.filter(id=log.id).exists())


# ===========================================================================
# 8. Tests de la commande de rattrapage des profils (Bug B7)
# ===========================================================================

class BackfillProfilesTestCase(TestCase):
    """Tests de la commande `python manage.py backfill_profiles`."""

    def setUp(self):
        self.user = User.objects.create_user(username="legacy", password="password123")
        # Simule un compte créé AVANT l'introduction du signal de profil.
        UserProfile.objects.filter(user=self.user).delete()

    def test_commande_cree_les_profils_manquants(self):
        from django.core.management import call_command

        call_command("backfill_profiles")
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, "legacy")
        self.assertTrue(profile.onboarding_completed)
        self.assertEqual(profile.recherches_restantes, 3)

    def test_commande_dry_run_ne_cree_rien(self):
        from django.core.management import call_command

        call_command("backfill_profiles", "--dry-run")
        self.assertFalse(UserProfile.objects.filter(user=self.user).exists())

    def test_commande_idempotente(self):
        from django.core.management import call_command

        call_command("backfill_profiles")
        call_command("backfill_profiles")
        self.assertEqual(UserProfile.objects.filter(user=self.user).count(), 1)

    def test_commande_sans_manquant(self):
        from django.core.management import call_command

        call_command("backfill_profiles")
        # Tous les profils existent : la seconde exécution ne doit rien créer.
        call_command("backfill_profiles")
        self.assertEqual(UserProfile.objects.filter(user=self.user).count(), 1)
