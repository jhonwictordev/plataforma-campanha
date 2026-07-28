from core.views import ModuloPlaceholderView


class RelatoriosHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Relatórios",
        "descricao": "Estrutura pronta para relatórios filtráveis, exportação em PDF/Excel e impressão com filtros favoritos.",
    }
