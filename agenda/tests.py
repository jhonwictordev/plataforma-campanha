from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from campanhas.models import Campanha
from liderancas.models import Lideranca

from .models import EventoAgenda

Usuario = get_user_model()


class AgendaPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Agenda A",
            nome_candidato="Candidata Agenda A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="15",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Agenda B",
            nome_candidato="Candidato Agenda B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="25",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_editor = Usuario.objects.create_user(
            email="agenda-editor@example.com",
            password="senha123",
            nome_completo="Editor Agenda",
            campanha=self.campanha_a,
            nivel_acesso="comunicacao",
        )
        self.usuario_outra_campanha = Usuario.objects.create_user(
            email="agenda-outra@example.com",
            password="senha123",
            nome_completo="Usuario Outra Campanha",
            campanha=self.campanha_b,
            nivel_acesso="comunicacao",
        )
        self.visualizador = Usuario.objects.create_user(
            email="agenda-visualizador@example.com",
            password="senha123",
            nome_completo="Visualizador Agenda",
            campanha=self.campanha_a,
            nivel_acesso="visualizador",
        )
        self.participante_a = Usuario.objects.create_user(
            email="participante-a@example.com",
            password="senha123",
            nome_completo="Participante A",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.participante_b = Usuario.objects.create_user(
            email="participante-b@example.com",
            password="senha123",
            nome_completo="Participante B",
            campanha=self.campanha_b,
            nivel_acesso="mobilizador",
        )
        self.lideranca_a = Lideranca.objects.create(
            campanha=self.campanha_a,
            nome_completo="Lideranca Agenda A",
            telefone="85911112222",
            tipo_lideranca="comunitaria",
            estado="CE",
            cidade="Fortaleza",
        )
        self.evento_a = EventoAgenda.objects.create(
            campanha=self.campanha_a,
            titulo="Reuniao regional",
            tipo="reuniao",
            data="2026-07-29",
            horario_inicial="10:00",
            horario_final="11:00",
            responsavel=self.usuario_editor,
            status="confirmado",
            prioridade="alta",
        )
        self.evento_a.participantes.add(self.participante_a)
        self.evento_a.liderancas_convidadas.add(self.lideranca_a)

        self.evento_b = EventoAgenda.objects.create(
            campanha=self.campanha_b,
            titulo="Evento outra campanha",
            tipo="visita",
            data="2026-07-29",
            horario_inicial="14:00",
            horario_final="15:00",
            responsavel=self.usuario_outra_campanha,
            status="confirmado",
            prioridade="media",
        )

    def test_lista_web_mostra_apenas_eventos_da_mesma_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("agenda:home"), {"visao": "semana", "referencia": "2026-07-28"})
        self.assertContains(resposta, "Reuniao regional")
        self.assertNotContains(resposta, "Evento outra campanha")

    def test_detalhe_web_bloqueia_idor_para_outra_campanha(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.get(reverse("agenda:detalhe", args=[self.evento_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_visualizador_nao_pode_criar_evento_na_web(self):
        self.client.force_login(self.visualizador)
        resposta = self.client.get(reverse("agenda:novo"))
        self.assertEqual(resposta.status_code, 403)

    def test_formulario_web_detecta_conflito_de_horario(self):
        self.client.force_login(self.usuario_editor)
        resposta = self.client.post(
            reverse("agenda:novo"),
            {
                "titulo": "Nova reuniao em conflito",
                "tipo": "reuniao",
                "data": "2026-07-29",
                "horario_inicial": "10:30",
                "horario_final": "11:30",
                "responsavel": str(self.usuario_editor.pk),
                "status": "confirmado",
                "prioridade": "alta",
                "participantes": [str(self.participante_a.pk)],
                "liderancas_convidadas": [str(self.lideranca_a.pk)],
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Existe conflito de agenda")

    def test_api_lista_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.get("/api/v1/agenda-eventos/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["titulo"], "Reuniao regional")

    def test_api_bloqueia_participante_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/agenda-eventos/",
            {
                "titulo": "Visita externa",
                "tipo": "visita",
                "data": "2026-07-30",
                "horario_inicial": "09:00:00",
                "horario_final": "10:00:00",
                "status": "confirmado",
                "prioridade": "media",
                "participantes": [str(self.participante_b.pk)],
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_conflito_de_horario(self):
        client = APIClient()
        client.force_authenticate(self.usuario_editor)
        resposta = client.post(
            "/api/v1/agenda-eventos/",
            {
                "titulo": "Entrevista em conflito",
                "tipo": "entrevista",
                "data": "2026-07-29",
                "horario_inicial": "10:15:00",
                "horario_final": "10:45:00",
                "status": "confirmado",
                "prioridade": "alta",
                "responsavel": str(self.usuario_editor.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_criacao_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador)
        resposta = client.post(
            "/api/v1/agenda-eventos/",
            {
                "titulo": "Evento somente leitura",
                "tipo": "prazo",
                "data": "2026-07-31",
                "horario_inicial": "08:00:00",
                "status": "confirmado",
                "prioridade": "baixa",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)
