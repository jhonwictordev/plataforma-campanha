from core.views import ModuloPlaceholderView


class EquipeHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Equipe e tarefas",
        "descricao": "Estrutura pronta para cadastro da equipe, departamentos e quadro Kanban de execução.",
    }
