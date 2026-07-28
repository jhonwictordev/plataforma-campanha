from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from core.mixins import MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_AUDITORIA, filtrar_queryset_por_usuario

from .forms import (
    AuditoriaFiltroFormulario,
    PoliticaRetencaoDadosFormulario,
    SolicitacaoTitularDadosFormulario,
)
from .models import LogSeguranca, PoliticaRetencaoDados, RegistroAuditoria, SolicitacaoTitularDados
from .services import (
    aplicar_filtros_log,
    aplicar_filtros_registro,
    aplicar_filtros_solicitacao,
    aplicar_solicitacao_titular,
    construir_resumo,
    enriquecer_politicas,
    filtrar_por_campanha,
    usuario_admin,
)


class AuditoriaQuerysetMixin:
    model = None

    def get_queryset(self):
        queryset = super().get_queryset()
        return filtrar_por_campanha(queryset, self.request.user)


class AuditoriaHomeView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "auditoria/home.html"
    niveis_permitidos = PAPEIS_AUDITORIA

    def _filtro_form(self):
        return AuditoriaFiltroFormulario(data=self.request.GET or None, usuario=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro_form = self._filtro_form()
        filtros = filtro_form.dados_resolvidos()

        registros = filtrar_por_campanha(
            RegistroAuditoria.objects.select_related("campanha", "usuario"),
            self.request.user,
            filtros["campanha_id"],
        )
        logs = filtrar_por_campanha(
            LogSeguranca.objects.select_related("campanha", "usuario"),
            self.request.user,
            filtros["campanha_id"],
        )
        politicas = filtrar_por_campanha(
            PoliticaRetencaoDados.objects.select_related("campanha", "responsavel"),
            self.request.user,
            filtros["campanha_id"],
        )
        solicitacoes = filtrar_por_campanha(
            SolicitacaoTitularDados.objects.select_related(
                "campanha",
                "contato_relacionado",
                "lideranca_relacionada",
                "responsavel_interno",
            ),
            self.request.user,
            filtros["campanha_id"],
        )

        registros = aplicar_filtros_registro(registros, filtros).order_by("-criado_em", "pk")
        logs = aplicar_filtros_log(logs, filtros).order_by("-criado_em", "pk")
        solicitacoes = aplicar_filtros_solicitacao(solicitacoes, filtros).order_by("status", "prazo_resposta", "-criado_em", "pk")
        politicas = enriquecer_politicas(politicas.order_by("tipo_registro", "nome", "pk"), self.request.user, filtros["campanha_id"])

        context["titulo"] = "Auditoria e seguranca"
        context["descricao"] = "Painel de rastreabilidade, retencao e atendimento LGPD com isolamento por campanha."
        context["filtro_form"] = filtro_form
        context["filtros"] = filtros
        context["resumo"] = construir_resumo(registros, logs, solicitacoes, politicas)
        context["registros_recentes"] = registros[:15]
        context["logs_recentes"] = logs[:15]
        context["solicitacoes_recentes"] = solicitacoes[:12]
        context["politicas"] = politicas
        context["pode_filtrar_campanha"] = usuario_admin(self.request.user)
        context["data_referencia"] = "28 de julho de 2026"
        return context


class RegistroAuditoriaDetailView(LoginRequiredMixin, NivelAcessoMixin, AuditoriaQuerysetMixin, DetailView):
    model = RegistroAuditoria
    template_name = "auditoria/registro_detalhe.html"
    context_object_name = "registro"
    niveis_permitidos = PAPEIS_AUDITORIA


class LogSegurancaDetailView(LoginRequiredMixin, NivelAcessoMixin, AuditoriaQuerysetMixin, DetailView):
    model = LogSeguranca
    template_name = "auditoria/log_detalhe.html"
    context_object_name = "log"
    niveis_permitidos = PAPEIS_AUDITORIA


class PoliticaRetencaoCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = PoliticaRetencaoDados
    form_class = PoliticaRetencaoDadosFormulario
    template_name = "auditoria/politica_formulario.html"
    success_url = reverse_lazy("auditoria:home")
    niveis_permitidos = PAPEIS_AUDITORIA
    mensagem_sucesso = "Politica de retencao criada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not usuario_admin(self.request.user):
            form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class PoliticaRetencaoUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    AuditoriaQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = PoliticaRetencaoDados
    form_class = PoliticaRetencaoDadosFormulario
    template_name = "auditoria/politica_formulario.html"
    success_url = reverse_lazy("auditoria:home")
    niveis_permitidos = PAPEIS_AUDITORIA
    mensagem_sucesso = "Politica de retencao atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class SolicitacaoTitularCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = SolicitacaoTitularDados
    form_class = SolicitacaoTitularDadosFormulario
    template_name = "auditoria/solicitacao_formulario.html"
    success_url = reverse_lazy("auditoria:home")
    niveis_permitidos = PAPEIS_AUDITORIA
    mensagem_sucesso = "Solicitacao do titular registrada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not usuario_admin(self.request.user):
            form.instance.campanha = self.request.user.campanha
        if form.instance.status == SolicitacaoTitularDados.Status.CONCLUIDA and not form.instance.data_conclusao:
            form.instance.data_conclusao = timezone.now()
        response = super().form_valid(form)
        if form.cleaned_data.get("executar_acao_lgpd") and self.object.status == SolicitacaoTitularDados.Status.CONCLUIDA:
            resultado = aplicar_solicitacao_titular(self.object)
            messages.info(self.request, resultado)
        return response


class SolicitacaoTitularUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    AuditoriaQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = SolicitacaoTitularDados
    form_class = SolicitacaoTitularDadosFormulario
    template_name = "auditoria/solicitacao_formulario.html"
    success_url = reverse_lazy("auditoria:home")
    niveis_permitidos = PAPEIS_AUDITORIA
    mensagem_sucesso = "Solicitacao do titular atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.instance.status == SolicitacaoTitularDados.Status.CONCLUIDA and not form.instance.data_conclusao:
            form.instance.data_conclusao = timezone.now()
        response = super().form_valid(form)
        if form.cleaned_data.get("executar_acao_lgpd") and self.object.status == SolicitacaoTitularDados.Status.CONCLUIDA:
            resultado = aplicar_solicitacao_titular(self.object)
            messages.info(self.request, resultado)
        return response
