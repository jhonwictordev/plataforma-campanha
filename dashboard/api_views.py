from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from agenda.models import EventoAgenda
from auditoria.models import RegistroAuditoria
from campanhas.models import Campanha
from comunicacao.models import CampanhaComunicacao, EnvioComunicacao, NotificacaoInterna
from core.api import ViewSetAnaliticoCampanhaProtegido
from core.permissions import PAPEIS_TODOS_MODULOS
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe, TarefaEquipe
from financeiro.models import LancamentoFinanceiro
from liderancas.models import Lideranca
from metas.models import MetaCampanha

from .serializers import DashboardRespostaSerializer
from .services import (
    alertas_por_categoria,
    campanha_resumida,
    campanhas_resumidas,
    comunicacao_resumo_periodo,
    comunicacoes_programadas,
    contatos_por_bairro,
    contatos_por_cidade,
    contas_vencidas,
    distribuicao_status_contatos,
    evolucao_financeira,
    liderancas_por_regiao,
    lista_periodos,
    mapa_cadastros_autorizados,
    metas_por_equipe,
    notificacoes_recentes,
    proximos_compromissos,
    resolver_periodo,
    resumo_financeiro_periodo,
    resumo_operacional,
    serializar_atividades_recentes,
    serializar_comunicacoes_programadas,
    serializar_contas_vencidas,
    serializar_financeiro_resumo,
    serializar_notificacoes,
    serializar_proximos_compromissos,
    serializar_tarefas_criticas,
    serie_evolucao_cadastros,
    tarefas_atrasadas,
)


class DashboardViewSet(ViewSetAnaliticoCampanhaProtegido):
    niveis_permitidos = PAPEIS_TODOS_MODULOS
    serializer_class = DashboardRespostaSerializer

    def _querysets_base(self):
        return {
            "contatos": self.filtrar_queryset(
                ContatoCRM.objects.select_related("campanha", "responsavel_cadastro", "lideranca_relacionada")
            ),
            "liderancas": self.filtrar_queryset(
                Lideranca.objects.select_related("campanha", "responsavel_contato")
            ),
            "equipe": self.filtrar_queryset(
                IntegranteEquipe.objects.select_related("campanha", "responsavel_direto", "usuario")
            ),
            "tarefas": self.filtrar_queryset(
                TarefaEquipe.objects.select_related("campanha", "responsavel", "responsavel__usuario")
            ),
            "metas": self.filtrar_queryset(
                MetaCampanha.objects.select_related("campanha", "responsavel", "equipe")
            ),
            "eventos": self.filtrar_queryset(
                EventoAgenda.objects.select_related("campanha", "responsavel")
            ),
            "financeiro": self.filtrar_queryset(
                LancamentoFinanceiro.objects.select_related(
                    "campanha",
                    "categoria",
                    "parceiro",
                    "responsavel_lancamento",
                    "centro_custo",
                )
            ),
            "envios": self.filtrar_queryset(
                EnvioComunicacao.objects.select_related(
                    "campanha",
                    "campanha_comunicacao",
                    "contato",
                    "responsavel_registro",
                )
            ),
            "comunicacoes": self.filtrar_queryset(
                CampanhaComunicacao.objects.select_related("campanha", "modelo_mensagem", "responsavel")
            ),
            "auditoria": self.filtrar_queryset(
                RegistroAuditoria.objects.select_related("campanha", "usuario")
            ),
            "notificacoes": self._notificacoes_usuario(),
        }

    def _notificacoes_usuario(self):
        queryset = NotificacaoInterna.objects.filter(usuario_destinatario=self.request.user).select_related(
            "campanha",
            "usuario_destinatario",
        )
        campanha_id = self.campanha_selecionada_id()
        if campanha_id:
            return queryset.filter(campanha_id=campanha_id)
        if not self.usuario_admin() and getattr(self.request.user, "campanha_id", None):
            return queryset.filter(campanha_id=self.request.user.campanha_id)
        return queryset

    def _aplicar_filtros_territoriais(self, dados):
        cidade = self.request.query_params.get("cidade", "").strip()
        bairro = self.request.query_params.get("bairro", "").strip()

        if cidade:
            dados["contatos"] = dados["contatos"].filter(cidade__iexact=cidade)
            dados["liderancas"] = dados["liderancas"].filter(cidade__iexact=cidade)
            dados["equipe"] = dados["equipe"].filter(cidade_regiao__icontains=cidade)
            dados["metas"] = dados["metas"].filter(regiao__icontains=cidade)
        if bairro:
            dados["contatos"] = dados["contatos"].filter(bairro__iexact=bairro)
            dados["liderancas"] = dados["liderancas"].filter(bairro__iexact=bairro)
            dados["metas"] = dados["metas"].filter(regiao__icontains=bairro)

        return cidade, bairro, dados

    def _campanha_atual(self):
        campanha_id = self.campanha_selecionada_id()
        if campanha_id:
            return Campanha.objects.filter(pk=campanha_id).first()
        if not self.usuario_admin() and getattr(self.request.user, "campanha_id", None):
            return Campanha.objects.filter(pk=self.request.user.campanha_id).first()
        return None

    def _campanhas_disponiveis(self):
        if not self.usuario_admin():
            return []
        campanhas = Campanha.objects.order_by("nome_campanha", "nome_candidato")
        return campanhas_resumidas(campanhas)

    @extend_schema(responses=DashboardRespostaSerializer)
    def list(self, request):
        periodo, data_inicial, data_final = resolver_periodo(request.query_params.get("periodo"))
        dados = self._querysets_base()
        cidade, bairro, dados = self._aplicar_filtros_territoriais(dados)

        contatos = dados["contatos"]
        liderancas = dados["liderancas"]
        equipe = dados["equipe"]
        tarefas = dados["tarefas"]
        metas = dados["metas"]
        eventos = dados["eventos"]
        financeiro = dados["financeiro"]
        envios = dados["envios"]
        comunicacoes = dados["comunicacoes"]
        auditoria = dados["auditoria"]
        notificacoes = dados["notificacoes"]

        financeiro_resumo = resumo_financeiro_periodo(financeiro, data_inicial, data_final)
        proximos_eventos = list(proximos_compromissos(eventos))
        tarefas_criticas = list(tarefas_atrasadas(tarefas))
        notificacoes_lista = list(notificacoes_recentes(notificacoes))
        comunicacoes_lista = list(comunicacoes_programadas(comunicacoes))
        contas_vencidas_lista = list(contas_vencidas(financeiro))
        atividades_recentes = list(auditoria.order_by("-criado_em", "pk")[:8])
        comunicacao_resumo = comunicacao_resumo_periodo(envios, data_inicial, data_final)
        resumo_operacao = resumo_operacional(notificacoes, comunicacoes, tarefas, eventos, financeiro, envios)
        novos_cadastros = (
            contatos.filter(criado_em__date__range=(data_inicial, data_final)).count()
            + liderancas.filter(criado_em__date__range=(data_inicial, data_final)).count()
        )

        cidades_disponiveis = [item for item in contatos.order_by("cidade").values_list("cidade", flat=True).distinct() if item]
        bairros_base = contatos
        if cidade:
            bairros_base = bairros_base.filter(cidade__iexact=cidade)
        bairros_disponiveis = [item for item in bairros_base.order_by("bairro").values_list("bairro", flat=True).distinct() if item]

        payload = {
            "periodo": periodo,
            "data_inicial": data_inicial,
            "data_final": data_final,
            "filtros": {
                "campanha": str(self.campanha_selecionada_id() or ""),
                "periodo": periodo,
                "cidade": cidade,
                "bairro": bairro,
            },
            "campanha_atual": campanha_resumida(self._campanha_atual()),
            "campanhas_disponiveis": self._campanhas_disponiveis(),
            "periodo_opcoes": [{"valor": valor, "rotulo": rotulo} for valor, rotulo in lista_periodos()],
            "cidades_disponiveis": cidades_disponiveis,
            "bairros_disponiveis": bairros_disponiveis,
            "indicadores": {
                "contatos": contatos.count(),
                "apoiadores": contatos.filter(status_funil=ContatoCRM.EtapasFunil.APOIADOR).count(),
                "liderancas": liderancas.count(),
                "voluntarios": equipe.filter(funcao__icontains="volunt").count(),
                "novos_cadastros": novos_cadastros,
                "compromissos_proximos": len(proximos_eventos),
                "tarefas_atrasadas": len(tarefas_criticas),
                "saldo_financeiro": serializar_financeiro_resumo(financeiro_resumo)["saldo"],
                "alertas_nao_lidos": resumo_operacao["alertas_nao_lidos"],
                "comunicacoes_agendadas": resumo_operacao["comunicacoes_agendadas"],
                "contas_vencidas": resumo_operacao["contas_vencidas"],
            },
            "financeiro_resumo": serializar_financeiro_resumo(financeiro_resumo),
            "comunicacao_resumo": comunicacao_resumo,
            "resumo_operacional": resumo_operacao,
            "proximos_compromissos": serializar_proximos_compromissos(proximos_eventos),
            "tarefas_criticas": serializar_tarefas_criticas(tarefas_criticas),
            "notificacoes_dashboard": serializar_notificacoes(notificacoes_lista),
            "comunicacoes_programadas": serializar_comunicacoes_programadas(comunicacoes_lista),
            "contas_vencidas": serializar_contas_vencidas(contas_vencidas_lista),
            "atividades_recentes": serializar_atividades_recentes(atividades_recentes),
            "graficos": {
                "evolucao": serie_evolucao_cadastros(contatos, liderancas, data_inicial, data_final),
                "status": distribuicao_status_contatos(contatos),
                "cidades": contatos_por_cidade(contatos),
                "bairros": contatos_por_bairro(contatos),
                "liderancas_regiao": liderancas_por_regiao(liderancas),
                "metas_equipe": metas_por_equipe(metas),
                "financeiro": evolucao_financeira(financeiro, data_inicial, data_final),
                "alertas_categoria": alertas_por_categoria(notificacoes),
            },
            "mapa_cadastros": mapa_cadastros_autorizados(contatos),
        }

        serializer = DashboardRespostaSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
