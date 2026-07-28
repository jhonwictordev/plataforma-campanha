from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import (
    PAPEIS_EQUIPE_ESCRITA,
    PAPEIS_EQUIPE_LEITURA,
    filtrar_queryset_por_usuario,
    usuario_tem_nivel,
)

from .forms import ComentarioTarefaEquipeFormulario, IntegranteEquipeFormulario, TarefaEquipeFormulario
from .models import ComentarioTarefaEquipe, IntegranteEquipe, TarefaEquipe
from .services import agrupar_tarefas_por_status, contar_tarefas_em_aberto


class EquipeHomeView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "equipe/home.html"
    niveis_permitidos = PAPEIS_EQUIPE_LEITURA

    def _integrantes_queryset(self):
        queryset = IntegranteEquipe.objects.select_related("responsavel_direto", "usuario")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)

        busca = self.request.GET.get("busca", "").strip()
        departamento = self.request.GET.get("departamento", "").strip()
        status_integrante = self.request.GET.get("status_integrante", "").strip()

        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca)
                | Q(email__icontains=busca)
                | Q(funcao__icontains=busca)
                | Q(departamento__icontains=busca)
            )
        if departamento:
            queryset = queryset.filter(departamento__iexact=departamento)
        if status_integrante:
            queryset = queryset.filter(status=status_integrante)
        return queryset.order_by("nome", "pk")

    def _tarefas_queryset(self):
        queryset = TarefaEquipe.objects.select_related("responsavel", "responsavel__usuario")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)

        busca = self.request.GET.get("busca", "").strip()
        status_tarefa = self.request.GET.get("status_tarefa", "").strip()
        responsavel = self.request.GET.get("responsavel", "").strip()

        if busca:
            queryset = queryset.filter(
                Q(titulo__icontains=busca)
                | Q(descricao__icontains=busca)
                | Q(comentarios__icontains=busca)
                | Q(comentarios_registrados__conteudo__icontains=busca)
            ).distinct()
        if status_tarefa:
            queryset = queryset.filter(status=status_tarefa)
        if responsavel:
            queryset = queryset.filter(responsavel_id=responsavel)
        return queryset.order_by("prazo", "pk")

    def _departamentos(self):
        queryset = IntegranteEquipe.objects.all()
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
        return queryset.order_by("departamento").values_list("departamento", flat=True).distinct()

    def _responsaveis_tarefa(self):
        queryset = IntegranteEquipe.objects.select_related("usuario")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
        return queryset.order_by("nome", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        integrantes = self._integrantes_queryset()
        tarefas = self._tarefas_queryset()
        hoje = timezone.localdate()

        context["titulo"] = "Equipe e tarefas"
        context["descricao"] = "Gerencie pessoas, responsabilidades e o fluxo de execucao da campanha em formato Kanban."
        context["integrantes"] = integrantes
        context["colunas_kanban"] = agrupar_tarefas_por_status(tarefas, TarefaEquipe.Status.choices)
        context["departamentos"] = self._departamentos()
        context["responsaveis_tarefa"] = self._responsaveis_tarefa()
        context["status_tarefas"] = TarefaEquipe.Status.choices
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_EQUIPE_ESCRITA)
        context["filtros"] = {
            "busca": self.request.GET.get("busca", ""),
            "departamento": self.request.GET.get("departamento", ""),
            "status_integrante": self.request.GET.get("status_integrante", ""),
            "status_tarefa": self.request.GET.get("status_tarefa", ""),
            "responsavel": self.request.GET.get("responsavel", ""),
        }
        context["resumo"] = {
            "integrantes_total": integrantes.count(),
            "integrantes_ativos": integrantes.filter(status__iexact="ativo").count(),
            "tarefas_abertas": contar_tarefas_em_aberto(tarefas),
            "tarefas_atrasadas": tarefas.filter(prazo__date__lt=hoje).exclude(
                status__in=[TarefaEquipe.Status.CONCLUIDO, TarefaEquipe.Status.CANCELADO]
            ).count(),
            "tarefas_concluidas": tarefas.filter(status=TarefaEquipe.Status.CONCLUIDO).count(),
        }
        return context


class IntegranteEquipeQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().select_related("responsavel_direto", "usuario")
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class TarefaEquipeQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().select_related("responsavel", "responsavel__usuario")
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class ComentarioTarefaEquipeQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().select_related("tarefa", "autor", "campanha")
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class IntegranteEquipeCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = IntegranteEquipe
    form_class = IntegranteEquipeFormulario
    template_name = "equipe/integrante_formulario.html"
    success_url = reverse_lazy("equipe:home")
    niveis_permitidos = PAPEIS_EQUIPE_ESCRITA
    mensagem_sucesso = "Integrante cadastrado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar integrantes.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class IntegranteEquipeDetailView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    IntegranteEquipeQuerysetMixin,
    DetailView,
):
    model = IntegranteEquipe
    template_name = "equipe/integrante_detalhe.html"
    context_object_name = "integrante"
    niveis_permitidos = PAPEIS_EQUIPE_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_EQUIPE_ESCRITA)
        context["tarefas_relacionadas"] = self.object.tarefas.order_by("status", "prazo", "pk")[:10]
        return context


class IntegranteEquipeUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    IntegranteEquipeQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = IntegranteEquipe
    form_class = IntegranteEquipeFormulario
    template_name = "equipe/integrante_formulario.html"
    success_url = reverse_lazy("equipe:home")
    niveis_permitidos = PAPEIS_EQUIPE_ESCRITA
    mensagem_sucesso = "Integrante atualizado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class TarefaEquipeCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = TarefaEquipe
    form_class = TarefaEquipeFormulario
    template_name = "equipe/tarefa_formulario.html"
    success_url = reverse_lazy("equipe:home")
    niveis_permitidos = PAPEIS_EQUIPE_ESCRITA
    mensagem_sucesso = "Tarefa cadastrada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar tarefas.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class TarefaEquipeDetailView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    TarefaEquipeQuerysetMixin,
    DetailView,
):
    model = TarefaEquipe
    template_name = "equipe/tarefa_detalhe.html"
    context_object_name = "tarefa"
    niveis_permitidos = PAPEIS_EQUIPE_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_EQUIPE_ESCRITA)
        comentarios_relacionados = self.object.comentarios_registrados.select_related("autor").order_by("-criado_em", "-pk")
        context["comentarios_relacionados"] = comentarios_relacionados
        context["resumo_tarefa"] = {
            "itens_checklist": len(self.object.checklist or []),
            "comentarios_registrados": comentarios_relacionados.count(),
            "possui_observacoes_internas": bool(self.object.comentarios),
        }
        return context


class TarefaEquipeUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    TarefaEquipeQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = TarefaEquipe
    form_class = TarefaEquipeFormulario
    template_name = "equipe/tarefa_formulario.html"
    success_url = reverse_lazy("equipe:home")
    niveis_permitidos = PAPEIS_EQUIPE_ESCRITA
    mensagem_sucesso = "Tarefa atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class ComentarioTarefaEquipeCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = ComentarioTarefaEquipe
    form_class = ComentarioTarefaEquipeFormulario
    template_name = "equipe/comentario_formulario.html"
    niveis_permitidos = PAPEIS_EQUIPE_ESCRITA
    mensagem_sucesso = "Comentario registrado com sucesso."

    def get_tarefa(self):
        if not hasattr(self, "_tarefa"):
            queryset = filtrar_queryset_por_usuario(
                TarefaEquipe.objects.select_related("campanha", "responsavel", "responsavel__usuario"),
                self.request.user,
            )
            self._tarefa = get_object_or_404(queryset, pk=self.kwargs["tarefa_pk"])
        return self._tarefa

    def form_valid(self, form):
        tarefa = self.get_tarefa()
        form.instance.tarefa = tarefa
        form.instance.campanha = tarefa.campanha
        form.instance.autor = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return f"{reverse('equipe:tarefa_detalhe', kwargs={'pk': self.get_tarefa().pk})}#comentarios"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tarefa"] = self.get_tarefa()
        return context


class ComentarioTarefaEquipeUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    ComentarioTarefaEquipeQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = ComentarioTarefaEquipe
    form_class = ComentarioTarefaEquipeFormulario
    template_name = "equipe/comentario_formulario.html"
    niveis_permitidos = PAPEIS_EQUIPE_ESCRITA
    mensagem_sucesso = "Comentario atualizado com sucesso."

    def get_success_url(self):
        return f"{reverse('equipe:tarefa_detalhe', kwargs={'pk': self.object.tarefa_id})}#comentarios"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tarefa"] = self.object.tarefa
        return context
