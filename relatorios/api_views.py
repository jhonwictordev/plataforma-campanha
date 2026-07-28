from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from campanhas.models import Campanha
from core.api import ViewSetAnaliticoCampanhaProtegido, ViewSetCampanhaProtegido
from core.permissions import PAPEIS_TODOS_MODULOS
from rest_framework.exceptions import ValidationError

from usuarios.models import Usuario

from .forms import RelatorioFiltroFormulario
from .models import FiltroFavoritoRelatorio
from .serializers import FiltroFavoritoRelatorioSerializer, RelatorioRespostaSerializer
from .services import (
    campanha_atual,
    gerar_relatorio,
    obter_relatorios_disponiveis,
    queryset_responsaveis,
    resposta_excel,
    resposta_pdf,
    usuario_admin,
    validar_tipo_relatorio,
)


class RelatorioViewSet(ViewSetAnaliticoCampanhaProtegido):
    niveis_permitidos = PAPEIS_TODOS_MODULOS
    serializer_class = RelatorioRespostaSerializer

    def _relatorios_disponiveis(self):
        relatorios = obter_relatorios_disponiveis(self.request.user)
        if not relatorios:
            raise ValidationError({"detail": "Nao ha relatorios disponiveis para este perfil."})
        return relatorios

    def _obter_formulario_e_filtros(self):
        relatorios_disponiveis = self._relatorios_disponiveis()
        tipo_requisitado = self.request.query_params.get("tipo_relatorio") or relatorios_disponiveis[0]["chave"]
        validar_tipo_relatorio(self.request.user, tipo_requisitado, relatorios_disponiveis)
        dados = self.request.query_params if self.request.query_params else None
        formulario = RelatorioFiltroFormulario(
            data=dados,
            usuario=self.request.user,
            relatorios_disponiveis=relatorios_disponiveis,
        )
        if dados is not None and not formulario.is_valid():
            raise ValidationError(formulario.errors)
        filtros = formulario.dados_resolvidos()
        return relatorios_disponiveis, filtros

    def _campanhas_disponiveis(self):
        if not usuario_admin(self.request.user):
            return []
        campanhas = Campanha.objects.order_by("nome_campanha", "nome_candidato")
        return [
            {
                "id": str(campanha.pk),
                "nome_campanha": campanha.nome_campanha,
                "nome_candidato": campanha.nome_candidato,
                "municipio": campanha.municipio,
                "estado": campanha.estado,
                "situacao": campanha.situacao,
            }
            for campanha in campanhas
        ]

    def _responsaveis_disponiveis(self, campanha_id):
        return [
            {
                "id": str(usuario.pk),
                "nome_completo": usuario.nome_completo,
                "campanha_id": str(usuario.campanha_id) if usuario.campanha_id else "",
            }
            for usuario in queryset_responsaveis(self.request.user, campanha_id)
        ]

    def _campanha_atual(self, campanha_id):
        campanha = campanha_atual(self.request.user, campanha_id)
        if not campanha:
            return None
        return {
            "id": str(campanha.pk),
            "nome_campanha": campanha.nome_campanha,
            "nome_candidato": campanha.nome_candidato,
            "municipio": campanha.municipio,
            "estado": campanha.estado,
            "situacao": campanha.situacao,
        }

    def _serializar_relatorio(self, relatorio):
        return {
            "tipo": relatorio["tipo"],
            "titulo": relatorio["titulo"],
            "descricao": relatorio["descricao"],
            "colunas": relatorio["colunas"],
            "linhas": relatorio["linhas"],
            "resumo": relatorio["resumo"],
            "observacao": relatorio["observacao"],
            "filtros_label": relatorio["filtros_label"],
            "campanha_atual": self._campanha_atual(
                str(relatorio["campanha_atual"].pk) if relatorio.get("campanha_atual") else ""
            ),
        }

    @extend_schema(responses=RelatorioRespostaSerializer)
    def list(self, request):
        relatorios_disponiveis, filtros = self._obter_formulario_e_filtros()
        relatorio = gerar_relatorio(filtros["tipo_relatorio"], filtros, request.user)

        payload = {
            "filtros": {
                "tipo_relatorio": filtros["tipo_relatorio"],
                "campanha": str(filtros["campanha_id"] or ""),
                "data_inicial": filtros["data_inicial"].isoformat(),
                "data_final": filtros["data_final"].isoformat(),
                "cidade": filtros["cidade"],
                "bairro": filtros["bairro"],
                "responsavel": str(filtros["responsavel_id"] or ""),
            },
            "campanha_atual": self._campanha_atual(filtros["campanha_id"]),
            "campanhas_disponiveis": self._campanhas_disponiveis(),
            "responsaveis": self._responsaveis_disponiveis(filtros["campanha_id"]),
            "relatorios_disponiveis": [
                {
                    "chave": item["chave"],
                    "rotulo": item["rotulo"],
                    "descricao": item["descricao"],
                }
                for item in relatorios_disponiveis
            ],
            "relatorio": self._serializar_relatorio(relatorio),
            "total_linhas": len(relatorio["linhas"]),
            "mostrar_filtro_campanha": usuario_admin(request.user),
        }
        serializer = RelatorioRespostaSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @action(detail=False, methods=["get"], url_path="excel")
    def excel(self, request):
        _, filtros = self._obter_formulario_e_filtros()
        relatorio = gerar_relatorio(filtros["tipo_relatorio"], filtros, request.user)
        return resposta_excel(relatorio)

    @action(detail=False, methods=["get"], url_path="pdf")
    def pdf(self, request):
        _, filtros = self._obter_formulario_e_filtros()
        relatorio = gerar_relatorio(filtros["tipo_relatorio"], filtros, request.user)
        return resposta_pdf(relatorio)


class FiltroFavoritoRelatorioViewSet(ViewSetCampanhaProtegido):
    queryset = FiltroFavoritoRelatorio.objects.select_related("campanha", "usuario").order_by("nome", "pk")
    serializer_class = FiltroFavoritoRelatorioSerializer
    niveis_permitidos_leitura = PAPEIS_TODOS_MODULOS
    niveis_permitidos_escrita = PAPEIS_TODOS_MODULOS
    filterset_fields = ("tipo_relatorio", "campanha")
    search_fields = ("nome", "tipo_relatorio")
    ordering_fields = ("nome", "criado_em", "atualizado_em")

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        usuario = self.request.user
        if not usuario_admin(usuario):
            serializer.save(campanha=usuario.campanha, usuario=usuario)
            return
        serializer.save(usuario=usuario)

    def destroy(self, request, *args, **kwargs):
        favorito = self.get_object()
        favorito.excluir_suavemente()
        return Response(status=204)
