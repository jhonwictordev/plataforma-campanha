from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_CRM


class EleitoresHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_CRM
    extra_context = {
        "titulo": "CRM de contatos",
        "descricao": "Estrutura inicial para pipeline de contatos, consentimento, tarefas e interações já vinculadas à campanha.",
    }
