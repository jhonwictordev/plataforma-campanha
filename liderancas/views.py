from core.views import ModuloPlaceholderView


class LiderancasHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Lideranças",
        "descricao": "Base preparada para CRM político de lideranças com histórico de relacionamento e segmentação territorial.",
    }
