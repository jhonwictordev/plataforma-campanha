from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from campanhas.models import Campanha
from eleitores.models import ContatoCRM

from .models import LogSeguranca, PoliticaRetencaoDados, RegistroAuditoria, SolicitacaoTitularDados

Usuario = get_user_model()


class AuditoriaGovernancaTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Auditoria A",
            nome_candidato="Candidata Auditoria A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="101",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Auditoria B",
            nome_candidato="Candidato Auditoria B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="102",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_coord_a = Usuario.objects.create_user(
            email="auditoria-a@example.com",
            password="senha123",
            nome_completo="Coordenador Auditoria A",
            campanha=self.campanha_a,
            nivel_acesso="coordenador_geral",
        )
        self.usuario_coord_b = Usuario.objects.create_user(
            email="auditoria-b@example.com",
            password="senha123",
            nome_completo="Coordenador Auditoria B",
            campanha=self.campanha_b,
            nivel_acesso="coordenador_geral",
        )
        self.usuario_staff = Usuario.objects.create_user(
            email="auditoria-staff@example.com",
            password="senha123",
            nome_completo="Staff Auditoria",
            nivel_acesso="administrador",
            is_staff=True,
        )
        self.usuario_mobilizador = Usuario.objects.create_user(
            email="auditoria-mobilizador@example.com",
            password="senha123",
            nome_completo="Mobilizador Auditoria",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )

        self.contato_a = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Auditoria A",
            telefone="85911110000",
            whatsapp="85911110000",
            email="contato-auditoria-a@example.com",
            cidade="Fortaleza",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )

        RegistroAuditoria.objects.create(
            campanha=self.campanha_a,
            acao="criado",
            modelo="eleitores.ContatoCRM",
            objeto_id=str(self.contato_a.pk),
            resumo="Contato da campanha A criado",
            usuario=self.usuario_coord_a,
        )
        RegistroAuditoria.objects.create(
            campanha=self.campanha_b,
            acao="criado",
            modelo="eleitores.ContatoCRM",
            objeto_id="objeto-b",
            resumo="Contato da campanha B criado",
            usuario=self.usuario_coord_b,
        )

        LogSeguranca.objects.create(
            campanha=self.campanha_a,
            evento="login",
            severidade="info",
            descricao="Login da campanha A",
            usuario=self.usuario_coord_a,
        )
        LogSeguranca.objects.create(
            campanha=self.campanha_b,
            evento="login_falhou",
            severidade="critico",
            descricao="Falha critica da campanha B",
            usuario=self.usuario_coord_b,
        )

        PoliticaRetencaoDados.objects.create(
            campanha=self.campanha_a,
            nome="Retencao CRM",
            tipo_registro=PoliticaRetencaoDados.TiposRegistro.CONTATOS,
            base_legal="Execucao de campanha",
            dias_retencao=30,
            dias_ate_anonimizacao=15,
            responsavel=self.usuario_coord_a,
        )

    def test_home_isola_registros_e_logs_por_campanha(self):
        self.client.force_login(self.usuario_coord_a)
        resposta = self.client.get(
            reverse("auditoria:home"),
            {
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Contato da campanha A criado")
        self.assertNotContains(resposta, "Contato da campanha B criado")
        self.assertContains(resposta, "Login da campanha A")
        self.assertNotContains(resposta, "Falha critica da campanha B")
        self.assertEqual(resposta.context["resumo"]["politicas_ativas"], 1)

    def test_home_bloqueia_usuario_sem_permissao(self):
        self.client.force_login(self.usuario_mobilizador)
        resposta = self.client.get(reverse("auditoria:home"))
        self.assertEqual(resposta.status_code, 403)

    def test_staff_pode_filtrar_outra_campanha(self):
        self.client.force_login(self.usuario_staff)
        resposta = self.client.get(
            reverse("auditoria:home"),
            {
                "campanha": str(self.campanha_b.pk),
                "data_inicial": "2026-07-01",
                "data_final": "2026-07-28",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Contato da campanha B criado")
        self.assertNotContains(resposta, "Contato da campanha A criado")
        self.assertEqual(resposta.context["resumo"]["logs_criticos"], 1)

    def test_concluir_solicitacao_revoga_consentimento_do_contato(self):
        self.client.force_login(self.usuario_coord_a)
        resposta = self.client.post(
            reverse("auditoria:solicitacao_nova"),
            {
                "nome_solicitante": "Titular Contato A",
                "email_solicitante": "titular@example.com",
                "telefone_solicitante": "85999990000",
                "canal_origem": "e-mail",
                "tipo_solicitacao": SolicitacaoTitularDados.TiposSolicitacao.REVOGACAO_CONSENTIMENTO,
                "status": SolicitacaoTitularDados.Status.CONCLUIDA,
                "descricao": "Solicitou a revogacao do consentimento de comunicacao.",
                "contato_relacionado": str(self.contato_a.pk),
                "lideranca_relacionada": "",
                "responsavel_interno": str(self.usuario_coord_a.pk),
                "prazo_resposta": "2026-07-29",
                "resposta_interna": "Atendido no mesmo dia.",
                "executar_acao_lgpd": "on",
            },
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.contato_a.refresh_from_db()
        self.assertFalse(self.contato_a.consentimento_comunicacao)
        self.assertEqual(self.contato_a.canal_autorizado, "")
        solicitacao = SolicitacaoTitularDados.objects.get(nome_solicitante="Titular Contato A")
        self.assertEqual(solicitacao.status, SolicitacaoTitularDados.Status.CONCLUIDA)
        self.assertIn("Consentimento de comunicacao do contato revogado.", solicitacao.resultado_execucao)

    def test_api_lista_registros_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_coord_a)
        resposta = client.get("/api/v1/auditoria-registros/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertTrue(any(item["resumo"] == "Contato da campanha A criado" for item in resultados))
        self.assertTrue(all(item["campanha"] == str(self.campanha_a.pk) for item in resultados))

    def test_api_staff_filtra_logs_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_staff)
        resposta = client.get(f"/api/v1/auditoria-logs/?campanha={self.campanha_b.pk}")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["descricao"], "Falha critica da campanha B")

    def test_api_bloqueia_criacao_manual_de_registro_auditoria(self):
        client = APIClient()
        client.force_authenticate(self.usuario_coord_a)
        resposta = client.post(
            "/api/v1/auditoria-registros/",
            {
                "acao": "manual",
                "modelo": "teste",
                "objeto_id": "1",
                "resumo": "Nao deve criar",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 405)

    def test_api_cria_politica_isolada_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_coord_a)
        resposta = client.post(
            "/api/v1/auditoria-politicas/",
            {
                "nome": "Retencao liderancas",
                "tipo_registro": PoliticaRetencaoDados.TiposRegistro.LIDERANCAS,
                "base_legal": "Interesse legitimo",
                "dias_retencao": 180,
                "dias_ate_anonimizacao": 60,
                "anonimizar_ao_expirar": True,
                "responsavel": str(self.usuario_coord_a.pk),
                "observacoes": "Politica criada via API.",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        politica = PoliticaRetencaoDados.objects.get(nome="Retencao liderancas")
        self.assertEqual(politica.campanha, self.campanha_a)
        self.assertEqual(politica.responsavel, self.usuario_coord_a)

    def test_api_bloqueia_politica_com_responsavel_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_coord_a)
        resposta = client.post(
            "/api/v1/auditoria-politicas/",
            {
                "nome": "Retencao invalida",
                "tipo_registro": PoliticaRetencaoDados.TiposRegistro.CONTATOS,
                "dias_retencao": 90,
                "responsavel": str(self.usuario_coord_b.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_cria_solicitacao_e_executa_revogacao(self):
        client = APIClient()
        client.force_authenticate(self.usuario_coord_a)
        resposta = client.post(
            "/api/v1/auditoria-solicitacoes/",
            {
                "nome_solicitante": "Titular API",
                "email_solicitante": "titular-api@example.com",
                "telefone_solicitante": "85988887777",
                "canal_origem": "api",
                "tipo_solicitacao": SolicitacaoTitularDados.TiposSolicitacao.REVOGACAO_CONSENTIMENTO,
                "status": SolicitacaoTitularDados.Status.CONCLUIDA,
                "descricao": "Revogar consentimento por API.",
                "contato_relacionado": str(self.contato_a.pk),
                "responsavel_interno": str(self.usuario_coord_a.pk),
                "prazo_resposta": "2026-07-29",
                "resposta_interna": "Executado via API.",
                "executar_acao_lgpd": True,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        self.contato_a.refresh_from_db()
        self.assertFalse(self.contato_a.consentimento_comunicacao)
        solicitacao = SolicitacaoTitularDados.objects.get(nome_solicitante="Titular API")
        self.assertIn("Consentimento de comunicacao do contato revogado.", solicitacao.resultado_execucao)

    def test_api_bloqueia_solicitacao_com_contato_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_coord_a)
        contato_b = ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato B API",
            telefone="85922223333",
            whatsapp="85922223333",
            email="contato-b-api@example.com",
            cidade="Caucaia",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )
        resposta = client.post(
            "/api/v1/auditoria-solicitacoes/",
            {
                "nome_solicitante": "Titular invalido",
                "tipo_solicitacao": SolicitacaoTitularDados.TiposSolicitacao.ANONIMIZACAO,
                "status": SolicitacaoTitularDados.Status.ABERTA,
                "descricao": "Nao deve aceitar contato cruzado.",
                "contato_relacionado": str(contato_b.pk),
                "responsavel_interno": str(self.usuario_coord_a.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_executar_acao_por_endpoint(self):
        client = APIClient()
        client.force_authenticate(self.usuario_coord_a)
        solicitacao = SolicitacaoTitularDados.objects.create(
            campanha=self.campanha_a,
            nome_solicitante="Titular endpoint",
            tipo_solicitacao=SolicitacaoTitularDados.TiposSolicitacao.REVOGACAO_CONSENTIMENTO,
            status=SolicitacaoTitularDados.Status.CONCLUIDA,
            descricao="Execucao posterior.",
            contato_relacionado=self.contato_a,
            responsavel_interno=self.usuario_coord_a,
        )
        self.contato_a.consentimento_comunicacao = True
        self.contato_a.canal_autorizado = "whatsapp"
        self.contato_a.save(update_fields=["consentimento_comunicacao", "canal_autorizado", "atualizado_em"])
        resposta = client.post(f"/api/v1/auditoria-solicitacoes/{solicitacao.pk}/executar/")
        self.assertEqual(resposta.status_code, 200)
        self.contato_a.refresh_from_db()
        self.assertFalse(self.contato_a.consentimento_comunicacao)

    def test_api_bloqueia_usuario_sem_permissao(self):
        client = APIClient()
        client.force_authenticate(self.usuario_mobilizador)
        resposta = client.get("/api/v1/auditoria-registros/")
        self.assertEqual(resposta.status_code, 403)
