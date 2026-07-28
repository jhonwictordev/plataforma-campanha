from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_COMUNICACAO


class ComunicacaoHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_COMUNICACAO
    extra_context = {
        "titulo": "Comunicação",
        "descricao": "Base preparada para mensagens autorizadas, listas de bloqueio, campanhas agendadas e métricas de entrega.",
    }
