from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA

from .models import ContatoCRM
from .serializers import ContatoCRMSerializer


class ContatoCRMViewSet(ViewSetCampanhaProtegido):
    queryset = ContatoCRM.objects.select_related(
        "campanha",
        "responsavel_cadastro",
        "lideranca_relacionada",
    ).order_by("nome_completo", "pk")
    serializer_class = ContatoCRMSerializer
    niveis_permitidos_leitura = PAPEIS_CRM_LEITURA
    niveis_permitidos_escrita = PAPEIS_CRM_ESCRITA
    filterset_fields = ("cidade", "bairro", "status_funil", "origem_contato", "consentimento_comunicacao")
    search_fields = ("nome_completo", "telefone", "email")
    ordering_fields = ("nome_completo", "cidade", "criado_em", "atualizado_em")
