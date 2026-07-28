from django.db import models

from core.models import ModeloCampanha


class ModeloMensagem(ModeloCampanha):
    nome = models.CharField(max_length=120)
    assunto = models.CharField(max_length=255, blank=True)
    conteudo = models.TextField()
    canal = models.CharField(max_length=30, db_index=True)

    def __str__(self):
        return self.nome


class ListaBloqueio(ModeloCampanha):
    contato = models.ForeignKey(
        "eleitores.ContatoCRM",
        on_delete=models.CASCADE,
        related_name="bloqueios_comunicacao",
    )
    canal = models.CharField(max_length=30)
    motivo = models.CharField(max_length=255, blank=True)


class CampanhaComunicacao(ModeloCampanha):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        AGENDADA = "agendada", "Agendada"
        ENVIANDO = "enviando", "Enviando"
        CONCLUIDA = "concluida", "Concluída"
        PAUSADA = "pausada", "Pausada"
        CANCELADA = "cancelada", "Cancelada"

    nome = models.CharField(max_length=255)
    assunto = models.CharField(max_length=255, blank=True)
    conteudo = models.TextField()
    canal = models.CharField(max_length=30, db_index=True)
    destinatarios = models.ManyToManyField("eleitores.ContatoCRM", related_name="campanhas_comunicacao", blank=True)
    data_envio = models.DateTimeField(blank=True, null=True)
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="comunicacoes_responsavel",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    quantidade_programada = models.PositiveIntegerField(default=0)
    quantidade_enviada = models.PositiveIntegerField(default=0)
    quantidade_entregue = models.PositiveIntegerField(default=0)
    quantidade_falha = models.PositiveIntegerField(default=0)
    quantidade_respostas = models.PositiveIntegerField(default=0)
