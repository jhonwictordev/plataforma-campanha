from decimal import Decimal

from django.utils import timezone

from .models import MetaCampanha


def percentual_visual(valor) -> int:
    try:
        percentual = int(Decimal(str(valor or 0)))
    except Exception:
        percentual = 0
    return max(0, min(percentual, 100))


def metas_por_status(metas):
    metas_lista = list(metas)
    grupos = []
    for valor, rotulo in MetaCampanha.Status.choices:
        grupos.append(
            {
                "valor": valor,
                "rotulo": rotulo,
                "metas": [meta for meta in metas_lista if meta.status == valor],
            }
        )
    return grupos


def metas_em_atraso(queryset):
    hoje = timezone.localdate()
    return queryset.filter(data_final__lt=hoje).exclude(
        status__in=[MetaCampanha.Status.CONCLUIDA, MetaCampanha.Status.CANCELADA]
    )
