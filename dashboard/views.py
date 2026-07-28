from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.views.generic import TemplateView

from agenda.models import EventoAgenda
from campanhas.models import Campanha
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe, TarefaEquipe
from financeiro.models import LancamentoFinanceiro
from liderancas.models import Lideranca
from metas.models import MetaCampanha
from core.mixins import NivelAcessoMixin
from core.permissions import PAPEIS_TODOS_MODULOS


class DashboardHomeView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "dashboard/home.html"
    niveis_permitidos = PAPEIS_TODOS_MODULOS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        campanha_id = getattr(usuario, "campanha_id", None)
        administracao_total = usuario.is_superuser or usuario.is_staff

        contatos = ContatoCRM.objects.all() if administracao_total and not campanha_id else ContatoCRM.objects.filter(campanha_id=campanha_id)
        liderancas = Lideranca.objects.all() if administracao_total and not campanha_id else Lideranca.objects.filter(campanha_id=campanha_id)
        equipe = IntegranteEquipe.objects.all() if administracao_total and not campanha_id else IntegranteEquipe.objects.filter(campanha_id=campanha_id)
        metas = MetaCampanha.objects.all() if administracao_total and not campanha_id else MetaCampanha.objects.filter(campanha_id=campanha_id)
        eventos = EventoAgenda.objects.all() if administracao_total and not campanha_id else EventoAgenda.objects.filter(campanha_id=campanha_id)
        financeiro = LancamentoFinanceiro.objects.all() if administracao_total and not campanha_id else LancamentoFinanceiro.objects.filter(campanha_id=campanha_id)

        context["campanha_atual"] = Campanha.objects.filter(id=campanha_id).first() if campanha_id else None
        context["indicadores"] = {
            "contatos": contatos.count(),
            "liderancas": liderancas.count(),
            "voluntarios": equipe.filter(funcao__icontains="volunt").count(),
            "metas_abertas": metas.filter(status="aberta").count(),
            "eventos_proximos": eventos.count(),
            "tarefas_atrasadas": (
                TarefaEquipe.objects.all().filter(status="a_fazer").count()
                if administracao_total and not campanha_id
                else TarefaEquipe.objects.filter(campanha_id=campanha_id, status="a_fazer").count()
            ),
        }
        context["grafico_status"] = list(contatos.values("status_funil").annotate(total=Count("id")).order_by("status_funil"))
        context["grafico_cidades"] = list(contatos.values("cidade").annotate(total=Count("id")).order_by("-total")[:8])
        context["financeiro_resumo"] = {
            "receitas": financeiro.filter(tipo__in=["receita", "doacao"]).aggregate(total=Sum("valor_reais"))["total"] or 0,
            "despesas": financeiro.filter(tipo="despesa").aggregate(total=Sum("valor_reais"))["total"] or 0,
        }
        return context
