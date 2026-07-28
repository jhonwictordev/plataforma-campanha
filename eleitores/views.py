from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView, View

from usuarios.models import Usuario

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA, filtrar_queryset_por_usuario, usuario_tem_nivel

from .forms import ContatoCRMFormulario, ExportacaoContatoCRMFormulario, ImportacaoContatoCRMFormulario
from .models import ContatoCRM
from .services import (
    COLUNAS_IMPORTACAO_EXEMPLO,
    agrupar_contatos_por_status,
    aplicar_filtros_contatos,
    contatos_autorizados_para_exportacao,
    exportar_contatos_csv,
    exportar_contatos_xlsx,
    importar_contatos_arquivo,
)


class ContatoCRMListaBaseMixin:
    def _queryset_filtrado(self):
        queryset = ContatoCRM.objects.select_related("lideranca_relacionada", "responsavel_cadastro")
        queryset = filtrar_queryset_por_usuario(queryset, self.request.user)
        return aplicar_filtros_contatos(queryset, self._filtros_atual())

    def _filtros_atual(self):
        return {
            "busca": self.request.GET.get("busca", ""),
            "cidade": self.request.GET.get("cidade", ""),
            "bairro": self.request.GET.get("bairro", ""),
            "status": self.request.GET.get("status", ""),
            "responsavel": self.request.GET.get("responsavel", ""),
            "origem": self.request.GET.get("origem", ""),
            "tag": self.request.GET.get("tag", ""),
        }

    def _querystring_sem_pagina(self):
        query = self.request.GET.copy()
        if "page" in query:
            query.pop("page")
        return query.urlencode()

    def _responsaveis_disponiveis(self):
        queryset = Usuario.objects.order_by("nome_completo", "pk")
        if not (self.request.user.is_superuser or getattr(self.request.user, "is_staff", False)):
            queryset = queryset.filter(campanha_id=getattr(self.request.user, "campanha_id", None))
        return queryset

    def _origens_disponiveis(self):
        queryset = ContatoCRM.objects.all()
        if not (self.request.user.is_superuser or getattr(self.request.user, "is_staff", False)):
            queryset = queryset.filter(campanha_id=getattr(self.request.user, "campanha_id", None))
        return (
            queryset.exclude(origem_contato="")
            .order_by("origem_contato")
            .values_list("origem_contato", flat=True)
            .distinct()
        )

    def _tags_disponiveis(self):
        queryset = ContatoCRM.objects.only("tags")
        if not (self.request.user.is_superuser or getattr(self.request.user, "is_staff", False)):
            queryset = queryset.filter(campanha_id=getattr(self.request.user, "campanha_id", None))
        tags = sorted({tag for contato in queryset for tag in (contato.tags or []) if tag})
        return tags


class EleitoresHomeView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, ContatoCRMListaBaseMixin, ListView):
    model = ContatoCRM
    template_name = "eleitores/lista.html"
    context_object_name = "contatos"
    niveis_permitidos = PAPEIS_CRM_LEITURA
    paginate_by = 20

    def get_queryset(self):
        return self._queryset_filtrado().order_by("nome_completo", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtros = self._filtros_atual()
        context["titulo"] = "CRM de contatos"
        context["descricao"] = "Cadastre, filtre, importe e acompanhe contatos da campanha com segregacao por territorio e consentimento."
        context["filtros"] = filtros
        context["status_opcoes"] = ContatoCRM.EtapasFunil.choices
        context["responsaveis_disponiveis"] = self._responsaveis_disponiveis()
        context["origens_disponiveis"] = self._origens_disponiveis()
        context["tags_disponiveis"] = self._tags_disponiveis()
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_CRM_ESCRITA)
        context["querystring_atual"] = self._querystring_sem_pagina()
        return context


class ContatoCRMKanbanView(LoginRequiredMixin, NivelAcessoMixin, ContatoCRMListaBaseMixin, TemplateView):
    template_name = "eleitores/kanban.html"
    niveis_permitidos = PAPEIS_CRM_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self._queryset_filtrado().order_by("nome_completo", "pk")
        filtros = self._filtros_atual()
        context["titulo"] = "Kanban do CRM"
        context["descricao"] = "Visualize o funil de relacionamento por etapa, mantendo o isolamento de campanha e os filtros do CRM."
        context["colunas_kanban"] = agrupar_contatos_por_status(queryset)
        context["filtros"] = filtros
        context["status_opcoes"] = ContatoCRM.EtapasFunil.choices
        context["responsaveis_disponiveis"] = self._responsaveis_disponiveis()
        context["origens_disponiveis"] = self._origens_disponiveis()
        context["tags_disponiveis"] = self._tags_disponiveis()
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_CRM_ESCRITA)
        context["total_contatos"] = queryset.count()
        context["querystring_atual"] = self._querystring_sem_pagina()
        return context


class ContatoCRMImportarView(LoginRequiredMixin, NivelAcessoMixin, FormView):
    template_name = "eleitores/importar.html"
    form_class = ImportacaoContatoCRMFormulario
    niveis_permitidos = PAPEIS_CRM_ESCRITA

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de importar contatos.")

        self.resultado_importacao = importar_contatos_arquivo(
            arquivo=form.cleaned_data["arquivo"],
            campanha=self.request.user.campanha,
            usuario=self.request.user,
            atualizar_existentes=form.cleaned_data.get("atualizar_existentes", False),
        )
        mensagens = [
            f"{self.resultado_importacao['criados']} criados",
            f"{self.resultado_importacao['atualizados']} atualizados",
            f"{self.resultado_importacao['ignorados']} ignorados",
        ]
        nivel = messages.WARNING if self.resultado_importacao["erros"] else messages.SUCCESS
        messages.add_message(
            self.request,
            level=nivel,
            message=f"Importacao concluida: {', '.join(mensagens)}.",
        )
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Importar contatos"
        context["descricao"] = "Aceita arquivos CSV e XLSX. O processamento respeita campanha, duplicidade e consentimento."
        context["colunas_exemplo"] = COLUNAS_IMPORTACAO_EXEMPLO
        context["resultado_importacao"] = getattr(self, "resultado_importacao", None)
        return context


class ContatoCRMExportarView(LoginRequiredMixin, NivelAcessoMixin, ContatoCRMListaBaseMixin, View):
    niveis_permitidos = PAPEIS_CRM_ESCRITA

    def get(self, request, *args, **kwargs):
        formulario = ExportacaoContatoCRMFormulario(request.GET or None)
        if not formulario.is_valid():
            messages.error(request, "Selecione um formato valido para exportar.")
            return self._redirecionar_home()

        queryset = self._queryset_filtrado().order_by("nome_completo", "pk")
        queryset = contatos_autorizados_para_exportacao(queryset)
        if not queryset.exists():
            messages.warning(
                request,
                "Nao ha contatos autorizados para exportacao com os filtros informados.",
            )
            return self._redirecionar_home()

        formato = formulario.cleaned_data["formato"]
        campanha = getattr(request.user, "campanha", None)
        if formato == "xlsx":
            return exportar_contatos_xlsx(queryset, usuario=request.user, campanha=campanha)
        return exportar_contatos_csv(queryset, usuario=request.user, campanha=campanha)

    def _redirecionar_home(self):
        url = reverse_lazy("eleitores:home")
        query = self.request.GET.copy()
        if "formato" in query:
            query.pop("formato")
        if query:
            return self._redirect_with_query(url, query.urlencode())
        return self._redirect_with_query(url, "")

    def _redirect_with_query(self, url, querystring):
        from django.shortcuts import redirect

        destino = f"{url}?{querystring}" if querystring else str(url)
        return redirect(destino)


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
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar contatos.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class ContatoCRMDetailView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, DetailView):
    model = ContatoCRM
    template_name = "eleitores/detalhe.html"
    context_object_name = "contato"
    niveis_permitidos = PAPEIS_CRM_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_CRM_ESCRITA)
        return context


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
