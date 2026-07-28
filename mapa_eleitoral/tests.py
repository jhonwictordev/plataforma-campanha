from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from agenda.models import EventoAgenda
from campanhas.models import Campanha
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe
from liderancas.models import Lideranca

Usuario = get_user_model()


class MapaEleitoralPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Mapa A",
            nome_candidato="Candidata Mapa A",
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
            nome_campanha="Campanha Mapa B",
            nome_candidato="Candidato Mapa B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="81",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_mobilizador_a = Usuario.objects.create_user(
            email="mapa-a@example.com",
            password="senha123",
            nome_completo="Mapa A",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.usuario_financeiro_a = Usuario.objects.create_user(
            email="mapa-financeiro@example.com",
            password="senha123",
            nome_completo="Financeiro Mapa",
            campanha=self.campanha_a,
            nivel_acesso="financeiro",
        )
        self.usuario_staff = Usuario.objects.create_user(
            email="mapa-staff@example.com",
            password="senha123",
            nome_completo="Staff Mapa",
            nivel_acesso="administrador",
            is_staff=True,
        )

        # Fortaleza: dois contatos autorizados suficientes para agregacao.
        ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Fortaleza 1",
            telefone="85910000001",
            whatsapp="85910000001",
            cidade="Fortaleza",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.730451"),
            longitude=Decimal("-38.521798"),
        )
        ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Fortaleza 2",
            telefone="85910000002",
            whatsapp="85910000002",
            cidade="Fortaleza",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.INTERESSADO,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.730430"),
            longitude=Decimal("-38.521760"),
        )
        # Caucaia: segundo territorio da mesma campanha.
        ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Caucaia 1",
            telefone="85910000003",
            whatsapp="85910000003",
            cidade="Caucaia",
            bairro="Jurema",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.736507"),
            longitude=Decimal("-38.653370"),
        )
        ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Caucaia 2",
            telefone="85910000004",
            whatsapp="85910000004",
            cidade="Caucaia",
            bairro="Jurema",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.736530"),
            longitude=Decimal("-38.653390"),
        )
        # Sem consentimento, nao deve entrar no mapa.
        ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Sem Consentimento",
            telefone="85910000005",
            whatsapp="85910000005",
            cidade="Fortaleza",
            bairro="Aldeota",
            status_funil=ContatoCRM.EtapasFunil.NOVO_CONTATO,
            consentimento_comunicacao=False,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.744325"),
            longitude=Decimal("-38.491531"),
        )

        # Outra campanha, nao pode vazar.
        ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato B1",
            telefone="85920000001",
            whatsapp="85920000001",
            cidade="Maracanau",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.876490"),
            longitude=Decimal("-38.625130"),
        )
        ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato B2",
            telefone="85920000002",
            whatsapp="85920000002",
            cidade="Maracanau",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.876510"),
            longitude=Decimal("-38.625140"),
        )

        Lideranca.objects.create(
            campanha=self.campanha_a,
            nome_completo="Lideranca A1",
            telefone="85930000001",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Fortaleza",
            bairro="Centro",
            regiao_eleitoral="Regional 1",
            consentimento_dados=True,
            apoiadores_estimados=120,
            latitude=Decimal("-3.730411"),
            longitude=Decimal("-38.521720"),
        )
        Lideranca.objects.create(
            campanha=self.campanha_a,
            nome_completo="Lideranca A2",
            telefone="85930000002",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Fortaleza",
            bairro="Centro",
            regiao_eleitoral="Regional 1",
            consentimento_dados=True,
            apoiadores_estimados=90,
            latitude=Decimal("-3.730392"),
            longitude=Decimal("-38.521700"),
        )
        Lideranca.objects.create(
            campanha=self.campanha_a,
            nome_completo="Lideranca Sem Consentimento",
            telefone="85930000003",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Fortaleza",
            bairro="Aldeota",
            regiao_eleitoral="Regional 2",
            consentimento_dados=False,
            apoiadores_estimados=40,
            latitude=Decimal("-3.744100"),
            longitude=Decimal("-38.492000"),
        )
        Lideranca.objects.create(
            campanha=self.campanha_b,
            nome_completo="Lideranca B1",
            telefone="85930000004",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Maracanau",
            bairro="Centro",
            regiao_eleitoral="Regional B",
            consentimento_dados=True,
            apoiadores_estimados=60,
            latitude=Decimal("-3.876530"),
            longitude=Decimal("-38.625120"),
        )
        Lideranca.objects.create(
            campanha=self.campanha_b,
            nome_completo="Lideranca B2",
            telefone="85930000005",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Maracanau",
            bairro="Centro",
            regiao_eleitoral="Regional B",
            consentimento_dados=True,
            apoiadores_estimados=50,
            latitude=Decimal("-3.876550"),
            longitude=Decimal("-38.625110"),
        )

        EventoAgenda.objects.create(
            campanha=self.campanha_a,
            titulo="Caminhada Fortaleza",
            tipo=EventoAgenda.Tipos.CAMINHADA,
            data=timezone.localdate(),
            horario_inicial="09:00",
            status=EventoAgenda.Status.CONFIRMADO,
            endereco="Fortaleza Centro",
            latitude=Decimal("-3.730500"),
            longitude=Decimal("-38.521900"),
        )
        EventoAgenda.objects.create(
            campanha=self.campanha_b,
            titulo="Evento Maracanau",
            tipo=EventoAgenda.Tipos.REUNIAO,
            data=timezone.localdate(),
            horario_inicial="14:00",
            status=EventoAgenda.Status.CONFIRMADO,
            endereco="Maracanau Centro",
            latitude=Decimal("-3.876600"),
            longitude=Decimal("-38.625100"),
        )

        IntegranteEquipe.objects.create(
            campanha=self.campanha_a,
            nome="Equipe Fortaleza",
            funcao="Mobilizador territorial",
            departamento="Mobilizacao",
            cidade_regiao="Fortaleza",
            status="ativo",
        )
        IntegranteEquipe.objects.create(
            campanha=self.campanha_b,
            nome="Equipe Maracanau",
            funcao="Mobilizador territorial",
            departamento="Mobilizacao",
            cidade_regiao="Maracanau",
            status="ativo",
        )

    def test_home_isola_dados_por_campanha(self):
        self.client.force_login(self.usuario_mobilizador_a)
        resposta = self.client.get(reverse("mapa_eleitoral:home"), {"periodo": "90d"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["resumo"]["territorios_monitorados"], 2)
        self.assertEqual(len(resposta.context["camadas_mapa"]["contatos"]), 2)
        self.assertEqual(len(resposta.context["camadas_mapa"]["liderancas"]), 1)
        self.assertContains(resposta, "Caminhada Fortaleza")
        self.assertNotContains(resposta, "Evento Maracanau")

    def test_home_filtra_por_cidade(self):
        self.client.force_login(self.usuario_mobilizador_a)
        resposta = self.client.get(reverse("mapa_eleitoral:home"), {"periodo": "90d", "cidade": "Fortaleza"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["resumo"]["territorios_monitorados"], 1)
        contatos = resposta.context["camadas_mapa"]["contatos"]
        self.assertEqual(len(contatos), 1)
        self.assertEqual(contatos[0]["cidade"], "Fortaleza")
        self.assertEqual(contatos[0]["total"], 2)

    def test_home_bloqueia_usuario_sem_permissao(self):
        self.client.force_login(self.usuario_financeiro_a)
        resposta = self.client.get(reverse("mapa_eleitoral:home"))
        self.assertEqual(resposta.status_code, 403)

    def test_api_lista_isola_por_campanha_e_consentimento(self):
        client = APIClient()
        client.force_authenticate(self.usuario_mobilizador_a)
        resposta = client.get("/api/v1/mapa-eleitoral/?periodo=90d&camada=consolidado")
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(dados["resumo"]["territorios_monitorados"], 2)
        self.assertEqual(len(dados["camadas"]["contatos"]), 2)
        self.assertEqual(len(dados["camadas"]["liderancas"]), 1)
        self.assertEqual(dados["camadas"]["liderancas"][0]["apoiadores_estimados"], 210)
        titulos_eventos = [item["titulo"] for item in dados["camadas"]["eventos"]]
        self.assertIn("Caminhada Fortaleza", titulos_eventos)
        self.assertNotIn("Evento Maracanau", titulos_eventos)

    def test_api_staff_pode_filtrar_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_staff)
        resposta = client.get(f"/api/v1/mapa-eleitoral/?periodo=90d&campanha={self.campanha_b.pk}")
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(dados["resumo"]["territorios_monitorados"], 1)
        self.assertEqual(dados["camadas"]["contatos"][0]["cidade"], "Maracanau")
        titulos_eventos = [item["titulo"] for item in dados["camadas"]["eventos"]]
        self.assertEqual(titulos_eventos, ["Evento Maracanau"])
