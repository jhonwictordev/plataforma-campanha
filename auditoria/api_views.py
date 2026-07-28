from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_AUDITORIA

from .models import LogSeguranca, PoliticaRetencaoDados, RegistroAuditoria, SolicitacaoTitularDados
from .serializers import (
    LogSegurancaSerializer,
    PoliticaRetencaoDadosSerializer,
    RegistroAuditoriaSerializer,
    SolicitacaoTitularDadosSerializer,
)
from .services import aplicar_solicitacao_titular


class RegistroAuditoriaViewSet(ViewSetCampanhaProtegido):
    queryset = RegistroAuditoria.objects.select_related("campanha", "usuario").order_by("-criado_em", "-pk")
    serializer_class = RegistroAuditoriaSerializer
    niveis_permitidos_leitura = PAPEIS_AUDITORIA
    niveis_permitidos_escrita = PAPEIS_AUDITORIA
    filterset_fields = ("campanha", "acao", "modelo", "usuario")
    search_fields = ("resumo", "modelo", "objeto_id")
    ordering_fields = ("criado_em", "atualizado_em", "acao", "modelo")
    http_method_names = ["get", "head", "options"]


class LogSegurancaViewSet(ViewSetCampanhaProtegido):
    queryset = LogSeguranca.objects.select_related("campanha", "usuario").order_by("-criado_em", "-pk")
    serializer_class = LogSegurancaSerializer
    niveis_permitidos_leitura = PAPEIS_AUDITORIA
    niveis_permitidos_escrita = PAPEIS_AUDITORIA
    filterset_fields = ("campanha", "evento", "severidade", "usuario")
    search_fields = ("evento", "descricao")
    ordering_fields = ("criado_em", "atualizado_em", "evento", "severidade")
    http_method_names = ["get", "head", "options"]


class PoliticaRetencaoDadosViewSet(ViewSetCampanhaProtegido):
    queryset = PoliticaRetencaoDados.objects.select_related("campanha", "responsavel").order_by("tipo_registro", "nome", "pk")
    serializer_class = PoliticaRetencaoDadosSerializer
    niveis_permitidos_leitura = PAPEIS_AUDITORIA
    niveis_permitidos_escrita = PAPEIS_AUDITORIA
    filterset_fields = ("campanha", "tipo_registro", "anonimizar_ao_expirar", "responsavel")
    search_fields = ("nome", "base_legal", "observacoes")
    ordering_fields = ("nome", "tipo_registro", "dias_retencao", "criado_em", "atualizado_em")


class SolicitacaoTitularDadosViewSet(ViewSetCampanhaProtegido):
    queryset = SolicitacaoTitularDados.objects.select_related(
        "campanha",
        "contato_relacionado",
        "lideranca_relacionada",
        "responsavel_interno",
    ).order_by("status", "prazo_resposta", "-criado_em", "-pk")
    serializer_class = SolicitacaoTitularDadosSerializer
    niveis_permitidos_leitura = PAPEIS_AUDITORIA
    niveis_permitidos_escrita = PAPEIS_AUDITORIA
    filterset_fields = ("campanha", "tipo_solicitacao", "status", "responsavel_interno")
    search_fields = ("nome_solicitante", "email_solicitante", "descricao", "resposta_interna", "resultado_execucao")
    ordering_fields = ("prazo_resposta", "executado_em", "data_conclusao", "criado_em", "atualizado_em")

    def _executar_acao(self, instancia, executar_acao):
        if not executar_acao:
            return
        if instancia.status != SolicitacaoTitularDados.Status.CONCLUIDA:
            raise ValidationError({"executar_acao_lgpd": "A solicitacao precisa estar concluida antes da execucao automatica."})
        aplicar_solicitacao_titular(instancia)

    def perform_create(self, serializer):
        executar_acao = serializer.validated_data.pop("executar_acao_lgpd", False)
        if serializer.validated_data.get("status") == SolicitacaoTitularDados.Status.CONCLUIDA:
            serializer.validated_data.setdefault("data_conclusao", timezone.now())
        instancia = serializer.save()
        self._executar_acao(instancia, executar_acao)

    def perform_update(self, serializer):
        executar_acao = serializer.validated_data.pop("executar_acao_lgpd", False)
        if (
            serializer.validated_data.get("status") == SolicitacaoTitularDados.Status.CONCLUIDA
            and not serializer.instance.data_conclusao
        ):
            serializer.validated_data.setdefault("data_conclusao", timezone.now())
        instancia = serializer.save()
        self._executar_acao(instancia, executar_acao)

    @action(detail=True, methods=["post"], url_path="executar")
    def executar(self, request, pk=None):
        solicitacao = self.get_object()
        if solicitacao.status != SolicitacaoTitularDados.Status.CONCLUIDA:
            raise ValidationError({"detail": "Conclua a solicitacao antes de executar a acao LGPD."})
        resultado = aplicar_solicitacao_titular(solicitacao)
        serializer = self.get_serializer(solicitacao)
        return Response({"solicitacao": serializer.data, "resultado": resultado})
