from django.urls import path

from .views import (
    AuditoriaHomeView,
    LogSegurancaDetailView,
    PoliticaRetencaoCreateView,
    PoliticaRetencaoUpdateView,
    RegistroAuditoriaDetailView,
    SolicitacaoTitularCreateView,
    SolicitacaoTitularUpdateView,
)

app_name = "auditoria"

urlpatterns = [
    path("", AuditoriaHomeView.as_view(), name="home"),
    path("registros/<uuid:pk>/", RegistroAuditoriaDetailView.as_view(), name="registro_detalhe"),
    path("logs/<uuid:pk>/", LogSegurancaDetailView.as_view(), name="log_detalhe"),
    path("politicas/nova/", PoliticaRetencaoCreateView.as_view(), name="politica_nova"),
    path("politicas/<uuid:pk>/editar/", PoliticaRetencaoUpdateView.as_view(), name="politica_editar"),
    path("solicitacoes/nova/", SolicitacaoTitularCreateView.as_view(), name="solicitacao_nova"),
    path("solicitacoes/<uuid:pk>/editar/", SolicitacaoTitularUpdateView.as_view(), name="solicitacao_editar"),
]
