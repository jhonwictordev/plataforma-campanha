from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .models import CampanhaComunicacao, EnvioComunicacao
from .services import processar_campanha_comunicacao, processar_campanhas_agendadas, processar_envio_comunicacao


@shared_task(name="comunicacao.tasks.processar_campanhas_agendadas_task")
def processar_campanhas_agendadas_task():
    return processar_campanhas_agendadas(referencia=timezone.now())


@shared_task(name="comunicacao.tasks.processar_campanha_comunicacao_task")
def processar_campanha_comunicacao_task(campanha_id: str, forcar_execucao: bool = False):
    campanha = CampanhaComunicacao.objects.select_related("campanha", "responsavel").get(pk=campanha_id)
    return processar_campanha_comunicacao(
        campanha_comunicacao=campanha,
        referencia=timezone.now(),
        forcar_execucao=forcar_execucao,
    )


@shared_task(name="comunicacao.tasks.processar_envio_comunicacao_task")
def processar_envio_comunicacao_task(envio_id: str, forcar_reenvio: bool = False):
    envio = EnvioComunicacao.objects.select_related("contato", "campanha_comunicacao").get(pk=envio_id)
    return processar_envio_comunicacao(envio, forcar_reenvio=forcar_reenvio)
