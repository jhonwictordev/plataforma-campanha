from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_FINANCEIRO_ESCRITA, PAPEIS_FINANCEIRO_LEITURA, usuario_tem_nivel

from .forms import (
    CategoriaFinanceiraFormulario,
    CentroCustoFormulario,
    LancamentoFinanceiroFormulario,
    ParceiroFinanceiroFormulario,
)
from .models import CategoriaFinanceira, CentroCusto, LancamentoFinanceiro, ParceiroFinanceiro
from .services import resumo_financeiro, top_categorias_despesa


class FinanceiroQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().select_related(
            "categoria",
            "parceiro",
            "responsavel_lancamento",
            "centro_custo",
        )


class FinanceiroHomeView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, FinanceiroQuerysetMixin, ListView):
    model = LancamentoFinanceiro
    template_name = "financeiro/home.html"
    context_object_name = "lancamentos"
    niveis_permitidos = PAPEIS_FINANCEIRO_LEITURA
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        busca = self.request.GET.get("busca", "").strip()
        tipo = self.request.GET.get("tipo", "").strip()
        status = self.request.GET.get("status", "").strip()
        categoria = self.request.GET.get("categoria", "").strip()
        parceiro = self.request.GET.get("parceiro", "").strip()
        centro_custo = self.request.GET.get("centro_custo", "").strip()

        if busca:
            queryset = queryset.filter(
                Q(descricao__icontains=busca)
                | Q(numero_documento__icontains=busca)
                | Q(observacoes__icontains=busca)
            )
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if status:
            queryset = queryset.filter(status=status)
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if parceiro:
            queryset = queryset.filter(parceiro_id=parceiro)
        if centro_custo:
            queryset = queryset.filter(centro_custo_id=centro_custo)
        return queryset.order_by("data_vencimento", "pk")

    def _categorias(self):
        queryset = CategoriaFinanceira.objects.order_by("tipo", "nome", "pk")
        if not (self.request.user.is_superuser or self.request.user.is_staff):
            queryset = queryset.filter(campanha_id=self.request.user.campanha_id)
        return queryset

    def _centros_custo(self):
        queryset = CentroCusto.objects.order_by("nome", "pk")
        if not (self.request.user.is_superuser or self.request.user.is_staff):
            queryset = queryset.filter(campanha_id=self.request.user.campanha_id)
        return queryset

    def _parceiros(self):
        queryset = ParceiroFinanceiro.objects.order_by("nome", "pk")
        if not (self.request.user.is_superuser or self.request.user.is_staff):
            queryset = queryset.filter(campanha_id=self.request.user.campanha_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Financeiro"
        context["descricao"] = (
            "Controle receitas, despesas, doacoes e compromissos financeiros com rastreabilidade por campanha."
        )
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_FINANCEIRO_ESCRITA)
        context["tipo_opcoes"] = LancamentoFinanceiro.Tipos.choices
        context["status_opcoes"] = LancamentoFinanceiro.Status.choices
        context["categorias"] = self._categorias()
        context["centros_custo"] = self._centros_custo()
        context["parceiros"] = self._parceiros()
        context["filtros"] = {
            "busca": self.request.GET.get("busca", ""),
            "tipo": self.request.GET.get("tipo", ""),
            "status": self.request.GET.get("status", ""),
            "categoria": self.request.GET.get("categoria", ""),
            "parceiro": self.request.GET.get("parceiro", ""),
            "centro_custo": self.request.GET.get("centro_custo", ""),
        }
        context["resumo"] = resumo_financeiro(self.object_list)
        context["top_categorias"] = top_categorias_despesa(self.object_list)
        return context


class LancamentoFinanceiroCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = LancamentoFinanceiro
    form_class = LancamentoFinanceiroFormulario
    template_name = "financeiro/lancamento_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Lancamento financeiro cadastrado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar lancamentos.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class LancamentoFinanceiroDetailView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    FinanceiroQuerysetMixin,
    DetailView,
):
    model = LancamentoFinanceiro
    template_name = "financeiro/lancamento_detalhe.html"
    context_object_name = "lancamento"
    niveis_permitidos = PAPEIS_FINANCEIRO_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_FINANCEIRO_ESCRITA)
        return context


class LancamentoFinanceiroUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    FinanceiroQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = LancamentoFinanceiro
    form_class = LancamentoFinanceiroFormulario
    template_name = "financeiro/lancamento_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Lancamento financeiro atualizado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class CategoriaFinanceiraQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset
        return queryset.filter(campanha_id=self.request.user.campanha_id)


class CategoriaFinanceiraCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = CategoriaFinanceira
    form_class = CategoriaFinanceiraFormulario
    template_name = "financeiro/catalogo_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Categoria financeira cadastrada com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_formulario"] = "Nova categoria financeira"
        context["rotulo_botao"] = "Salvar categoria"
        return context

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar categorias.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class CategoriaFinanceiraUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    CategoriaFinanceiraQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = CategoriaFinanceira
    form_class = CategoriaFinanceiraFormulario
    template_name = "financeiro/catalogo_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Categoria financeira atualizada com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_formulario"] = "Editar categoria financeira"
        context["rotulo_botao"] = "Salvar categoria"
        return context


class CentroCustoQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset
        return queryset.filter(campanha_id=self.request.user.campanha_id)


class CentroCustoCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = CentroCusto
    form_class = CentroCustoFormulario
    template_name = "financeiro/catalogo_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Centro de custo cadastrado com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_formulario"] = "Novo centro de custo"
        context["rotulo_botao"] = "Salvar centro de custo"
        return context

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar centros de custo.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class CentroCustoUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    CentroCustoQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = CentroCusto
    form_class = CentroCustoFormulario
    template_name = "financeiro/catalogo_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Centro de custo atualizado com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_formulario"] = "Editar centro de custo"
        context["rotulo_botao"] = "Salvar centro de custo"
        return context


class ParceiroFinanceiroQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset
        return queryset.filter(campanha_id=self.request.user.campanha_id)


class ParceiroFinanceiroCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = ParceiroFinanceiro
    form_class = ParceiroFinanceiroFormulario
    template_name = "financeiro/catalogo_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Parceiro financeiro cadastrado com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_formulario"] = "Novo parceiro financeiro"
        context["rotulo_botao"] = "Salvar parceiro"
        return context

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar parceiros.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class ParceiroFinanceiroUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    ParceiroFinanceiroQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = ParceiroFinanceiro
    form_class = ParceiroFinanceiroFormulario
    template_name = "financeiro/catalogo_formulario.html"
    success_url = reverse_lazy("financeiro:home")
    niveis_permitidos = PAPEIS_FINANCEIRO_ESCRITA
    mensagem_sucesso = "Parceiro financeiro atualizado com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_formulario"] = "Editar parceiro financeiro"
        context["rotulo_botao"] = "Salvar parceiro"
        return context
