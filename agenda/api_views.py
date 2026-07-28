from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_AGENDA_ESCRITA, PAPEIS_AGENDA_LEITURA

from .models import EventoAgenda
from .serializers import EventoAgendaSerializer


class EventoAgendaViewSet(ViewSetCampanhaProtegido):
    queryset = (
        EventoAgenda.objects.select_related("campanha", "responsavel")
        .prefetch_related("participantes", "liderancas_convidadas")
        .order_by("data", "horario_inicial", "pk")
    )
    serializer_class = EventoAgendaSerializer
    niveis_permitidos_leitura = PAPEIS_AGENDA_LEITURA
    niveis_permitidos_escrita = PAPEIS_AGENDA_ESCRITA
    filterset_fields = ("data", "tipo", "status", "prioridade", "responsavel")
    search_fields = ("titulo", "descricao", "endereco", "observacoes")
    ordering_fields = ("data", "horario_inicial", "criado_em", "atualizado_em")
