from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_CRM_ESCRITA, PAPEIS_CRM_LEITURA

from .models import ContatoCRM, InteracaoContato, TarefaContato
from .serializers import (
    ContatoCRMSerializer,
    InteracaoContatoSerializer,
    TarefaContatoSerializer,
)


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


class InteracaoContatoViewSet(ViewSetCampanhaProtegido):
    queryset = InteracaoContato.objects.select_related("campanha", "contato", "responsavel").order_by("-data_hora", "-pk")
    serializer_class = InteracaoContatoSerializer
    niveis_permitidos_leitura = PAPEIS_CRM_LEITURA
    niveis_permitidos_escrita = PAPEIS_CRM_ESCRITA
    filterset_fields = ("contato", "responsavel", "tipo")
    search_fields = ("descricao", "tipo", "contato__nome_completo")
    ordering_fields = ("data_hora", "criado_em", "atualizado_em")


class TarefaContatoViewSet(ViewSetCampanhaProtegido):
    queryset = TarefaContato.objects.select_related("campanha", "contato", "responsavel").order_by("concluida", "prazo", "pk")
    serializer_class = TarefaContatoSerializer
    niveis_permitidos_leitura = PAPEIS_CRM_LEITURA
    niveis_permitidos_escrita = PAPEIS_CRM_ESCRITA
    filterset_fields = ("contato", "responsavel", "concluida")
    search_fields = ("titulo", "contato__nome_completo")
    ordering_fields = ("prazo", "criado_em", "atualizado_em")
