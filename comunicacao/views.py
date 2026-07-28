from core.views import ModuloPlaceholderView


class ComunicacaoHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Comunicação",
        "descricao": "Base preparada para mensagens autorizadas, listas de bloqueio, campanhas agendadas e métricas de entrega.",
    }
