from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from agenda.api_views import EventoAgendaViewSet
from eleitores.api_views import ContatoCRMViewSet
from equipe.api_views import IntegranteEquipeViewSet, TarefaEquipeViewSet
from liderancas.api_views import LiderancaViewSet
from metas.api_views import MetaCampanhaViewSet

api_router = DefaultRouter()
api_router.register("agenda-eventos", EventoAgendaViewSet, basename="api-agenda-eventos")
api_router.register("contatos", ContatoCRMViewSet, basename="api-contatos")
api_router.register("equipe-integrantes", IntegranteEquipeViewSet, basename="api-equipe-integrantes")
api_router.register("equipe-tarefas", TarefaEquipeViewSet, basename="api-equipe-tarefas")
api_router.register("liderancas", LiderancaViewSet, basename="api-liderancas")
api_router.register("metas-campanha", MetaCampanhaViewSet, basename="api-metas-campanha")

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
    path("api/schema/", staff_member_required(SpectacularAPIView.as_view()), name="schema"),
    path(
        "api/docs/",
        staff_member_required(SpectacularSwaggerView.as_view(url_name="schema")),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        staff_member_required(SpectacularRedocView.as_view(url_name="schema")),
        name="redoc",
    ),
    path("api/v1/", include(api_router.urls)),
    path("", include("dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
