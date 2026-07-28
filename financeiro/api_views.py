from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_FINANCEIRO_ESCRITA, PAPEIS_FINANCEIRO_LEITURA

from .models import CategoriaFinanceira, CentroCusto, LancamentoFinanceiro, ParceiroFinanceiro
from .serializers import (
    CategoriaFinanceiraSerializer,
    CentroCustoSerializer,
    LancamentoFinanceiroSerializer,
    ParceiroFinanceiroSerializer,
)


class CategoriaFinanceiraViewSet(ViewSetCampanhaProtegido):
    queryset = CategoriaFinanceira.objects.select_related("campanha").order_by("tipo", "nome", "pk")
    serializer_class = CategoriaFinanceiraSerializer
    niveis_permitidos_leitura = PAPEIS_FINANCEIRO_LEITURA
    niveis_permitidos_escrita = PAPEIS_FINANCEIRO_ESCRITA
    filterset_fields = ("tipo",)
    search_fields = ("nome",)
    ordering_fields = ("nome", "tipo", "criado_em")


class CentroCustoViewSet(ViewSetCampanhaProtegido):
    queryset = CentroCusto.objects.select_related("campanha").order_by("nome", "pk")
    serializer_class = CentroCustoSerializer
    niveis_permitidos_leitura = PAPEIS_FINANCEIRO_LEITURA
    niveis_permitidos_escrita = PAPEIS_FINANCEIRO_ESCRITA
    filterset_fields = ("codigo",)
    search_fields = ("nome", "codigo")
    ordering_fields = ("nome", "codigo", "criado_em")


class ParceiroFinanceiroViewSet(ViewSetCampanhaProtegido):
    queryset = ParceiroFinanceiro.objects.select_related("campanha").order_by("nome", "pk")
    serializer_class = ParceiroFinanceiroSerializer
    niveis_permitidos_leitura = PAPEIS_FINANCEIRO_LEITURA
    niveis_permitidos_escrita = PAPEIS_FINANCEIRO_ESCRITA
    filterset_fields = ("tipo",)
    search_fields = ("nome", "documento", "email", "telefone")
    ordering_fields = ("nome", "tipo", "criado_em")


class LancamentoFinanceiroViewSet(ViewSetCampanhaProtegido):
    queryset = LancamentoFinanceiro.objects.select_related(
        "campanha",
        "categoria",
        "parceiro",
        "responsavel_lancamento",
        "centro_custo",
    ).order_by("data_vencimento", "pk")
    serializer_class = LancamentoFinanceiroSerializer
    niveis_permitidos_leitura = PAPEIS_FINANCEIRO_LEITURA
    niveis_permitidos_escrita = PAPEIS_FINANCEIRO_ESCRITA
    filterset_fields = ("tipo", "status", "categoria", "centro_custo", "parceiro")
    search_fields = ("descricao", "numero_documento", "observacoes")
    ordering_fields = ("data_vencimento", "data_pagamento", "valor_reais", "criado_em", "atualizado_em")
