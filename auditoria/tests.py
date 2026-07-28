from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
