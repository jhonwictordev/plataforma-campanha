from django.urls import path

from .views import (
    AtivarDoisFatoresView,
    CodigosRecuperacaoView,
    DesativarDoisFatoresView,
    PerfilUsuarioView,
    RegenerarCodigosRecuperacaoView,
    SegurancaDoisFatoresView,
)

app_name = "usuarios"

urlpatterns = [
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
