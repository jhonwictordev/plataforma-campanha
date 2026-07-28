from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_EQUIPE


class EquipeHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_EQUIPE
    extra_context = {
        "titulo": "Equipe e tarefas",
        "descricao": "Estrutura pronta para cadastro da equipe, departamentos e quadro Kanban de execução.",
    }
