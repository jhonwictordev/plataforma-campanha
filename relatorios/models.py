from django.db import models

from core.models import ModeloCampanha


class FiltroFavoritoRelatorio(ModeloCampanha):
    nome = models.CharField(max_length=120)
    tipo_relatorio = models.CharField(max_length=60, db_index=True)
    filtros = models.JSONField(default=dict)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="filtros_favoritos_relatorio",
    )

    def __str__(self):
        return self.nome
