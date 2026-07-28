from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Campanha

Usuario = get_user_model()


class CampanhaPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha A",
            nome_candidato="Candidata A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="11",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha B",
            nome_candidato="Candidato B",
            cargo_disputado="vereador",
            partido="BBB",
            numero_candidato="22",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="planejamento",
        )
        self.coordenador_geral = Usuario.objects.create_user(
            email="coord-geral-campanhas@example.com",
            password="senha123",
            nome_completo="Coordenador Geral",
            nivel_acesso="coordenador_geral",
        )
        self.visualizador_a = Usuario.objects.create_user(
            email="visualizador-campanhas@example.com",
            password="senha123",
            nome_completo="Visualizador Campanhas",
            campanha=self.campanha_a,
            nivel_acesso="visualizador",
        )
        self.financeiro_b = Usuario.objects.create_user(
            email="financeiro-b@example.com",
            password="senha123",
            nome_completo="Financeiro B",
            campanha=self.campanha_b,
            nivel_acesso="financeiro",
        )
        self.coordenador_livre = Usuario.objects.create_user(
            email="coord-livre@example.com",
            password="senha123",
            nome_completo="Coordenador Livre",
            nivel_acesso="coordenador_regional",
        )
        self.coordenador_outra_campanha = Usuario.objects.create_user(
            email="coord-outra@example.com",
            password="senha123",
            nome_completo="Coordenador Outra Campanha",
            campanha=self.campanha_b,
            nivel_acesso="coordenador_regional",
        )

    def test_lista_web_mostra_apenas_campanha_vinculada_para_usuario_comum(self):
        self.client.force_login(self.visualizador_a)
        resposta = self.client.get(reverse("campanhas:lista"))
        self.assertContains(resposta, "Campanha A")
        self.assertNotContains(resposta, "Campanha B")

    def test_detalhe_web_bloqueia_campanha_de_outra_operacao(self):
        self.client.force_login(self.visualizador_a)
        resposta = self.client.get(reverse("campanhas:detalhe", args=[self.campanha_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_gestao_web_permite_criar_campanha_e_vincula_coordenador_livre(self):
        self.client.force_login(self.coordenador_geral)
        resposta = self.client.post(
            reverse("campanhas:nova"),
            {
                "nome_campanha": "Campanha Nova",
                "nome_candidato": "Candidata Nova",
                "cargo_disputado": "prefeito",
                "partido": "CCC",
                "numero_candidato": "33",
                "estado": "CE",
                "municipio": "Maracanau",
                "data_inicio": "2026-07-10",
                "data_eleicao": "2026-10-04",
                "situacao": "planejamento",
                "cor_primaria": "#112233",
                "cor_secundaria": "#445566",
                "coordenador_responsavel": str(self.coordenador_livre.pk),
                "descricao": "Descricao da nova campanha",
                "objetivos_gerais": "Objetivos gerais da campanha",
            },
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        campanha = Campanha.objects.get(nome_campanha="Campanha Nova")
        self.coordenador_livre.refresh_from_db()
        self.assertEqual(self.coordenador_livre.campanha_id, campanha.pk)

    def test_gestao_web_arquiva_campanha_com_soft_delete(self):
        self.client.force_login(self.coordenador_geral)
        resposta = self.client.post(reverse("campanhas:excluir", args=[self.campanha_a.pk]), follow=True)
        self.assertEqual(resposta.status_code, 200)
        campanha = Campanha.todos_objetos.get(pk=self.campanha_a.pk)
        self.assertFalse(campanha.ativo)
        self.assertNotIn(self.campanha_a, Campanha.objects.all())

    def test_api_lista_isola_por_campanha_para_usuario_comum(self):
        client = APIClient()
        client.force_authenticate(self.visualizador_a)
        resposta = client.get("/api/v1/campanhas/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["nome_campanha"], "Campanha A")

    def test_api_bloqueia_retrieve_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.visualizador_a)
        resposta = client.get(f"/api/v1/campanhas/{self.campanha_b.pk}/")
        self.assertEqual(resposta.status_code, 404)

    def test_api_bloqueia_criacao_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador_a)
        resposta = client.post(
            "/api/v1/campanhas/",
            {
                "nome_campanha": "Sem permissao",
                "nome_candidato": "Usuario Sem Permissao",
                "cargo_disputado": "prefeito",
                "partido": "DDD",
                "numero_candidato": "44",
                "estado": "CE",
                "municipio": "Sobral",
                "data_inicio": "2026-07-15",
                "data_eleicao": "2026-10-04",
                "situacao": "planejamento",
                "cor_primaria": "#112233",
                "cor_secundaria": "#445566",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_api_valida_coordenador_vinculado_a_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.coordenador_geral)
        resposta = client.post(
            "/api/v1/campanhas/",
            {
                "nome_campanha": "Campanha Invalida",
                "nome_candidato": "Candidata Invalida",
                "cargo_disputado": "prefeito",
                "partido": "EEE",
                "numero_candidato": "55",
                "estado": "CE",
                "municipio": "Aquiraz",
                "data_inicio": "2026-07-20",
                "data_eleicao": "2026-10-04",
                "situacao": "planejamento",
                "cor_primaria": "#223344",
                "cor_secundaria": "#556677",
                "coordenador_responsavel": str(self.coordenador_outra_campanha.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_cria_campanha_e_vincula_coordenador_disponivel(self):
        client = APIClient()
        client.force_authenticate(self.coordenador_geral)
        resposta = client.post(
            "/api/v1/campanhas/",
            {
                "nome_campanha": "Campanha API Nova",
                "nome_candidato": "Candidato API",
                "cargo_disputado": "deputado_federal",
                "partido": "FFF",
                "numero_candidato": "66",
                "estado": "CE",
                "municipio": "Juazeiro do Norte",
                "data_inicio": "2026-07-25",
                "data_eleicao": "2026-10-04",
                "situacao": "ativa",
                "cor_primaria": "#010203",
                "cor_secundaria": "#040506",
                "coordenador_responsavel": str(self.coordenador_livre.pk),
                "descricao": "Campanha criada via API",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        campanha = Campanha.objects.get(nome_campanha="Campanha API Nova")
        self.coordenador_livre.refresh_from_db()
        self.assertEqual(self.coordenador_livre.campanha_id, campanha.pk)
        self.assertEqual(resposta.json()["total_usuarios_vinculados"], 1)

    def test_api_soft_delete_arquiva_sem_remover_registro(self):
        client = APIClient()
        client.force_authenticate(self.coordenador_geral)
        resposta = client.delete(f"/api/v1/campanhas/{self.campanha_a.pk}/")
        self.assertEqual(resposta.status_code, 204)
        self.assertFalse(Campanha.todos_objetos.get(pk=self.campanha_a.pk).ativo)
