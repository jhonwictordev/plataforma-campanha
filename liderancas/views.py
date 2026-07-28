from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA, filtrar_queryset_por_usuario, usuario_tem_nivel

from .forms import InteracaoLiderancaFormulario, LiderancaFormulario
from .models import InteracaoLideranca, Lideranca
from .services import sincronizar_ultimo_contato_lideranca


class LiderancasHomeView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, ListView):
    model = Lideranca
    template_name = "liderancas/lista.html"
    context_object_name = "liderancas"
    niveis_permitidos = PAPEIS_CRM_LEITURA
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("responsavel_contato")
        busca = self.request.GET.get("busca", "").strip()
        cidade = self.request.GET.get("cidade", "").strip()
        situacao = self.request.GET.get("situacao", "").strip()
        if busca:
            queryset = queryset.filter(
                Q(nome_completo__icontains=busca)
                | Q(nome_conhecido__icontains=busca)
                | Q(telefone__icontains=busca)
                | Q(email__icontains=busca)
            )
        if cidade:
            queryset = queryset.filter(cidade__iexact=cidade)
        if situacao:
            queryset = queryset.filter(situacao_relacionamento=situacao)
        return queryset.order_by("nome_completo", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Liderancas"
        context["descricao"] = "Gerencie liderancas politicas e comunitarias com historico de relacionamento e recorte territorial."
        context["filtros"] = {
            "busca": self.request.GET.get("busca", ""),
            "cidade": self.request.GET.get("cidade", ""),
            "situacao": self.request.GET.get("situacao", ""),
        }
        context["situacao_opcoes"] = Lideranca.Situacoes.choices
        return context


class LiderancaCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = Lideranca
    form_class = LiderancaFormulario
    template_name = "liderancas/formulario.html"
    success_url = reverse_lazy("liderancas:home")
    niveis_permitidos = PAPEIS_CRM_ESCRITA
    mensagem_sucesso = "Lideranca cadastrada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar liderancas.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class LiderancaDetailView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, DetailView):
    model = Lideranca
    template_name = "liderancas/detalhe.html"
    context_object_name = "lideranca"
    niveis_permitidos = PAPEIS_CRM_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interacoes = self.object.interacoes.select_related("responsavel").order_by("-data_hora", "-pk")[:12]
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_CRM_ESCRITA)
        context["interacoes_relacionadas"] = interacoes
        context["resumo_relacionamento"] = {
            "interacoes": self.object.interacoes.count(),
            "reunioes": self.object.interacoes.filter(tipo=InteracaoLideranca.Tipos.REUNIAO).count(),
            "ultima_interacao": self.object.data_ultimo_contato,
        }
        return context


class LiderancaUpdateView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, MensagemSucessoMixin, UpdateView):
    model = Lideranca
    form_class = LiderancaFormulario
    template_name = "liderancas/formulario.html"
    success_url = reverse_lazy("liderancas:home")
    niveis_permitidos = PAPEIS_CRM_ESCRITA
    mensagem_sucesso = "Lideranca atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class InteracaoLiderancaQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().select_related("lideranca", "responsavel")
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class InteracaoLiderancaCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = InteracaoLideranca
    form_class = InteracaoLiderancaFormulario
    template_name = "liderancas/interacao_formulario.html"
    niveis_permitidos = PAPEIS_CRM_ESCRITA
    mensagem_sucesso = "Interacao registrada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_lideranca(self):
        if not hasattr(self, "_lideranca_relacionada"):
            queryset = Lideranca.objects.select_related("responsavel_contato")
            queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
            self._lideranca_relacionada = get_object_or_404(queryset, pk=self.kwargs["lideranca_pk"])
        return self._lideranca_relacionada

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lideranca_relacionada"] = self.get_lideranca()
        return context

    def get_success_url(self):
        return reverse("liderancas:detalhe", args=[self.get_lideranca().pk])

    def form_valid(self, form):
        lideranca = self.get_lideranca()
        form.instance.lideranca = lideranca
        form.instance.campanha = lideranca.campanha
        if not form.instance.responsavel_id:
            form.instance.responsavel = self.request.user
        response = super().form_valid(form)
        sincronizar_ultimo_contato_lideranca(lideranca)
        return response


class InteracaoLiderancaUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    InteracaoLiderancaQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = InteracaoLideranca
    form_class = InteracaoLiderancaFormulario
    template_name = "liderancas/interacao_formulario.html"
    niveis_permitidos = PAPEIS_CRM_ESCRITA
    mensagem_sucesso = "Interacao atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lideranca_relacionada"] = self.object.lideranca
        return context

    def get_success_url(self):
        return reverse("liderancas:detalhe", args=[self.object.lideranca_id])

    def form_valid(self, form):
        response = super().form_valid(form)
        sincronizar_ultimo_contato_lideranca(self.object.lideranca)
        return response
