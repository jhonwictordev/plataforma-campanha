from core.views import ModuloPlaceholderView


class EleitoresHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "CRM de contatos",
        "descricao": "Estrutura inicial para pipeline de contatos, consentimento, tarefas e interações já vinculadas à campanha.",
    }
