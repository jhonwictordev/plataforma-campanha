import json

from django.contrib import messages
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
    RegistroWebhookFiltroFormulario,
)
from .models import (
    CampanhaComunicacao,
    CanalComunicacao,
    EnvioComunicacao,
    ListaBloqueio,
    ModeloMensagem,
    NotificacaoInterna,
    RegistroWebhookComunicacao,
)
from .services import (
    contar_contatos_autorizados,
    listar_notificacoes_usuario,
    marcar_todas_notificacoes_como_lidas,
    obter_status_integracoes_oficiais,
    processar_campanha_comunicacao,
    reprocessar_envio_individual,
    registrar_descadastro,
    resumir_registros_webhook,
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


class RegistroWebhookQuerysetMixin:
    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("campanha", "envio", "envio__contato", "envio__campanha_comunicacao")
        )
        return filtrar_queryset_por_usuario(queryset, self.request.user, campo_campanha="campanha_id")


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
        context["pode_executar_agora"] = context["pode_editar"] and self.object.status in [
            CampanhaComunicacao.Status.AGENDADA,
            CampanhaComunicacao.Status.PAUSADA,
        ]
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


class CampanhaComunicacaoExecutarAgoraView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    View,
):
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA

    def get_queryset(self):
        queryset = CampanhaComunicacao.objects.select_related("responsavel", "modelo_mensagem", "campanha")
        return filtrar_queryset_por_usuario(queryset, self.request.user)

    def post(self, request, pk):
        campanha = get_object_or_404(self.get_queryset(), pk=pk)
        resumo = processar_campanha_comunicacao(campanha, forcar_execucao=True)
        if resumo.get("status") == "pausada":
            messages.warning(
                request,
                resumo.get("erro") or "A campanha foi pausada por falta de integracao oficial configurada.",
            )
        else:
            messages.success(
                request,
                (
                    f"Processamento concluido: {resumo.get('processados', 0)} envio(s) OK, "
                    f"{resumo.get('falhas', 0)} falha(s)."
                ),
            )
        return redirect("comunicacao:campanha_detalhe", pk=campanha.pk)


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


class EnvioComunicacaoReprocessarView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    EnvioComunicacaoQuerysetMixin,
    View,
):
    model = EnvioComunicacao
    niveis_permitidos = PAPEIS_COMUNICACAO_ESCRITA

    def get_queryset(self):
        queryset = EnvioComunicacao.objects.select_related(
            "campanha_comunicacao",
            "contato",
            "responsavel_registro",
            "campanha_comunicacao__campanha",
        )
        return filtrar_queryset_por_usuario(queryset, self.request.user)

    def post(self, request, pk):
        envio = get_object_or_404(self.get_queryset(), pk=pk)
        if envio.status not in {EnvioComunicacao.Status.FALHA, EnvioComunicacao.Status.PROGRAMADO}:
            messages.warning(
                request,
                "Este envio nao esta em um estado seguro para reprocessamento manual.",
            )
        else:
            resumo = reprocessar_envio_individual(envio)
            if resumo["resultado"] == "sucesso":
                messages.success(
                    request,
                    (
                        f"Envio reprocessado com sucesso. Restam {resumo['falhas_restantes']} falha(s) "
                        f"e {resumo['programados_restantes']} envio(s) programado(s) nesta campanha."
                    ),
                )
            else:
                messages.error(request, resumo["motivo"])
        proximo = request.POST.get("next", "").strip()
        if proximo:
            return redirect(proximo)
        return redirect("comunicacao:campanha_detalhe", pk=envio.campanha_comunicacao_id)


class ComunicacaoOperacaoView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "comunicacao/operacao.html"
    niveis_permitidos = PAPEIS_COMUNICACAO_LEITURA

    def _campanhas_queryset(self):
        queryset = CampanhaComunicacao.objects.select_related("responsavel", "campanha")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
        return queryset.order_by("data_envio", "-atualizado_em", "pk")

    def _envios_falha_queryset(self):
        queryset = EnvioComunicacao.objects.select_related(
            "campanha_comunicacao",
            "contato",
            "responsavel_registro",
        )
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
        return queryset.filter(status=EnvioComunicacao.Status.FALHA).order_by("-atualizado_em", "pk")

    def _webhooks_queryset(self):
        queryset = RegistroWebhookComunicacao.objects.select_related(
            "campanha",
            "envio",
            "envio__contato",
            "envio__campanha_comunicacao",
        )
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user, campo_campanha="campanha_id")
        return queryset.order_by("-recebido_em", "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formulario = RegistroWebhookFiltroFormulario(self.request.GET or None)
        campanhas = self._campanhas_queryset()
        envios_falha = self._envios_falha_queryset()
        webhooks = self._webhooks_queryset()

        if formulario.is_valid():
            canal = formulario.cleaned_data.get("canal")
            assinatura = formulario.cleaned_data.get("assinatura")
            processamento = formulario.cleaned_data.get("processamento")
            provedor = (formulario.cleaned_data.get("provedor") or "").strip()
            evento = (formulario.cleaned_data.get("evento") or "").strip()
            busca = (formulario.cleaned_data.get("busca") or "").strip()

            if canal:
                webhooks = webhooks.filter(canal=canal)
            if assinatura == "valida":
                webhooks = webhooks.filter(assinatura_valida=True)
            elif assinatura == "invalida":
                webhooks = webhooks.filter(assinatura_valida=False)
            if processamento == "processado":
                webhooks = webhooks.filter(processado_com_sucesso=True)
            elif processamento == "pendente":
                webhooks = webhooks.filter(processado_com_sucesso=False)
            if provedor:
                webhooks = webhooks.filter(provedor__icontains=provedor)
            if evento:
                webhooks = webhooks.filter(evento__icontains=evento)
            if busca:
                webhooks = webhooks.filter(
                    Q(identificador_externo__icontains=busca)
                    | Q(mensagem_processamento__icontains=busca)
                    | Q(envio__contato__nome_completo__icontains=busca)
                    | Q(envio__campanha_comunicacao__nome__icontains=busca)
                )

        context["titulo"] = "Operacao de integracoes"
        context["descricao"] = "Acompanhe integrações oficiais, webhooks, campanhas pausadas e reprocessamentos seguros."
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_COMUNICACAO_ESCRITA)
        context["filtro_form"] = formulario
        context["integracoes"] = obter_status_integracoes_oficiais()
        context["campanhas_pausadas"] = campanhas.filter(status=CampanhaComunicacao.Status.PAUSADA)[:8]
        context["campanhas_com_falha"] = campanhas.filter(quantidade_falha__gt=0)[:8]
        context["envios_falha"] = envios_falha[:12]
        context["registros_webhook"] = webhooks[:20]
        context["resumo_webhooks"] = resumir_registros_webhook(webhooks)
        context["resumo_operacao"] = {
            "campanhas_pausadas": campanhas.filter(status=CampanhaComunicacao.Status.PAUSADA).count(),
            "campanhas_com_falha": campanhas.filter(quantidade_falha__gt=0).count(),
            "envios_falha": envios_falha.count(),
            "webhooks_total": webhooks.count(),
        }
        return context


class RegistroWebhookComunicacaoDetailView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    RegistroWebhookQuerysetMixin,
    DetailView,
):
    model = RegistroWebhookComunicacao
    template_name = "comunicacao/webhook_detalhe.html"
    context_object_name = "registro_webhook"
    niveis_permitidos = PAPEIS_COMUNICACAO_LEITURA

    def get_queryset(self):
        queryset = RegistroWebhookComunicacao.objects.select_related(
            "campanha",
            "envio",
            "envio__contato",
            "envio__campanha_comunicacao",
        )
        return filtrar_queryset_por_usuario(queryset, self.request.user, campo_campanha="campanha_id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_COMUNICACAO_ESCRITA)
        context["dados_recebidos_formatados"] = json.dumps(
            self.object.dados_recebidos,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        return context


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
