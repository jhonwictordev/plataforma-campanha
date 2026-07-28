from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView

from auditoria.models import LogSeguranca
from campanhas.models import Campanha
from core.mixins import MensagemSucessoMixin, NivelAcessoMixin

from .forms import (
    FormularioAutenticacaoUsuario,
    FormularioConfirmacaoSenha,
    FormularioCriacaoUsuario,
    FormularioGestaoUsuario,
    FormularioPerfilUsuario,
    FormularioTokenDoisFatores,
)
from .models import Usuario
from .policies import PAPEIS_GESTAO_USUARIOS, usuario_pode_gerir_multicampanha
from .two_factor import (
    ativar_dois_fatores,
    desativar_dois_fatores,
    obter_ou_criar_dispositivo_pendente,
    quantidade_codigos_recuperacao,
    qr_code_data_uri,
    registrar_log_dois_fatores,
    regenerar_codigos_recuperacao,
    segredo_base32,
    sincronizar_estado_dois_fatores,
    usuario_exige_dois_fatores,
    verificar_token_login,
)

SESSAO_USUARIO_PRE_2FA = "usuario_pre_2fa_id"
SESSAO_BACKEND_PRE_2FA = "usuario_pre_2fa_backend"
SESSAO_REDIRECIONAMENTO_PRE_2FA = "usuario_pre_2fa_redirect"
SESSAO_CODIGOS_RECUPERACAO = "usuarios_codigos_recuperacao_2fa"


def limpar_estado_pre_2fa(request) -> None:
    for chave in (
        SESSAO_USUARIO_PRE_2FA,
        SESSAO_BACKEND_PRE_2FA,
        SESSAO_REDIRECIONAMENTO_PRE_2FA,
    ):
        request.session.pop(chave, None)


def obter_usuario_pre_2fa(request) -> Usuario | None:
    usuario_id = request.session.get(SESSAO_USUARIO_PRE_2FA)
    if not usuario_id:
        return None
    return Usuario.objects.filter(pk=usuario_id, is_active=True).first()


def obter_redirecionamento_seguro(request) -> str:
    destino = request.session.get(SESSAO_REDIRECIONAMENTO_PRE_2FA) or settings.LOGIN_REDIRECT_URL
    if url_has_allowed_host_and_scheme(destino, {request.get_host()}, require_https=request.is_secure()):
        return destino
    return str(reverse("dashboard:home"))


def registrar_log_gestao_usuario(usuario_executor, request, evento: str, descricao: str, severidade: str = "info") -> None:
    LogSeguranca.todos_objetos.create(
        campanha=getattr(usuario_executor, "campanha", None),
        usuario=usuario_executor,
        evento=evento,
        severidade=severidade,
        descricao=descricao,
        endereco_ip=request.META.get("REMOTE_ADDR"),
    )


class LoginUsuarioView(LoginView):
    template_name = "registration/login.html"
    authentication_form = FormularioAutenticacaoUsuario
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if request.session.get(SESSAO_USUARIO_PRE_2FA):
            return redirect("login_2fa")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        usuario = form.get_user()
        limpar_estado_pre_2fa(self.request)
        if usuario_exige_dois_fatores(usuario):
            self.request.session[SESSAO_USUARIO_PRE_2FA] = str(usuario.pk)
            self.request.session[SESSAO_BACKEND_PRE_2FA] = usuario.backend
            self.request.session[SESSAO_REDIRECIONAMENTO_PRE_2FA] = self.get_redirect_url() or self.get_success_url()
            self.request.session.set_expiry(300)
            registrar_log_dois_fatores(
                usuario=usuario,
                evento="login_2fa_pendente",
                descricao=f"Segundo fator solicitado para {usuario.email}.",
                endereco_ip=self.request.META.get("REMOTE_ADDR"),
            )
            messages.info(
                self.request,
                "Informe o codigo do aplicativo autenticador ou um codigo de recuperacao para concluir o login.",
            )
            return redirect("login_2fa")
        return super().form_valid(form)


class LoginDoisFatoresView(FormView):
    template_name = "usuarios/login_2fa.html"
    form_class = FormularioTokenDoisFatores

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        self.usuario_pre_2fa = obter_usuario_pre_2fa(request)
        if self.usuario_pre_2fa is None:
            messages.info(request, "Faça o login novamente para continuar.")
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["usuario_pre_2fa"] = self.usuario_pre_2fa
        return context

    def form_valid(self, form):
        token = form.cleaned_data["token"].strip().replace(" ", "")
        backend = self.request.session.get(SESSAO_BACKEND_PRE_2FA)
        if not backend:
            messages.error(self.request, "A sessao de autenticacao expirou. Entre novamente.")
            limpar_estado_pre_2fa(self.request)
            return redirect("login")

        dispositivo, metodo = verificar_token_login(self.usuario_pre_2fa, token)
        if dispositivo is None:
            registrar_log_dois_fatores(
                usuario=self.usuario_pre_2fa,
                evento="login_2fa_falhou",
                descricao=f"Codigo de segundo fator invalido para {self.usuario_pre_2fa.email}.",
                endereco_ip=self.request.META.get("REMOTE_ADDR"),
                severidade="aviso",
            )
            form.add_error("token", "Codigo invalido. Verifique o aplicativo autenticador ou use um codigo de recuperacao.")
            return self.form_invalid(form)

        self.usuario_pre_2fa.otp_device = dispositivo
        login(self.request, self.usuario_pre_2fa, backend=backend)
        self.request.session.set_expiry(None)
        limpar_estado_pre_2fa(self.request)

        if metodo == "recuperacao":
            messages.warning(
                self.request,
                "Login concluido com codigo de recuperacao. Gere novos codigos assim que possivel.",
            )
        else:
            messages.success(self.request, "Autenticacao em dois fatores confirmada com sucesso.")

        registrar_log_dois_fatores(
            usuario=self.usuario_pre_2fa,
            evento="login_2fa_validado",
            descricao=f"Login com segundo fator concluido para {self.usuario_pre_2fa.email} via {metodo}.",
            endereco_ip=self.request.META.get("REMOTE_ADDR"),
        )
        return redirect(obter_redirecionamento_seguro(self.request))


class CancelarLoginDoisFatoresView(View):
    def get(self, request, *args, **kwargs):
        limpar_estado_pre_2fa(request)
        messages.info(request, "A verificacao em duas etapas foi cancelada.")
        return redirect("login")


class PerfilUsuarioView(LoginRequiredMixin, UpdateView):
    model = Usuario
    form_class = FormularioPerfilUsuario
    template_name = "usuarios/perfil.html"
    success_url = reverse_lazy("usuarios:perfil")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dois_fatores_ativo"] = sincronizar_estado_dois_fatores(self.request.user)
        return context


class SegurancaDoisFatoresView(LoginRequiredMixin, TemplateView):
    template_name = "usuarios/dois_fatores.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dois_fatores_ativo"] = sincronizar_estado_dois_fatores(self.request.user)
        context["codigos_recuperacao_restantes"] = quantidade_codigos_recuperacao(self.request.user)
        return context


class AtivarDoisFatoresView(LoginRequiredMixin, FormView):
    template_name = "usuarios/dois_fatores_ativar.html"
    form_class = FormularioTokenDoisFatores
    success_url = reverse_lazy("usuarios:dois_fatores_codigos")

    def dispatch(self, request, *args, **kwargs):
        if sincronizar_estado_dois_fatores(request.user):
            messages.info(request, "A autenticacao em dois fatores ja esta ativa nesta conta.")
            return redirect("usuarios:dois_fatores")
        self.dispositivo = obter_ou_criar_dispositivo_pendente(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config_url"] = self.dispositivo.config_url
        context["segredo_manual"] = segredo_base32(self.dispositivo)
        context["qr_code_data_uri"] = qr_code_data_uri(self.dispositivo.config_url)
        return context

    def form_valid(self, form):
        dispositivo, codigos = ativar_dois_fatores(self.request.user, form.cleaned_data["token"].strip())
        if dispositivo is None:
            form.add_error("token", "Nao foi possivel validar o codigo informado. Tente novamente.")
            return self.form_invalid(form)

        self.request.session[SESSAO_CODIGOS_RECUPERACAO] = codigos
        registrar_log_dois_fatores(
            usuario=self.request.user,
            evento="2fa_ativado",
            descricao=f"Segundo fator habilitado para {self.request.user.email}.",
            endereco_ip=self.request.META.get("REMOTE_ADDR"),
        )
        messages.success(
            self.request,
            "Autenticacao em dois fatores ativada. Guarde os codigos de recuperacao em local seguro.",
        )
        return super().form_valid(form)


class DesativarDoisFatoresView(LoginRequiredMixin, FormView):
    template_name = "usuarios/dois_fatores_form.html"
    form_class = FormularioConfirmacaoSenha
    success_url = reverse_lazy("usuarios:dois_fatores")

    def dispatch(self, request, *args, **kwargs):
        if not sincronizar_estado_dois_fatores(request.user):
            messages.info(request, "A autenticacao em dois fatores nao esta ativa nesta conta.")
            return redirect("usuarios:dois_fatores")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Desativar autenticacao em dois fatores"
        context["descricao"] = "Confirme sua senha para remover o autenticador e invalidar os codigos de recuperacao atuais."
        context["rotulo_botao"] = "Desativar 2FA"
        return context

    def form_valid(self, form):
        desativar_dois_fatores(self.request.user)
        self.request.session.pop(SESSAO_CODIGOS_RECUPERACAO, None)
        registrar_log_dois_fatores(
            usuario=self.request.user,
            evento="2fa_desativado",
            descricao=f"Segundo fator desativado para {self.request.user.email}.",
            endereco_ip=self.request.META.get("REMOTE_ADDR"),
            severidade="aviso",
        )
        messages.success(self.request, "Autenticacao em dois fatores desativada com sucesso.")
        return super().form_valid(form)


class RegenerarCodigosRecuperacaoView(LoginRequiredMixin, FormView):
    template_name = "usuarios/dois_fatores_form.html"
    form_class = FormularioConfirmacaoSenha
    success_url = reverse_lazy("usuarios:dois_fatores_codigos")

    def dispatch(self, request, *args, **kwargs):
        if not sincronizar_estado_dois_fatores(request.user):
            messages.info(request, "Ative a autenticacao em dois fatores antes de gerar codigos de recuperacao.")
            return redirect("usuarios:dois_fatores")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Gerar novos codigos de recuperacao"
        context["descricao"] = "Os codigos antigos deixarao de funcionar assim que os novos forem emitidos."
        context["rotulo_botao"] = "Gerar novos codigos"
        return context

    def form_valid(self, form):
        codigos = regenerar_codigos_recuperacao(self.request.user)
        self.request.session[SESSAO_CODIGOS_RECUPERACAO] = codigos
        registrar_log_dois_fatores(
            usuario=self.request.user,
            evento="2fa_codigos_regenerados",
            descricao=f"Codigos de recuperacao regenerados para {self.request.user.email}.",
            endereco_ip=self.request.META.get("REMOTE_ADDR"),
        )
        messages.success(self.request, "Novos codigos de recuperacao gerados com sucesso.")
        return super().form_valid(form)


class CodigosRecuperacaoView(LoginRequiredMixin, TemplateView):
    template_name = "usuarios/dois_fatores_codigos.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get(SESSAO_CODIGOS_RECUPERACAO):
            messages.info(request, "Nao ha novos codigos para exibir no momento.")
            return redirect("usuarios:dois_fatores")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["codigos_recuperacao"] = self.request.session.get(SESSAO_CODIGOS_RECUPERACAO, [])
        context["codigos_restantes"] = quantidade_codigos_recuperacao(self.request.user)
        return context


class GestaoUsuariosMixin(NivelAcessoMixin):
    niveis_permitidos = PAPEIS_GESTAO_USUARIOS


class QuerysetGestaoUsuariosMixin:
    def get_queryset(self):
        queryset = Usuario.objects.select_related("campanha").order_by("nome_completo", "email", "pk")
        usuario = self.request.user
        if usuario_pode_gerir_multicampanha(usuario):
            return queryset
        if not getattr(usuario, "campanha_id", None):
            return queryset.none()
        return queryset.filter(campanha_id=usuario.campanha_id).filter(
            Q(pk=usuario.pk) | ~Q(nivel_acesso__in=PAPEIS_GESTAO_USUARIOS)
        )


class UsuarioListView(LoginRequiredMixin, GestaoUsuariosMixin, QuerysetGestaoUsuariosMixin, ListView):
    model = Usuario
    template_name = "usuarios/lista.html"
    context_object_name = "usuarios"
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()
        busca = self.request.GET.get("q", "").strip()
        nivel_acesso = self.request.GET.get("nivel_acesso", "").strip()
        status = self.request.GET.get("status", "").strip()
        campanha = self.request.GET.get("campanha", "").strip()

        if busca:
            queryset = queryset.filter(
                Q(nome_completo__icontains=busca)
                | Q(nome_exibicao__icontains=busca)
                | Q(email__icontains=busca)
                | Q(telefone__icontains=busca)
            )
        if nivel_acesso:
            queryset = queryset.filter(nivel_acesso=nivel_acesso)
        if status == "ativos":
            queryset = queryset.filter(is_active=True)
        elif status == "inativos":
            queryset = queryset.filter(is_active=False)
        if campanha and usuario_pode_gerir_multicampanha(self.request.user):
            queryset = queryset.filter(campanha_id=campanha)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset_filtrado = self.get_queryset()
        context["filtros"] = {
            "q": self.request.GET.get("q", "").strip(),
            "nivel_acesso": self.request.GET.get("nivel_acesso", "").strip(),
            "status": self.request.GET.get("status", "").strip(),
            "campanha": self.request.GET.get("campanha", "").strip(),
        }
        context["niveis_acesso"] = Usuario.NiveisAcesso.choices
        context["pode_gerir_multicampanha"] = usuario_pode_gerir_multicampanha(self.request.user)
        context["campanhas_disponiveis"] = Campanha.objects.filter(
            usuarios_vinculados__in=queryset_filtrado.exclude(campanha__isnull=True)
        ).distinct().order_by("nome_campanha")
        context["resumo"] = {
            "total": queryset_filtrado.count(),
            "ativos": queryset_filtrado.filter(is_active=True).count(),
            "com_2fa": queryset_filtrado.filter(dois_fatores_habilitado=True).count(),
            "inativos": queryset_filtrado.filter(is_active=False).count(),
        }
        return context


class UsuarioDetailView(LoginRequiredMixin, GestaoUsuariosMixin, QuerysetGestaoUsuariosMixin, DetailView):
    model = Usuario
    template_name = "usuarios/detalhe.html"
    context_object_name = "usuario_alvo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = self.object.logs_seguranca.order_by("-criado_em", "-pk")
        context["pode_editar"] = self.object.pk != self.request.user.pk
        context["ultimos_logs"] = logs[:6]
        context["resumo_seguranca"] = {
            "tentativas_falhas": self.object.tentativas_falhas,
            "ultimo_acesso": self.object.ultimo_acesso_registrado or self.object.last_login,
            "dois_fatores": self.object.dois_fatores_habilitado,
        }
        return context


class UsuarioCreateView(LoginRequiredMixin, GestaoUsuariosMixin, MensagemSucessoMixin, CreateView):
    model = Usuario
    form_class = FormularioCriacaoUsuario
    template_name = "usuarios/formulario.html"
    mensagem_sucesso = "Usuario cadastrado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario_logado"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("usuarios:detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = "Novo usuario"
        context["subtitulo_pagina"] = "Cadastre acessos internos respeitando campanha, funcao e minimo privilegio."
        context["texto_botao_salvar"] = "Criar usuario"
        return context

    def form_valid(self, form):
        resposta = super().form_valid(form)
        registrar_log_gestao_usuario(
            self.request.user,
            self.request,
            evento="usuario_criado_web",
            descricao=f"Usuario {self.object.email} criado pela interface web.",
        )
        return resposta


class UsuarioUpdateView(
    LoginRequiredMixin,
    GestaoUsuariosMixin,
    QuerysetGestaoUsuariosMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = Usuario
    form_class = FormularioGestaoUsuario
    template_name = "usuarios/formulario.html"
    mensagem_sucesso = "Usuario atualizado com sucesso."

    def dispatch(self, request, *args, **kwargs):
        if str(kwargs.get("pk")) == str(request.user.pk):
            messages.info(request, "Use a tela de perfil para editar sua propria conta.")
            return redirect("usuarios:perfil")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario_logado"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("usuarios:detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = "Editar usuario"
        context["subtitulo_pagina"] = "Atualize dados de contato, papel e status de acesso sem sair do escopo da campanha."
        context["texto_botao_salvar"] = "Salvar alteracoes"
        return context

    def form_valid(self, form):
        resposta = super().form_valid(form)
        registrar_log_gestao_usuario(
            self.request.user,
            self.request,
            evento="usuario_atualizado_web",
            descricao=f"Usuario {self.object.email} atualizado pela interface web.",
        )
        return resposta


class UsuarioDeleteView(LoginRequiredMixin, GestaoUsuariosMixin, QuerysetGestaoUsuariosMixin, DeleteView):
    model = Usuario
    template_name = "usuarios/excluir.html"
    success_url = reverse_lazy("usuarios:lista")

    def dispatch(self, request, *args, **kwargs):
        if str(kwargs.get("pk")) == str(request.user.pk):
            messages.info(request, "Nao e permitido desativar sua propria conta por esta area.")
            return redirect("usuarios:perfil")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=["is_active", "atualizado_em"])
        registrar_log_gestao_usuario(
            self.request.user,
            self.request,
            evento="usuario_desativado_web",
            descricao=f"Usuario {self.object.email} desativado pela interface web.",
            severidade="aviso",
        )
        messages.success(self.request, "Usuario desativado com sucesso.")
        return redirect(self.get_success_url())
