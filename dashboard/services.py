from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from comunicacao.models import EnvioComunicacao
from eleitores.models import ContatoCRM
from equipe.models import TarefaEquipe

PERIODOS_DASHBOARD = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
}


def resolver_periodo(periodo: str | None):
    periodo_normalizado = periodo if periodo in PERIODOS_DASHBOARD else "30d"
    hoje = timezone.localdate()
    dias = PERIODOS_DASHBOARD[periodo_normalizado]
    inicio = hoje - timedelta(days=dias - 1)
    return periodo_normalizado, inicio, hoje


def lista_periodos():
    return [
        ("7d", "Ultimos 7 dias"),
        ("30d", "Ultimos 30 dias"),
        ("90d", "Ultimos 90 dias"),
        ("180d", "Ultimos 180 dias"),
    ]


def serie_evolucao_cadastros(contatos, liderancas, data_inicial, data_final):
    totais_contatos = {
        item["periodo"]: item["total"]
        for item in contatos.filter(criado_em__date__range=(data_inicial, data_final))
        .annotate(periodo=TruncDate("criado_em"))
        .values("periodo")
        .annotate(total=Count("id"))
    }
    totais_liderancas = {
        item["periodo"]: item["total"]
        for item in liderancas.filter(criado_em__date__range=(data_inicial, data_final))
        .annotate(periodo=TruncDate("criado_em"))
        .values("periodo")
        .annotate(total=Count("id"))
    }

    serie = []
    data_cursor = data_inicial
    while data_cursor <= data_final:
        serie.append(
            {
                "rotulo": data_cursor.strftime("%d/%m"),
                "contatos": totais_contatos.get(data_cursor, 0),
                "liderancas": totais_liderancas.get(data_cursor, 0),
            }
        )
        data_cursor += timedelta(days=1)
    return serie


def distribuicao_status_contatos(contatos):
    rotulos = dict(ContatoCRM.EtapasFunil.choices)
    return [
        {
            "rotulo": rotulos.get(item["status_funil"], item["status_funil"]),
            "total": item["total"],
        }
        for item in contatos.values("status_funil").annotate(total=Count("id")).order_by("-total", "status_funil")
    ]


def _top_por_campo(queryset, campo, limite=8, rotulo_padrao="Nao informado"):
    contador = defaultdict(int)
    for valor in queryset.values_list(campo, flat=True):
        contador[(valor or "").strip() or rotulo_padrao] += 1
    itens = [{"rotulo": chave, "total": total} for chave, total in contador.items()]
    itens.sort(key=lambda item: (-item["total"], item["rotulo"]))
    return itens[:limite]


def contatos_por_cidade(contatos, limite=8):
    return _top_por_campo(contatos, "cidade", limite=limite)


def contatos_por_bairro(contatos, limite=8):
    return _top_por_campo(contatos, "bairro", limite=limite)


def liderancas_por_regiao(liderancas, limite=8):
    return _top_por_campo(liderancas, "regiao_eleitoral", limite=limite)


def metas_por_equipe(metas, limite=8):
    grupos = {}
    for meta in metas:
        chave = "Sem equipe"
        if meta.equipe_id and meta.equipe:
            chave = meta.equipe.nome
        elif meta.responsavel_id and meta.responsavel:
            chave = meta.responsavel.nome_completo

        atual = grupos.setdefault(
            chave,
            {
                "rotulo": chave,
                "valor_esperado": Decimal("0"),
                "valor_realizado": Decimal("0"),
            },
        )
        atual["valor_esperado"] += meta.valor_esperado or Decimal("0")
        atual["valor_realizado"] += meta.valor_realizado or Decimal("0")

    resultados = []
    for grupo in grupos.values():
        esperado = grupo["valor_esperado"]
        realizado = grupo["valor_realizado"]
        percentual = float((realizado / esperado) * Decimal("100")) if esperado else 0.0
        resultados.append(
            {
                "rotulo": grupo["rotulo"],
                "percentual": round(percentual, 2),
            }
        )

    resultados.sort(key=lambda item: (-item["percentual"], item["rotulo"]))
    return resultados[:limite]


def evolucao_financeira(financeiro, data_inicial, data_final):
    referencias = (
        financeiro.annotate(referencia=Coalesce("data_pagamento", "data_vencimento"))
        .filter(referencia__range=(data_inicial, data_final))
        .annotate(periodo=TruncMonth("referencia"))
        .values("periodo", "tipo")
        .annotate(total=Sum("valor_reais"))
        .order_by("periodo")
    )
    agrupado = defaultdict(lambda: {"receitas": 0.0, "despesas": 0.0})
    for item in referencias:
        periodo = item["periodo"]
        if not periodo:
            continue
        chave = periodo.strftime("%m/%Y")
        total = float(item["total"] or 0)
        if item["tipo"] in {"receita", "doacao"}:
            agrupado[chave]["receitas"] += total
        elif item["tipo"] == "despesa":
            agrupado[chave]["despesas"] += total

    resultados = []
    for chave, valores in sorted(agrupado.items(), key=lambda item: tuple(reversed(item[0].split("/")))):
        resultados.append(
            {
                "rotulo": chave,
                "receitas": round(valores["receitas"], 2),
                "despesas": round(valores["despesas"], 2),
            }
        )
    return resultados


def resumo_financeiro_periodo(financeiro, data_inicial, data_final):
    referencia = financeiro.annotate(referencia=Coalesce("data_pagamento", "data_vencimento")).filter(
        referencia__range=(data_inicial, data_final)
    )
    receitas = referencia.filter(tipo__in=["receita", "doacao"]).aggregate(total=Sum("valor_reais"))["total"] or Decimal("0")
    despesas = referencia.filter(tipo="despesa").aggregate(total=Sum("valor_reais"))["total"] or Decimal("0")
    saldo = receitas - despesas
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": saldo,
    }


def proximos_compromissos(eventos, limite=6):
    hoje = timezone.localdate()
    return (
        eventos.filter(data__gte=hoje)
        .exclude(status__in=["cancelado", "concluido"])
        .order_by("data", "horario_inicial", "pk")[:limite]
    )


def tarefas_atrasadas(tarefas, limite=6):
    agora = timezone.now()
    queryset = tarefas.exclude(status__in=[TarefaEquipe.Status.CONCLUIDO, TarefaEquipe.Status.CANCELADO]).filter(
        prazo__lt=agora
    )
    return queryset.order_by("prazo", "pk")[:limite]


def mapa_cadastros_autorizados(contatos, limite=80):
    pontos = (
        contatos.filter(consentimento_comunicacao=True, latitude__isnull=False, longitude__isnull=False)
        .values("cidade", "bairro", "latitude", "longitude")
        .annotate(total=Count("id"))
        .filter(total__gte=2)
        .order_by("-total", "cidade")[:limite]
    )
    return [
        {
            "lat": float(item["latitude"]),
            "lng": float(item["longitude"]),
            "cidade": item["cidade"],
            "bairro": item["bairro"] or "Nao informado",
            "total": item["total"],
        }
        for item in pontos
    ]


def comunicacao_resumo_periodo(envios, data_inicial, data_final):
    queryset = envios.filter(atualizado_em__date__range=(data_inicial, data_final))
    return {
        "respostas": queryset.filter(status=EnvioComunicacao.Status.RESPONDIDO).count(),
        "falhas": queryset.filter(status=EnvioComunicacao.Status.FALHA).count(),
    }
