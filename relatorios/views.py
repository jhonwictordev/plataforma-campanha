from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_TODOS_MODULOS


class RelatoriosHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_TODOS_MODULOS
    extra_context = {
        "titulo": "Relatórios",
        "descricao": "Estrutura pronta para relatórios filtráveis, exportação em PDF/Excel e impressão com filtros favoritos.",
    }
