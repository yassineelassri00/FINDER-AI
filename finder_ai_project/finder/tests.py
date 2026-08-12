"""
Suite de tests unitaires complète pour l'application Finder-AI.

Organisation :
  ConfigSecuriteTestCase  — Verrous de sécurité settings (S1, S6, Logging)
  ThrottlingTestCase      — Throttling API DRF renvoyant 429 (S2)
  ModelTestCase        — Tests des modèles ORM et de leurs méthodes
  ViewTestCase         — Tests des vues HTML (authentification, navigation)
  APITestCase          — Tests des endpoints API JSON
  FichierContexteTestCase — Tests de l'upload et de la gestion des fichiers
  ServiceFichiersTestCase — Tests des règles de validation des uploads (S5)
  PlusPlanTestCase     — Tests de l'activation du Plan Finder Plus
  RechercheSemantiqueTestCase — Tests du moteur TF-IDF
  ScraperTestCase      — Tests du robot de Web Scraping
"""

import json
import io
from unittest import mock

from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config import settings as settings_module
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
from finder.services.llm_service import RequiresAPIKeyError
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
# 1.bis. Tests de la configuration de sécurité (S1, S6, Logging)
# ===========================================================================

class ConfigSecuriteTestCase(SimpleTestCase):
    """Fail-fast des secrets, verrous HTTPS en production, throttling & logs."""

    def test_secret_key_absente_leve_improperly_configured(self):
        """S1 : sans SECRET_KEY (vide), le serveur refuse de démarrer."""
        with self.assertRaises(ImproperlyConfigured):
            settings_module._verifier_secret_key("")
        # Une clé valide passe sans erreur.
        self.assertEqual(
            settings_module._verifier_secret_key("secret-de-test"), "secret-de-test"
        )

    def test_debug_true_interdit_en_production(self):
        """S1 : DEBUG=True en environnement de production doit faire échouer."""
        with self.assertRaises(ImproperlyConfigured):
            settings_module._verifier_mode_production("production", True)
        # DEBUG reste autorisé en dev et DEBUG=False en prod démarre normalement.
        settings_module._verifier_mode_production("development", True)
        settings_module._verifier_mode_production("production", False)

    def test_https_force_en_production(self):
        """S6 : en production, HTTPS/cookies sécurisés sont incontournables."""
        self.assertTrue(settings_module._force_https_production("production", False))
        self.assertTrue(settings_module._force_https_production("production", True))
        self.assertFalse(settings_module._force_https_production("development", False))

    def test_headers_securite_actives(self):
        """S6 : X-Frame-Options DENY et protections de base sont actives."""
        self.assertEqual(django_settings.X_FRAME_OPTIONS, "DENY")
        self.assertTrue(django_settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertTrue(django_settings.SESSION_COOKIE_HTTPONLY)

    def test_throttling_configure_dans_rest_framework(self):
        """S2 : les classes de throttling par défaut sont actives sur l'API."""
        rf = django_settings.REST_FRAMEWORK
        self.assertIn(
            "rest_framework.throttling.AnonRateThrottle",
            rf["DEFAULT_THROTTLE_CLASSES"],
        )
        self.assertIn(
            "rest_framework.throttling.UserRateThrottle",
            rf["DEFAULT_THROTTLE_CLASSES"],
        )
        self.assertIn("anon", rf["DEFAULT_THROTTLE_RATES"])
        self.assertIn("user", rf["DEFAULT_THROTTLE_RATES"])

    def test_logging_configure(self):
        """Logging : niveau INFO pour Django, WARNING pour les requêtes."""
        self.assertEqual(
            django_settings.LOGGING["loggers"]["django"]["level"], "INFO"
        )
        self.assertEqual(
            django_settings.LOGGING["loggers"]["django.request"]["level"], "WARNING"
        )
        self.assertIn("console", django_settings.LOGGING["handlers"])

    def test_email_backend_repli_console_sans_smtp(self):
        """S3 : sans SMTP, la messagerie tombe sur le backend console."""
        # La logique de repli choisit la console sans hôte SMTP, le SMTP sinon.
        self.assertEqual(
            settings_module._choisir_email_backend(""),
            "django.core.mail.backends.console.EmailBackend",
        )
        self.assertEqual(
            settings_module._choisir_email_backend("smtp.example.com"),
            "django.core.mail.backends.smtp.EmailBackend",
        )
        # Le backend effectif reste toujours un backend valide.
        self.assertIn(
            settings_module.EMAIL_BACKEND,
            (
                "django.core.mail.backends.console.EmailBackend",
                "django.core.mail.backends.smtp.EmailBackend",
            ),
        )
        # (N.B. : Django remplace EMAIL_BACKEND par locmem pendant la suite de
        # tests, d'où l'assertion sur le module config et non sur le settings.)

    def test_limite_corps_de_requete(self):
        """S2 : le corps des requêtes est plafonné (anti-DoS), au-dessus du fichier max."""
        self.assertLessEqual(django_settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 6 * 1024 * 1024)
        self.assertGreater(
            django_settings.DATA_UPLOAD_MAX_MEMORY_SIZE,
            django_settings.UPLOAD_MAX_SIZE_BYTES,
        )
        self.assertLessEqual(django_settings.UPLOAD_MAX_SIZE_BYTES, 5 * 1024 * 1024)


# ===========================================================================
# 1.ter. Tests du throttling DRF (S2)
# ===========================================================================

class ThrottlingTestCase(TestCase):
    """Le throttling DRF doit renvoyer 429 au-delà de la limite autorisée."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(
            username="throttleuser", password="password123"
        )
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"full_name": "T User", "job_role": "dev"}
        )
        self.client.login(username="throttleuser", password="password123")
        self.url = reverse("research_start")
        self.payload = json.dumps({"query": "agent conversationnel"})

    @mock.patch(
        "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
        {"anon": "3/min", "user": "3/min"},
    )
    def test_api_renvoie_429_au_dela_de_la_limite(self):
        """Limite 3 requêtes/min : la 4e requête est bloquée en 429."""
        for _ in range(3):
            self.client.post(self.url, data=self.payload, content_type="application/json")
        response = self.client.post(
            self.url, data=self.payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 429)

    @mock.patch(
        "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
        {"anon": "2/min", "user": "2/min"},
    )
    def test_api_sous_la_limite_n_est_pas_bloquee(self):
        """Sous la limite, le throttling ne bloque pas (pas de 429)."""
        response = self.client.post(
            self.url, data=self.payload, content_type="application/json"
        )
        # Le gating Plan Plus s'applique (402), mais pas le throttling.
        self.assertEqual(response.status_code, 402)


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

    def test_upload_svg_rejete(self):
        """S5 : le format .svg (XSS stocké) est strictement interdit."""
        response = self._upload(
            name="malicious.svg", content=b"<svg onload=alert(1)></svg>"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_upload_html_deguise_en_texte_rejete(self):
        """S5 : un HTML déguisé sous extension .txt doit être rejeté (XSS)."""
        response = self._upload(
            name="payload.txt",
            content=b"<html><script>alert(document.cookie)</script></html>",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_upload_svg_deguise_en_txt_rejete(self):
        """S5 : un SVG déguisé sous extension .txt doit être rejeté."""
        response = self._upload(
            name="payload.txt", content=b"<svg onload=alert(1)>"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_upload_pdf_magic_bytes_invalides_rejete(self):
        """S5 : un fichier .pdf qui n'est pas un vrai PDF est rejeté."""
        response = self._upload(name="faux.pdf", content=b"Ceci nest pas un pdf")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_upload_json_valide_accepte(self):
        """S5 : un fichier .json légitime reste accepté (pas de sur-restriction)."""
        response = self._upload(
            name="config.json", content=b'{"outils": ["ChatGPT", "Copilot"]}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])


# ===========================================================================
# 4.bis. Tests unitaires du service de validation des fichiers (S5)
# ===========================================================================

class ServiceFichiersTestCase(SimpleTestCase):
    """Règles de validation des uploads au niveau du service (files.py)."""

    def test_extension_svg_refusee(self):
        from finder.services.files import extension_autorisee

        self.assertFalse(extension_autorisee("logo.svg"))
        self.assertFalse(extension_autorisee("LOGO.SVG"))

    def test_balisage_deguise_detecte(self):
        """La lecture du type MIME réel rejette le balisage XSS sous texte."""
        from finder.services.files import contenu_coherent_avec_extension

        self.assertFalse(
            contenu_coherent_avec_extension(".txt", b"<script>alert(1)</script>")
        )
        self.assertFalse(
            contenu_coherent_avec_extension(".py", b"<svg onload=alert(1)>")
        )
        self.assertFalse(
            contenu_coherent_avec_extension(".txt", b'<?xml version="1.0"?>')
        )
        self.assertTrue(
            contenu_coherent_avec_extension(".txt", b"contenu de test")
        )

    def test_magic_bytes_images_pdf(self):
        """Les types binaires doivent correspondre à leurs magic bytes."""
        from finder.services.files import contenu_coherent_avec_extension

        self.assertTrue(
            contenu_coherent_avec_extension(".png", b"\x89PNG\r\n\x1a\n" + b"donnees")
        )
        self.assertTrue(contenu_coherent_avec_extension(".pdf", b"%PDF-1.4"))
        self.assertFalse(contenu_coherent_avec_extension(".png", b"<html>"))

    def test_taille_limite_a_5_mo(self):
        """La taille maximale d'un fichier de contexte est plafonnée (5 Mo)."""
        from finder.services.files import taille_autorisee

        self.assertTrue(taille_autorisee(4 * 1024 * 1024))
        self.assertTrue(taille_autorisee(5 * 1024 * 1024))
        self.assertFalse(taille_autorisee(5 * 1024 * 1024 + 1))
        self.assertFalse(taille_autorisee(-1))


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


    def test_recherche_personnalisee_profil_stack(self):
        """Un profil avec technology_stack=['code'] doit booster le score de
        GitHub Copilot (qui correspond) sans toucher à celui de DALL-E."""
        invalider_index()
        resultats_sans_profil = {
            o.id: s for o, s in recherche_semantique("génération")
        }

        user = User.objects.create_user(username="profiluser", password="password123")
        profile = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "full_name": "Profil User",
                "job_role": "dev",
                "technology_stack": ["code"],
                "goals": [],
                "professional_context": "",
            },
        )[0]

        resultats_avec_profil = {
            o.id: s for o, s in recherche_semantique("génération", profil=profile)
        }

        # Copilot (outil2) correspond à la stack "code" : score boosté de 25 %.
        self.assertGreater(
            resultats_avec_profil[self.outil2.id],
            resultats_sans_profil[self.outil2.id],
        )
        self.assertAlmostEqual(
            resultats_avec_profil[self.outil2.id],
            resultats_sans_profil[self.outil2.id] * 1.25,
            places=6,
        )
        # DALL-E (outil1) ne correspond pas : score inchangé.
        self.assertEqual(
            resultats_avec_profil[self.outil1.id],
            resultats_sans_profil[self.outil1.id],
        )
        # Le bonus fait passer Copilot devant DALL-E dans le classement.
        ids_avec = [o.id for o, _ in recherche_semantique("génération", profil=profile)]
        self.assertEqual(ids_avec, [self.outil2.id, self.outil1.id])

    def test_bonus_personnalisation_cap_a_un(self):
        """Le score final ne doit jamais dépasser 1.0 malgré le bonus."""
        from finder.services.vector_search import _bonus_personnalisation

        user = User.objects.create_user(username="bonususer", password="password123")
        profile = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "full_name": "Bonus User",
                "job_role": "dev",
                "technology_stack": ["code"],
                "goals": [],
            },
        )[0]
        from finder.services.vector_search import _tokens_profil

        tokens = _tokens_profil(profile)
        # Copilot correspond totalement au profil : bonus max 1.25.
        bonus = _bonus_personnalisation(self.outil2, tokens)
        self.assertEqual(bonus, 1.25)
        # DALL-E ne correspond pas : aucun bonus.
        self.assertEqual(_bonus_personnalisation(self.outil1, tokens), 1.0)


# ===========================================================================
# 6.bis. Tests du service LLM (Gemini) — P2
# ===========================================================================

class LLMServiceTestCase(TestCase):
    """Résolution de la clé Gemini et génération du résumé IA."""

    def setUp(self):
        self.user = User.objects.create_user(username="llmuser", password="password123")
        # Le signal post_save crée déjà un profil : on le récupère / le complète.
        self.profile = UserProfile.objects.update_or_create(
            user=self.user,
            defaults={"full_name": "LLM User", "job_role": "dev"},
        )[0]
        self.resultats = [
            {
                "nom": "ChatGPT",
                "description": "Agent conversationnel d'OpenAI",
                "categorie": {"nom": "NLP"},
                "score_pertinence": 0.9,
            }
        ]

    def test_cle_personnelle_prime(self):
        """Une clé personnelle est toujours utilisée en premier."""
        from finder.services.llm_service import _resoudre_cle_api

        self.profile.gemini_api_key = "cle-personnelle"
        self.profile.save()
        self.assertEqual(_resoudre_cle_api(self.user), "cle-personnelle")

    @override_settings(GEMINI_SERVER_API_KEY="cle-serveur-test")
    def test_abonne_plus_utilise_la_cle_serveur(self):
        """Sans clé personnelle, un abonné Plus utilise la clé serveur."""
        from finder.services.llm_service import _resoudre_cle_api

        self.profile.est_abonne_plus = True
        self.profile.save()
        self.assertEqual(_resoudre_cle_api(self.user), "cle-serveur-test")

    @override_settings(GEMINI_SERVER_API_KEY="cle-serveur-test")
    def test_non_abonne_sans_cle_leve_RequiresAPIKeyError(self):
        """Gratuit + aucune clé → RequiresAPIKeyError (converti en 402 par l'API)."""
        from finder.services.llm_service import _resoudre_cle_api

        with self.assertRaises(RequiresAPIKeyError):
            _resoudre_cle_api(self.user)

    @override_settings(GEMINI_SERVER_API_KEY="cle-serveur-test")
    @mock.patch(
        "finder.services.llm_service._generer_texte_gemini",
        return_value="Synthèse IA de test.",
    )
    def test_resume_ia_genere(self, mock_gemini):
        """Avec une clé résolvable, Gemini génère le résumé (provenance 'ia')."""
        from finder.services.llm_service import generer_resume_recherche

        self.profile.est_abonne_plus = True
        self.profile.save()
        texte, provenance = generer_resume_recherche(
            "agent conversationnel", self.resultats, self.user
        )
        self.assertEqual(provenance, "ia")
        self.assertEqual(texte, "Synthèse IA de test.")
        mock_gemini.assert_called_once()

    @override_settings(GEMINI_SERVER_API_KEY="cle-serveur-test")
    @mock.patch(
        "finder.services.llm_service._generer_texte_gemini",
        side_effect=TimeoutError("timeout Gemini"),
    )
    def test_panne_gemini_replie_sans_crash(self, mock_gemini):
        """Une panne externe de Gemini ne remonte jamais : repli sans crash."""
        from finder.services.llm_service import generer_resume_recherche

        self.profile.est_abonne_plus = True
        self.profile.save()
        texte, provenance = generer_resume_recherche(
            "agent conversationnel", self.resultats, self.user
        )
        self.assertEqual(provenance, "fallback")
        self.assertIn("ChatGPT", texte)


# ===========================================================================
# 6.ter. Tests d'intégration API — gating Plan Plus et résumé IA (P2)
# ===========================================================================

class RechercheWebGatingTestCase(TestCase):
    """Gating Plan Plus de la recherche web et intégration du résumé IA."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="gatuser", password="password123")
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={"full_name": "Gat User", "job_role": "dev"},
        )
        self.categorie = Categorie.objects.create(nom="Image", slug="image")
        self.outil = OutilIA.objects.create(
            nom="DALL-E",
            description="Génération d'images par intelligence artificielle",
            url_site="https://openai.com/dall-e",
            type_tarification="Payant",
            type_integration="API",
            categorie=self.categorie,
            est_valide=True,
        )
        self.client.login(username="gatuser", password="password123")
        from finder.services.vector_search import invalider_index

        invalider_index()

    def test_mode_web_explicite_requiert_plan_plus(self):
        """source_mode='web' sans abonnement → 402 Payment Required."""
        response = self.client.post(
            reverse("api_recherche_workspace"),
            data=json.dumps({"q": "génération images", "source_mode": "web"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 402)
        self.assertFalse(response.json()["ok"])
        self.assertIn("Plan Plus", response.json()["error"])

    def test_mode_hybride_gratuit_se_replie_sur_le_catalogue(self):
        """source_mode='hybrid' sans abonnement → 200, web_gated=True, pas de web."""
        response = self.client.post(
            reverse("api_recherche_workspace"),
            data=json.dumps({"q": "génération images", "source_mode": "hybrid"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["web_gated"])
        self.assertEqual(data["web_results"], [])
        self.assertEqual(data["preferences_appliquees"]["source_mode_effectif"], "catalog")

    def test_mode_web_abonne_plus_declenche_tavily(self):
        """Un abonné Plus en mode hybride déclenche réellement le client Tavily."""
        profile = UserProfile.objects.get(user=self.user)
        profile.est_abonne_plus = True
        profile.save()

        mock_web = [
            {
                "title": "Article IA",
                "url": "https://exemple.fr/ia",
                "domain": "exemple.fr",
                "content": "Extrait pertinent",
                "score": 0.9,
            }
        ]
        with mock.patch(
            "finder.api_views.rechercher_web_tavily", return_value=mock_web
        ):
            response = self.client.post(
                reverse("api_recherche_workspace"),
                data=json.dumps({"q": "génération images", "source_mode": "hybrid"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["web_gated"])
        self.assertEqual(len(data["web_results"]), 1)
        self.assertEqual(data["web_results"][0]["title"], "Article IA")

    def test_resume_ia_explicite_sans_cle_renvoie_402(self):
        """resume_ia=True sans clé Gemini résolvable → 402."""
        response = self.client.post(
            reverse("api_recherche_workspace"),
            data=json.dumps({"q": "génération images", "resume_ia": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 402)
        self.assertIn("Clé Gemini manquante", response.json()["error"])

    def test_resume_ia_remplace_la_synthese(self):
        """Quand Gemini répond, la synthèse exposée est le résumé IA."""
        with mock.patch(
            "finder.api_views.generer_resume_recherche",
            return_value=("Résumé IA généré par Gemini.", "ia"),
        ):
            response = self.client.post(
                reverse("api_recherche_workspace"),
                data=json.dumps({"q": "génération images"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["resume_ia_active"])
        self.assertEqual(data["synthese"], "Résumé IA généré par Gemini.")
        self.assertEqual(data["resume_ia"], "Résumé IA généré par Gemini.")

    def test_resume_ia_panne_replie_sans_erreur(self):
        """Une panne Gemini (sans clé) ne fait pas échouer la recherche (200)."""
        with mock.patch(
            "finder.api_views.generer_resume_recherche",
            side_effect=RequiresAPIKeyError("pas de clé"),
        ):
            response = self.client.post(
                reverse("api_recherche_workspace"),
                data=json.dumps({"q": "génération images"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["resume_ia_active"])
        self.assertIsNone(data["resume_ia"])
        self.assertTrue(data["synthese"])

    def test_research_start_requiert_plan_plus(self):
        """Le endpoint /api/research/ (tâche Tavily) refuse les non-Plus en 402."""
        response = self.client.post(
            reverse("research_start"),
            data=json.dumps({"query": "agent conversationnel"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 402)


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
