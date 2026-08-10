from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finder", "0007_codeaccesplus_alter_avis_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="professional_context",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="gemini_api_key",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="search_preferences",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="ui_preferences",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
