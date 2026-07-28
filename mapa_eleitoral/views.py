from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_CRM


class MapaEleitoralHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_CRM
    extra_context = {
        "titulo": "Mapa eleitoral",
        "descricao": "Base do painel territorial preparada para Leaflet.js, clusters e visualização agregada com consentimento.",
    }
