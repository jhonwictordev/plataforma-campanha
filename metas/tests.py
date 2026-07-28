from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from campanhas.models import Campanha
from equipe.models import IntegranteEquipe

from .models import MetaCampanha

Usuario = get_user_model()


class MetaCampanhaPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Metas A",
            nome_candidato="Candidata Metas A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="51",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Metas B",
            nome_candidato="Candidato Metas B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="61",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_editor = Usuario.objects.create_user(
            email="metas-editor@example.com",
            password="senha123",
            nome_completo="Editor Metas",
            campanha=self.campanha_a,
            nivel_acesso="comunicacao",
        )
        self.visualizador = Usuario.objects.create_user(
            email="metas-visualizador@example.com",
            password="senha123",
            nome_completo="Visualizador Metas",
            campanha=self.campanha_a,
            nivel_acesso="visualizador",
        )
        self.usuario_outra_campanha = Usuario.objects.create_user(
            email="metas-outra@example.com",
            password="senha123",
            nome_completo="Responsavel Outra Campanha",
            campanha=self.campanha_b,
            nivel_acesso="comunicacao",
        )
        self.equipe_a = IntegranteEquipe.objects.create(
            campanha=self.campanha_a,
            nome="Equipe A",
            funcao="Mobilizador",
            departamento="Rua",
            status="ativo",
            usuario=self.usuario_editor,
        )
        self.equipe_b = IntegranteEquipe.objects.create(
            campanha=self.campanha_b,
            nome="Equipe B",
            funcao="Mobilizador",
            departamento="Rua",
            status="ativo",
            usuario=self.usuario_outra_campanha,
        )
        self.meta_a = MetaCampanha.objects.create(
            campanha=self.campanha_a,
            nome="Meta de novos contatos",
            descricao="Expandir base em Fortaleza",
            tipo=MetaCampanha.Tipos.NOVOS_CONTATOS,
            valor_esperado=Decimal("100.00"),
            valor_realizado=Decimal("40.00"),
            data_inicial="2026-07-10",
            data_final="2026-08-15",
            responsavel=self.usuario_editor,
            equipe=self.equipe_a,
            regiao="Regional 2",
            status=MetaCampanha.Status.EM_ANDAMENTO,
        )
        self.meta_b = MetaCampanha.objects.create(
            campanha=self.campanha_b,
            nome="Meta outra campanha",
            descricao="Volume externo",
            tipo=MetaCampanha.Tipos.EVENTOS_REALIZADOS,
            valor_esperado=Decimal("20.00"),
            valor_realizado=Decimal("25.00"),
            data_inicial="2026-07-01",
            data_final="2026-07-20",
            responsavel=self.usuario_outra_campanha,
            equipe=self.equipe_b,
            regiao="Regional B",
            status=MetaCampanha.Status.ATRASADA,
        )

    def test_model_calcula_percentual_automaticamente(self):
        self.assertEqual(self.meta_a.percentual_conclusao, Decimal("40.00"))
        self.assertEqual(self.meta_b.percentual_conclusao, Decimal("125.00"))

    def test_lista_web_mostra_apenas_metas_da_mesma_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("metas:home"))
        self.assertContains(resposta, "Meta de novos contatos")
        self.assertNotContains(resposta, "Meta outra campanha")

    def test_detalhe_web_bloqueia_idor_para_outra_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("metas:detalhe", args=[self.meta_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_visualizador_nao_pode_criar_meta_na_web(self):
        self.client.force_login(self.visualizador)
        resposta = self.client.get(reverse("metas:nova"))
        self.assertEqual(resposta.status_code, 403)

    def test_api_lista_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.get("/api/v1/metas-campanha/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["nome"], "Meta de novos contatos")

    def test_api_bloqueia_equipe_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/metas-campanha/",
            {
                "nome": "Meta cruzada por equipe",
                "tipo": MetaCampanha.Tipos.EVENTOS_REALIZADOS,
                "valor_esperado": "12.00",
                "valor_realizado": "0.00",
                "data_inicial": "2026-07-28",
                "data_final": "2026-08-10",
                "equipe": str(self.equipe_b.pk),
                "status": MetaCampanha.Status.ABERTA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_responsavel_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/metas-campanha/",
            {
                "nome": "Meta cruzada por responsavel",
                "tipo": MetaCampanha.Tipos.LIGACOES_REALIZADAS,
                "valor_esperado": "50.00",
                "valor_realizado": "10.00",
                "data_inicial": "2026-07-28",
                "data_final": "2026-08-05",
                "responsavel": self.usuario_outra_campanha.pk,
                "status": MetaCampanha.Status.EM_ANDAMENTO,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_criacao_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador)
        resposta = client.post(
            "/api/v1/metas-campanha/",
            {
                "nome": "Meta somente leitura",
                "tipo": MetaCampanha.Tipos.TAREFAS_CONCLUIDAS,
                "valor_esperado": "10.00",
                "valor_realizado": "0.00",
                "data_inicial": "2026-07-28",
                "data_final": "2026-08-03",
                "status": MetaCampanha.Status.ABERTA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_api_rejeita_valor_esperado_igual_a_zero(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/metas-campanha/",
            {
                "nome": "Meta invalida",
                "tipo": MetaCampanha.Tipos.MENSAGENS_ENVIADAS,
                "valor_esperado": "0.00",
                "valor_realizado": "0.00",
                "data_inicial": "2026-07-28",
                "data_final": "2026-08-03",
                "status": MetaCampanha.Status.ABERTA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
