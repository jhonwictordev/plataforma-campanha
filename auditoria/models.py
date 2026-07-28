from datetime import timedelta

from django.db import models
from django.utils import timezone

from core.models import ModeloBase, ModeloCampanha


class RegistroAuditoria(ModeloBase):
    campanha = models.ForeignKey(
        "campanhas.Campanha",
        on_delete=models.SET_NULL,
        related_name="registros_auditoria",
        null=True,
        blank=True,
    )
    acao = models.CharField(max_length=50, db_index=True)
    modelo = models.CharField(max_length=120, db_index=True)
    objeto_id = models.CharField(max_length=64, db_index=True)
    resumo = models.CharField(max_length=255)
    dados_anteriores = models.JSONField(default=dict, blank=True)
    dados_novos = models.JSONField(default=dict, blank=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="registros_auditoria",
        null=True,
        blank=True,
    )
    endereco_ip = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Registros de auditoria"
        indexes = [
            models.Index(fields=["modelo", "objeto_id"]),
            models.Index(fields=["acao", "criado_em"]),
        ]


class LogSeguranca(ModeloBase):
    campanha = models.ForeignKey(
        "campanhas.Campanha",
        on_delete=models.SET_NULL,
        related_name="logs_seguranca",
        null=True,
        blank=True,
    )
    evento = models.CharField(max_length=80, db_index=True)
    severidade = models.CharField(max_length=20, default="info", db_index=True)
    descricao = models.TextField()
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="logs_seguranca",
        null=True,
        blank=True,
    )
    endereco_ip = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        verbose_name = "Log de seguranca"
        verbose_name_plural = "Logs de seguranca"
        indexes = [
            models.Index(fields=["evento", "criado_em"]),
            models.Index(fields=["severidade", "criado_em"]),
        ]


class PoliticaRetencaoDados(ModeloCampanha):
    class TiposRegistro(models.TextChoices):
        CONTATOS = "contatos", "Contatos"
        LIDERANCAS = "liderancas", "Liderancas"
        EVENTOS = "eventos", "Eventos"
        EQUIPE = "equipe", "Equipe"
        METAS = "metas", "Metas"
        FINANCEIRO = "financeiro", "Financeiro"
        COMUNICACAO = "comunicacao", "Comunicacao"
        AUDITORIA = "auditoria", "Auditoria"
        SEGURANCA = "seguranca", "Seguranca"

    nome = models.CharField(max_length=120)
    tipo_registro = models.CharField(max_length=30, choices=TiposRegistro.choices, db_index=True)
    base_legal = models.CharField(max_length=120, blank=True)
    dias_retencao = models.PositiveIntegerField(default=365)
    dias_ate_anonimizacao = models.PositiveIntegerField(default=0)
    anonimizar_ao_expirar = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="politicas_retencao",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Politica de retencao"
        verbose_name_plural = "Politicas de retencao"
        indexes = [
            models.Index(fields=["tipo_registro"]),
            models.Index(fields=["campanha", "tipo_registro"]),
        ]

    def __str__(self):
        return self.nome

    def data_limite_retencao(self):
        return timezone.localdate() - timedelta(days=self.dias_retencao)

    def data_limite_anonimizacao(self):
        if not self.dias_ate_anonimizacao:
            return None
        return timezone.localdate() - timedelta(days=self.dias_ate_anonimizacao)


class SolicitacaoTitularDados(ModeloCampanha):
    class TiposSolicitacao(models.TextChoices):
        ACESSO = "acesso", "Acesso"
        CORRECAO = "correcao", "Correcao"
        ANONIMIZACAO = "anonimizacao", "Anonimizacao"
        EXCLUSAO = "exclusao", "Exclusao logica"
        REVOGACAO_CONSENTIMENTO = "revogacao_consentimento", "Revogacao de consentimento"

    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        EM_ANALISE = "em_analise", "Em analise"
        CONCLUIDA = "concluida", "Concluida"
        NEGADA = "negada", "Negada"

    nome_solicitante = models.CharField(max_length=255)
    email_solicitante = models.EmailField(blank=True)
    telefone_solicitante = models.CharField(max_length=20, blank=True)
    canal_origem = models.CharField(max_length=60, blank=True)
    tipo_solicitacao = models.CharField(max_length=30, choices=TiposSolicitacao.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTA, db_index=True)
    descricao = models.TextField()
    contato_relacionado = models.ForeignKey(
        "eleitores.ContatoCRM",
        on_delete=models.SET_NULL,
        related_name="solicitacoes_titular",
        null=True,
        blank=True,
    )
    lideranca_relacionada = models.ForeignKey(
        "liderancas.Lideranca",
        on_delete=models.SET_NULL,
        related_name="solicitacoes_titular",
        null=True,
        blank=True,
    )
    responsavel_interno = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="solicitacoes_titular_responsavel",
        null=True,
        blank=True,
    )
    prazo_resposta = models.DateField(blank=True, null=True)
    resposta_interna = models.TextField(blank=True)
    executado_em = models.DateTimeField(blank=True, null=True)
    resultado_execucao = models.TextField(blank=True)
    data_conclusao = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Solicitacao do titular"
        verbose_name_plural = "Solicitacoes dos titulares"
        indexes = [
            models.Index(fields=["tipo_solicitacao", "status"]),
            models.Index(fields=["prazo_resposta"]),
        ]

    def __str__(self):
        return f"{self.nome_solicitante} - {self.get_tipo_solicitacao_display()}"
