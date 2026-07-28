from __future__ import annotations

from datetime import datetime, timedelta

from celery import shared_task
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from agenda.models import EventoAgenda
from auditoria.models import PoliticaRetencaoDados, SolicitacaoTitularDados
from auditoria.services import preview_politica_retencao
from comunicacao.models import CampanhaComunicacao, NotificacaoInterna
from comunicacao.services import criar_notificacao_interna
from equipe.models import TarefaEquipe
from financeiro.models import LancamentoFinanceiro
from usuarios.models import Usuario


def _usuarios_coordenacao(campanha, incluir_financeiro: bool = False):
    niveis = [
        Usuario.NiveisAcesso.COORDENADOR_GERAL,
        Usuario.NiveisAcesso.COORDENADOR_REGIONAL,
    ]
    if incluir_financeiro:
        niveis.append(Usuario.NiveisAcesso.FINANCEIRO)
    queryset = Usuario.objects.filter(campanha=campanha, nivel_acesso__in=niveis, is_active=True)
    return list(queryset.order_by("nome_completo", "pk"))


def sinalizar_campanhas_agendadas(referencia=None) -> dict[str, int]:
    referencia = referencia or timezone.now()
    campanhas = (
        CampanhaComunicacao.objects.filter(
            status=CampanhaComunicacao.Status.AGENDADA,
            data_envio__isnull=False,
            data_envio__lte=referencia,
        )
        .select_related("campanha", "responsavel")
        .prefetch_related("destinatarios")
        .order_by("data_envio", "pk")
    )

    notificacoes = 0
    campanhas_sinalizadas = 0
    for campanha_comunicacao in campanhas:
        usuarios_destino = []
        if campanha_comunicacao.responsavel_id:
            usuarios_destino.append(campanha_comunicacao.responsavel)
        if campanha_comunicacao.campanha.coordenador_responsavel_id:
            coordenador = campanha_comunicacao.campanha.coordenador_responsavel
            if coordenador and coordenador.is_active and coordenador not in usuarios_destino:
                usuarios_destino.append(coordenador)
        if not usuarios_destino:
            usuarios_destino.extend(_usuarios_coordenacao(campanha_comunicacao.campanha))

        total_destinatarios = campanha_comunicacao.destinatarios.count()
        for usuario in usuarios_destino:
            chave = f"comunicacao-agendada:{campanha_comunicacao.id}:{campanha_comunicacao.data_envio.isoformat()}"
            _, criada = criar_notificacao_interna(
                campanha=campanha_comunicacao.campanha,
                usuario_destinatario=usuario,
                titulo="Campanha de comunicacao no horario de execucao",
                mensagem=(
                    f"A campanha '{campanha_comunicacao.nome}' chegou ao horario agendado em "
                    f"{timezone.localtime(campanha_comunicacao.data_envio):%d/%m/%Y %H:%M} "
                    f"com {total_destinatarios} destinatario(s)."
                ),
                categoria=NotificacaoInterna.Categorias.COMUNICACAO,
                url_destino=reverse("comunicacao:campanha_detalhe", args=[campanha_comunicacao.pk]),
                chave_unica=chave,
                origem_modelo="CampanhaComunicacao",
                origem_id=str(campanha_comunicacao.pk),
            )
            notificacoes += 1 if criada else 0
        campanhas_sinalizadas += 1

    return {"campanhas": campanhas_sinalizadas, "notificacoes": notificacoes}


def gerar_lembretes_agenda(referencia=None, janela_horas: int = 24) -> dict[str, int]:
    referencia = referencia or timezone.now()
    limite = referencia + timedelta(hours=janela_horas)
    eventos = (
        EventoAgenda.objects.exclude(status__in=[EventoAgenda.Status.CANCELADO, EventoAgenda.Status.CONCLUIDO])
        .select_related("campanha", "responsavel")
        .prefetch_related("participantes")
        .order_by("data", "horario_inicial", "pk")
    )

    eventos_considerados = 0
    notificacoes = 0
    for evento in eventos:
        data_hora_evento = datetime.combine(evento.data, evento.horario_inicial)
        data_hora_evento = timezone.make_aware(data_hora_evento, timezone.get_current_timezone())
        if not (referencia <= data_hora_evento <= limite):
            continue

        usuarios_destino = list(evento.participantes.all())
        if evento.responsavel_id and evento.responsavel not in usuarios_destino:
            usuarios_destino.append(evento.responsavel)
        for usuario in usuarios_destino:
            chave = f"agenda:{evento.id}:{usuario.id}:{evento.data.isoformat()}:{evento.horario_inicial.isoformat()}"
            _, criada = criar_notificacao_interna(
                campanha=evento.campanha,
                usuario_destinatario=usuario,
                titulo="Lembrete de agenda",
                mensagem=(
                    f"O evento '{evento.titulo}' acontece em {evento.data:%d/%m/%Y} "
                    f"as {evento.horario_inicial:%H:%M}."
                ),
                categoria=NotificacaoInterna.Categorias.AGENDA,
                url_destino=reverse("agenda:detalhe", args=[evento.pk]),
                chave_unica=chave,
                origem_modelo="EventoAgenda",
                origem_id=str(evento.pk),
            )
            notificacoes += 1 if criada else 0
        eventos_considerados += 1

    return {"eventos": eventos_considerados, "notificacoes": notificacoes}


def gerar_alertas_tarefas(referencia=None) -> dict[str, int]:
    referencia = referencia or timezone.now()
    hoje = timezone.localdate()
    tarefas = (
        TarefaEquipe.objects.exclude(status__in=[TarefaEquipe.Status.CONCLUIDO, TarefaEquipe.Status.CANCELADO])
        .filter(prazo__isnull=False, prazo__lte=referencia + timedelta(days=1))
        .select_related("campanha", "responsavel", "responsavel__usuario")
        .order_by("prazo", "pk")
    )

    notificacoes = 0
    tarefas_alertadas = 0
    for tarefa in tarefas:
        if not tarefa.responsavel_id or not tarefa.responsavel.usuario_id or not tarefa.responsavel.usuario.is_active:
            continue
        usuario = tarefa.responsavel.usuario
        atrasada = tarefa.prazo < referencia
        chave = f"tarefa:{tarefa.id}:{usuario.id}:{hoje.isoformat()}"
        _, criada = criar_notificacao_interna(
            campanha=tarefa.campanha,
            usuario_destinatario=usuario,
            titulo="Tarefa atrasada" if atrasada else "Tarefa com prazo proximo",
            mensagem=(
                f"A tarefa '{tarefa.titulo}' esta {'atrasada' if atrasada else 'com prazo proximo'} "
                f"desde {timezone.localtime(tarefa.prazo):%d/%m/%Y %H:%M}."
            ),
            categoria=NotificacaoInterna.Categorias.EQUIPE,
            url_destino=reverse("equipe:tarefa_detalhe", args=[tarefa.pk]),
            chave_unica=chave,
            origem_modelo="TarefaEquipe",
            origem_id=str(tarefa.pk),
        )
        notificacoes += 1 if criada else 0
        tarefas_alertadas += 1

    return {"tarefas": tarefas_alertadas, "notificacoes": notificacoes}


def gerar_alertas_financeiros(referencia=None) -> dict[str, int]:
    referencia = referencia or timezone.now()
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=2)
    lancamentos = (
        LancamentoFinanceiro.objects.filter(status=LancamentoFinanceiro.Status.PENDENTE, data_vencimento__isnull=False)
        .filter(data_vencimento__lte=limite)
        .select_related("campanha", "responsavel_lancamento")
        .order_by("data_vencimento", "pk")
    )

    notificacoes = 0
    lancamentos_alertados = 0
    for lancamento in lancamentos:
        usuarios_destino = []
        if lancamento.responsavel_lancamento_id and lancamento.responsavel_lancamento.is_active:
            usuarios_destino.append(lancamento.responsavel_lancamento)
        for usuario in _usuarios_coordenacao(lancamento.campanha, incluir_financeiro=True):
            if usuario not in usuarios_destino:
                usuarios_destino.append(usuario)

        atrasado = lancamento.data_vencimento < hoje
        for usuario in usuarios_destino:
            chave = f"financeiro:{lancamento.id}:{usuario.id}:{hoje.isoformat()}"
            _, criada = criar_notificacao_interna(
                campanha=lancamento.campanha,
                usuario_destinatario=usuario,
                titulo="Lancamento financeiro vencido" if atrasado else "Lancamento financeiro a vencer",
                mensagem=(
                    f"O lancamento '{lancamento.descricao}' esta "
                    f"{'vencido' if atrasado else 'previsto'} para {lancamento.data_vencimento:%d/%m/%Y}."
                ),
                categoria=NotificacaoInterna.Categorias.FINANCEIRO,
                url_destino=reverse("financeiro:lancamento_detalhe", args=[lancamento.pk]),
                chave_unica=chave,
                origem_modelo="LancamentoFinanceiro",
                origem_id=str(lancamento.pk),
            )
            notificacoes += 1 if criada else 0
        lancamentos_alertados += 1

    return {"lancamentos": lancamentos_alertados, "notificacoes": notificacoes}


def gerar_alertas_lgpd(referencia=None) -> dict[str, int]:
    referencia = referencia or timezone.now()
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=3)
    solicitacoes = (
        SolicitacaoTitularDados.objects.filter(
            status__in=[
                SolicitacaoTitularDados.Status.ABERTA,
                SolicitacaoTitularDados.Status.EM_ANALISE,
            ],
            prazo_resposta__isnull=False,
            prazo_resposta__lte=limite,
        )
        .select_related("campanha", "responsavel_interno", "campanha__coordenador_responsavel")
        .order_by("prazo_resposta", "pk")
    )

    notificacoes = 0
    solicitacoes_alertadas = 0
    for solicitacao in solicitacoes:
        usuarios_destino = []
        if solicitacao.responsavel_interno_id and solicitacao.responsavel_interno.is_active:
            usuarios_destino.append(solicitacao.responsavel_interno)
        if (
            solicitacao.campanha.coordenador_responsavel_id
            and solicitacao.campanha.coordenador_responsavel.is_active
            and solicitacao.campanha.coordenador_responsavel not in usuarios_destino
        ):
            usuarios_destino.append(solicitacao.campanha.coordenador_responsavel)
        if not usuarios_destino:
            usuarios_destino.extend(_usuarios_coordenacao(solicitacao.campanha))

        atrasada = solicitacao.prazo_resposta < hoje
        for usuario in usuarios_destino:
            chave = f"lgpd:{solicitacao.id}:{usuario.id}:{hoje.isoformat()}"
            _, criada = criar_notificacao_interna(
                campanha=solicitacao.campanha,
                usuario_destinatario=usuario,
                titulo="Solicitacao LGPD em atraso" if atrasada else "Solicitacao LGPD com prazo proximo",
                mensagem=(
                    f"A solicitacao de {solicitacao.nome_solicitante} esta "
                    f"{'em atraso' if atrasada else 'com prazo de resposta proximo'} para "
                    f"{solicitacao.prazo_resposta:%d/%m/%Y}."
                ),
                categoria=NotificacaoInterna.Categorias.LGPD,
                url_destino=reverse("auditoria:solicitacao_editar", args=[solicitacao.pk]),
                chave_unica=chave,
                origem_modelo="SolicitacaoTitularDados",
                origem_id=str(solicitacao.pk),
            )
            notificacoes += 1 if criada else 0
        solicitacoes_alertadas += 1

    return {"solicitacoes": solicitacoes_alertadas, "notificacoes": notificacoes}


def gerar_alertas_retencao(referencia=None) -> dict[str, int]:
    referencia = referencia or timezone.now()
    hoje = timezone.localdate()
    politicas = (
        PoliticaRetencaoDados.objects.select_related("campanha", "responsavel", "campanha__coordenador_responsavel")
        .order_by("campanha__nome_campanha", "nome", "pk")
    )

    notificacoes = 0
    politicas_alertadas = 0
    for politica in politicas:
        preview = preview_politica_retencao(politica, usuario=None, campanha_id=str(politica.campanha_id))
        if not preview["registros_expirados"] and not preview["registros_para_anonimizar"]:
            continue

        usuarios_destino = []
        if politica.responsavel_id and politica.responsavel.is_active:
            usuarios_destino.append(politica.responsavel)
        if (
            politica.campanha.coordenador_responsavel_id
            and politica.campanha.coordenador_responsavel.is_active
            and politica.campanha.coordenador_responsavel not in usuarios_destino
        ):
            usuarios_destino.append(politica.campanha.coordenador_responsavel)
        if not usuarios_destino:
            usuarios_destino.extend(_usuarios_coordenacao(politica.campanha))

        for usuario in usuarios_destino:
            chave = f"retencao:{politica.id}:{usuario.id}:{hoje.isoformat()}"
            _, criada = criar_notificacao_interna(
                campanha=politica.campanha,
                usuario_destinatario=usuario,
                titulo="Politica de retencao com registros pendentes",
                mensagem=(
                    f"A politica '{politica.nome}' possui {preview['registros_expirados']} registro(s) fora do prazo "
                    f"e {preview['registros_para_anonimizar']} item(ns) elegiveis para anonimizar."
                ),
                categoria=NotificacaoInterna.Categorias.RETENCAO,
                url_destino=reverse("auditoria:home"),
                chave_unica=chave,
                origem_modelo="PoliticaRetencaoDados",
                origem_id=str(politica.pk),
            )
            notificacoes += 1 if criada else 0
        politicas_alertadas += 1

    return {"politicas": politicas_alertadas, "notificacoes": notificacoes}


@shared_task(name="core.tasks.sinalizar_campanhas_agendadas_task")
def sinalizar_campanhas_agendadas_task():
    return sinalizar_campanhas_agendadas()


@shared_task(name="core.tasks.gerar_lembretes_agenda_task")
def gerar_lembretes_agenda_task():
    return gerar_lembretes_agenda()


@shared_task(name="core.tasks.gerar_alertas_tarefas_task")
def gerar_alertas_tarefas_task():
    return gerar_alertas_tarefas()


@shared_task(name="core.tasks.gerar_alertas_financeiros_task")
def gerar_alertas_financeiros_task():
    return gerar_alertas_financeiros()


@shared_task(name="core.tasks.gerar_alertas_lgpd_task")
def gerar_alertas_lgpd_task():
    return gerar_alertas_lgpd()


@shared_task(name="core.tasks.gerar_alertas_retencao_task")
def gerar_alertas_retencao_task():
    return gerar_alertas_retencao()
