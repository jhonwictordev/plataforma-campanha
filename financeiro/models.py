from django.db import models

from core.models import ModeloCampanha


class CategoriaFinanceira(ModeloCampanha):
    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, db_index=True)

    def __str__(self):
        return self.nome


class CentroCusto(ModeloCampanha):
    nome = models.CharField(max_length=120)
    codigo = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.nome


class ParceiroFinanceiro(ModeloCampanha):
    nome = models.CharField(max_length=255)
    documento = models.CharField(max_length=20, blank=True)
    tipo = models.CharField(max_length=20, default="fornecedor", db_index=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.nome


class LancamentoFinanceiro(ModeloCampanha):
    class Tipos(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"
        DOACAO = "doacao", "Doação"

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
    status = models.CharField(max_length=20, default="pendente", db_index=True)
    forma_pagamento = models.CharField(max_length=50, blank=True)
    numero_documento = models.CharField(max_length=50, blank=True)
    comprovante = models.FileField(upload_to="financeiro/comprovantes/", blank=True, null=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Lançamento financeiro"
        verbose_name_plural = "Lançamentos financeiros"
