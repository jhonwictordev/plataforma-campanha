from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from agenda.models import EventoAgenda
from comunicacao.models import EnvioComunicacao
from core.permissions import filtrar_queryset_por_usuario
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe
from financeiro.models import LancamentoFinanceiro
from liderancas.models import Lideranca
from metas.models import MetaCampanha

from .models import LogSeguranca, PoliticaRetencaoDados, RegistroAuditoria, SolicitacaoTitularDados

RETENCAO_MODELOS = {
    PoliticaRetencaoDados.TiposRegistro.CONTATOS: ContatoCRM,
    PoliticaRetencaoDados.TiposRegistro.LIDERANCAS: Lideranca,
    PoliticaRetencaoDados.TiposRegistro.EVENTOS: EventoAgenda,
    PoliticaRetencaoDados.TiposRegistro.EQUIPE: IntegranteEquipe,
    PoliticaRetencaoDados.TiposRegistro.METAS: MetaCampanha,
    PoliticaRetencaoDados.TiposRegistro.FINANCEIRO: LancamentoFinanceiro,
    PoliticaRetencaoDados.TiposRegistro.COMUNICACAO: EnvioComunicacao,
    PoliticaRetencaoDados.TiposRegistro.AUDITORIA: RegistroAuditoria,
    PoliticaRetencaoDados.TiposRegistro.SEGURANCA: LogSeguranca,
}


def usuario_admin(usuario) -> bool:
    return bool(usuario.is_superuser or getattr(usuario, "is_staff", False))


def filtrar_por_campanha(queryset, usuario=None, campanha_id: str = ""):
    if usuario is None:
        if campanha_id:
            return queryset.filter(campanha_id=campanha_id)
        return queryset
    if usuario_admin(usuario):
        if campanha_id:
            return queryset.filter(campanha_id=campanha_id)
        return queryset
    return filtrar_queryset_por_usuario(queryset, usuario)


def aplicar_filtros_registro(queryset, filtros):
    queryset = queryset.filter(criado_em__date__range=(filtros["data_inicial"], filtros["data_final"]))
    if filtros["usuario_id"]:
        queryset = queryset.filter(usuario_id=filtros["usuario_id"])
    if filtros["acao"]:
        queryset = queryset.filter(acao__icontains=filtros["acao"])
    if filtros["modelo"]:
        queryset = queryset.filter(modelo__icontains=filtros["modelo"])
    if filtros["busca"]:
        queryset = queryset.filter(
            Q(resumo__icontains=filtros["busca"])
            | Q(modelo__icontains=filtros["busca"])
            | Q(objeto_id__icontains=filtros["busca"])
        )
    return queryset


def aplicar_filtros_log(queryset, filtros):
    queryset = queryset.filter(criado_em__date__range=(filtros["data_inicial"], filtros["data_final"]))
    if filtros["usuario_id"]:
        queryset = queryset.filter(usuario_id=filtros["usuario_id"])
    if filtros["evento"]:
        queryset = queryset.filter(evento__icontains=filtros["evento"])
    if filtros["severidade"]:
        queryset = queryset.filter(severidade=filtros["severidade"])
    if filtros["busca"]:
        queryset = queryset.filter(
            Q(descricao__icontains=filtros["busca"])
            | Q(evento__icontains=filtros["busca"])
        )
    return queryset


def aplicar_filtros_solicitacao(queryset, filtros):
    queryset = queryset.filter(criado_em__date__range=(filtros["data_inicial"], filtros["data_final"]))
    if filtros["usuario_id"]:
        queryset = queryset.filter(responsavel_interno_id=filtros["usuario_id"])
    if filtros["busca"]:
        queryset = queryset.filter(
            Q(nome_solicitante__icontains=filtros["busca"])
            | Q(descricao__icontains=filtros["busca"])
            | Q(email_solicitante__icontains=filtros["busca"])
        )
    return queryset


def construir_resumo(registros, logs, solicitacoes, politicas):
    total_politicas = politicas.count() if hasattr(politicas, "model") else len(politicas)
    return {
        "registros": registros.count(),
        "logs": logs.count(),
        "logs_criticos": logs.filter(severidade__iexact="critico").count(),
        "logs_aviso": logs.filter(severidade__iexact="aviso").count(),
        "solicitacoes_abertas": solicitacoes.filter(
            status__in=[
                SolicitacaoTitularDados.Status.ABERTA,
                SolicitacaoTitularDados.Status.EM_ANALISE,
            ]
        ).count(),
        "politicas_ativas": total_politicas,
    }


def preview_politica_retencao(politica, usuario, campanha_id: str = ""):
    model = RETENCAO_MODELOS.get(politica.tipo_registro)
    if model is None:
        return {"registros_expirados": 0, "registros_para_anonimizar": 0}

    queryset = filtrar_por_campanha(model.objects.all(), usuario, campanha_id or str(politica.campanha_id))
    limite_retencao = timezone.now() - timedelta(days=politica.dias_retencao)
    expirados = queryset.filter(criado_em__lte=limite_retencao).count()

    anonimizacao = 0
    if politica.dias_ate_anonimizacao:
        limite_anonimizacao = timezone.now() - timedelta(days=politica.dias_ate_anonimizacao)
        anonimizacao = queryset.filter(criado_em__lte=limite_anonimizacao).count()

    return {
        "registros_expirados": expirados,
        "registros_para_anonimizar": anonimizacao,
    }


def enriquecer_politicas(politicas, usuario, campanha_id: str = ""):
    retorno = []
    for politica in politicas:
        preview = preview_politica_retencao(politica, usuario, campanha_id)
        politica.registros_expirados = preview["registros_expirados"]
        politica.registros_para_anonimizar = preview["registros_para_anonimizar"]
        retorno.append(politica)
    return retorno


def anonimizar_contato(contato: ContatoCRM):
    contato.nome_completo = "Titular anonimizado"
    contato.telefone = ""
    contato.whatsapp = ""
    contato.email = ""
    contato.data_nascimento = None
    contato.cidade = contato.cidade or "Nao informado"
    contato.bairro = ""
    contato.endereco = ""
    contato.zona_eleitoral = ""
    contato.secao_eleitoral = ""
    contato.origem_contato = ""
    contato.observacoes = ""
    contato.proxima_acao = ""
    contato.consentimento_comunicacao = False
    contato.canal_autorizado = ""
    contato.data_consentimento = None
    contato.latitude = None
    contato.longitude = None
    contato.save()


def anonimizar_lideranca(lideranca: Lideranca):
    lideranca.nome_completo = "Titular anonimizado"
    lideranca.nome_conhecido = ""
    lideranca.cpf = ""
    lideranca.telefone = ""
    lideranca.whatsapp = ""
    lideranca.email = ""
    lideranca.data_nascimento = None
    lideranca.genero = ""
    lideranca.organizacao = ""
    lideranca.cargo_funcao = ""
    lideranca.bairro = ""
    lideranca.endereco = ""
    lideranca.zona_eleitoral = ""
    lideranca.secao_eleitoral = ""
    lideranca.observacoes = ""
    lideranca.proxima_acao = ""
    lideranca.tags = []
    lideranca.consentimento_dados = False
    lideranca.data_consentimento = None
    lideranca.latitude = None
    lideranca.longitude = None
    lideranca.save()


def revogar_consentimento_contato(contato: ContatoCRM):
    contato.consentimento_comunicacao = False
    contato.canal_autorizado = ""
    contato.data_consentimento = None
    contato.save(update_fields=["consentimento_comunicacao", "canal_autorizado", "data_consentimento", "atualizado_em"])


def revogar_consentimento_lideranca(lideranca: Lideranca):
    lideranca.consentimento_dados = False
    lideranca.data_consentimento = None
    lideranca.save(update_fields=["consentimento_dados", "data_consentimento", "atualizado_em"])


@transaction.atomic
def aplicar_solicitacao_titular(solicitacao: SolicitacaoTitularDados):
    if solicitacao.status != SolicitacaoTitularDados.Status.CONCLUIDA:
        raise PermissionDenied("A acao automatica so pode ser executada em solicitacoes concluidas.")

    mensagens = []
    contato = solicitacao.contato_relacionado
    lideranca = solicitacao.lideranca_relacionada

    if solicitacao.tipo_solicitacao == SolicitacaoTitularDados.TiposSolicitacao.REVOGACAO_CONSENTIMENTO:
        if contato:
            revogar_consentimento_contato(contato)
            mensagens.append("Consentimento de comunicacao do contato revogado.")
        if lideranca:
            revogar_consentimento_lideranca(lideranca)
            mensagens.append("Consentimento de dados da lideranca revogado.")

    elif solicitacao.tipo_solicitacao == SolicitacaoTitularDados.TiposSolicitacao.ANONIMIZACAO:
        if contato:
            anonimizar_contato(contato)
            mensagens.append("Contato anonimizado.")
        if lideranca:
            anonimizar_lideranca(lideranca)
            mensagens.append("Lideranca anonimizada.")

    elif solicitacao.tipo_solicitacao == SolicitacaoTitularDados.TiposSolicitacao.EXCLUSAO:
        if contato:
            anonimizar_contato(contato)
            contato.excluir_suavemente()
            mensagens.append("Contato anonimizado e excluido logicamente.")
        if lideranca:
            anonimizar_lideranca(lideranca)
            lideranca.excluir_suavemente()
            mensagens.append("Lideranca anonimizada e excluida logicamente.")

    if not mensagens:
        mensagens.append("Solicitacao concluida sem efeito automatico aplicavel.")

    solicitacao.executado_em = timezone.now()
    solicitacao.resultado_execucao = " ".join(mensagens)
    solicitacao.data_conclusao = solicitacao.data_conclusao or timezone.now()
    solicitacao.save(update_fields=["executado_em", "resultado_execucao", "data_conclusao", "atualizado_em"])
    return solicitacao.resultado_execucao
