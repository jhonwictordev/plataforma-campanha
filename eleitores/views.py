from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA

from .forms import ContatoCRMFormulario
from .models import ContatoCRM


class EleitoresHomeView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, ListView):
    model = ContatoCRM
    template_name = "eleitores/lista.html"
    context_object_name = "contatos"
    niveis_permitidos = PAPEIS_CRM_LEITURA
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("lideranca_relacionada", "responsavel_cadastro")
        busca = self.request.GET.get("busca", "").strip()
        cidade = self.request.GET.get("cidade", "").strip()
        status = self.request.GET.get("status", "").strip()
        if busca:
            queryset = queryset.filter(Q(nome_completo__icontains=busca) | Q(telefone__icontains=busca) | Q(email__icontains=busca))
        if cidade:
            queryset = queryset.filter(cidade__iexact=cidade)
        if status:
            queryset = queryset.filter(status_funil=status)
        return queryset.order_by("nome_completo", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "CRM de contatos"
        context["descricao"] = "Cadastre, filtre e acompanhe contatos da campanha com segregação por território e consentimento."
        context["filtros"] = {
            "busca": self.request.GET.get("busca", ""),
            "cidade": self.request.GET.get("cidade", ""),
            "status": self.request.GET.get("status", ""),
        }
        context["status_opcoes"] = ContatoCRM.EtapasFunil.choices
        return context


class ContatoCRMCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = ContatoCRM
    form_class = ContatoCRMFormulario
    template_name = "eleitores/formulario.html"
    success_url = reverse_lazy("eleitores:home")
    niveis_permitidos = PAPEIS_CRM_ESCRITA
    mensagem_sucesso = "Contato cadastrado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuário a uma campanha antes de cadastrar contatos.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class ContatoCRMDetailView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, DetailView):
    model = ContatoCRM
    template_name = "eleitores/detalhe.html"
    context_object_name = "contato"
    niveis_permitidos = PAPEIS_CRM_LEITURA


class ContatoCRMUpdateView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, MensagemSucessoMixin, UpdateView):
    model = ContatoCRM
    form_class = ContatoCRMFormulario
    template_name = "eleitores/formulario.html"
    success_url = reverse_lazy("eleitores:home")
    niveis_permitidos = PAPEIS_CRM_ESCRITA
    mensagem_sucesso = "Contato atualizado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs
