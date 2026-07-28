from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_AGENDA


class AgendaHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_AGENDA
    extra_context = {
        "titulo": "Agenda",
        "descricao": "Calendário compartilhado preparado para eventos, participantes, lembretes e conflitos de horário.",
    }
