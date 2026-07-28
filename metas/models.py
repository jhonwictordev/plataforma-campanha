from django.db import models

from core.models import ModeloCampanha


class MetaCampanha(ModeloCampanha):
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=80, db_index=True)
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
    status = models.CharField(max_length=20, default="aberta", db_index=True)
    percentual_conclusao = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Meta"
        verbose_name_plural = "Metas"
