from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from agenda.models import EventoAgenda
from auditoria.models import RegistroAuditoria
from campanhas.models import Campanha
from comunicacao.models import EnvioComunicacao
from core.mixins import NivelAcessoMixin
from core.permissions import PAPEIS_TODOS_MODULOS, filtrar_queryset_por_usuario
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe, TarefaEquipe
from financeiro.models import LancamentoFinanceiro
from liderancas.models import Lideranca
from metas.models import MetaCampanha

from .services import (
    comunicacao_resumo_periodo,
    contatos_por_bairro,
    contatos_por_cidade,
    distribuicao_status_contatos,
    evolucao_financeira,
    lista_periodos,
    liderancas_por_regiao,
    mapa_cadastros_autorizados,
    metas_por_equipe,
    proximos_compromissos,
    resolver_periodo,
    resumo_financeiro_periodo,
    serie_evolucao_cadastros,
    tarefas_atrasadas,
)


class DashboardHomeView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "dashboard/home.html"
    niveis_permitidos = PAPEIS_TODOS_MODULOS

    def _usuario_admin(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def _campanha_selecionada_id(self):
        if not self._usuario_admin():
            return getattr(self.request.user, "campanha_id", None)
        campanha_id = self.request.GET.get("campanha", "").strip()
        return campanha_id or None

    def _filtrar_queryset(self, queryset):
        if self._usuario_admin():
            campanha_id = self._campanha_selecionada_id()
            if campanha_id:
                return queryset.filter(campanha_id=campanha_id)
            return queryset
        return filtrar_queryset_por_usuario(queryset, self.request.user)

    def _querysets_base(self):
        return {
            "contatos": self._filtrar_queryset(
                ContatoCRM.objects.select_related("campanha", "responsavel_cadastro", "lideranca_relacionada")
            ),
            "liderancas": self._filtrar_queryset(
                Lideranca.objects.select_related("campanha", "responsavel_contato")
            ),
            "equipe": self._filtrar_queryset(
                IntegranteEquipe.objects.select_related("campanha", "responsavel_direto", "usuario")
            ),
            "tarefas": self._filtrar_queryset(
                TarefaEquipe.objects.select_related("campanha", "responsavel", "responsavel__usuario")
            ),
            "metas": self._filtrar_queryset(
                MetaCampanha.objects.select_related("campanha", "responsavel", "equipe")
            ),
            "eventos": self._filtrar_queryset(
                EventoAgenda.objects.select_related("campanha", "responsavel")
            ),
            "financeiro": self._filtrar_queryset(
                LancamentoFinanceiro.objects.select_related(
                    "campanha",
                    "categoria",
                    "parceiro",
                    "responsavel_lancamento",
                    "centro_custo",
                )
            ),
            "envios": self._filtrar_queryset(
                EnvioComunicacao.objects.select_related(
                    "campanha",
                    "campanha_comunicacao",
                    "contato",
                    "responsavel_registro",
                )
            ),
            "auditoria": self._filtrar_queryset(
                RegistroAuditoria.objects.select_related("campanha", "usuario")
            ),
        }

    def _aplicar_filtros_territoriais(self, dados):
        cidade = self.request.GET.get("cidade", "").strip()
        bairro = self.request.GET.get("bairro", "").strip()

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

    def _campanhas_disponiveis(self):
        if not self._usuario_admin():
            return Campanha.objects.none()
        return Campanha.objects.order_by("nome_campanha", "nome_candidato")

    def _campanha_atual(self):
        campanha_id = self._campanha_selecionada_id()
        if campanha_id:
            return Campanha.objects.filter(pk=campanha_id).first()
        if not self._usuario_admin():
            return Campanha.objects.filter(pk=self.request.user.campanha_id).first()
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodo, data_inicial, data_final = resolver_periodo(self.request.GET.get("periodo"))
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
        auditoria = dados["auditoria"]

        financeiro_resumo = resumo_financeiro_periodo(financeiro, data_inicial, data_final)
        proximos_eventos = proximos_compromissos(eventos)
        tarefas_criticas = tarefas_atrasadas(tarefas)
        comunicacao_resumo = comunicacao_resumo_periodo(envios, data_inicial, data_final)
        novos_cadastros = (
            contatos.filter(criado_em__date__range=(data_inicial, data_final)).count()
            + liderancas.filter(criado_em__date__range=(data_inicial, data_final)).count()
        )

        cidades_disponiveis = contatos.order_by("cidade").values_list("cidade", flat=True).distinct()
        bairros_base = contatos
        if cidade:
            bairros_base = bairros_base.filter(cidade__iexact=cidade)
        bairros_disponiveis = bairros_base.order_by("bairro").values_list("bairro", flat=True).distinct()

        context["campanha_atual"] = self._campanha_atual()
        context["campanhas_disponiveis"] = self._campanhas_disponiveis()
        context["mostrar_filtro_campanha"] = self._usuario_admin()
        context["periodo_opcoes"] = lista_periodos()
        context["cidades_disponiveis"] = [item for item in cidades_disponiveis if item]
        context["bairros_disponiveis"] = [item for item in bairros_disponiveis if item]
        context["filtros"] = {
            "campanha": self._campanha_selecionada_id() or "",
            "periodo": periodo,
            "cidade": cidade,
            "bairro": bairro,
        }
        context["indicadores"] = {
            "contatos": contatos.count(),
            "apoiadores": contatos.filter(status_funil=ContatoCRM.EtapasFunil.APOIADOR).count(),
            "liderancas": liderancas.count(),
            "voluntarios": equipe.filter(funcao__icontains="volunt").count(),
            "novos_cadastros": novos_cadastros,
            "compromissos_proximos": proximos_eventos.count(),
            "tarefas_atrasadas": tarefas_criticas.count(),
            "saldo_financeiro": financeiro_resumo["saldo"],
        }
        context["financeiro_resumo"] = financeiro_resumo
        context["comunicacao_resumo"] = comunicacao_resumo
        context["proximos_compromissos"] = proximos_eventos
        context["tarefas_criticas"] = tarefas_criticas
        context["atividades_recentes"] = auditoria.order_by("-criado_em", "pk")[:8]
        context["grafico_evolucao"] = serie_evolucao_cadastros(contatos, liderancas, data_inicial, data_final)
        context["grafico_status"] = distribuicao_status_contatos(contatos)
        context["grafico_cidades"] = contatos_por_cidade(contatos)
        context["grafico_bairros"] = contatos_por_bairro(contatos)
        context["grafico_liderancas_regiao"] = liderancas_por_regiao(liderancas)
        context["grafico_metas_equipe"] = metas_por_equipe(metas)
        context["grafico_financeiro"] = evolucao_financeira(financeiro, data_inicial, data_final)
        context["mapa_cadastros"] = mapa_cadastros_autorizados(contatos)
        context["data_referencia"] = "28 de julho de 2026"
        return context
