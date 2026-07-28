from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_EQUIPE


class MetasHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_EQUIPE
    extra_context = {
        "titulo": "Metas",
        "descricao": "Painel inicial de metas quantitativas com progresso, responsáveis e foco territorial.",
    }
