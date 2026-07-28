from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from agenda.models import EventoAgenda
from campanhas.models import Campanha
from eleitores.models import ContatoCRM
from financeiro.models import LancamentoFinanceiro
from relatorios.models import FiltroFavoritoRelatorio

Usuario = get_user_model()


class RelatoriosCentroTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Relatorios A",
            nome_candidato="Candidata Relatorios A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="91",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Relatorios B",
            nome_candidato="Candidato Relatorios B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="92",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_mobilizador = Usuario.objects.create_user(
            email="relatorios-mobilizador@example.com",
            password="senha123",
            nome_completo="Mobilizador Relatorios",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.usuario_financeiro = Usuario.objects.create_user(
            email="relatorios-financeiro@example.com",
            password="senha123",
            nome_completo="Financeiro Relatorios",
            campanha=self.campanha_a,
            nivel_acesso="financeiro",
        )
        self.usuario_staff = Usuario.objects.create_user(
            email="relatorios-staff@example.com",
            password="senha123",
            nome_completo="Staff Relatorios",
            nivel_acesso="administrador",
            is_staff=True,
        )
        self.usuario_outro_mobilizador = Usuario.objects.create_user(
            email="relatorios-outro@example.com",
            password="senha123",
            nome_completo="Outro Mobilizador",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )

        ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato A",
            telefone="85911110000",
            whatsapp="85911110000",
            email="contato-a@example.com",
            cidade="Fortaleza",
            bairro="Centro",
            origem_contato="Site",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )
        ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato B",
            telefone="85922220000",
            whatsapp="85922220000",
            email="contato-b@example.com",
            cidade="Caucaia",
            bairro="Centro",
            origem_contato="Evento",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )

        LancamentoFinanceiro.objects.create(
            campanha=self.campanha_a,
            descricao="Receita principal A",
            tipo=LancamentoFinanceiro.Tipos.RECEITA,
            valor_reais=Decimal("1500.00"),
            data_vencimento="2026-07-18",
            status=LancamentoFinanceiro.Status.LIQUIDADO,
            responsavel_lancamento=self.usuario_financeiro,
        )
        LancamentoFinanceiro.objects.create(
            campanha=self.campanha_b,
            descricao="Despesa principal B",
            tipo=LancamentoFinanceiro.Tipos.DESPESA,
            valor_reais=Decimal("900.00"),
            data_vencimento="2026-07-19",
            status=LancamentoFinanceiro.Status.PENDENTE,
        )

        EventoAgenda.objects.create(
            campanha=self.campanha_a,
            titulo="Caminhada A",
            tipo=EventoAgenda.Tipos.CAMINHADA,
            data="2026-07-20",
            horario_inicial="09:00",
            status=EventoAgenda.Status.CONFIRMADO,
            endereco="Fortaleza Centro",
        )

    def test_home_contatos_isola_dados_por_campanha(self):
        self.client.force_login(self.usuario_mobilizador)
        resposta = self.client.get(
            reverse("relatorios:home"),
            {
                "tipo_relatorio": "contatos_cadastrados",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Contato A")
        self.assertNotContains(resposta, "Contato B")
        self.assertEqual(resposta.context["total_linhas"], 1)

    def test_financeiro_nao_acessa_relatorio_crm(self):
        self.client.force_login(self.usuario_financeiro)
        resposta = self.client.get(
            reverse("relatorios:home"),
            {
                "tipo_relatorio": "contatos_cadastrados",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 403)

    def test_salva_filtro_favorito_vinculando_usuario_e_campanha(self):
        self.client.force_login(self.usuario_mobilizador)
        resposta = self.client.post(
            reverse("relatorios:favorito_salvar"),
            {
                "nome": "Favorito Fortaleza",
                "tipo_relatorio": "contatos_cadastrados",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
                "cidade": "Fortaleza",
                "bairro": "Centro",
                "responsavel": "",
            },
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        favorito = FiltroFavoritoRelatorio.objects.get(nome="Favorito Fortaleza")
        self.assertEqual(favorito.usuario, self.usuario_mobilizador)
        self.assertEqual(favorito.campanha, self.campanha_a)
        self.assertEqual(favorito.tipo_relatorio, "contatos_cadastrados")
        self.assertEqual(favorito.filtros["cidade"], "Fortaleza")

    def test_exporta_excel_financeiro(self):
        self.client.force_login(self.usuario_financeiro)
        resposta = self.client.get(
            reverse("relatorios:exportar_excel"),
            {
                "tipo_relatorio": "financeiro",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("attachment; filename=", resposta["Content-Disposition"])

    def test_exporta_pdf_eventos(self):
        self.client.force_login(self.usuario_mobilizador)
        resposta = self.client.get(
            reverse("relatorios:exportar_pdf"),
            {
                "tipo_relatorio": "eventos",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/pdf")
        self.assertIn(b"%PDF", resposta.content[:4])

    def test_api_relatorio_json_isola_dados_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_mobilizador)
        resposta = client.get(
            "/api/v1/relatorios/",
            {
                "tipo_relatorio": "contatos_cadastrados",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(dados["total_linhas"], 1)
        self.assertEqual(dados["campanha_atual"]["id"], str(self.campanha_a.pk))
        self.assertEqual(dados["relatorio"]["linhas"][0]["nome"], "Contato A")

    def test_api_financeiro_nao_acessa_relatorio_crm(self):
        client = APIClient()
        client.force_authenticate(self.usuario_financeiro)
        resposta = client.get(
            "/api/v1/relatorios/",
            {
                "tipo_relatorio": "contatos_cadastrados",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 403)

    def test_api_staff_pode_filtrar_relatorio_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_staff)
        resposta = client.get(
            f"/api/v1/relatorios/?tipo_relatorio=contatos_cadastrados&campanha={self.campanha_b.pk}&data_inicial=2026-07-01&data_final=2026-07-28"
        )
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(dados["total_linhas"], 1)
        self.assertEqual(dados["relatorio"]["linhas"][0]["nome"], "Contato B")

    def test_api_exporta_excel_financeiro(self):
        client = APIClient()
        client.force_authenticate(self.usuario_financeiro)
        resposta = client.get(
            "/api/v1/relatorios/excel/",
            {
                "tipo_relatorio": "financeiro",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("attachment; filename=", resposta["Content-Disposition"])

    def test_api_exporta_pdf_eventos(self):
        client = APIClient()
        client.force_authenticate(self.usuario_mobilizador)
        resposta = client.get(
            "/api/v1/relatorios/pdf/",
            {
                "tipo_relatorio": "eventos",
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/pdf")
        self.assertIn(b"%PDF", resposta.content[:4])

    def test_api_favoritos_isolam_por_usuario(self):
        favorito_usuario = FiltroFavoritoRelatorio.objects.create(
            campanha=self.campanha_a,
            usuario=self.usuario_mobilizador,
            nome="Favorito do usuario A",
            tipo_relatorio="contatos_cadastrados",
            filtros={
                "tipo_relatorio": "contatos_cadastrados",
                "campanha": str(self.campanha_a.pk),
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
                "cidade": "Fortaleza",
                "bairro": "",
                "responsavel": "",
            },
        )
        FiltroFavoritoRelatorio.objects.create(
            campanha=self.campanha_a,
            usuario=self.usuario_outro_mobilizador,
            nome="Favorito de outro usuario",
            tipo_relatorio="contatos_cadastrados",
            filtros={
                "tipo_relatorio": "contatos_cadastrados",
                "campanha": str(self.campanha_a.pk),
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
                "cidade": "",
                "bairro": "",
                "responsavel": "",
            },
        )
        client = APIClient()
        client.force_authenticate(self.usuario_mobilizador)
        resposta = client.get("/api/v1/relatorios-favoritos/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["id"], str(favorito_usuario.pk))

    def test_api_cria_favorito_vinculando_usuario_e_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_mobilizador)
        resposta = client.post(
            "/api/v1/relatorios-favoritos/",
            {
                "nome": "Favorito API",
                "tipo_relatorio": "contatos_cadastrados",
                "filtros": {
                    "data_inicial": "2026-07-01",
                    "data_final": "2026-07-28",
                    "cidade": "Fortaleza",
                    "bairro": "Centro",
                    "responsavel": "",
                },
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        favorito = FiltroFavoritoRelatorio.objects.get(nome="Favorito API")
        self.assertEqual(favorito.usuario, self.usuario_mobilizador)
        self.assertEqual(favorito.campanha, self.campanha_a)
        self.assertEqual(favorito.filtros["cidade"], "Fortaleza")

    def test_api_bloqueia_favorito_para_relatorio_sem_permissao(self):
        client = APIClient()
        client.force_authenticate(self.usuario_financeiro)
        resposta = client.post(
            "/api/v1/relatorios-favoritos/",
            {
                "nome": "Favorito invalido",
                "tipo_relatorio": "contatos_cadastrados",
                "filtros": {
                    "data_inicial": "2026-07-01",
                    "data_final": "2026-07-28",
                },
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)
