from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from campanhas.models import Campanha

from .models import ComentarioTarefaEquipe, IntegranteEquipe, TarefaEquipe

Usuario = get_user_model()


class EquipePermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Equipe A",
            nome_candidato="Candidata Equipe A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="31",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Equipe B",
            nome_candidato="Candidato Equipe B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="41",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_editor = Usuario.objects.create_user(
            email="equipe-editor@example.com",
            password="senha123",
            nome_completo="Editor Equipe",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.visualizador = Usuario.objects.create_user(
            email="equipe-visualizador@example.com",
            password="senha123",
            nome_completo="Visualizador Equipe",
            campanha=self.campanha_a,
            nivel_acesso="visualizador",
        )
        self.usuario_outra_campanha = Usuario.objects.create_user(
            email="equipe-outra@example.com",
            password="senha123",
            nome_completo="Editor Outra Campanha",
            campanha=self.campanha_b,
            nivel_acesso="mobilizador",
        )
        self.integrante_a = IntegranteEquipe.objects.create(
            campanha=self.campanha_a,
            nome="Integrante A",
            telefone="85911110000",
            email="integrante-a@example.com",
            funcao="Coordenador de campo",
            departamento="Mobilizacao",
            cidade_regiao="Fortaleza",
            status="ativo",
            usuario=self.usuario_editor,
        )
        self.integrante_b = IntegranteEquipe.objects.create(
            campanha=self.campanha_b,
            nome="Integrante B",
            telefone="85922220000",
            email="integrante-b@example.com",
            funcao="Coordenador regional",
            departamento="Operacoes",
            cidade_regiao="Caucaia",
            status="ativo",
            usuario=self.usuario_outra_campanha,
        )
        self.tarefa_a = TarefaEquipe.objects.create(
            campanha=self.campanha_a,
            titulo="Tarefa A",
            descricao="Organizar caminhada",
            responsavel=self.integrante_a,
            prazo="2026-07-30T15:00:00Z",
            prioridade="alta",
            status="a_fazer",
        )
        self.tarefa_b = TarefaEquipe.objects.create(
            campanha=self.campanha_b,
            titulo="Tarefa B",
            descricao="Fechar roteiro de visitas",
            responsavel=self.integrante_b,
            prazo="2026-07-31T15:00:00Z",
            prioridade="media",
            status="em_andamento",
        )
        self.comentario_a = ComentarioTarefaEquipe.objects.create(
            campanha=self.campanha_a,
            tarefa=self.tarefa_a,
            autor=self.usuario_editor,
            conteudo="Primeiro andamento da tarefa A.",
        )
        self.comentario_b = ComentarioTarefaEquipe.objects.create(
            campanha=self.campanha_b,
            tarefa=self.tarefa_b,
            autor=self.usuario_outra_campanha,
            conteudo="Andamento da tarefa B.",
        )

    def test_home_mostra_apenas_dados_da_mesma_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("equipe:home"))
        self.assertContains(resposta, "Integrante A")
        self.assertContains(resposta, "Tarefa A")
        self.assertNotContains(resposta, "Integrante B")
        self.assertNotContains(resposta, "Tarefa B")

    def test_detalhe_integrante_bloqueia_idor(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("equipe:integrante_detalhe", args=[self.integrante_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_detalhe_tarefa_bloqueia_idor(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("equipe:tarefa_detalhe", args=[self.tarefa_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_detalhe_tarefa_mostra_apenas_comentarios_da_mesma_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("equipe:tarefa_detalhe", args=[self.tarefa_a.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Primeiro andamento da tarefa A.")
        self.assertNotContains(resposta, "Andamento da tarefa B.")

    def test_visualizador_nao_pode_criar_integrante_na_web(self):
        self.client.force_login(self.visualizador)
        resposta = self.client.get(reverse("equipe:integrante_novo"))
        self.assertEqual(resposta.status_code, 403)

    def test_visualizador_nao_pode_criar_tarefa_na_web(self):
        self.client.force_login(self.visualizador)
        resposta = self.client.get(reverse("equipe:tarefa_nova"))
        self.assertEqual(resposta.status_code, 403)

    def test_web_cria_comentario_para_tarefa_da_mesma_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.post(
            reverse("equipe:comentario_novo", args=[self.tarefa_a.pk]),
            {"conteudo": "Novo comentario web na tarefa A."},
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(
            ComentarioTarefaEquipe.objects.filter(
                tarefa=self.tarefa_a,
                campanha=self.campanha_a,
                conteudo="Novo comentario web na tarefa A.",
                autor=self.usuario_editor,
            ).exists()
        )

    def test_web_bloqueia_comentario_em_tarefa_de_outra_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("equipe:comentario_novo", args=[self.tarefa_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_api_lista_integrantes_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.get("/api/v1/equipe-integrantes/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["nome"], "Integrante A")

    def test_api_lista_tarefas_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.get("/api/v1/equipe-tarefas/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["titulo"], "Tarefa A")

    def test_api_lista_comentarios_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.get("/api/v1/equipe-comentarios/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["conteudo"], "Primeiro andamento da tarefa A.")

    def test_api_bloqueia_integrante_com_usuario_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/equipe-integrantes/",
            {
                "nome": "Integrante Novo",
                "funcao": "Motorista",
                "departamento": "Logistica",
                "status": "ativo",
                "usuario": self.usuario_outra_campanha.pk,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_tarefa_com_responsavel_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/equipe-tarefas/",
            {
                "titulo": "Tarefa Cruzada",
                "descricao": "Nao deve passar",
                "responsavel": str(self.integrante_b.pk),
                "prioridade": "alta",
                "status": "a_fazer",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_comentario_em_tarefa_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/equipe-comentarios/",
            {
                "tarefa": str(self.tarefa_b.pk),
                "conteudo": "Tentativa cruzada.",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_criacao_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador)
        resposta = client.post(
            "/api/v1/equipe-tarefas/",
            {
                "titulo": "Tarefa Somente Leitura",
                "prioridade": "baixa",
                "status": "a_fazer",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_api_bloqueia_comentario_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador)
        resposta = client.post(
            "/api/v1/equipe-comentarios/",
            {
                "tarefa": str(self.tarefa_a.pk),
                "conteudo": "Tentativa somente leitura.",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)
