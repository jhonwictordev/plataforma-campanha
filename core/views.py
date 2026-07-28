from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .mixins import NivelAcessoMixin


class ModuloPlaceholderView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "dashboard/modulo_placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = context.get("titulo", kwargs.get("titulo", "Módulo"))
        context["descricao"] = context.get(
            "descricao",
            kwargs.get(
                "descricao",
                "Este módulo já está estruturado e pronto para receber as próximas telas, formulários e APIs.",
            ),
        )
        context["acao_principal"] = context.get("acao_principal", "Continuar implementação")
        return context
