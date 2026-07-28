from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA

from .models import InteracaoLideranca, Lideranca
from .serializers import InteracaoLiderancaSerializer, LiderancaSerializer


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


class InteracaoLiderancaViewSet(ViewSetCampanhaProtegido):
    queryset = InteracaoLideranca.objects.select_related("campanha", "lideranca", "responsavel").order_by("-data_hora", "-pk")
    serializer_class = InteracaoLiderancaSerializer
    niveis_permitidos_leitura = PAPEIS_CRM_LEITURA
    niveis_permitidos_escrita = PAPEIS_CRM_ESCRITA
    filterset_fields = ("lideranca", "responsavel", "tipo")
    search_fields = ("resumo", "detalhes", "lideranca__nome_completo", "lideranca__nome_conhecido")
    ordering_fields = ("data_hora", "criado_em", "atualizado_em")
