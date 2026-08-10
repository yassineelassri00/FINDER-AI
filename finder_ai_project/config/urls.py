"""
Configuration URL racine du projet Finder-AI.

Les erreurs 404 et 500 sont gérées par des vues personnalisées (finder/views.py)
qui retournent du JSON pour les requêtes API et du HTML pour les navigateurs.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from finder.views import handler_404 as custom_404, handler_500 as custom_500

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("finder.urls")),
]

# Service des fichiers statiques et médias en développement
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Gestionnaires d'erreurs globaux
handler404 = custom_404
handler500 = custom_500