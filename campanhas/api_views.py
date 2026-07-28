from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_TODOS_MODULOS

from .models import Campanha
from .serializers import CampanhaSerializer
from .views import PAPEIS_GESTAO_CAMPANHA, usuario_pode_gerir_todas_campanhas


class CampanhaViewSet(ViewSetCampanhaProtegido):
    queryset = Campanha.objects.select_related("coordenador_responsavel").order_by("data_eleicao", "nome_campanha", "pk")
    serializer_class = CampanhaSerializer
    permission_classes = [IsAuthenticated]
    niveis_permitidos_leitura = PAPEIS_TODOS_MODULOS
    niveis_permitidos_escrita = PAPEIS_GESTAO_CAMPANHA
    exigir_campanha = False
    campo_campanha = "id"
    filterset_fields = ("situacao", "estado", "municipio", "cargo_disputado")
    search_fields = ("nome_campanha", "nome_candidato", "partido", "numero_candidato", "municipio")
    ordering_fields = ("data_eleicao", "nome_campanha", "nome_candidato", "criado_em", "atualizado_em")

    def get_queryset(self):
        queryset = self.queryset.all()
        usuario = self.request.user
        if usuario_pode_gerir_todas_campanhas(usuario):
            return queryset
        if getattr(usuario, "campanha_id", None):
            return queryset.filter(pk=usuario.campanha_id)
        return queryset.none()

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        campanha = self.get_object()
        campanha.excluir_suavemente()
        return Response(status=status.HTTP_204_NO_CONTENT)
