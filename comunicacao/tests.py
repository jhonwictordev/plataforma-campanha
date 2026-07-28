from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from campanhas.models import Campanha
from eleitores.models import ContatoCRM

from .models import CampanhaComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem, NotificacaoInterna
from .services import sincronizar_envios_campanha

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

    def test_lista_web_mostra_apenas_campanhas_da_mesma_campanha(self):
        self.client.force_login(self.usuario_comunicacao)
        resposta = self.client.get(reverse("comunicacao:home"))
        self.assertContains(resposta, "Campanha A")
        self.assertNotContains(resposta, "Campanha B")

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
