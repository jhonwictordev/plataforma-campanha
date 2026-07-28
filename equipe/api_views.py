from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_EQUIPE_ESCRITA, PAPEIS_EQUIPE_LEITURA

from .models import ComentarioTarefaEquipe, IntegranteEquipe, TarefaEquipe
from .serializers import (
    ComentarioTarefaEquipeSerializer,
    IntegranteEquipeSerializer,
    TarefaEquipeSerializer,
)


class IntegranteEquipeViewSet(ViewSetCampanhaProtegido):
    queryset = IntegranteEquipe.objects.select_related(
        "campanha",
        "responsavel_direto",
        "usuario",
    ).order_by("nome", "pk")
    serializer_class = IntegranteEquipeSerializer
    niveis_permitidos_leitura = PAPEIS_EQUIPE_LEITURA
    niveis_permitidos_escrita = PAPEIS_EQUIPE_ESCRITA
    filterset_fields = ("departamento", "cidade_regiao", "status", "funcao")
    search_fields = ("nome", "email", "telefone", "funcao", "departamento")
    ordering_fields = ("nome", "data_entrada", "criado_em", "atualizado_em")


class TarefaEquipeViewSet(ViewSetCampanhaProtegido):
    queryset = TarefaEquipe.objects.select_related(
        "campanha",
        "responsavel",
        "responsavel__usuario",
    ).order_by("status", "prazo", "pk")
    serializer_class = TarefaEquipeSerializer
    niveis_permitidos_leitura = PAPEIS_EQUIPE_LEITURA
    niveis_permitidos_escrita = PAPEIS_EQUIPE_ESCRITA
    filterset_fields = ("status", "prioridade", "responsavel")
    search_fields = ("titulo", "descricao", "comentarios", "comentarios_registrados__conteudo")
    ordering_fields = ("status", "prazo", "criado_em", "atualizado_em")


class ComentarioTarefaEquipeViewSet(ViewSetCampanhaProtegido):
    queryset = ComentarioTarefaEquipe.objects.select_related(
        "campanha",
        "tarefa",
        "autor",
    ).order_by("-criado_em", "-pk")
    serializer_class = ComentarioTarefaEquipeSerializer
    niveis_permitidos_leitura = PAPEIS_EQUIPE_LEITURA
    niveis_permitidos_escrita = PAPEIS_EQUIPE_ESCRITA
    filterset_fields = ("tarefa", "autor")
    search_fields = ("conteudo",)
    ordering_fields = ("criado_em", "atualizado_em")
