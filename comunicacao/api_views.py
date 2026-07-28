from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework import status
from django.utils import timezone

from core.api import ViewSetCampanhaProtegido
from core.permissions import (
    PAPEIS_COMUNICACAO_ESCRITA,
    PAPEIS_COMUNICACAO_LEITURA,
    PAPEIS_TODOS_MODULOS,
    usuario_tem_nivel,
)
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView

from .models import (
    CampanhaComunicacao,
    CanalComunicacao,
    EnvioComunicacao,
    ListaBloqueio,
    ModeloMensagem,
    NotificacaoInterna,
)
from .serializers import (
    CampanhaComunicacaoSerializer,
    EnvioComunicacaoSerializer,
    ListaBloqueioSerializer,
    ModeloMensagemSerializer,
    NotificacaoInternaSerializer,
)
from .services import processar_campanha_comunicacao, receber_webhook_comunicacao
from .services import reprocessar_envio_individual


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

    @action(detail=True, methods=["post"], url_path="executar")
    def executar(self, request, pk=None):
        if not usuario_tem_nivel(request.user, PAPEIS_COMUNICACAO_ESCRITA):
            raise PermissionDenied("Voce nao possui permissao para executar campanhas de comunicacao.")
        campanha = self.get_object()
        resumo = processar_campanha_comunicacao(campanha, referencia=timezone.now(), forcar_execucao=True)
        serializer = self.get_serializer(campanha)
        return Response({"campanha": serializer.data, "processamento": resumo})


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

    @action(detail=True, methods=["post"], url_path="reprocessar")
    def reprocessar(self, request, pk=None):
        if not usuario_tem_nivel(request.user, PAPEIS_COMUNICACAO_ESCRITA):
            raise PermissionDenied("Voce nao possui permissao para reprocessar envios.")
        envio = self.get_object()
        resumo = reprocessar_envio_individual(envio)
        serializer = self.get_serializer(envio)
        return Response({"envio": serializer.data, "processamento": resumo})


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


class WebhookComunicacaoAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    @extend_schema(
        tags=["comunicacao"],
        request=OpenApiTypes.OBJECT,
        responses={
            200: inline_serializer(
                name="WebhookComunicacaoSucessoSerializer",
                fields={
                    "detail": serializers.CharField(),
                    "status": serializers.CharField(required=False),
                    "registro_id": serializers.CharField(required=False, allow_blank=True),
                    "envio_id": serializers.CharField(required=False, allow_blank=True),
                },
            ),
            202: inline_serializer(
                name="WebhookComunicacaoAceitoSerializer",
                fields={
                    "detail": serializers.CharField(),
                    "status": serializers.CharField(required=False),
                    "registro_id": serializers.CharField(required=False, allow_blank=True),
                },
            ),
            403: inline_serializer(
                name="WebhookComunicacaoErroSerializer",
                fields={
                    "detail": serializers.CharField(),
                    "status": serializers.CharField(required=False),
                    "registro_id": serializers.CharField(required=False, allow_blank=True),
                },
            ),
        },
    )
    def post(self, request, canal):
        canais_validos = {
            CanalComunicacao.EMAIL,
            CanalComunicacao.WHATSAPP,
            CanalComunicacao.SMS,
        }
        if canal not in canais_validos:
            return Response(
                {"detail": "Canal de webhook nao suportado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        token = (request.headers.get("X-Webhook-Token") or "").strip()
        resultado = receber_webhook_comunicacao(
            canal=canal,
            payload=request.data if isinstance(request.data, dict) else {},
            token=token,
            endereco_ip=request.META.get("REMOTE_ADDR"),
        )
        return Response(
            {"detail": resultado["mensagem"], **{k: v for k, v in resultado.items() if k not in {"mensagem", "status_http"}}},
            status=resultado["status_http"],
        )
