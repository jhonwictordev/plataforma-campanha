from core.views import ModuloPlaceholderView


class AgendaHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Agenda",
        "descricao": "Calendário compartilhado preparado para eventos, participantes, lembretes e conflitos de horário.",
    }
