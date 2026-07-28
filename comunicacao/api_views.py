from django.utils import timezone

from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_COMUNICACAO_ESCRITA, PAPEIS_COMUNICACAO_LEITURA, PAPEIS_TODOS_MODULOS
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import CampanhaComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem, NotificacaoInterna
from .serializers import (
    CampanhaComunicacaoSerializer,
    EnvioComunicacaoSerializer,
    ListaBloqueioSerializer,
    ModeloMensagemSerializer,
    NotificacaoInternaSerializer,
)


class ModeloMensagemViewSet(ViewSetCampanhaProtegido):
    queryset = ModeloMensagem.objects.select_related("campanha").order_by("canal", "nome", "pk")
    serializer_class = ModeloMensagemSerializer
    niveis_permitidos_leitura = PAPEIS_COMUNICACAO_LEITURA
    niveis_permitidos_escrita = PAPEIS_COMUNICACAO_ESCRITA
    filterset_fields = ("canal",)
    search_fields = ("nome", "assunto", "conteudo")
    ordering_fields = ("nome", "canal", "criado_em")


class CampanhaComunicacaoViewSet(ViewSetCampanhaProtegido):
    queryset = CampanhaComunicacao.objects.select_related("campanha", "modelo_mensagem", "responsavel").order_by(
        "data_envio",
        "pk",
    )
    serializer_class = CampanhaComunicacaoSerializer
    niveis_permitidos_leitura = PAPEIS_COMUNICACAO_LEITURA
    niveis_permitidos_escrita = PAPEIS_COMUNICACAO_ESCRITA
    filterset_fields = ("canal", "status", "responsavel")
    search_fields = ("nome", "assunto", "conteudo")
    ordering_fields = ("data_envio", "nome", "criado_em", "atualizado_em")


class ListaBloqueioViewSet(ViewSetCampanhaProtegido):
    queryset = ListaBloqueio.objects.select_related("campanha", "contato", "solicitado_por").order_by("-criado_em", "pk")
    serializer_class = ListaBloqueioSerializer
    niveis_permitidos_leitura = PAPEIS_COMUNICACAO_LEITURA
    niveis_permitidos_escrita = PAPEIS_COMUNICACAO_ESCRITA
    filterset_fields = ("canal", "contato")
    search_fields = ("contato__nome_completo", "motivo")
    ordering_fields = ("criado_em", "canal", "atualizado_em")


class EnvioComunicacaoViewSet(ViewSetCampanhaProtegido):
    queryset = EnvioComunicacao.objects.select_related(
        "campanha",
        "campanha_comunicacao",
        "contato",
        "responsavel_registro",
    ).order_by("-atualizado_em", "pk")
    serializer_class = EnvioComunicacaoSerializer
    niveis_permitidos_leitura = PAPEIS_COMUNICACAO_LEITURA
    niveis_permitidos_escrita = PAPEIS_COMUNICACAO_ESCRITA
    filterset_fields = ("canal", "status", "campanha_comunicacao", "contato", "cancelou_inscricao")
    search_fields = ("contato__nome_completo", "erro_envio", "resposta_recebida", "mensagem_enviada")
    ordering_fields = ("data_programada", "data_envio", "data_entrega", "data_resposta", "criado_em", "atualizado_em")


class NotificacaoInternaViewSet(ViewSetCampanhaProtegido):
    queryset = NotificacaoInterna.objects.select_related("campanha", "usuario_destinatario").order_by("-criado_em", "-pk")
    serializer_class = NotificacaoInternaSerializer
    niveis_permitidos_leitura = PAPEIS_TODOS_MODULOS
    niveis_permitidos_escrita = PAPEIS_TODOS_MODULOS
    filterset_fields = ("categoria", "lida_em")
    search_fields = ("titulo", "mensagem", "origem_modelo")
    ordering_fields = ("criado_em", "enviada_em", "lida_em", "atualizado_em")
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(usuario_destinatario=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        instancia = self.get_object()
        if instancia.usuario_destinatario_id != request.user.id:
            raise PermissionDenied("Voce nao pode alterar notificacoes de outro usuario.")
        instancia.lida_em = timezone.now()
        instancia.save(update_fields=["lida_em", "atualizado_em"])
        serializer = self.get_serializer(instancia)
        return Response(serializer.data)
