from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA

from .forms import LiderancaFormulario
from .models import Lideranca


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
        context["titulo"] = "Lideranças"
        context["descricao"] = "Gerencie lideranças políticas e comunitárias com histórico de relacionamento e recorte territorial."
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
    mensagem_sucesso = "Liderança cadastrada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuário a uma campanha antes de cadastrar lideranças.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class LiderancaDetailView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, DetailView):
    model = Lideranca
    template_name = "liderancas/detalhe.html"
    context_object_name = "lideranca"
    niveis_permitidos = PAPEIS_CRM_LEITURA


class LiderancaUpdateView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, MensagemSucessoMixin, UpdateView):
    model = Lideranca
    form_class = LiderancaFormulario
    template_name = "liderancas/formulario.html"
    success_url = reverse_lazy("liderancas:home")
    niveis_permitidos = PAPEIS_CRM_ESCRITA
    mensagem_sucesso = "Liderança atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs
