from django.urls import path

from .views import (
    CampanhaComunicacaoCreateView,
    CampanhaComunicacaoDetailView,
    CampanhaComunicacaoExecutarAgoraView,
    CampanhaComunicacaoUpdateView,
    ComunicacaoHomeView,
    EnvioComunicacaoUpdateView,
    ListaBloqueioCreateView,
    ListaBloqueioUpdateView,
    ModeloMensagemCreateView,
    ModeloMensagemUpdateView,
    NotificacaoInternaListView,
    NotificacaoInternaMarcarLidaView,
    NotificacaoInternaMarcarTodasLidasView,
)

app_name = "comunicacao"

urlpatterns = [
    path("", ComunicacaoHomeView.as_view(), name="home"),
    path("notificacoes/", NotificacaoInternaListView.as_view(), name="notificacoes"),
    path("notificacoes/marcar-todas/", NotificacaoInternaMarcarTodasLidasView.as_view(), name="notificacoes_marcar_todas"),
    path("notificacoes/<uuid:pk>/marcar-lida/", NotificacaoInternaMarcarLidaView.as_view(), name="notificacao_marcar_lida"),
    path("campanhas/nova/", CampanhaComunicacaoCreateView.as_view(), name="campanha_nova"),
    path("campanhas/<uuid:pk>/", CampanhaComunicacaoDetailView.as_view(), name="campanha_detalhe"),
    path("campanhas/<uuid:pk>/executar/", CampanhaComunicacaoExecutarAgoraView.as_view(), name="campanha_executar"),
    path("campanhas/<uuid:pk>/editar/", CampanhaComunicacaoUpdateView.as_view(), name="campanha_editar"),
    path("modelos/novo/", ModeloMensagemCreateView.as_view(), name="modelo_novo"),
    path("modelos/<uuid:pk>/editar/", ModeloMensagemUpdateView.as_view(), name="modelo_editar"),
    path("bloqueios/novo/", ListaBloqueioCreateView.as_view(), name="bloqueio_novo"),
    path("bloqueios/<uuid:pk>/editar/", ListaBloqueioUpdateView.as_view(), name="bloqueio_editar"),
    path("envios/<uuid:pk>/editar/", EnvioComunicacaoUpdateView.as_view(), name="envio_editar"),
]
