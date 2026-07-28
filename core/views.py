from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from .health import obter_estado_prontidao
from .mixins import NivelAcessoMixin


class ModuloPlaceholderView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "dashboard/modulo_placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = context.get("titulo", kwargs.get("titulo", "Modulo"))
        context["descricao"] = context.get(
            "descricao",
            kwargs.get(
                "descricao",
                "Este modulo ja esta estruturado e pronto para receber as proximas telas, formularios e APIs.",
            ),
        )
        context["acao_principal"] = context.get("acao_principal", "Continuar implementacao")
        return context


@method_decorator(never_cache, name="dispatch")
class HealthcheckView(View):
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                "status": "ok",
                "aplicacao": "plataforma_campanha",
            }
        )


@method_decorator(never_cache, name="dispatch")
class ProntidaoView(View):
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        payload, status_http = obter_estado_prontidao()
        return JsonResponse(payload, status=status_http)
