from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from campanhas.models import Campanha
from eleitores.models import ContatoCRM, InteracaoContato


Usuario = get_user_model()


class FluxosPrioritariosDemonstracaoTestCase(TestCase):
    """Prova os tres fluxos principais apenas com pessoas e campanhas ficticias."""

    @classmethod
    def setUpTestData(cls):
        cls.campanha_a = Campanha.objects.create(
            nome_campanha="DEMO Jornada Segura A",
            nome_candidato="Candidata Ficticia Aurora",
            cargo_disputado=Campanha.Cargos.PREFEITO,
            partido="DEM",
            numero_candidato="71",
            estado="CE",
            municipio="Cidade Demonstracao A",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao=Campanha.Situacoes.ATIVA,
        )
        cls.campanha_b = Campanha.objects.create(
            nome_campanha="DEMO Jornada Segura B",
            nome_candidato="Candidato Ficticio Horizonte",
            cargo_disputado=Campanha.Cargos.PREFEITO,
            partido="DEM",
            numero_candidato="72",
            estado="CE",
            municipio="Cidade Demonstracao B",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao=Campanha.Situacoes.ATIVA,
        )
        cls.admin = Usuario.objects.create_user(
            email="admin.fluxos@demo.plataformacampanha.local",
            password="SenhaDemo2026!",
            nome_completo="Administradora Ficticia",
            nivel_acesso=Usuario.NiveisAcesso.ADMINISTRADOR,
            is_staff=True,
        )
        cls.coordenador_livre = Usuario.objects.create_user(
            email="coordenador.livre@demo.plataformacampanha.local",
            password="SenhaDemo2026!",
            nome_completo="Coordenador Ficticio Livre",
            nivel_acesso=Usuario.NiveisAcesso.COORDENADOR_GERAL,
        )
        cls.mobilizador_a = Usuario.objects.create_user(
            email="mobilizador.a@demo.plataformacampanha.local",
            password="SenhaDemo2026!",
            nome_completo="Mobilizador Ficticio A",
            nivel_acesso=Usuario.NiveisAcesso.MOBILIZADOR,
            campanha=cls.campanha_a,
        )

    def test_fluxo_1_criar_campanha_e_configurar_permissoes(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(
            reverse("campanhas:nova"),
            {
                "nome_campanha": "DEMO Nova Campanha Segura",
                "nome_candidato": "Pessoa Candidata Ficticia",
                "cargo_disputado": Campanha.Cargos.VEREADOR,
                "partido": "DEM",
                "numero_candidato": "73001",
                "estado": "CE",
                "municipio": "Cidade Demonstracao C",
                "data_inicio": "2026-07-10",
                "data_eleicao": "2026-10-04",
                "situacao": Campanha.Situacoes.PLANEJAMENTO,
                "cor_primaria": "#123456",
                "cor_secundaria": "#ABCDEF",
                "coordenador_responsavel": str(self.coordenador_livre.pk),
                "descricao": "Registro sintetico para demonstracao.",
                "objetivos_gerais": "Validar criacao e controle de acesso.",
            },
        )
        self.assertEqual(resposta.status_code, 302)

        campanha = Campanha.objects.get(nome_campanha="DEMO Nova Campanha Segura")
        self.coordenador_livre.refresh_from_db()
        self.assertEqual(self.coordenador_livre.campanha_id, campanha.pk)

        self.client.force_login(self.coordenador_livre)
        resposta = self.client.post(
            reverse("usuarios:novo"),
            {
                "email": "mobilizador.novo@demo.plataformacampanha.local",
                "nome_completo": "Mobilizadora Ficticia Nova",
                "campanha": str(campanha.pk),
                "nivel_acesso": Usuario.NiveisAcesso.MOBILIZADOR,
                "password1": "SenhaDemo2026!",
                "password2": "SenhaDemo2026!",
            },
        )
        self.assertEqual(resposta.status_code, 302)
        mobilizador = Usuario.objects.get(email="mobilizador.novo@demo.plataformacampanha.local")
        self.assertEqual(mobilizador.campanha_id, campanha.pk)
        self.assertEqual(mobilizador.nivel_acesso, Usuario.NiveisAcesso.MOBILIZADOR)

    def test_fluxo_2_cadastrar_contato_e_acompanhar_interacao(self):
        self.client.force_login(self.mobilizador_a)
        resposta = self.client.post(
            reverse("eleitores:novo"),
            {
                "nome_completo": "Contato Ficticio Jornada",
                "telefone": "85990001111",
                "whatsapp": "85990001111",
                "email": "contato.jornada@demo.plataformacampanha.local",
                "cidade": "Cidade Demonstracao A",
                "bairro": "Bairro Exemplo",
                "origem_contato": "Demonstracao sintetica",
                "status_funil": ContatoCRM.EtapasFunil.NOVO_CONTATO,
                "tags_texto": "demo, jornada-segura",
                "consentimento_comunicacao": "on",
                "canal_autorizado": "whatsapp",
            },
        )
        self.assertEqual(resposta.status_code, 302)
        contato = ContatoCRM.objects.get(email="contato.jornada@demo.plataformacampanha.local")
        self.assertEqual(contato.campanha_id, self.campanha_a.pk)

        momento = timezone.localtime().replace(second=0, microsecond=0)
        resposta = self.client.post(
            reverse("eleitores:interacao_nova", args=[contato.pk]),
            {
                "tipo": "visita",
                "data_hora": momento.strftime("%Y-%m-%dT%H:%M"),
                "descricao": "Interacao sintetica acompanhada de ponta a ponta.",
                "responsavel": str(self.mobilizador_a.pk),
            },
        )
        self.assertEqual(resposta.status_code, 302)
        interacao = InteracaoContato.objects.get(contato=contato)
        self.assertEqual(interacao.campanha_id, self.campanha_a.pk)

        detalhe = self.client.get(reverse("eleitores:detalhe", args=[contato.pk]))
        self.assertContains(detalhe, "Interacao sintetica acompanhada de ponta a ponta.")
        self.assertEqual(detalhe.context["resumo_relacionamento"]["interacoes"], 1)

    def test_fluxo_3_relatorio_ignora_tentativa_de_acesso_a_outra_campanha(self):
        hoje = timezone.localdate()
        contato_a = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Visivel da Campanha A",
            telefone="85990002222",
            cidade="Cidade Demonstracao A",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
        )
        ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato Sigiloso da Campanha B",
            telefone="85990003333",
            cidade="Cidade Demonstracao B",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
        )

        self.client.force_login(self.mobilizador_a)
        resposta = self.client.get(
            reverse("relatorios:home"),
            {
                "tipo_relatorio": "contatos_cadastrados",
                "campanha": str(self.campanha_b.pk),
                "data_inicial": (hoje - timedelta(days=1)).isoformat(),
                "data_final": (hoje + timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, contato_a.nome_completo)
        self.assertNotContains(resposta, "Contato Sigiloso da Campanha B")
        self.assertEqual(resposta.context["campanha_atual"].pk, self.campanha_a.pk)
        self.assertEqual(resposta.context["total_linhas"], 1)

