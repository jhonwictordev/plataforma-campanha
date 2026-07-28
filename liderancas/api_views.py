from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA

from .models import Lideranca
from .serializers import LiderancaSerializer


class LiderancaViewSet(ViewSetCampanhaProtegido):
    queryset = Lideranca.objects.select_related(
        "campanha",
        "responsavel_contato",
    ).order_by("nome_completo", "pk")
    serializer_class = LiderancaSerializer
    niveis_permitidos_leitura = PAPEIS_CRM_LEITURA
    niveis_permitidos_escrita = PAPEIS_CRM_ESCRITA
    filterset_fields = ("cidade", "bairro", "tipo_lideranca", "situacao_relacionamento", "regiao_eleitoral")
    search_fields = ("nome_completo", "nome_conhecido", "telefone", "email")
    ordering_fields = ("nome_completo", "cidade", "criado_em", "atualizado_em")
