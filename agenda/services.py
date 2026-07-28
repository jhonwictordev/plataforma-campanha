from __future__ import annotations

from datetime import time
from typing import Iterable

from .models import EventoAgenda


def normalizar_checklist(valor: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if isinstance(valor, (list, tuple)):
        return [str(item).strip() for item in valor if str(item).strip()]
    if not valor:
        return []
    itens = []
    for linha in str(valor).splitlines():
        item = linha.strip().lstrip("-").lstrip("•").strip()
        if item:
            itens.append(item)
    return itens


def _horario_final_resolvido(horario_inicial: time, horario_final: time | None) -> time:
    return horario_final or horario_inicial


def horarios_se_sobrepoem(
    horario_inicial_a: time,
    horario_final_a: time | None,
    horario_inicial_b: time,
    horario_final_b: time | None,
) -> bool:
    fim_a = _horario_final_resolvido(horario_inicial_a, horario_final_a)
    fim_b = _horario_final_resolvido(horario_inicial_b, horario_final_b)
    return horario_inicial_a <= fim_b and horario_inicial_b <= fim_a


def descrever_evento(evento: EventoAgenda) -> str:
    horario_final = _horario_final_resolvido(evento.horario_inicial, evento.horario_final)
    return f"{evento.titulo} ({evento.data:%d/%m/%Y} {evento.horario_inicial:%H:%M}-{horario_final:%H:%M})"


def buscar_conflitos_evento(
    *,
    campanha,
    data,
    horario_inicial,
    horario_final=None,
    responsavel=None,
    participantes: Iterable | None = None,
    liderancas: Iterable | None = None,
    ignorar_evento_id=None,
) -> list[EventoAgenda]:
    if campanha is None or data is None or horario_inicial is None:
        return []

    usuario_ids = {
        getattr(item, "pk", item)
        for item in (participantes or [])
        if getattr(item, "pk", item) is not None
    }
    if responsavel is not None:
        usuario_ids.add(getattr(responsavel, "pk", responsavel))

    lideranca_ids = {
        getattr(item, "pk", item)
        for item in (liderancas or [])
        if getattr(item, "pk", item) is not None
    }

    if not usuario_ids and not lideranca_ids:
        return []

    queryset = (
        EventoAgenda.objects.filter(campanha=campanha, data=data)
        .exclude(status=EventoAgenda.Status.CANCELADO)
        .select_related("responsavel")
        .prefetch_related("participantes", "liderancas_convidadas")
        .order_by("horario_inicial", "pk")
    )
    if ignorar_evento_id:
        queryset = queryset.exclude(pk=ignorar_evento_id)

    conflitos = []
    for evento in queryset:
        if not horarios_se_sobrepoem(horario_inicial, horario_final, evento.horario_inicial, evento.horario_final):
            continue

        usuarios_evento_ids = set(evento.participantes.values_list("pk", flat=True))
        if evento.responsavel_id:
            usuarios_evento_ids.add(evento.responsavel_id)

        liderancas_evento_ids = set(evento.liderancas_convidadas.values_list("pk", flat=True))

        if usuario_ids.intersection(usuarios_evento_ids) or lideranca_ids.intersection(liderancas_evento_ids):
            conflitos.append(evento)

    return conflitos
