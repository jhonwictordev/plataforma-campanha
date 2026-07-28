from django.db import models

from core.models import ModeloCampanha


class RegistroAuditoria(ModeloCampanha):
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


class LogSeguranca(ModeloCampanha):
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
