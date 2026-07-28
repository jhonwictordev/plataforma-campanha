from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_CRM


class LiderancasHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_CRM
    extra_context = {
        "titulo": "Lideranças",
        "descricao": "Base preparada para CRM político de lideranças com histórico de relacionamento e segmentação territorial.",
    }
