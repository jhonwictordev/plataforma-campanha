from django.urls import path

from .views import (
    AtivarDoisFatoresView,
    CodigosRecuperacaoView,
    DesativarDoisFatoresView,
    PerfilUsuarioView,
    RegenerarCodigosRecuperacaoView,
    SegurancaDoisFatoresView,
    UsuarioCreateView,
    UsuarioDeleteView,
    UsuarioDetailView,
    UsuarioListView,
    UsuarioUpdateView,
)

app_name = "usuarios"

urlpatterns = [
    path("", UsuarioListView.as_view(), name="lista"),
    path("novo/", UsuarioCreateView.as_view(), name="novo"),
    path("<int:pk>/", UsuarioDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", UsuarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", UsuarioDeleteView.as_view(), name="excluir"),
    path("perfil/", PerfilUsuarioView.as_view(), name="perfil"),
    path("seguranca/dois-fatores/", SegurancaDoisFatoresView.as_view(), name="dois_fatores"),
    path("seguranca/dois-fatores/ativar/", AtivarDoisFatoresView.as_view(), name="dois_fatores_ativar"),
    path("seguranca/dois-fatores/desativar/", DesativarDoisFatoresView.as_view(), name="dois_fatores_desativar"),
    path("seguranca/dois-fatores/codigos/", CodigosRecuperacaoView.as_view(), name="dois_fatores_codigos"),
    path(
        "seguranca/dois-fatores/codigos/regenerar/",
        RegenerarCodigosRecuperacaoView.as_view(),
        name="dois_fatores_regenerar",
    ),
]
