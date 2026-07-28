from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import (
    PAPEIS_COMUNICACAO_ESCRITA,
    PAPEIS_COMUNICACAO_LEITURA,
    filtrar_queryset_por_usuario,
    usuario_tem_nivel,
)

from eleitores.models import ContatoCRM

from .forms import (
    CampanhaComunicacaoFormulario,
    EnvioComunicacaoFormulario,
    ListaBloqueioFormulario,
    ModeloMensagemFormulario,
    NotificacaoInternaFiltroFormulario,
)
from .models import CampanhaComunicacao, CanalComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem, NotificacaoInterna
from .services import (
    contar_contatos_autorizados,
    listar_notificacoes_usuario,
    marcar_todas_notificacoes_como_lidas,
    registrar_descadastro,
    sincronizar_envios_campanha,
)


class ComunicacaoHomeView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "comunicacao/home.html"
    niveis_permitidos = PAPEIS_COMUNICACAO_LEITURA

    def _campanhas_queryset(self):
        queryset = CampanhaComunicacao.objects.select_related("responsavel", "modelo_mensagem")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)

        busca = self.request.GET.get("busca", "").strip()
        canal = self.request.GET.get("canal", "").strip()
        status = self.request.GET.get("status", "").strip()

        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca)
                | Q(assunto__icontains=busca)
                | Q(conteudo__icontains=busca)
            )
        if canal:
            queryset = queryset.filter(canal=canal)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("data_envio", "-criado_em", "pk")

    def _modelos_queryset(self):
        queryset = ModeloMensagem.objects.order_by("canal", "nome", "pk")
        return filtrar_queryset_por_usuario(queryset, self.request.user)

    def _bloqueios_queryset(self):
        queryset = ListaBloqueio.objects.select_related("contato", "solicitado_por")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
        return queryset.order_by("-criado_em", "pk")

    def _envios_queryset(self, campanhas):
        queryset = EnvioComunicacao.objects.select_related("campanha_comunicacao", "contato", "responsavel_registro")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
        if campanhas is not None:
            queryset = queryset.filter(campanha_comunicacao__in=campanhas)
        return queryset.order_by("-atualizado_em", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campanhas = self._campanhas_queryset()
        modelos = self._modelos_queryset()
        bloqueios = self._bloqueios_queryset()
        envios = self._envios_queryset(campanhas)

        campanha_id = None if (self.request.user.is_superuser or self.request.user.is_staff) else self.request.user.campanha_id
        total_autorizados = (
            contar_contatos_autorizados(campanha_id=campanha_id)
            if campanha_id
            else ContatoCRM.objects.filter(consentimento_comunicacao=True).count()
        )

        context["titulo"] = "Comunicacao"
        context["descricao"] = (
            "Gerencie campanhas autorizadas, modelos, bloqueios e respostas sem burlar limites de plataforma."
        )
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_COMUNICACAO_ESCRITA)
        context["campanhas_comunicacao"] = campanhas[:12]
        context["modelos_mensagem"] = modelos[:8]
        context["bloqueios"] = bloqueios[:8]
        context["envios_recentes"] = envios[:10]
        context["notificacoes_recentes"] = listar_notificacoes_usuario(self.request.user, limite=6)
        context["status_opcoes"] = CampanhaComunicacao.Status.choices
        context["canal_opcoes"] = CanalComunicacao.choices
        context["filtros"] = {
            "busca": self.request.GET.get("busca", ""),
            "canal": self.request.GET.get("canal", ""),
            "status": self.request.GET.get("status", ""),
        }
        context["resumo"] = {
            "campanhas_total": campanhas.count(),
            "campanhas_agendadas": campanhas.filter(status=CampanhaComunicacao.Status.AGENDADA).count(),
            "envios_programados": envios.filter(status=EnvioComunicacao.Status.PROGRAMADO).count(),
            "envios_falha": envios.filter(status=EnvioComunicacao.Status.FALHA).count(),
            "respostas": envios.filter(status=EnvioComunicacao.Status.RESPONDIDO).count(),
            "bloqueios_total": bloqueios.count(),
            "contatos_autorizados": total_autorizados,
            "notificacoes_nao_lidas": NotificacaoInterna.objects.filter(
                usuario_destinatario=self.request.user,
                lida_em__isnull=True,
            ).count(),
        }
        return context


class ModeloMensagemQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class CampanhaComunicacaoQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().select_related("responsavel", "modelo_mensagem")
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class ListaBloqueioQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().select_related("contato", "solicitado_por")
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class EnvioComunicacaoQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().select_related("campanha_comunicacao", "contato", "responsavel_registro")
        return filtrar_queryset_por_usuario(queryset, self.request.user)


class ModeloMensagemCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = ModeloMensagem
    form_class = ModeloMensagemFormulario
    template_name = "comunicacao/modelo_formulario.html"
    success_url = reverse_lazy("comunicacao:home")
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA
    mensagem_sucesso = "Modelo de mensagem cadastrado com sucesso."

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar modelos.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class ModeloMensagemUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    ModeloMensagemQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = ModeloMensagem
    form_class = ModeloMensagemFormulario
    template_name = "comunicacao/modelo_formulario.html"
    success_url = reverse_lazy("comunicacao:home")
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA
    mensagem_sucesso = "Modelo de mensagem atualizado com sucesso."


class CampanhaComunicacaoCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = CampanhaComunicacao
    form_class = CampanhaComunicacaoFormulario
    template_name = "comunicacao/campanha_formulario.html"
    success_url = reverse_lazy("comunicacao:home")
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA
    mensagem_sucesso = "Campanha de comunicacao cadastrada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar campanhas de comunicacao.")
        form.instance.campanha = self.request.user.campanha
        if not form.instance.responsavel_id:
            form.instance.responsavel = self.request.user
        response = super().form_valid(form)
        sincronizar_envios_campanha(
            campanha_comunicacao=self.object,
            destinatarios=form.cleaned_data.get("destinatarios", []),
            usuario=self.request.user,
        )
        return response


class CampanhaComunicacaoDetailView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    CampanhaComunicacaoQuerysetMixin,
    DetailView,
):
    model = CampanhaComunicacao
    template_name = "comunicacao/campanha_detalhe.html"
    context_object_name = "campanha_comunicacao"
    niveis_permitidos = PAPEIS_COMUNICACAO_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_COMUNICACAO_ESCRITA)
        context["envios"] = self.object.envios.select_related("contato", "responsavel_registro").order_by(
            "status",
            "data_programada",
            "pk",
        )
        return context


class CampanhaComunicacaoUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    CampanhaComunicacaoQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = CampanhaComunicacao
    form_class = CampanhaComunicacaoFormulario
    template_name = "comunicacao/campanha_formulario.html"
    success_url = reverse_lazy("comunicacao:home")
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA
    mensagem_sucesso = "Campanha de comunicacao atualizada com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        sincronizar_envios_campanha(
            campanha_comunicacao=self.object,
            destinatarios=form.cleaned_data.get("destinatarios", self.object.destinatarios.all()),
            usuario=self.request.user,
        )
        return response


class ListaBloqueioCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = ListaBloqueio
    form_class = ListaBloqueioFormulario
    template_name = "comunicacao/bloqueio_formulario.html"
    success_url = reverse_lazy("comunicacao:home")
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA
    mensagem_sucesso = "Bloqueio cadastrado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de registrar bloqueios.")
        form.instance.campanha = self.request.user.campanha
        form.instance.solicitado_por = self.request.user
        return super().form_valid(form)


class ListaBloqueioUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    ListaBloqueioQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = ListaBloqueio
    form_class = ListaBloqueioFormulario
    template_name = "comunicacao/bloqueio_formulario.html"
    success_url = reverse_lazy("comunicacao:home")
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA
    mensagem_sucesso = "Bloqueio atualizado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class EnvioComunicacaoUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    EnvioComunicacaoQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = EnvioComunicacao
    form_class = EnvioComunicacaoFormulario
    template_name = "comunicacao/envio_formulario.html"
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA
    mensagem_sucesso = "Envio atualizado com sucesso."

    def get_success_url(self):
        return reverse_lazy("comunicacao:campanha_detalhe", kwargs={"pk": self.object.campanha_comunicacao_id})

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_descadastro(self.object, usuario=self.request.user)
        self.object.campanha_comunicacao.atualizar_metricas()
        return response


class NotificacaoInternaListView(LoginRequiredMixin, TemplateView):
    template_name = "comunicacao/notificacoes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formulario = NotificacaoInternaFiltroFormulario(self.request.GET or None)
        queryset = listar_notificacoes_usuario(self.request.user)

        if formulario.is_valid():
            categoria = formulario.cleaned_data.get("categoria")
            status = formulario.cleaned_data.get("status")
            busca = (formulario.cleaned_data.get("busca") or "").strip()
            if categoria:
                queryset = queryset.filter(categoria=categoria)
            if status == "nao_lidas":
                queryset = queryset.filter(lida_em__isnull=True)
            elif status == "lidas":
                queryset = queryset.filter(lida_em__isnull=False)
            if busca:
                queryset = queryset.filter(Q(titulo__icontains=busca) | Q(mensagem__icontains=busca))

        context["titulo"] = "Notificacoes internas"
        context["descricao"] = "Acompanhe alertas operacionais, lembretes e sinais de risco da campanha."
        context["filtro_form"] = formulario
        context["notificacoes"] = queryset[:40]
        context["nao_lidas"] = queryset.filter(lida_em__isnull=True).count()
        return context


class NotificacaoInternaMarcarLidaView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notificacao = get_object_or_404(NotificacaoInterna, pk=pk, usuario_destinatario=request.user)
        notificacao.marcar_como_lida()
        proximo = request.POST.get("next", "").strip()
        if proximo:
            return redirect(proximo)
        if notificacao.url_destino:
            return redirect(notificacao.url_destino)
        return redirect("comunicacao:notificacoes")


class NotificacaoInternaMarcarTodasLidasView(LoginRequiredMixin, View):
    def post(self, request):
        marcar_todas_notificacoes_como_lidas(request.user)
        return redirect("comunicacao:notificacoes")
