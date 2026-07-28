from django.db import models
from django.utils.dateparse import parse_date
from django.utils import timezone

from core.models import ModeloCampanha


class CategoriaFinanceira(ModeloCampanha):
    class Tipos(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"
        DOACAO = "doacao", "Doacao"

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=Tipos.choices, db_index=True)

    class Meta:
        verbose_name = "Categoria financeira"
        verbose_name_plural = "Categorias financeiras"
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["tipo"]),
        ]

    def __str__(self):
        return self.nome


class CentroCusto(ModeloCampanha):
    nome = models.CharField(max_length=120)
    codigo = models.CharField(max_length=20, blank=True, db_index=True)

    class Meta:
        verbose_name = "Centro de custo"
        verbose_name_plural = "Centros de custo"
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["codigo"]),
        ]

    def __str__(self):
        return self.nome


class ParceiroFinanceiro(ModeloCampanha):
    class Tipos(models.TextChoices):
        FORNECEDOR = "fornecedor", "Fornecedor"
        DOADOR = "doador", "Doador"
        PRESTADOR = "prestador", "Prestador"
        OUTRO = "outro", "Outro"

    nome = models.CharField(max_length=255)
    documento = models.CharField(max_length=20, blank=True)
    tipo = models.CharField(max_length=20, choices=Tipos.choices, default=Tipos.FORNECEDOR, db_index=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "Parceiro financeiro"
        verbose_name_plural = "Parceiros financeiros"
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["tipo"]),
        ]

    def __str__(self):
        return self.nome


class LancamentoFinanceiro(ModeloCampanha):
    class Tipos(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"
        DOACAO = "doacao", "Doacao"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        LIQUIDADO = "liquidado", "Liquidado"
        CANCELADO = "cancelado", "Cancelado"

    descricao = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=Tipos.choices, db_index=True)
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    valor_reais = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField(blank=True, null=True)
    data_pagamento = models.DateField(blank=True, null=True)
    parceiro = models.ForeignKey(
        ParceiroFinanceiro,
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    responsavel_lancamento = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="lancamentos_financeiros",
        null=True,
        blank=True,
    )
    centro_custo = models.ForeignKey(
        CentroCusto,
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE, db_index=True)
    forma_pagamento = models.CharField(max_length=50, blank=True)
    numero_documento = models.CharField(max_length=50, blank=True)
    comprovante = models.FileField(upload_to="financeiro/comprovantes/", blank=True, null=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Lancamento financeiro"
        verbose_name_plural = "Lancamentos financeiros"
        indexes = [
            models.Index(fields=["tipo", "status"]),
            models.Index(fields=["data_vencimento"]),
            models.Index(fields=["data_pagamento"]),
        ]

    def __str__(self):
        return self.descricao

    @staticmethod
    def _normalizar_data(valor):
        if isinstance(valor, str):
            return parse_date(valor)
        return valor

    @property
    def esta_vencido(self) -> bool:
        if self.status in {self.Status.LIQUIDADO, self.Status.CANCELADO}:
            return False
        data_vencimento = self._normalizar_data(self.data_vencimento)
        if not data_vencimento:
            return False
        return data_vencimento < timezone.localdate()

    def save(self, *args, **kwargs):
        if self.status == self.Status.LIQUIDADO and not self.data_pagamento:
            self.data_pagamento = timezone.localdate()
        super().save(*args, **kwargs)
