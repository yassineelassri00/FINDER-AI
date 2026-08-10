# Generated manually for Finder-AI onboarding preferences.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("finder", "0002_researchjob_researchresult_source"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("organization", models.CharField(blank=True, max_length=150)),
                ("job_role", models.CharField(max_length=100)),
                ("experience_level", models.CharField(blank=True, max_length=50)),
                ("goals", models.JSONField(blank=True, default=list)),
                ("research_sources", models.JSONField(blank=True, default=list)),
                ("technology_stack", models.JSONField(blank=True, default=list)),
                ("budget_preference", models.CharField(blank=True, max_length=50)),
                ("result_style", models.CharField(choices=[("decision", "Décision rapide"), ("balanced", "Vue équilibrée"), ("detailed", "Analyse détaillée")], default="balanced", max_length=20)),
                ("preferred_language", models.CharField(default="fr", max_length=10)),
                ("watch_frequency", models.CharField(default="on_demand", max_length=30)),
                ("onboarding_completed", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="finder_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
