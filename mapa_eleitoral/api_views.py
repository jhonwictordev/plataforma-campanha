from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from agenda.models import EventoAgenda
from core.api import ViewSetAnaliticoCampanhaProtegido
from core.permissions import PAPEIS_CRM
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe
from liderancas.models import Lideranca

from .serializers import MapaEleitoralRespostaSerializer
from .services import construir_payload, resolver_camada, resolver_periodo


class MapaEleitoralViewSet(ViewSetAnaliticoCampanhaProtegido):
    niveis_permitidos = PAPEIS_CRM
    serializer_class = MapaEleitoralRespostaSerializer

    def _querysets_base(self):
        return {
            "contatos": self.filtrar_queryset(
                ContatoCRM.objects.select_related("campanha", "responsavel_cadastro", "lideranca_relacionada")
            ),
            "liderancas": self.filtrar_queryset(
                Lideranca.objects.select_related("campanha", "responsavel_contato")
            ),
            "eventos": self.filtrar_queryset(
                EventoAgenda.objects.select_related("campanha", "responsavel")
            ),
            "equipes": self.filtrar_queryset(
                IntegranteEquipe.objects.select_related("campanha", "responsavel_direto", "usuario")
            ),
        }

    def _aplicar_filtros_territoriais(self, dados):
        cidade = self.request.query_params.get("cidade", "").strip()
        bairro = self.request.query_params.get("bairro", "").strip()

        if cidade:
            dados["contatos"] = dados["contatos"].filter(cidade__iexact=cidade)
            dados["liderancas"] = dados["liderancas"].filter(cidade__iexact=cidade)
            dados["equipes"] = dados["equipes"].filter(cidade_regiao__icontains=cidade)
            dados["eventos"] = dados["eventos"].filter(endereco__icontains=cidade)
        if bairro:
            dados["contatos"] = dados["contatos"].filter(bairro__iexact=bairro)
            dados["liderancas"] = dados["liderancas"].filter(bairro__iexact=bairro)
            dados["eventos"] = dados["eventos"].filter(endereco__icontains=bairro)
        return cidade, bairro, dados

    @extend_schema(responses=MapaEleitoralRespostaSerializer)
    def list(self, request):
        periodo, data_inicial, data_final = resolver_periodo(request.query_params.get("periodo"))
        camada_ativa = resolver_camada(request.query_params.get("camada"))
        dados = self._querysets_base()
        cidade, bairro, dados = self._aplicar_filtros_territoriais(dados)

        payload = construir_payload(
            contatos=dados["contatos"],
            liderancas=dados["liderancas"],
            eventos=dados["eventos"],
            equipes=dados["equipes"],
            camada_ativa=camada_ativa,
            periodo=periodo,
            data_inicial=data_inicial,
            data_final=data_final,
            cidade=cidade,
            bairro=bairro,
        )
        serializer = MapaEleitoralRespostaSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
