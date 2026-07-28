import os
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch

from campanhas.models import Campanha
from eleitores.models import ContatoCRM

from .models import (
    CampanhaComunicacao,
    EnvioComunicacao,
    ListaBloqueio,
    ModeloMensagem,
    NotificacaoInterna,
    RegistroWebhookComunicacao,
)
from .services import processar_campanha_comunicacao, processar_campanhas_agendadas, sincronizar_envios_campanha

Usuario = get_user_model()


class ComunicacaoPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Comunicacao A",
            nome_candidato="Candidata Comunicacao A",
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
            nome_campanha="Campanha Comunicacao B",
            nome_candidato="Candidato Comunicacao B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="41",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_comunicacao = Usuario.objects.create_user(
            email="comunicacao-a@example.com",
            password="senha123",
            nome_completo="Comunicacao A",
            campanha=self.campanha_a,
            nivel_acesso="comunicacao",
        )
        self.usuario_mobilizador = Usuario.objects.create_user(
            email="mobilizador-a@example.com",
            password="senha123",
            nome_completo="Mobilizador A",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.usuario_outra_campanha = Usuario.objects.create_user(
            email="comunicacao-b@example.com",
            password="senha123",
            nome_completo="Comunicacao B",
            campanha=self.campanha_b,
            nivel_acesso="comunicacao",
        )
        self.contato_autorizado_a = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Autorizado A",
            telefone="85911110000",
            whatsapp="85911110000",
            cidade="Fortaleza",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )
        self.contato_sem_consentimento_a = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Sem Consentimento A",
            telefone="85922220000",
            whatsapp="85922220000",
            cidade="Fortaleza",
            status_funil=ContatoCRM.EtapasFunil.INTERESSADO,
            consentimento_comunicacao=False,
            canal_autorizado="whatsapp",
        )
        self.contato_bloqueado_a = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Bloqueado A",
            telefone="85933330000",
            whatsapp="85933330000",
            cidade="Fortaleza",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )
        self.contato_outra_campanha = ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato B",
            telefone="85944440000",
            whatsapp="85944440000",
            cidade="Caucaia",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )
        self.modelo_a = ModeloMensagem.objects.create(
            campanha=self.campanha_a,
            nome="Modelo WhatsApp A",
            canal="whatsapp",
            assunto="Convite",
            conteudo="Mensagem autorizada A",
        )
        self.modelo_b = ModeloMensagem.objects.create(
            campanha=self.campanha_b,
            nome="Modelo WhatsApp B",
            canal="whatsapp",
            assunto="Convite B",
            conteudo="Mensagem autorizada B",
        )
        self.bloqueio_a = ListaBloqueio.objects.create(
            campanha=self.campanha_a,
            contato=self.contato_bloqueado_a,
            canal="whatsapp",
            motivo="Solicitou nao receber mais mensagens.",
            solicitado_por=self.usuario_comunicacao,
        )
        self.campanha_comunicacao_a = CampanhaComunicacao.objects.create(
            campanha=self.campanha_a,
            nome="Campanha A",
            modelo_mensagem=self.modelo_a,
            assunto="Convite principal",
            conteudo="Vamos para a caminhada de 28 de julho de 2026.",
            canal="whatsapp",
            data_envio="2026-08-05T10:00:00Z",
            responsavel=self.usuario_comunicacao,
            status=CampanhaComunicacao.Status.AGENDADA,
        )
        self.campanha_comunicacao_a.destinatarios.set([self.contato_autorizado_a])
        sincronizar_envios_campanha(
            campanha_comunicacao=self.campanha_comunicacao_a,
            destinatarios=self.campanha_comunicacao_a.destinatarios.all(),
            usuario=self.usuario_comunicacao,
        )
        self.envio_a = self.campanha_comunicacao_a.envios.get(contato=self.contato_autorizado_a)

        self.campanha_comunicacao_b = CampanhaComunicacao.objects.create(
            campanha=self.campanha_b,
            nome="Campanha B",
            modelo_mensagem=self.modelo_b,
            assunto="Mensagem B",
            conteudo="Convite B",
            canal="whatsapp",
            data_envio="2026-08-07T10:00:00Z",
            responsavel=self.usuario_outra_campanha,
            status=CampanhaComunicacao.Status.AGENDADA,
        )
        self.campanha_comunicacao_b.destinatarios.set([self.contato_outra_campanha])
        sincronizar_envios_campanha(
            campanha_comunicacao=self.campanha_comunicacao_b,
            destinatarios=self.campanha_comunicacao_b.destinatarios.all(),
            usuario=self.usuario_outra_campanha,
        )

    def _criar_envio_email_falho(self, *, nome_campanha="Campanha Email Falha", assunto="Email falho"):
        contato_email = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo=f"Contato {nome_campanha}",
            telefone="85988880000",
            email=f"{nome_campanha.lower().replace(' ', '-')}@example.com",
            cidade="Fortaleza",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="email",
        )
        modelo_email = ModeloMensagem.objects.create(
            campanha=self.campanha_a,
            nome=f"Modelo {nome_campanha}",
            canal="email",
            assunto=assunto,
            conteudo="Mensagem de e-mail para reprocessamento.",
        )
        campanha_email = CampanhaComunicacao.objects.create(
            campanha=self.campanha_a,
            nome=nome_campanha,
            modelo_mensagem=modelo_email,
            assunto=assunto,
            conteudo="Mensagem de e-mail para reprocessamento.",
            canal="email",
            data_envio="2026-08-08T10:00:00Z",
            responsavel=self.usuario_comunicacao,
            status=CampanhaComunicacao.Status.CONCLUIDA,
        )
        campanha_email.destinatarios.set([contato_email])
        sincronizar_envios_campanha(campanha_email, campanha_email.destinatarios.all(), usuario=self.usuario_comunicacao)
        envio = campanha_email.envios.get(contato=contato_email)
        envio.status = EnvioComunicacao.Status.FALHA
        envio.erro_envio = "Falha simulada para reprocessamento."
        envio.ultimo_erro_tecnico = "Falha simulada para reprocessamento."
        envio.tentativas_envio = 1
        envio.save(
            update_fields=["status", "erro_envio", "ultimo_erro_tecnico", "tentativas_envio", "atualizado_em"]
        )
        campanha_email.quantidade_falha = 1
        campanha_email.erro_ultima_execucao = "Falha simulada para reprocessamento."
        campanha_email.save(update_fields=["quantidade_falha", "erro_ultima_execucao", "atualizado_em"])
        return campanha_email, envio

    def test_lista_web_mostra_apenas_campanhas_da_mesma_campanha(self):
        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.get(reverse("comunicacao:home"))
        self.assertContains(resposta, "Campanha A")
        self.assertNotContains(resposta, "Campanha B")

    def test_painel_operacao_web_exibe_apenas_webhooks_da_mesma_campanha(self):
        RegistroWebhookComunicacao.objects.create(
            campanha=self.campanha_a,
            envio=self.envio_a,
            canal="whatsapp",
            provedor="whatsapp_oficial",
            evento="delivered",
            identificador_externo="wa-a-001",
            dados_recebidos={"message_id": "wa-a-001"},
            assinatura_valida=True,
            processado_com_sucesso=True,
        )
        envio_b = self.campanha_comunicacao_b.envios.first()
        RegistroWebhookComunicacao.objects.create(
            campanha=self.campanha_b,
            envio=envio_b,
            canal="whatsapp",
            provedor="whatsapp_oficial",
            evento="failed",
            identificador_externo="wa-b-001",
            dados_recebidos={"message_id": "wa-b-001"},
            assinatura_valida=False,
            processado_com_sucesso=False,
        )

        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.get(reverse("comunicacao:operacao"), {"assinatura": "valida"})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "wa-a-001")
        self.assertNotContains(resposta, "wa-b-001")

    def test_detalhe_webhook_bloqueia_idor_para_outra_campanha(self):
        envio_b = self.campanha_comunicacao_b.envios.first()
        webhook_b = RegistroWebhookComunicacao.objects.create(
            campanha=self.campanha_b,
            envio=envio_b,
            canal="whatsapp",
            provedor="whatsapp_oficial",
            evento="failed",
            identificador_externo="wa-b-idor",
            dados_recebidos={"message_id": "wa-b-idor"},
            assinatura_valida=True,
            processado_com_sucesso=False,
        )

        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.get(reverse("comunicacao:webhook_detalhe", args=[webhook_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_detalhe_web_bloqueia_idor_para_outra_campanha(self):
        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.get(reverse("comunicacao:campanha_detalhe", args=[self.campanha_comunicacao_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_mobilizador_nao_acessa_modulo_web(self):
        self.client.force_login(self.usuario_mobilizador)
        resposta = self.client.get(reverse("comunicacao:home"))
        self.assertEqual(resposta.status_code, 403)

    def test_api_lista_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.get("/api/v1/comunicacao-campanhas/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["nome"], "Campanha A")

    def test_api_bloqueia_destinatario_sem_consentimento(self):
        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.post(
            "/api/v1/comunicacao-campanhas/",
            {
                "nome": "Campanha sem consentimento",
                "modelo_mensagem": str(self.modelo_a.pk),
                "assunto": "Assunto",
                "conteudo": "Conteudo",
                "canal": "whatsapp",
                "destinatarios": [str(self.contato_sem_consentimento_a.pk)],
                "data_envio": "2026-08-06T10:00:00Z",
                "status": CampanhaComunicacao.Status.AGENDADA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_destinatario_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.post(
            "/api/v1/comunicacao-campanhas/",
            {
                "nome": "Campanha cruzada",
                "modelo_mensagem": str(self.modelo_a.pk),
                "assunto": "Assunto",
                "conteudo": "Conteudo",
                "canal": "whatsapp",
                "destinatarios": [str(self.contato_outra_campanha.pk)],
                "data_envio": "2026-08-06T10:00:00Z",
                "status": CampanhaComunicacao.Status.AGENDADA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_destinatario_em_lista_bloqueio(self):
        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.post(
            "/api/v1/comunicacao-campanhas/",
            {
                "nome": "Campanha bloqueada",
                "modelo_mensagem": str(self.modelo_a.pk),
                "assunto": "Assunto",
                "conteudo": "Conteudo",
                "canal": "whatsapp",
                "destinatarios": [str(self.contato_bloqueado_a.pk)],
                "data_envio": "2026-08-06T10:00:00Z",
                "status": CampanhaComunicacao.Status.AGENDADA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_cria_campanha_e_sincroniza_envios(self):
        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.post(
            "/api/v1/comunicacao-campanhas/",
            {
                "nome": "Campanha sincronizada",
                "modelo_mensagem": str(self.modelo_a.pk),
                "canal": "whatsapp",
                "destinatarios": [str(self.contato_autorizado_a.pk)],
                "data_envio": "2026-08-08T10:00:00Z",
                "status": CampanhaComunicacao.Status.AGENDADA,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()["quantidade_programada"], 1)
        campanha = CampanhaComunicacao.objects.get(pk=resposta.json()["id"])
        self.assertEqual(campanha.envios.count(), 1)

    def test_api_atualiza_envio_com_resposta_e_registra_descadastro(self):
        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.patch(
            f"/api/v1/comunicacao-envios/{self.envio_a.pk}/",
            {
                "status": EnvioComunicacao.Status.RESPONDIDO,
                "resposta_recebida": "Quero sair da lista.",
                "cancelou_inscricao": True,
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNotNone(resposta.json()["data_resposta"])
        self.assertTrue(
            ListaBloqueio.objects.filter(
                campanha=self.campanha_a,
                contato=self.contato_autorizado_a,
                canal="whatsapp",
            ).exists()
        )

    def test_reprocessamento_web_de_envio_falho(self):
        campanha_email, envio = self._criar_envio_email_falho(nome_campanha="Campanha Email Reprocessar")
        mail.outbox.clear()

        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.post(
            reverse("comunicacao:envio_reprocessar", args=[envio.pk]),
            {"next": reverse("comunicacao:operacao")},
        )
        self.assertEqual(resposta.status_code, 302)
        envio.refresh_from_db()
        campanha_email.refresh_from_db()
        self.assertEqual(envio.status, EnvioComunicacao.Status.ENVIADO)
        self.assertEqual(campanha_email.status, CampanhaComunicacao.Status.CONCLUIDA)
        self.assertEqual(len(mail.outbox), 1)

    def test_api_reprocessa_envio_falho(self):
        _, envio = self._criar_envio_email_falho(nome_campanha="Campanha Email API Reprocessar")
        mail.outbox.clear()

        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.post(f"/api/v1/comunicacao-envios/{envio.pk}/reprocessar/", {}, format="json")
        self.assertEqual(resposta.status_code, 200)
        envio.refresh_from_db()
        self.assertEqual(envio.status, EnvioComunicacao.Status.ENVIADO)
        self.assertEqual(resposta.json()["processamento"]["resultado"], "sucesso")
        self.assertEqual(len(mail.outbox), 1)

    def test_usuario_visualiza_apenas_suas_notificacoes(self):
        NotificacaoInterna.objects.create(
            campanha=self.campanha_a,
            usuario_destinatario=self.usuario_comunicacao,
            titulo="Alerta A",
            mensagem="Mensagem A",
            categoria=NotificacaoInterna.Categorias.SISTEMA,
        )
        NotificacaoInterna.objects.create(
            campanha=self.campanha_b,
            usuario_destinatario=self.usuario_outra_campanha,
            titulo="Alerta B",
            mensagem="Mensagem B",
            categoria=NotificacaoInterna.Categorias.SISTEMA,
        )
        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.get(reverse("comunicacao:notificacoes"))
        self.assertContains(resposta, "Alerta A")
        self.assertNotContains(resposta, "Alerta B")

    def test_api_marca_notificacao_como_lida(self):
        notificacao = NotificacaoInterna.objects.create(
            campanha=self.campanha_a,
            usuario_destinatario=self.usuario_comunicacao,
            titulo="Alerta de leitura",
            mensagem="Mensagem",
            categoria=NotificacaoInterna.Categorias.SISTEMA,
        )
        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.patch(f"/api/v1/comunicacao-notificacoes/{notificacao.pk}/", {}, format="json")
        self.assertEqual(resposta.status_code, 200)
        notificacao.refresh_from_db()
        self.assertIsNotNone(notificacao.lida_em)

    def test_processamento_email_envia_para_backend_oficial(self):
        contato_email = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Email",
            telefone="85955550000",
            email="contato-email@example.com",
            cidade="Fortaleza",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="email",
        )
        modelo_email = ModeloMensagem.objects.create(
            campanha=self.campanha_a,
            nome="Modelo Email",
            canal="email",
            assunto="Assunto oficial",
            conteudo="Mensagem de e-mail autorizada.",
        )
        campanha_email = CampanhaComunicacao.objects.create(
            campanha=self.campanha_a,
            nome="Campanha Email",
            modelo_mensagem=modelo_email,
            assunto="Assunto oficial",
            conteudo="Mensagem de e-mail autorizada.",
            canal="email",
            data_envio="2026-07-28T09:00:00Z",
            responsavel=self.usuario_comunicacao,
            status=CampanhaComunicacao.Status.AGENDADA,
        )
        campanha_email.destinatarios.set([contato_email])
        sincronizar_envios_campanha(
            campanha_comunicacao=campanha_email,
            destinatarios=campanha_email.destinatarios.all(),
            usuario=self.usuario_comunicacao,
        )

        resultado = processar_campanha_comunicacao(campanha_email, forcar_execucao=True)

        campanha_email.refresh_from_db()
        envio = campanha_email.envios.get(contato=contato_email)
        self.assertEqual(resultado["processados"], 1)
        self.assertEqual(campanha_email.status, CampanhaComunicacao.Status.CONCLUIDA)
        self.assertEqual(campanha_email.provedor_ultimo_envio, "email_django")
        self.assertEqual(envio.status, EnvioComunicacao.Status.ENVIADO)
        self.assertEqual(envio.tentativas_envio, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["contato-email@example.com"])

    def test_processamento_whatsapp_sem_integracao_pausa_campanha(self):
        resultado = processar_campanha_comunicacao(self.campanha_comunicacao_a, forcar_execucao=True)
        self.campanha_comunicacao_a.refresh_from_db()
        self.assertEqual(resultado["status"], "pausada")
        self.assertEqual(self.campanha_comunicacao_a.status, CampanhaComunicacao.Status.PAUSADA)
        self.assertIn("integracao oficial", self.campanha_comunicacao_a.erro_ultima_execucao.lower())
        self.assertTrue(
            NotificacaoInterna.objects.filter(
                campanha=self.campanha_a,
                usuario_destinatario=self.usuario_comunicacao,
                titulo__icontains="Campanha pausada",
            ).exists()
        )

    def test_processar_campanhas_agendadas_considera_apenas_comunicacoes_vencidas(self):
        resultado = processar_campanhas_agendadas()
        self.assertEqual(resultado["campanhas"], 0)

        self.campanha_comunicacao_a.data_envio = "2026-07-27T10:00:00Z"
        self.campanha_comunicacao_a.save(update_fields=["data_envio", "atualizado_em"])
        resultado = processar_campanhas_agendadas()
        self.assertEqual(resultado["campanhas"], 1)
        self.assertEqual(resultado["pausadas"], 1)

    def test_execucao_manual_web_processa_campanha(self):
        contato_email = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Manual",
            telefone="85966660000",
            email="manual@example.com",
            cidade="Fortaleza",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="email",
        )
        modelo_email = ModeloMensagem.objects.create(
            campanha=self.campanha_a,
            nome="Modelo Email Manual",
            canal="email",
            assunto="Manual",
            conteudo="Disparo manual.",
        )
        campanha_email = CampanhaComunicacao.objects.create(
            campanha=self.campanha_a,
            nome="Campanha Manual",
            modelo_mensagem=modelo_email,
            assunto="Manual",
            conteudo="Disparo manual.",
            canal="email",
            data_envio="2026-08-08T10:00:00Z",
            responsavel=self.usuario_comunicacao,
            status=CampanhaComunicacao.Status.AGENDADA,
        )
        campanha_email.destinatarios.set([contato_email])
        sincronizar_envios_campanha(campanha_email, campanha_email.destinatarios.all(), usuario=self.usuario_comunicacao)

        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.post(reverse("comunicacao:campanha_executar", args=[campanha_email.pk]))
        self.assertEqual(resposta.status_code, 302)
        campanha_email.refresh_from_db()
        self.assertEqual(campanha_email.status, CampanhaComunicacao.Status.CONCLUIDA)

    def test_api_executa_campanha_manual(self):
        contato_email = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato API",
            telefone="85977770000",
            email="api@example.com",
            cidade="Fortaleza",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="email",
        )
        modelo_email = ModeloMensagem.objects.create(
            campanha=self.campanha_a,
            nome="Modelo Email API",
            canal="email",
            assunto="API",
            conteudo="Disparo API.",
        )
        campanha_email = CampanhaComunicacao.objects.create(
            campanha=self.campanha_a,
            nome="Campanha API",
            modelo_mensagem=modelo_email,
            assunto="API",
            conteudo="Disparo API.",
            canal="email",
            data_envio="2026-08-08T10:00:00Z",
            responsavel=self.usuario_comunicacao,
            status=CampanhaComunicacao.Status.AGENDADA,
        )
        campanha_email.destinatarios.set([contato_email])
        sincronizar_envios_campanha(campanha_email, campanha_email.destinatarios.all(), usuario=self.usuario_comunicacao)

        client = APIClient()
        client.force_authenticate(self.usuario_comunicacao)
        resposta = client.post(f"/api/v1/comunicacao-campanhas/{campanha_email.pk}/executar/", {}, format="json")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["processamento"]["processados"], 1)

    @patch.dict(os.environ, {"WHATSAPP_OFFICIAL_WEBHOOK_TOKEN": "token-webhook-whatsapp"}, clear=False)
    def test_webhook_invalido_rejeita_requisicao(self):
        resposta = self.client.post(
            "/api/v1/comunicacao/webhooks/whatsapp/",
            {"event": "delivered", "send_id": str(self.envio_a.pk)},
            content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN="token-errado",
        )
        self.assertEqual(resposta.status_code, 403)
        self.envio_a.refresh_from_db()
        self.assertEqual(self.envio_a.status, EnvioComunicacao.Status.PROGRAMADO)
        self.assertTrue(
            RegistroWebhookComunicacao.todos_objetos.filter(
                canal="whatsapp",
                assinatura_valida=False,
            ).exists()
        )

    @patch.dict(os.environ, {"WHATSAPP_OFFICIAL_WEBHOOK_TOKEN": "token-webhook-whatsapp"}, clear=False)
    def test_webhook_confirma_entrega_por_send_id(self):
        self.envio_a.identificador_externo = "wa-msg-001"
        self.envio_a.provedor_utilizado = "whatsapp_oficial"
        self.envio_a.save(update_fields=["identificador_externo", "provedor_utilizado", "atualizado_em"])

        resposta = self.client.post(
            "/api/v1/comunicacao/webhooks/whatsapp/",
            {
                "provider": "whatsapp_oficial",
                "event": "delivered",
                "send_id": str(self.envio_a.pk),
                "message_id": "wa-msg-001",
                "detail": "Mensagem entregue ao destinatario.",
            },
            content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN="token-webhook-whatsapp",
        )
        self.assertEqual(resposta.status_code, 200)
        self.envio_a.refresh_from_db()
        self.assertEqual(self.envio_a.status, EnvioComunicacao.Status.ENTREGUE)
        self.assertEqual(self.envio_a.identificador_externo, "wa-msg-001")
        self.assertTrue(
            RegistroWebhookComunicacao.todos_objetos.filter(
                envio=self.envio_a,
                assinatura_valida=True,
                processado_com_sucesso=True,
            ).exists()
        )

    @patch.dict(os.environ, {"WHATSAPP_OFFICIAL_WEBHOOK_TOKEN": "token-webhook-whatsapp"}, clear=False)
    def test_webhook_descadastro_registra_bloqueio_e_notifica(self):
        resposta = self.client.post(
            "/api/v1/comunicacao/webhooks/whatsapp/",
            {
                "provider": "whatsapp_oficial",
                "event": "unsubscribe",
                "send_id": str(self.envio_a.pk),
                "response_text": "STOP",
                "message_id": "wa-msg-stop",
            },
            content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN="token-webhook-whatsapp",
        )
        self.assertEqual(resposta.status_code, 200)
        self.envio_a.refresh_from_db()
        self.assertEqual(self.envio_a.status, EnvioComunicacao.Status.RESPONDIDO)
        self.assertTrue(self.envio_a.cancelou_inscricao)
        self.assertTrue(
            ListaBloqueio.objects.filter(
                campanha=self.campanha_a,
                contato=self.contato_autorizado_a,
                canal="whatsapp",
            ).exists()
        )
        self.assertTrue(
            NotificacaoInterna.objects.filter(
                campanha=self.campanha_a,
                usuario_destinatario=self.usuario_comunicacao,
                titulo__icontains="Descadastro recebido",
            ).exists()
        )

    @patch.dict(os.environ, {"WHATSAPP_OFFICIAL_WEBHOOK_TOKEN": "token-webhook-whatsapp"}, clear=False)
    def test_webhook_sem_envio_correspondente_retorna_aceite_tecnico(self):
        resposta = self.client.post(
            "/api/v1/comunicacao/webhooks/whatsapp/",
            {
                "provider": "whatsapp_oficial",
                "event": "delivered",
                "send_id": "11111111-1111-1111-1111-111111111111",
                "message_id": "wa-msg-desconhecida",
            },
            content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN="token-webhook-whatsapp",
        )
        self.assertEqual(resposta.status_code, 202)
        self.assertTrue(
            RegistroWebhookComunicacao.todos_objetos.filter(
                identificador_externo="wa-msg-desconhecida",
                assinatura_valida=True,
                processado_com_sucesso=False,
            ).exists()
        )
