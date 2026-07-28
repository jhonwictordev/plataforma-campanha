from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from campanhas.models import Campanha

from .models import InteracaoLideranca, Lideranca

Usuario = get_user_model()


class LiderancaPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Lideranca A",
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
            nome_campanha="Campanha Lideranca B",
            nome_candidato="Candidato B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="20",
            estado="CE",
            municipio="Maracanau",
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
            nome_completo="Lideranca A",
            telefone="85977770000",
            tipo_lideranca="politica",
            estado="CE",
            cidade="Fortaleza",
            responsavel_contato=self.usuario_a,
        )
        self.lideranca_b = Lideranca.objects.create(
            campanha=self.campanha_b,
            nome_completo="Lideranca B",
            telefone="85966660000",
            tipo_lideranca="empresarial",
            estado="CE",
            cidade="Maracanau",
            responsavel_contato=self.usuario_b,
        )
        self.interacao_a = InteracaoLideranca.objects.create(
            campanha=self.campanha_a,
            lideranca=self.lideranca_a,
            tipo=InteracaoLideranca.Tipos.REUNIAO,
            data_hora=timezone.now(),
            resumo="Reuniao territorial",
            detalhes="Alinhamento de mobilizacao regional.",
            responsavel=self.usuario_a,
        )
        self.interacao_b = InteracaoLideranca.objects.create(
            campanha=self.campanha_b,
            lideranca=self.lideranca_b,
            tipo=InteracaoLideranca.Tipos.MENSAGEM,
            data_hora=timezone.now(),
            resumo="Mensagem da campanha B",
            detalhes="Historico de outra campanha.",
            responsavel=self.usuario_b,
        )

    def test_web_detalhe_nao_mostra_lideranca_de_outra_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("liderancas:detalhe", args=[self.lideranca_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_web_detalhe_exibe_historico_da_mesma_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("liderancas:detalhe", args=[self.lideranca_a.pk]))
        self.assertContains(resposta, "Reuniao territorial")
        self.assertContains(resposta, "Alinhamento de mobilizacao regional.")
        self.assertNotContains(resposta, "Mensagem da campanha B")

    def test_visualizador_nao_pode_criar_lideranca_na_web(self):
        self.client.force_login(self.visualizador_a)
        resposta = self.client.get(reverse("liderancas:novo"))
        self.assertEqual(resposta.status_code, 403)

    def test_web_cria_interacao_para_lideranca_da_mesma_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.post(
            reverse("liderancas:interacao_nova", args=[self.lideranca_a.pk]),
            {
                "tipo": InteracaoLideranca.Tipos.LIGACAO,
                "data_hora": "2026-07-29T10:00",
                "resumo": "Ligacao de acompanhamento",
                "detalhes": "Confirmou agenda para sexta-feira.",
                "responsavel": str(self.usuario_a.pk),
            },
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            InteracaoLideranca.objects.filter(
                lideranca=self.lideranca_a,
                resumo="Ligacao de acompanhamento",
            ).exists()
        )
        self.lideranca_a.refresh_from_db()
        self.assertEqual(
            timezone.localtime(self.lideranca_a.data_ultimo_contato).strftime("%Y-%m-%d %H:%M"),
            "2026-07-29 10:00",
        )

    def test_web_bloqueia_interacao_para_lideranca_de_outra_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("liderancas:interacao_nova", args=[self.lideranca_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_api_lista_retorna_apenas_mesma_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.get("/api/v1/liderancas/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["nome_completo"], "Lideranca A")

    def test_api_lista_interacoes_retorna_apenas_mesma_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.get("/api/v1/lideranca-interacoes/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["resumo"], "Reuniao territorial")

    def test_api_bloqueia_interacao_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.post(
            "/api/v1/lideranca-interacoes/",
            {
                "lideranca": str(self.lideranca_b.pk),
                "tipo": InteracaoLideranca.Tipos.VISITA,
                "data_hora": "2026-07-29T13:00:00Z",
                "resumo": "Tentativa indevida",
                "detalhes": "Nao deveria salvar.",
                "responsavel": str(self.usuario_a.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_responsavel_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.post(
            "/api/v1/liderancas/",
            {
                "nome_completo": "Lideranca Nova",
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

    def test_api_bloqueia_criacao_de_interacao_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador_a)
        resposta = client.post(
            "/api/v1/lideranca-interacoes/",
            {
                "lideranca": str(self.lideranca_a.pk),
                "tipo": InteracaoLideranca.Tipos.COMPROMISSO,
                "data_hora": "2026-07-29T15:00:00Z",
                "resumo": "Compromisso sem permissao",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)
