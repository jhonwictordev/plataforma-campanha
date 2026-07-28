from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from agenda.models import EventoAgenda
from campanhas.models import Campanha
from core.mixins import NivelAcessoMixin
from core.permissions import PAPEIS_CRM, filtrar_queryset_por_usuario
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe
from liderancas.models import Lideranca

from .services import (
    construir_payload,
    lista_camadas,
    lista_periodos,
    resolver_camada,
    resolver_periodo,
)


class MapaEleitoralHomeView(LoginRequiredMixin, NivelAcessoMixin, TemplateView):
    template_name = "mapa_eleitoral/home.html"
    niveis_permitidos = PAPEIS_CRM

    def _usuario_admin(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def _campanha_selecionada_id(self):
        if not self._usuario_admin():
            return getattr(self.request.user, "campanha_id", None)
        campanha_id = self.request.GET.get("campanha", "").strip()
        return campanha_id or None

    def _filtrar_queryset(self, queryset):
        if self._usuario_admin():
            campanha_id = self._campanha_selecionada_id()
            if campanha_id:
                return queryset.filter(campanha_id=campanha_id)
            return queryset
        return filtrar_queryset_por_usuario(queryset, self.request.user)

    def _querysets_base(self):
        return {
            "contatos": self._filtrar_queryset(
                ContatoCRM.objects.select_related("campanha", "responsavel_cadastro", "lideranca_relacionada")
            ),
            "liderancas": self._filtrar_queryset(
                Lideranca.objects.select_related("campanha", "responsavel_contato")
            ),
            "eventos": self._filtrar_queryset(
                EventoAgenda.objects.select_related("campanha", "responsavel")
            ),
            "equipes": self._filtrar_queryset(
                IntegranteEquipe.objects.select_related("campanha", "responsavel_direto", "usuario")
            ),
        }

    def _aplicar_filtros_territoriais(self, dados):
        cidade = self.request.GET.get("cidade", "").strip()
        bairro = self.request.GET.get("bairro", "").strip()

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

    def _campanhas_disponiveis(self):
        if not self._usuario_admin():
            return Campanha.objects.none()
        return Campanha.objects.order_by("nome_campanha", "nome_candidato")

    def _campanha_atual(self):
        campanha_id = self._campanha_selecionada_id()
        if campanha_id:
            return Campanha.objects.filter(pk=campanha_id).first()
        if not self._usuario_admin() and getattr(self.request.user, "campanha_id", None):
            return Campanha.objects.filter(pk=self.request.user.campanha_id).first()
        return None

    def _cidades_disponiveis(self, contatos, liderancas):
        cidades = set(contatos.exclude(cidade="").values_list("cidade", flat=True))
        cidades.update(liderancas.exclude(cidade="").values_list("cidade", flat=True))
        return sorted(item for item in cidades if item)

    def _bairros_disponiveis(self, contatos, liderancas, cidade: str):
        contatos_base = contatos
        liderancas_base = liderancas
        if cidade:
            contatos_base = contatos_base.filter(cidade__iexact=cidade)
            liderancas_base = liderancas_base.filter(cidade__iexact=cidade)
        bairros = set(contatos_base.exclude(bairro="").values_list("bairro", flat=True))
        bairros.update(liderancas_base.exclude(bairro="").values_list("bairro", flat=True))
        return sorted(item for item in bairros if item)

    def _camadas_painel(self, payload):
        definicoes = (
            ("contatos", "Contatos autorizados", "bi-people-fill", "primary"),
            ("liderancas", "Liderancas com consentimento", "bi-person-badge-fill", "warning"),
            ("eventos", "Eventos mapeados", "bi-calendar-event-fill", "success"),
            ("equipes", "Atuacao das equipes", "bi-diagram-3-fill", "info"),
        )
        retorno = []
        for chave, rotulo, icone, classe in definicoes:
            retorno.append(
                {
                    "chave": chave,
                    "rotulo": rotulo,
                    "icone": icone,
                    "classe": classe,
                    "ativa": payload["visibilidade"][chave],
                    "total": len(payload["camadas"][chave]),
                }
            )
        return retorno

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodo, data_inicial, data_final = resolver_periodo(self.request.GET.get("periodo"))
        camada_ativa = resolver_camada(self.request.GET.get("camada"))
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

        context["campanha_atual"] = self._campanha_atual()
        context["campanhas_disponiveis"] = self._campanhas_disponiveis()
        context["mostrar_filtro_campanha"] = self._usuario_admin()
        context["periodo_opcoes"] = lista_periodos()
        context["camada_opcoes"] = lista_camadas()
        context["cidades_disponiveis"] = self._cidades_disponiveis(dados["contatos"], dados["liderancas"])
        context["bairros_disponiveis"] = self._bairros_disponiveis(dados["contatos"], dados["liderancas"], cidade)
        context["filtros"] = {
            "campanha": self._campanha_selecionada_id() or "",
            "periodo": periodo,
            "camada": camada_ativa,
            "cidade": cidade,
            "bairro": bairro,
        }
        context["camadas_mapa"] = payload["camadas"]
        context["visibilidade_camadas"] = payload["visibilidade"]
        context["resumo"] = payload["resumo"]
        context["destaques"] = payload["destaques"]
        context["camadas_painel"] = self._camadas_painel(payload)
        context["eventos_lista"] = payload["camadas"]["eventos"][:6]
        context["equipes_lista"] = payload["camadas"]["equipes"][:6]
        context["titulo"] = "Mapa eleitoral"
        context["descricao"] = (
            "Painel territorial com camadas protegidas por campanha, consentimento e agregacao responsavel."
        )
        context["data_referencia"] = "28 de julho de 2026"
        return context
