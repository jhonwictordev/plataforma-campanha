from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from campanhas.models import Campanha

from .models import CategoriaFinanceira, CentroCusto, LancamentoFinanceiro, ParceiroFinanceiro

Usuario = get_user_model()


class FinanceiroPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Financeiro A",
            nome_candidato="Candidata Financeiro A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="71",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Financeiro B",
            nome_candidato="Candidato Financeiro B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="81",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_financeiro = Usuario.objects.create_user(
            email="financeiro-a@example.com",
            password="senha123",
            nome_completo="Financeiro A",
            campanha=self.campanha_a,
            nivel_acesso="financeiro",
        )
        self.usuario_mobilizador = Usuario.objects.create_user(
            email="mobilizador-a@example.com",
            password="senha123",
            nome_completo="Mobilizador A",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.usuario_outra_campanha = Usuario.objects.create_user(
            email="financeiro-b@example.com",
            password="senha123",
            nome_completo="Financeiro B",
            campanha=self.campanha_b,
            nivel_acesso="financeiro",
        )
        self.categoria_a = CategoriaFinanceira.objects.create(
            campanha=self.campanha_a,
            nome="Combustivel",
            tipo=CategoriaFinanceira.Tipos.DESPESA,
        )
        self.categoria_b = CategoriaFinanceira.objects.create(
            campanha=self.campanha_b,
            nome="Doacoes externas",
            tipo=CategoriaFinanceira.Tipos.DOACAO,
        )
        self.centro_a = CentroCusto.objects.create(
            campanha=self.campanha_a,
            nome="Rua",
            codigo="RUA-01",
        )
        self.centro_b = CentroCusto.objects.create(
            campanha=self.campanha_b,
            nome="Midia",
            codigo="MID-02",
        )
        self.parceiro_a = ParceiroFinanceiro.objects.create(
            campanha=self.campanha_a,
            nome="Fornecedor A",
            tipo=ParceiroFinanceiro.Tipos.FORNECEDOR,
        )
        self.parceiro_b = ParceiroFinanceiro.objects.create(
            campanha=self.campanha_b,
            nome="Doador B",
            tipo=ParceiroFinanceiro.Tipos.DOADOR,
        )
        self.lancamento_a = LancamentoFinanceiro.objects.create(
            campanha=self.campanha_a,
            descricao="Compra de combustivel",
            tipo=LancamentoFinanceiro.Tipos.DESPESA,
            categoria=self.categoria_a,
            valor_reais=Decimal("1200.00"),
            data_vencimento="2026-07-20",
            parceiro=self.parceiro_a,
            responsavel_lancamento=self.usuario_financeiro,
            centro_custo=self.centro_a,
            status=LancamentoFinanceiro.Status.PENDENTE,
        )
        self.lancamento_b = LancamentoFinanceiro.objects.create(
            campanha=self.campanha_b,
            descricao="Doacao principal",
            tipo=LancamentoFinanceiro.Tipos.DOACAO,
            categoria=self.categoria_b,
            valor_reais=Decimal("5000.00"),
            data_vencimento="2026-08-05",
            parceiro=self.parceiro_b,
            responsavel_lancamento=self.usuario_outra_campanha,
            centro_custo=self.centro_b,
            status=LancamentoFinanceiro.Status.LIQUIDADO,
        )

    def test_model_marca_lancamento_em_atraso(self):
        self.assertTrue(self.lancamento_a.esta_vencido)
        self.assertFalse(self.lancamento_b.esta_vencido)

    def test_lista_web_mostra_apenas_lancamentos_da_mesma_campanha(self):
        self.client.force_login(self.usuario_financeiro)
        resposta = self.client.get(reverse("financeiro:home"))
        self.assertContains(resposta, "Compra de combustivel")
        self.assertNotContains(resposta, "Doacao principal")

    def test_detalhe_web_bloqueia_idor_para_outra_campanha(self):
        self.client.force_login(self.usuario_financeiro)
        resposta = self.client.get(reverse("financeiro:lancamento_detalhe", args=[self.lancamento_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_mobilizador_nao_acessa_financeiro_web(self):
        self.client.force_login(self.usuario_mobilizador)
        resposta = self.client.get(reverse("financeiro:home"))
        self.assertEqual(resposta.status_code, 403)

    def test_api_lista_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_financeiro)
        resposta = client.get("/api/v1/financeiro-lancamentos/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["descricao"], "Compra de combustivel")

    def test_api_bloqueia_parceiro_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_financeiro)
        resposta = client.post(
            "/api/v1/financeiro-lancamentos/",
            {
                "descricao": "Lancamento cruzado",
                "tipo": LancamentoFinanceiro.Tipos.DESPESA,
                "categoria": str(self.categoria_a.pk),
                "valor_reais": "500.00",
                "data_vencimento": "2026-08-01",
                "parceiro": str(self.parceiro_b.pk),
                "centro_custo": str(self.centro_a.pk),
                "status": LancamentoFinanceiro.Status.PENDENTE,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_categoria_com_tipo_diferente(self):
        client = APIClient()
        client.force_authenticate(self.usuario_financeiro)
        resposta = client.post(
            "/api/v1/financeiro-lancamentos/",
            {
                "descricao": "Receita com categoria errada",
                "tipo": LancamentoFinanceiro.Tipos.RECEITA,
                "categoria": str(self.categoria_a.pk),
                "valor_reais": "700.00",
                "data_vencimento": "2026-08-02",
                "centro_custo": str(self.centro_a.pk),
                "status": LancamentoFinanceiro.Status.PENDENTE,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_criacao_para_usuario_sem_permissao(self):
        client = APIClient()
        client.force_authenticate(self.usuario_mobilizador)
        resposta = client.post(
            "/api/v1/financeiro-lancamentos/",
            {
                "descricao": "Tentativa sem permissao",
                "tipo": LancamentoFinanceiro.Tipos.DESPESA,
                "valor_reais": "90.00",
                "status": LancamentoFinanceiro.Status.PENDENTE,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_api_preenche_data_pagamento_ao_liquidar(self):
        client = APIClient()
        client.force_authenticate(self.usuario_financeiro)
        resposta = client.post(
            "/api/v1/financeiro-lancamentos/",
            {
                "descricao": "Despesa liquidada",
                "tipo": LancamentoFinanceiro.Tipos.DESPESA,
                "categoria": str(self.categoria_a.pk),
                "valor_reais": "300.00",
                "data_vencimento": "2026-08-03",
                "parceiro": str(self.parceiro_a.pk),
                "centro_custo": str(self.centro_a.pk),
                "status": LancamentoFinanceiro.Status.LIQUIDADO,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()["data_pagamento"], "2026-07-28")
