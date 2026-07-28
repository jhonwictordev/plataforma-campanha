from django.urls import path

from .views import (
    CategoriaFinanceiraCreateView,
    CategoriaFinanceiraUpdateView,
    CentroCustoCreateView,
    CentroCustoUpdateView,
    FinanceiroHomeView,
    LancamentoFinanceiroCreateView,
    LancamentoFinanceiroDetailView,
    LancamentoFinanceiroUpdateView,
    ParceiroFinanceiroCreateView,
    ParceiroFinanceiroUpdateView,
)

app_name = "financeiro"

urlpatterns = [
    path("", FinanceiroHomeView.as_view(), name="home"),
    path("lancamentos/novo/", LancamentoFinanceiroCreateView.as_view(), name="lancamento_novo"),
    path("lancamentos/<uuid:pk>/", LancamentoFinanceiroDetailView.as_view(), name="lancamento_detalhe"),
    path("lancamentos/<uuid:pk>/editar/", LancamentoFinanceiroUpdateView.as_view(), name="lancamento_editar"),
    path("categorias/nova/", CategoriaFinanceiraCreateView.as_view(), name="categoria_nova"),
    path("categorias/<uuid:pk>/editar/", CategoriaFinanceiraUpdateView.as_view(), name="categoria_editar"),
    path("centros-custo/novo/", CentroCustoCreateView.as_view(), name="centro_custo_novo"),
    path("centros-custo/<uuid:pk>/editar/", CentroCustoUpdateView.as_view(), name="centro_custo_editar"),
    path("parceiros/novo/", ParceiroFinanceiroCreateView.as_view(), name="parceiro_novo"),
    path("parceiros/<uuid:pk>/editar/", ParceiroFinanceiroUpdateView.as_view(), name="parceiro_editar"),
]
