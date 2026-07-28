from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone

PERIODO_OPCOES = (
    ("30d", "Ultimos 30 dias"),
    ("90d", "Ultimos 90 dias"),
    ("180d", "Ultimos 180 dias"),
)

CAMADA_OPCOES = (
    ("consolidado", "Todas as camadas"),
    ("contatos", "Contatos autorizados"),
    ("liderancas", "Liderancas com consentimento"),
    ("eventos", "Eventos mapeados"),
    ("equipes", "Atuacao das equipes"),
)


def lista_periodos():
    return PERIODO_OPCOES


def lista_camadas():
    return CAMADA_OPCOES


def resolver_periodo(periodo: str | None):
    periodo_valido = {item[0] for item in PERIODO_OPCOES}
    periodo = periodo if periodo in periodo_valido else "90d"
    dias = {"30d": 30, "90d": 90, "180d": 180}[periodo]
    data_final = timezone.localdate()
    data_inicial = data_final - timedelta(days=dias - 1)
    return periodo, data_inicial, data_final


def resolver_camada(camada: str | None) -> str:
    camadas_validas = {item[0] for item in CAMADA_OPCOES}
    return camada if camada in camadas_validas else "consolidado"


def _float(valor):
    if valor is None:
        return None
    return float(valor)


def _top_por_campo(queryset, campo: str, limite: int = 5):
    itens = (
        queryset.exclude(**{f"{campo}__exact": ""})
        .values(campo)
        .annotate(total=Count("id"))
        .order_by("-total", campo)[:limite]
    )
    return [{"rotulo": item[campo], "total": item["total"]} for item in itens if item[campo]]


def contatos_agregados(contatos, minimo_total: int = 2):
    registros = (
        contatos.filter(
            consentimento_comunicacao=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .exclude(cidade="")
        .values("cidade", "bairro")
        .annotate(total=Count("id"), lat=Avg("latitude"), lng=Avg("longitude"))
        .filter(total__gte=minimo_total)
        .order_by("-total", "cidade", "bairro")
    )
    retorno = []
    for item in registros:
        retorno.append(
            {
                "camada": "contatos",
                "cidade": item["cidade"],
                "bairro": item["bairro"] or "",
                "lat": _float(item["lat"]),
                "lng": _float(item["lng"]),
                "total": item["total"],
                "popup": (
                    f"{item['cidade']} / {item['bairro']}<br>{item['total']} contatos autorizados"
                    if item["bairro"]
                    else f"{item['cidade']}<br>{item['total']} contatos autorizados"
                ),
            }
        )
    return retorno


def liderancas_agregadas(liderancas, minimo_total: int = 2):
    registros = (
        liderancas.filter(
            consentimento_dados=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .exclude(cidade="")
        .values("cidade", "regiao_eleitoral")
        .annotate(
            total=Count("id"),
            lat=Avg("latitude"),
            lng=Avg("longitude"),
            apoiadores=Sum("apoiadores_estimados"),
        )
        .filter(total__gte=minimo_total)
        .order_by("-total", "cidade", "regiao_eleitoral")
    )
    retorno = []
    for item in registros:
        regiao = item["regiao_eleitoral"] or "Regiao nao informada"
        retorno.append(
            {
                "camada": "liderancas",
                "cidade": item["cidade"],
                "regiao": regiao,
                "lat": _float(item["lat"]),
                "lng": _float(item["lng"]),
                "total": item["total"],
                "apoiadores_estimados": int(item["apoiadores"] or 0),
                "popup": (
                    f"{regiao} / {item['cidade']}<br>"
                    f"{item['total']} liderancas com consentimento<br>"
                    f"{int(item['apoiadores'] or 0)} apoiadores estimados"
                ),
            }
        )
    return retorno


def eventos_mapeados(eventos, data_inicial, data_final):
    registros = (
        eventos.filter(
            data__range=(data_inicial, data_final),
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .order_by("data", "horario_inicial", "pk")
    )
    retorno = []
    for evento in registros:
        retorno.append(
            {
                "camada": "eventos",
                "titulo": evento.titulo,
                "tipo": evento.get_tipo_display(),
                "status": evento.get_status_display(),
                "data": evento.data.isoformat(),
                "lat": _float(evento.latitude),
                "lng": _float(evento.longitude),
                "popup": (
                    f"{evento.titulo}<br>{evento.get_tipo_display()}<br>"
                    f"{evento.data:%d/%m/%Y} as {evento.horario_inicial:%H:%M}<br>"
                    f"{evento.get_status_display()}"
                ),
            }
        )
    return retorno


def _centroides_por_cidade(contatos, liderancas):
    centroides = {}
    fontes = [
        contatos.filter(
            consentimento_comunicacao=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .exclude(cidade="")
        .values("cidade")
        .annotate(lat=Avg("latitude"), lng=Avg("longitude")),
        liderancas.filter(
            consentimento_dados=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .exclude(cidade="")
        .values("cidade")
        .annotate(lat=Avg("latitude"), lng=Avg("longitude")),
    ]
    for fonte in fontes:
        for item in fonte:
            chave = item["cidade"].strip().casefold()
            if chave not in centroides:
                centroides[chave] = {
                    "cidade": item["cidade"],
                    "lat": _float(item["lat"]),
                    "lng": _float(item["lng"]),
                }
    return centroides


def equipes_territorializadas(equipes, contatos, liderancas):
    centroides = _centroides_por_cidade(contatos, liderancas)
    agregados = defaultdict(lambda: {"total": 0, "departamentos": set()})
    base = equipes.filter(status__iexact="ativo").exclude(cidade_regiao="")
    for integrante in base:
        chave = integrante.cidade_regiao.strip().casefold()
        agregados[chave]["rotulo"] = integrante.cidade_regiao.strip()
        agregados[chave]["total"] += 1
        if integrante.departamento:
            agregados[chave]["departamentos"].add(integrante.departamento)

    retorno = []
    for chave, dados in agregados.items():
        centroide = centroides.get(chave)
        if not centroide:
            continue
        departamentos = sorted(dados["departamentos"])
        retorno.append(
            {
                "camada": "equipes",
                "cidade": centroide["cidade"],
                "territorio": dados["rotulo"],
                "lat": centroide["lat"],
                "lng": centroide["lng"],
                "total": dados["total"],
                "departamentos": departamentos,
                "popup": (
                    f"{dados['rotulo']}<br>{dados['total']} integrantes ativos<br>"
                    f"{', '.join(departamentos[:3])}"
                ),
            }
        )
    retorno.sort(key=lambda item: (-item["total"], item["territorio"]))
    return retorno


def visibilidade_camadas(camada_ativa: str):
    if camada_ativa == "consolidado":
        return {
            "contatos": True,
            "liderancas": True,
            "eventos": True,
            "equipes": True,
        }
    return {
        "contatos": camada_ativa == "contatos",
        "liderancas": camada_ativa == "liderancas",
        "eventos": camada_ativa == "eventos",
        "equipes": camada_ativa == "equipes",
    }


def resumo_territorial(camadas: dict):
    cidades = set()
    bairros = set()
    for item in camadas["contatos"]:
        if item.get("cidade"):
            cidades.add(item["cidade"])
        if item.get("bairro"):
            bairros.add(f"{item['cidade']}::{item['bairro']}")
    for item in camadas["liderancas"]:
        if item.get("cidade"):
            cidades.add(item["cidade"])
    for item in camadas["equipes"]:
        if item.get("cidade"):
            cidades.add(item["cidade"])
    return {
        "territorios_monitorados": len(cidades),
        "bairros_prioritarios": len(bairros),
        "liderancas_georreferenciadas": sum(item["total"] for item in camadas["liderancas"]),
        "eventos_mapeados": len(camadas["eventos"]),
        "equipes_ativas": sum(item["total"] for item in camadas["equipes"]),
    }


def construir_payload(
    *,
    contatos,
    liderancas,
    eventos,
    equipes,
    camada_ativa: str,
    periodo: str,
    data_inicial,
    data_final,
    cidade: str = "",
    bairro: str = "",
):
    camadas = {
        "contatos": contatos_agregados(contatos),
        "liderancas": liderancas_agregadas(liderancas),
        "eventos": eventos_mapeados(eventos, data_inicial, data_final),
        "equipes": equipes_territorializadas(equipes, contatos, liderancas),
    }
    return {
        "camada": camada_ativa,
        "periodo": periodo,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "filtros": {
            "cidade": cidade,
            "bairro": bairro,
        },
        "visibilidade": visibilidade_camadas(camada_ativa),
        "camadas": camadas,
        "resumo": resumo_territorial(camadas),
        "destaques": {
            "cidades": _top_por_campo(
                contatos.filter(consentimento_comunicacao=True),
                "cidade",
            ),
            "bairros": _top_por_campo(
                contatos.filter(consentimento_comunicacao=True),
                "bairro",
            ),
            "regioes": _top_por_campo(
                liderancas.filter(consentimento_dados=True),
                "regiao_eleitoral",
            ),
            "equipes": _top_por_campo(
                equipes.filter(status__iexact="ativo"),
                "cidade_regiao",
            ),
        },
    }
