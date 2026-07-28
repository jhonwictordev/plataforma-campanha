import uuid

from django.db import models
from django.utils import timezone

from .managers import GerenciadorAtivo


class ModeloBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    excluido_em = models.DateTimeField(blank=True, null=True)
    ativo = models.BooleanField(default=True, db_index=True)

    objects = GerenciadorAtivo()
    todos_objetos = models.Manager()

    class Meta:
        abstract = True
        ordering = ("-criado_em",)

    def excluir_suavemente(self):
        self.ativo = False
        self.excluido_em = timezone.now()
        self.save(update_fields=["ativo", "excluido_em", "atualizado_em"])


class ModeloCampanha(ModeloBase):
    campanha = models.ForeignKey(
        "campanhas.Campanha",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    class Meta:
        abstract = True
