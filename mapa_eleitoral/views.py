from core.views import ModuloPlaceholderView


class MapaEleitoralHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Mapa eleitoral",
        "descricao": "Base do painel territorial preparada para Leaflet.js, clusters e visualização agregada com consentimento.",
    }
