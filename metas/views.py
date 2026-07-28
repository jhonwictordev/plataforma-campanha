from core.views import ModuloPlaceholderView


class MetasHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Metas",
        "descricao": "Painel inicial de metas quantitativas com progresso, responsáveis e foco territorial.",
    }
