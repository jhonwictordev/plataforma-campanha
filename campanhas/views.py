from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from agenda.models import EventoAgenda
from comunicacao.models import CampanhaComunicacao
from core.mixins import MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_TODOS_MODULOS
from eleitores.models import ContatoCRM
from equipe.models import TarefaEquipe
from financeiro.models import LancamentoFinanceiro
from liderancas.models import Lideranca
from metas.models import MetaCampanha

from .forms import FormularioCampanha
from .models import Campanha

Usuario = get_user_model()

PAPEIS_GESTAO_CAMPANHA = ("administrador", "coordenador_geral")


def usuario_pode_gerir_todas_campanhas(usuario) -> bool:
    if not getattr(usuario, "is_authenticated", False):
        return False
    return bool(usuario.is_superuser or getattr(usuario, "is_staff", False) or usuario.nivel_acesso in PAPEIS_GESTAO_CAMPANHA)


class GestaoCampanhaMixin(NivelAcessoMixin):
    niveis_permitidos = PAPEIS_GESTAO_CAMPANHA
    exige_campanha = False

    def test_func(self):
        return NivelAcessoMixin.test_func(self)


class QuerysetCampanhaMixin:
    def get_queryset(self):
        queryset = Campanha.objects.select_related("coordenador_responsavel").order_by(
            "data_eleicao",
            "nome_campanha",
            "pk",
        )
        usuario = self.request.user
        if usuario_pode_gerir_todas_campanhas(usuario):
            return queryset
        if getattr(usuario, "campanha_id", None):
            return queryset.filter(pk=usuario.campanha_id)
        return queryset.none()


class PersistenciaCampanhaMixin:
    model = Campanha
    form_class = FormularioCampanha
    template_name = "campanhas/formulario.html"
    success_url = reverse_lazy("campanhas:lista")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = "Nova campanha" if self.object is None else "Editar campanha"
        context["subtitulo_pagina"] = (
            "Cadastre os dados estruturais da operacao eleitoral."
            if self.object is None
            else "Atualize os dados institucionais, territoriais e visuais da campanha."
        )
        context["texto_botao_salvar"] = "Salvar campanha" if self.object is None else "Salvar alteracoes"
        return context

    def form_valid(self, form):
        resposta = super().form_valid(form)
        self._sincronizar_coordenador()
        return resposta

    def _sincronizar_coordenador(self):
        coordenador = self.object.coordenador_responsavel
        if (
            coordenador
            and not (coordenador.is_superuser or getattr(coordenador, "is_staff", False))
            and coordenador.campanha_id != self.object.pk
        ):
            coordenador.campanha = self.object
            coordenador.save(update_fields=["campanha", "atualizado_em"])


class CampanhaListView(LoginRequiredMixin, NivelAcessoMixin, QuerysetCampanhaMixin, ListView):
    model = Campanha
    template_name = "campanhas/lista.html"
    context_object_name = "campanhas"
    niveis_permitidos = PAPEIS_TODOS_MODULOS
    exige_campanha = False

    def get_queryset(self):
        queryset = super().get_queryset()
        termo = self.request.GET.get("q", "").strip()
        situacao = self.request.GET.get("situacao", "").strip()
        estado = self.request.GET.get("estado", "").strip()

        if termo:
            queryset = queryset.filter(
                Q(nome_campanha__icontains=termo)
                | Q(nome_candidato__icontains=termo)
                | Q(partido__icontains=termo)
                | Q(numero_candidato__icontains=termo)
                | Q(municipio__icontains=termo)
            )
        if situacao:
            queryset = queryset.filter(situacao=situacao)
        if estado:
            queryset = queryset.filter(estado__iexact=estado)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtros"] = {
            "q": self.request.GET.get("q", "").strip(),
            "situacao": self.request.GET.get("situacao", "").strip(),
            "estado": self.request.GET.get("estado", "").strip(),
        }
        context["situacoes"] = Campanha.Situacoes.choices
        context["pode_gerir_campanhas"] = usuario_pode_gerir_todas_campanhas(self.request.user)
        return context


class CampanhaDetailView(LoginRequiredMixin, NivelAcessoMixin, QuerysetCampanhaMixin, DetailView):
    model = Campanha
    template_name = "campanhas/detalhe.html"
    context_object_name = "campanha"
    niveis_permitidos = PAPEIS_TODOS_MODULOS
    exige_campanha = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campanha = self.object
        context["pode_gerir_campanhas"] = usuario_pode_gerir_todas_campanhas(self.request.user)
        context["resumo_operacao"] = {
            "usuarios": Usuario.objects.filter(campanha=campanha, is_active=True).count(),
            "contatos": ContatoCRM.objects.filter(campanha=campanha).count(),
            "liderancas": Lideranca.objects.filter(campanha=campanha).count(),
            "eventos": EventoAgenda.objects.filter(campanha=campanha).count(),
            "tarefas": TarefaEquipe.objects.filter(campanha=campanha).count(),
            "metas": MetaCampanha.objects.filter(campanha=campanha).count(),
            "lancamentos": LancamentoFinanceiro.objects.filter(campanha=campanha).count(),
            "comunicacoes": CampanhaComunicacao.objects.filter(campanha=campanha).count(),
        }
        return context


class CampanhaCreateView(LoginRequiredMixin, GestaoCampanhaMixin, PersistenciaCampanhaMixin, MensagemSucessoMixin, CreateView):
    mensagem_sucesso = "Campanha cadastrada com sucesso."


class CampanhaUpdateView(LoginRequiredMixin, GestaoCampanhaMixin, QuerysetCampanhaMixin, PersistenciaCampanhaMixin, MensagemSucessoMixin, UpdateView):
    mensagem_sucesso = "Campanha atualizada com sucesso."


class CampanhaDeleteView(LoginRequiredMixin, GestaoCampanhaMixin, QuerysetCampanhaMixin, DeleteView):
    model = Campanha
    template_name = "campanhas/excluir.html"
    success_url = reverse_lazy("campanhas:lista")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = "Arquivar campanha"
        return context

    def form_valid(self, form):
        self.object.excluir_suavemente()
        messages.success(self.request, "Campanha arquivada com sucesso.")
        return redirect(self.get_success_url())
