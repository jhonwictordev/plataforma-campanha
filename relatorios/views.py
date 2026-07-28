from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from core.mixins import NivelAcessoMixin
from core.permissions import PAPEIS_TODOS_MODULOS

from .forms import FiltroFavoritoRelatorioFormulario, RelatorioFiltroFormulario
from .models import FiltroFavoritoRelatorio
from .services import (
    campanha_atual,
    filters_to_querystring,
    gerar_relatorio,
    obter_relatorios_disponiveis,
    queryset_responsaveis,
    resposta_excel,
    resposta_pdf,
    serialize_filters,
    usuario_admin,
    validar_tipo_relatorio,
)


class RelatorioBaseMixin(LoginRequiredMixin, NivelAcessoMixin):
    niveis_permitidos = PAPEIS_TODOS_MODULOS

    def dispatch(self, request, *args, **kwargs):
        self.relatorios_disponiveis = obter_relatorios_disponiveis(request.user)
        if not self.relatorios_disponiveis:
            return HttpResponseBadRequest("Nao ha relatorios disponiveis para este perfil.")
        tipo_requisitado = (
            request.GET.get("tipo_relatorio")
            or request.POST.get("tipo_relatorio")
            or self.relatorios_disponiveis[0]["chave"]
        )
        validar_tipo_relatorio(request.user, tipo_requisitado, self.relatorios_disponiveis)
        return super().dispatch(request, *args, **kwargs)

    def _dados_formulario(self, origem):
        if origem is None:
            return None
        return origem if origem else None

    def get_filtro_form(self, origem=None):
        return RelatorioFiltroFormulario(
            data=self._dados_formulario(origem),
            usuario=self.request.user,
            relatorios_disponiveis=self.relatorios_disponiveis,
        )

    def get_filtros(self, origem=None):
        formulario = self.get_filtro_form(origem=origem)
        return formulario, formulario.dados_resolvidos()

    def get_relatorio(self, filtros):
        return gerar_relatorio(filtros["tipo_relatorio"], filtros, self.request.user)

    def get_favoritos(self):
        queryset = FiltroFavoritoRelatorio.objects.filter(usuario=self.request.user).order_by("nome", "pk")
        if not usuario_admin(self.request.user):
            queryset = queryset.filter(campanha_id=getattr(self.request.user, "campanha_id", None))

        favoritos = []
        relatorios_permitidos = {item["chave"] for item in self.relatorios_disponiveis}
        for favorito in queryset:
            if favorito.tipo_relatorio not in relatorios_permitidos:
                continue
            favorito.querystring = filters_to_querystring(favorito.filtros)
            favoritos.append(favorito)
        return favoritos


class RelatoriosHomeView(RelatorioBaseMixin, TemplateView):
    template_name = "relatorios/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro_form, filtros = self.get_filtros(origem=self.request.GET)
        relatorio = self.get_relatorio(filtros)

        paginator = Paginator(relatorio["linhas"], 20)
        page_obj = paginator.get_page(self.request.GET.get("pagina"))
        filtros_serializados = serialize_filters(filtros)

        cards_relatorios = []
        for item in self.relatorios_disponiveis:
            cards_relatorios.append(
                {
                    **item,
                    "ativo": item["chave"] == filtros["tipo_relatorio"],
                    "querystring": filters_to_querystring({**filtros_serializados, "tipo_relatorio": item["chave"]}),
                }
            )

        context["titulo"] = "Relatorios"
        context["descricao"] = "Central de relatorios filtraveis com favoritos, impressao e exportacao segura por campanha."
        context["filtro_form"] = filtro_form
        context["favorito_form"] = FiltroFavoritoRelatorioFormulario()
        context["relatorio"] = relatorio
        context["page_obj"] = page_obj
        context["linhas"] = page_obj.object_list
        context["total_linhas"] = len(relatorio["linhas"])
        context["filtros"] = filtros
        context["filtros_querystring"] = filters_to_querystring(filtros_serializados)
        context["cards_relatorios"] = cards_relatorios
        context["favoritos"] = self.get_favoritos()
        context["mostrar_filtro_campanha"] = usuario_admin(self.request.user)
        context["campanha_atual"] = campanha_atual(self.request.user, filtros["campanha_id"])
        context["responsaveis"] = queryset_responsaveis(self.request.user, filtros["campanha_id"])
        context["data_referencia"] = "28 de julho de 2026"
        return context


class RelatorioExcelView(RelatorioBaseMixin, View):
    def get(self, request, *args, **kwargs):
        _, filtros = self.get_filtros(origem=request.GET)
        relatorio = self.get_relatorio(filtros)
        return resposta_excel(relatorio)


class RelatorioPdfView(RelatorioBaseMixin, View):
    def get(self, request, *args, **kwargs):
        _, filtros = self.get_filtros(origem=request.GET)
        relatorio = self.get_relatorio(filtros)
        return resposta_pdf(relatorio)


class RelatorioImpressaoView(RelatorioBaseMixin, TemplateView):
    template_name = "relatorios/impressao.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _, filtros = self.get_filtros(origem=self.request.GET)
        context["relatorio"] = self.get_relatorio(filtros)
        context["data_referencia"] = "28 de julho de 2026"
        return context


class FiltroFavoritoRelatorioCreateView(RelatorioBaseMixin, View):
    def post(self, request, *args, **kwargs):
        nome_form = FiltroFavoritoRelatorioFormulario(request.POST)
        _, filtros = self.get_filtros(origem=request.POST)
        redirect_url = f"{reverse('relatorios:home')}?{filters_to_querystring(serialize_filters(filtros))}"

        if not nome_form.is_valid():
            messages.error(request, "Informe um nome valido para salvar o filtro favorito.")
            return redirect(redirect_url)

        campanha = campanha_atual(request.user, filtros["campanha_id"])
        if not campanha:
            messages.error(request, "Selecione uma campanha especifica antes de salvar um filtro favorito.")
            return redirect(redirect_url)

        FiltroFavoritoRelatorio.objects.update_or_create(
            usuario=request.user,
            campanha=campanha,
            nome=nome_form.cleaned_data["nome"],
            defaults={
                "tipo_relatorio": filtros["tipo_relatorio"],
                "filtros": serialize_filters(filtros),
            },
        )
        messages.success(request, "Filtro favorito salvo com sucesso.")
        return redirect(redirect_url)


class FiltroFavoritoRelatorioDeleteView(RelatorioBaseMixin, View):
    def post(self, request, *args, **kwargs):
        queryset = FiltroFavoritoRelatorio.objects.filter(usuario=request.user)
        if not usuario_admin(request.user):
            queryset = queryset.filter(campanha_id=getattr(request.user, "campanha_id", None))
        favorito = get_object_or_404(queryset, pk=kwargs["pk"])
        favorito.excluir_suavemente()
        messages.success(request, "Filtro favorito removido com sucesso.")
        return redirect("relatorios:home")
