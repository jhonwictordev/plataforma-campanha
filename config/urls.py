from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("contas/", include("django.contrib.auth.urls")),
    path("usuarios/", include("usuarios.urls")),
    path("campanhas/", include("campanhas.urls")),
    path("liderancas/", include("liderancas.urls")),
    path("eleitores/", include("eleitores.urls")),
    path("agenda/", include("agenda.urls")),
    path("equipe/", include("equipe.urls")),
    path("metas/", include("metas.urls")),
    path("financeiro/", include("financeiro.urls")),
    path("comunicacao/", include("comunicacao.urls")),
    path("mapa/", include("mapa_eleitoral.urls")),
    path("relatorios/", include("relatorios.urls")),
    path("auditoria/", include("auditoria.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include("dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
