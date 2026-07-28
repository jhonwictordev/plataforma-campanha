from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from core.models import ModeloCampanha


class MetaCampanha(ModeloCampanha):
    class Tipos(models.TextChoices):
        NOVOS_CONTATOS = "novos_contatos", "Novos contatos"
        APOIADORES_CADASTRADOS = "apoiadores_cadastrados", "Apoiadores cadastrados"
        LIDERANCAS_CONQUISTADAS = "liderancas_conquistadas", "Liderancas conquistadas"
        EVENTOS_REALIZADOS = "eventos_realizados", "Eventos realizados"
        PARTICIPANTES_EVENTOS = "participantes_eventos", "Participantes em eventos"
        VOLUNTARIOS_CADASTRADOS = "voluntarios_cadastrados", "Voluntarios cadastrados"
        BAIRROS_VISITADOS = "bairros_visitados", "Bairros visitados"
        MUNICIPIOS_VISITADOS = "municipios_visitados", "Municipios visitados"
        LIGACOES_REALIZADAS = "ligacoes_realizadas", "Ligacoes realizadas"
        MENSAGENS_ENVIADAS = "mensagens_enviadas", "Mensagens enviadas"
        DOACOES_REGISTRADAS = "doacoes_registradas", "Doacoes registradas"
        TAREFAS_CONCLUIDAS = "tarefas_concluidas", "Tarefas concluidas"

    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        EM_RISCO = "em_risco", "Em risco"
        CONCLUIDA = "concluida", "Concluida"
        ATRASADA = "atrasada", "Atrasada"
        CANCELADA = "cancelada", "Cancelada"

    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=80, choices=Tipos.choices, db_index=True)
    valor_esperado = models.DecimalField(max_digits=12, decimal_places=2)
    valor_realizado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    data_inicial = models.DateField()
    data_final = models.DateField()
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="metas_responsavel",
        null=True,
        blank=True,
    )
    equipe = models.ForeignKey(
        "equipe.IntegranteEquipe",
        on_delete=models.SET_NULL,
        related_name="metas",
        null=True,
        blank=True,
    )
    regiao = models.CharField(max_length=120, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTA, db_index=True)
    percentual_conclusao = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Meta"
        verbose_name_plural = "Metas"

    def __str__(self):
        return self.nome

    def calcular_percentual(self) -> Decimal:
        if not self.valor_esperado:
            return Decimal("0.00")
        percentual = (self.valor_realizado / self.valor_esperado) * Decimal("100")
        return percentual.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.percentual_conclusao = self.calcular_percentual()
        super().save(*args, **kwargs)
