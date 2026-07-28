from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from campanhas.models import Campanha

from .models import Lideranca

Usuario = get_user_model()


class LiderancaPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Liderança A",
            nome_candidato="Candidata A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="10",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-01-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Liderança B",
            nome_candidato="Candidato B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="20",
            estado="CE",
            municipio="Maracanaú",
            data_inicio="2026-01-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_a = Usuario.objects.create_user(
            email="coordenador-a@example.com",
            password="senha123",
            nome_completo="Coordenador A",
            campanha=self.campanha_a,
            nivel_acesso="coordenador_regional",
        )
        self.usuario_b = Usuario.objects.create_user(
            email="coordenador-b@example.com",
            password="senha123",
            nome_completo="Coordenador B",
            campanha=self.campanha_b,
            nivel_acesso="coordenador_regional",
        )
        self.visualizador_a = Usuario.objects.create_user(
            email="visualizador-lideranca@example.com",
            password="senha123",
            nome_completo="Visualizador Lideranca",
            campanha=self.campanha_a,
            nivel_acesso="visualizador",
        )
        self.lideranca_a = Lideranca.objects.create(
            campanha=self.campanha_a,
            nome_completo="Liderança A",
            telefone="85977770000",
            tipo_lideranca="politica",
            estado="CE",
            cidade="Fortaleza",
            responsavel_contato=self.usuario_a,
        )
        self.lideranca_b = Lideranca.objects.create(
            campanha=self.campanha_b,
            nome_completo="Liderança B",
            telefone="85966660000",
            tipo_lideranca="empresarial",
            estado="CE",
            cidade="Maracanaú",
            responsavel_contato=self.usuario_b,
        )

    def test_web_detalhe_nao_mostra_lideranca_de_outra_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("liderancas:detalhe", args=[self.lideranca_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_visualizador_nao_pode_criar_lideranca_na_web(self):
        self.client.force_login(self.visualizador_a)
        resposta = self.client.get(reverse("liderancas:novo"))
        self.assertEqual(resposta.status_code, 403)

    def test_api_lista_retorna_apenas_mesma_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.get("/api/v1/liderancas/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["nome_completo"], "Liderança A")

    def test_api_bloqueia_responsavel_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.post(
            "/api/v1/liderancas/",
            {
                "nome_completo": "Liderança Nova",
                "telefone": "85955550000",
                "tipo_lideranca": "regional",
                "estado": "CE",
                "cidade": "Fortaleza",
                "responsavel_contato": self.usuario_b.pk,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_criacao_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador_a)
        resposta = client.post(
            "/api/v1/liderancas/",
            {
                "nome_completo": "Lideranca Somente Leitura",
                "telefone": "85944440000",
                "tipo_lideranca": "regional",
                "estado": "CE",
                "cidade": "Fortaleza",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)
