from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_METAS_ESCRITA, PAPEIS_METAS_LEITURA

from .models import MetaCampanha
from .serializers import MetaCampanhaSerializer


class MetaCampanhaViewSet(ViewSetCampanhaProtegido):
    queryset = MetaCampanha.objects.select_related(
        "campanha",
        "responsavel",
        "equipe",
        "equipe__usuario",
    ).order_by("data_final", "pk")
    serializer_class = MetaCampanhaSerializer
    niveis_permitidos_leitura = PAPEIS_METAS_LEITURA
    niveis_permitidos_escrita = PAPEIS_METAS_ESCRITA
    filterset_fields = ("tipo", "status", "regiao", "responsavel", "equipe")
    search_fields = ("nome", "descricao", "regiao")
    ordering_fields = ("data_final", "data_inicial", "valor_esperado", "valor_realizado", "percentual_conclusao")
