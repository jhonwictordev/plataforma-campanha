from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_METAS_ESCRITA, PAPEIS_METAS_LEITURA, usuario_tem_nivel

from .forms import MetaCampanhaFormulario
from .models import MetaCampanha
from .services import metas_em_atraso, percentual_visual

Usuario = get_user_model()


class MetasQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().select_related("responsavel", "equipe", "equipe__usuario")


class MetasHomeView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, MetasQuerysetMixin, ListView):
    model = MetaCampanha
    template_name = "metas/home.html"
    context_object_name = "metas"
    niveis_permitidos = PAPEIS_METAS_LEITURA
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        busca = self.request.GET.get("busca", "").strip()
        tipo = self.request.GET.get("tipo", "").strip()
        status = self.request.GET.get("status", "").strip()
        regiao = self.request.GET.get("regiao", "").strip()
        responsavel = self.request.GET.get("responsavel", "").strip()
        equipe = self.request.GET.get("equipe", "").strip()

        if busca:
            queryset = queryset.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca) | Q(regiao__icontains=busca))
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if status:
            queryset = queryset.filter(status=status)
        if regiao:
            queryset = queryset.filter(regiao__icontains=regiao)
        if responsavel:
            queryset = queryset.filter(responsavel_id=responsavel)
        if equipe:
            queryset = queryset.filter(equipe_id=equipe)
        return queryset.order_by("data_final", "pk")

    def _responsaveis(self):
        queryset = Usuario.objects.order_by("nome_completo", "pk")
        if not (self.request.user.is_superuser or self.request.user.is_staff):
            return queryset.filter(campanha_id=self.request.user.campanha_id)
        return queryset

    def _equipes(self):
        queryset = MetaCampanha._meta.get_field("equipe").remote_field.model.objects.order_by("nome", "pk")
        if not (self.request.user.is_superuser or self.request.user.is_staff):
            return queryset.filter(campanha_id=self.request.user.campanha_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metas_pagina = list(context["page_obj"].object_list if context.get("page_obj") else context["metas"])
        for meta in metas_pagina:
            meta.percentual_visual = percentual_visual(meta.percentual_conclusao)

        queryset = self.object_list
        media_percentual = Decimal("0")
        total_metas = queryset.count()
        if total_metas:
            soma = sum((meta.percentual_conclusao for meta in queryset), Decimal("0"))
            media_percentual = (soma / total_metas).quantize(Decimal("0.01"))

        context["metas"] = metas_pagina
        context["titulo"] = "Metas da campanha"
        context["descricao"] = "Acompanhe entregas, volumes e desempenho territorial com progresso automatico por meta."
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_METAS_ESCRITA)
        context["tipo_opcoes"] = MetaCampanha.Tipos.choices
        context["status_opcoes"] = MetaCampanha.Status.choices
        context["responsaveis"] = self._responsaveis()
        context["equipes"] = self._equipes()
        context["filtros"] = {
            "busca": self.request.GET.get("busca", ""),
            "tipo": self.request.GET.get("tipo", ""),
            "status": self.request.GET.get("status", ""),
            "regiao": self.request.GET.get("regiao", ""),
            "responsavel": self.request.GET.get("responsavel", ""),
            "equipe": self.request.GET.get("equipe", ""),
        }
        context["resumo"] = {
            "total": total_metas,
            "concluidas": queryset.filter(status=MetaCampanha.Status.CONCLUIDA).count(),
            "atrasadas": metas_em_atraso(queryset).count(),
            "em_risco": queryset.filter(status=MetaCampanha.Status.EM_RISCO).count(),
            "media_percentual": media_percentual,
        }
        return context


class MetaCampanhaCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = MetaCampanha
    form_class = MetaCampanhaFormulario
    template_name = "metas/formulario.html"
    success_url = reverse_lazy("metas:home")
    niveis_permitidos = PAPEIS_METAS_ESCRITA
    mensagem_sucesso = "Meta cadastrada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar metas.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class MetaCampanhaDetailView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    MetasQuerysetMixin,
    DetailView,
):
    model = MetaCampanha
    template_name = "metas/detalhe.html"
    context_object_name = "meta_campanha"
    niveis_permitidos = PAPEIS_METAS_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_METAS_ESCRITA)
        context["percentual_visual"] = percentual_visual(self.object.percentual_conclusao)
        return context


class MetaCampanhaUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    MetasQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = MetaCampanha
    form_class = MetaCampanhaFormulario
    template_name = "metas/formulario.html"
    success_url = reverse_lazy("metas:home")
    niveis_permitidos = PAPEIS_METAS_ESCRITA
    mensagem_sucesso = "Meta atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs
