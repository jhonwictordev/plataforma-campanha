from django.db import models
from django.utils import timezone


class QuerySetAtivo(models.QuerySet):
    def ativos(self):
        return self.filter(excluido_em__isnull=True, ativo=True)

    def inativos(self):
        return self.filter(ativo=False)

    def excluir_suavemente(self):
        return self.update(ativo=False, excluido_em=timezone.now())


class GerenciadorAtivo(models.Manager):
    def get_queryset(self):
        return QuerySetAtivo(self.model, using=self._db).ativos()
