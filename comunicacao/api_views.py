from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_COMUNICACAO_ESCRITA, PAPEIS_COMUNICACAO_LEITURA

from .models import CampanhaComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem
from .serializers import (
    CampanhaComunicacaoSerializer,
    EnvioComunicacaoSerializer,
    ListaBloqueioSerializer,
    ModeloMensagemSerializer,
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
