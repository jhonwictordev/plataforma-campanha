from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from agenda.api_views import EventoAgendaViewSet
from auditoria.api_views import (
    LogSegurancaViewSet,
    PoliticaRetencaoDadosViewSet,
    RegistroAuditoriaViewSet,
    SolicitacaoTitularDadosViewSet,
)
from campanhas.api_views import CampanhaViewSet
from comunicacao.api_views import (
    CampanhaComunicacaoViewSet,
    EnvioComunicacaoViewSet,
    ListaBloqueioViewSet,
    ModeloMensagemViewSet,
    NotificacaoInternaViewSet,
    WebhookComunicacaoAPIView,
)
from dashboard.api_views import DashboardViewSet
from eleitores.api_views import ContatoCRMViewSet, InteracaoContatoViewSet, TarefaContatoViewSet
from equipe.api_views import ComentarioTarefaEquipeViewSet, IntegranteEquipeViewSet, TarefaEquipeViewSet
from financeiro.api_views import (
    CategoriaFinanceiraViewSet,
    CentroCustoViewSet,
    LancamentoFinanceiroViewSet,
    ParceiroFinanceiroViewSet,
)
from liderancas.api_views import InteracaoLiderancaViewSet, LiderancaViewSet
from mapa_eleitoral.api_views import MapaEleitoralViewSet
from metas.api_views import MetaCampanhaViewSet
from relatorios.api_views import FiltroFavoritoRelatorioViewSet, RelatorioViewSet
from usuarios.api_views import AlterarSenhaAPIView, MeuPerfilAPIView, TokenJWTUsuarioView, UsuarioViewSet
from usuarios.views import CancelarLoginDoisFatoresView, LoginDoisFatoresView, LoginUsuarioView

api_router = DefaultRouter()
api_router.register("agenda-eventos", EventoAgendaViewSet, basename="api-agenda-eventos")
api_router.register("auditoria-registros", RegistroAuditoriaViewSet, basename="api-auditoria-registros")
api_router.register("auditoria-logs", LogSegurancaViewSet, basename="api-auditoria-logs")
api_router.register("auditoria-politicas", PoliticaRetencaoDadosViewSet, basename="api-auditoria-politicas")
api_router.register("auditoria-solicitacoes", SolicitacaoTitularDadosViewSet, basename="api-auditoria-solicitacoes")
api_router.register("campanhas", CampanhaViewSet, basename="api-campanhas")
api_router.register("comunicacao-modelos", ModeloMensagemViewSet, basename="api-comunicacao-modelos")
api_router.register("comunicacao-campanhas", CampanhaComunicacaoViewSet, basename="api-comunicacao-campanhas")
api_router.register("comunicacao-bloqueios", ListaBloqueioViewSet, basename="api-comunicacao-bloqueios")
api_router.register("comunicacao-envios", EnvioComunicacaoViewSet, basename="api-comunicacao-envios")
api_router.register("comunicacao-notificacoes", NotificacaoInternaViewSet, basename="api-comunicacao-notificacoes")
api_router.register("dashboard", DashboardViewSet, basename="api-dashboard")
api_router.register("financeiro-categorias", CategoriaFinanceiraViewSet, basename="api-financeiro-categorias")
api_router.register("financeiro-centros-custo", CentroCustoViewSet, basename="api-financeiro-centros-custo")
api_router.register("financeiro-lancamentos", LancamentoFinanceiroViewSet, basename="api-financeiro-lancamentos")
api_router.register("financeiro-parceiros", ParceiroFinanceiroViewSet, basename="api-financeiro-parceiros")
api_router.register("contatos", ContatoCRMViewSet, basename="api-contatos")
api_router.register("contato-interacoes", InteracaoContatoViewSet, basename="api-contato-interacoes")
api_router.register("contato-tarefas", TarefaContatoViewSet, basename="api-contato-tarefas")
api_router.register("equipe-integrantes", IntegranteEquipeViewSet, basename="api-equipe-integrantes")
api_router.register("equipe-tarefas", TarefaEquipeViewSet, basename="api-equipe-tarefas")
api_router.register("equipe-comentarios", ComentarioTarefaEquipeViewSet, basename="api-equipe-comentarios")
api_router.register("liderancas", LiderancaViewSet, basename="api-liderancas")
api_router.register("lideranca-interacoes", InteracaoLiderancaViewSet, basename="api-lideranca-interacoes")
api_router.register("mapa-eleitoral", MapaEleitoralViewSet, basename="api-mapa-eleitoral")
api_router.register("metas-campanha", MetaCampanhaViewSet, basename="api-metas-campanha")
api_router.register("relatorios", RelatorioViewSet, basename="api-relatorios")
api_router.register("relatorios-favoritos", FiltroFavoritoRelatorioViewSet, basename="api-relatorios-favoritos")
api_router.register("usuarios", UsuarioViewSet, basename="api-usuarios")

urlpatterns = [
    path("", include("core.urls")),
    path("admin/", admin.site.urls),
    path("contas/login/", LoginUsuarioView.as_view(), name="login"),
    path("contas/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("contas/2fa/", LoginDoisFatoresView.as_view(), name="login_2fa"),
    path("contas/2fa/cancelar/", CancelarLoginDoisFatoresView.as_view(), name="login_2fa_cancelar"),
    path("contas/password_change/", auth_views.PasswordChangeView.as_view(), name="password_change"),
    path("contas/password_change/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("contas/password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("contas/password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("contas/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("contas/reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
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
    path("api/v1/comunicacao/webhooks/<str:canal>/", WebhookComunicacaoAPIView.as_view(), name="api-comunicacao-webhook"),
    path("api/v1/auth/token/", TokenJWTUsuarioView.as_view(), name="api-token-obter"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("api/v1/auth/token/verify/", TokenVerifyView.as_view(), name="api-token-verify"),
    path("api/v1/usuarios/me/", MeuPerfilAPIView.as_view(), name="api-usuarios-me"),
    path("api/v1/usuarios/alterar-senha/", AlterarSenhaAPIView.as_view(), name="api-usuarios-alterar-senha"),
    path("api/v1/", include(api_router.urls)),
    path("", include("dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
