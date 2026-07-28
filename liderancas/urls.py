from django.urls import path

from .views import (
    InteracaoLiderancaCreateView,
    InteracaoLiderancaUpdateView,
    LiderancaCreateView,
    LiderancaDetailView,
    LiderancaUpdateView,
    LiderancasHomeView,
)

app_name = "liderancas"

urlpatterns = [
    path("", LiderancasHomeView.as_view(), name="home"),
    path("novo/", LiderancaCreateView.as_view(), name="novo"),
    path("<uuid:lideranca_pk>/interacoes/nova/", InteracaoLiderancaCreateView.as_view(), name="interacao_nova"),
    path("interacoes/<uuid:pk>/editar/", InteracaoLiderancaUpdateView.as_view(), name="interacao_editar"),
    path("<uuid:pk>/", LiderancaDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", LiderancaUpdateView.as_view(), name="editar"),
]
