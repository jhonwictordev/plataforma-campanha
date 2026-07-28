from django.urls import path

from .views import (
    CampanhaComunicacaoCreateView,
    CampanhaComunicacaoDetailView,
    CampanhaComunicacaoUpdateView,
    ComunicacaoHomeView,
    EnvioComunicacaoUpdateView,
    ListaBloqueioCreateView,
    ListaBloqueioUpdateView,
    ModeloMensagemCreateView,
    ModeloMensagemUpdateView,
)

app_name = "comunicacao"

urlpatterns = [
    path("", ComunicacaoHomeView.as_view(), name="home"),
    path("campanhas/nova/", CampanhaComunicacaoCreateView.as_view(), name="campanha_nova"),
    path("campanhas/<uuid:pk>/", CampanhaComunicacaoDetailView.as_view(), name="campanha_detalhe"),
    path("campanhas/<uuid:pk>/editar/", CampanhaComunicacaoUpdateView.as_view(), name="campanha_editar"),
    path("modelos/novo/", ModeloMensagemCreateView.as_view(), name="modelo_novo"),
    path("modelos/<uuid:pk>/editar/", ModeloMensagemUpdateView.as_view(), name="modelo_editar"),
    path("bloqueios/novo/", ListaBloqueioCreateView.as_view(), name="bloqueio_novo"),
    path("bloqueios/<uuid:pk>/editar/", ListaBloqueioUpdateView.as_view(), name="bloqueio_editar"),
    path("envios/<uuid:pk>/editar/", EnvioComunicacaoUpdateView.as_view(), name="envio_editar"),
]
