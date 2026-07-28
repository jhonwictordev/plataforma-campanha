from django.db import models

from core.models import ModeloCampanha


class EventoAgenda(ModeloCampanha):
    class Tipos(models.TextChoices):
        REUNIAO = "reuniao", "Reunião"
        VISITA = "visita", "Visita"
        CAMINHADA = "caminhada", "Caminhada"
        ENTREVISTA = "entrevista", "Entrevista"
        GRAVACAO = "gravacao", "Gravação"
        COMPROMISSO = "compromisso", "Compromisso do candidato"
        ACAO_DE_RUA = "acao_rua", "Ação de rua"
        EVENTO_INTERNO = "evento_interno", "Evento interno"
        PRAZO = "prazo", "Prazo importante"

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONFIRMADO = "confirmado", "Confirmado"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=25, choices=Tipos.choices)
    data = models.DateField()
    horario_inicial = models.TimeField()
    horario_final = models.TimeField(blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True)
    link_localizacao = models.URLField(blank=True)
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="eventos_responsavel",
        null=True,
        blank=True,
    )
    participantes = models.ManyToManyField("usuarios.Usuario", related_name="eventos_participando", blank=True)
    liderancas_convidadas = models.ManyToManyField(
        "liderancas.Lideranca",
        related_name="eventos_convidados",
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    prioridade = models.CharField(max_length=15, default="media")
    checklist = models.JSONField(default=list, blank=True)
    observacoes = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        verbose_name = "Evento de agenda"
        verbose_name_plural = "Eventos de agenda"
        indexes = [models.Index(fields=["data", "status"]), models.Index(fields=["tipo"])]

    def __str__(self):
        return f"{self.titulo} - {self.data:%d/%m/%Y}"
