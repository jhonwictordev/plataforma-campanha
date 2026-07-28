from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import LancamentoFinanceiro


def resumo_financeiro(queryset):
    hoje = timezone.localdate()
    total_receitas = (
        queryset.filter(tipo__in=[LancamentoFinanceiro.Tipos.RECEITA, LancamentoFinanceiro.Tipos.DOACAO]).aggregate(
            total=Sum("valor_reais")
        )["total"]
        or Decimal("0")
    )
    total_despesas = queryset.filter(tipo=LancamentoFinanceiro.Tipos.DESPESA).aggregate(total=Sum("valor_reais"))[
        "total"
    ] or Decimal("0")
    saldo = total_receitas - total_despesas
    contas_vencidas = queryset.filter(
        tipo=LancamentoFinanceiro.Tipos.DESPESA,
        status=LancamentoFinanceiro.Status.PENDENTE,
        data_vencimento__lt=hoje,
    ).aggregate(total=Sum("valor_reais"))["total"] or Decimal("0")
    contas_a_vencer = queryset.filter(
        tipo=LancamentoFinanceiro.Tipos.DESPESA,
        status=LancamentoFinanceiro.Status.PENDENTE,
        data_vencimento__gte=hoje,
    ).aggregate(total=Sum("valor_reais"))["total"] or Decimal("0")

    return {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo": saldo,
        "contas_vencidas": contas_vencidas,
        "contas_a_vencer": contas_a_vencer,
    }


def top_categorias_despesa(queryset, limite=5):
    return (
        queryset.filter(tipo=LancamentoFinanceiro.Tipos.DESPESA)
        .values("categoria__nome")
        .annotate(total=Sum("valor_reais"))
        .order_by("-total")[:limite]
    )
