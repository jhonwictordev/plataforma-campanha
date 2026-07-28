from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from agenda.models import EventoAgenda
from auditoria.models import RegistroAuditoria
from campanhas.models import Campanha
from comunicacao.models import CampanhaComunicacao, CanalComunicacao, NotificacaoInterna
from eleitores.models import ContatoCRM
from equipe.models import IntegranteEquipe, TarefaEquipe
from financeiro.models import LancamentoFinanceiro
from liderancas.models import Lideranca

Usuario = get_user_model()


class DashboardHomeViewTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha Dashboard A",
            nome_candidato="Candidata Dashboard A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="51",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha Dashboard B",
            nome_candidato="Candidato Dashboard B",
            cargo_disputado="prefeito",
            partido="BBB",
            numero_candidato="61",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_a = Usuario.objects.create_user(
            email="dashboard-a@example.com",
            password="senha123",
            nome_completo="Dashboard A",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.usuario_b = Usuario.objects.create_user(
            email="dashboard-b@example.com",
            password="senha123",
            nome_completo="Dashboard B",
            campanha=self.campanha_b,
            nivel_acesso="mobilizador",
        )
        self.usuario_a_aux = Usuario.objects.create_user(
            email="dashboard-a-aux@example.com",
            password="senha123",
            nome_completo="Dashboard A Aux",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.usuario_staff = Usuario.objects.create_user(
            email="dashboard-staff@example.com",
            password="senha123",
            nome_completo="Dashboard Staff",
            nivel_acesso="administrador",
            is_staff=True,
        )

        self.contato_a1 = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato A1",
            telefone="85911110001",
            whatsapp="85911110001",
            cidade="Fortaleza",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.730451"),
            longitude=Decimal("-38.521798"),
        )
        self.contato_a2 = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato A2",
            telefone="85911110002",
            whatsapp="85911110002",
            cidade="Fortaleza",
            bairro="Centro",
            status_funil=ContatoCRM.EtapasFunil.NOVO_CONTATO,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            latitude=Decimal("-3.730451"),
            longitude=Decimal("-38.521798"),
        )
        self.contato_a3 = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato A3",
            telefone="85911110003",
            whatsapp="85911110003",
            cidade="Caucaia",
            bairro="Jurema",
            status_funil=ContatoCRM.EtapasFunil.NOVO_CONTATO,
            consentimento_comunicacao=False,
            canal_autorizado="whatsapp",
        )
        self.contato_b1 = ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato B1",
            telefone="85922220001",
            whatsapp="85922220001",
            cidade="Maracanau",
            bairro="Novo Maracanau",
            status_funil=ContatoCRM.EtapasFunil.LIDERANCA,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )

        self.lideranca_a = Lideranca.objects.create(
            campanha=self.campanha_a,
            nome_completo="Lideranca A",
            telefone="85933330001",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Fortaleza",
            bairro="Centro",
            regiao_eleitoral="Regional 1",
        )
        self.lideranca_b = Lideranca.objects.create(
            campanha=self.campanha_b,
            nome_completo="Lideranca B",
            telefone="85933330002",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Caucaia",
            bairro="Centro",
            regiao_eleitoral="Regional 2",
        )

        self.integrante_a = IntegranteEquipe.objects.create(
            campanha=self.campanha_a,
            nome="Voluntario A",
            funcao="Voluntario de rua",
            departamento="Mobilizacao",
            cidade_regiao="Fortaleza",
            status="ativo",
        )
        self.integrante_b = IntegranteEquipe.objects.create(
            campanha=self.campanha_b,
            nome="Coordenador B",
            funcao="Coordenador",
            departamento="Coordenacao",
            cidade_regiao="Caucaia",
            status="ativo",
        )

        TarefaEquipe.objects.create(
            campanha=self.campanha_a,
            titulo="Tarefa atrasada A",
            responsavel=self.integrante_a,
            prazo=timezone.now() - timedelta(days=1),
            status=TarefaEquipe.Status.A_FAZER,
        )
        TarefaEquipe.objects.create(
            campanha=self.campanha_b,
            titulo="Tarefa atrasada B",
            responsavel=self.integrante_b,
            prazo=timezone.now() - timedelta(days=1),
            status=TarefaEquipe.Status.A_FAZER,
        )

        EventoAgenda.objects.create(
            campanha=self.campanha_a,
            titulo="Evento A",
            tipo=EventoAgenda.Tipos.REUNIAO,
            data=timezone.localdate() + timedelta(days=2),
            horario_inicial="10:00",
            status=EventoAgenda.Status.CONFIRMADO,
        )
        EventoAgenda.objects.create(
            campanha=self.campanha_b,
            titulo="Evento B",
            tipo=EventoAgenda.Tipos.REUNIAO,
            data=timezone.localdate() + timedelta(days=3),
            horario_inicial="11:00",
            status=EventoAgenda.Status.CONFIRMADO,
        )

        LancamentoFinanceiro.objects.create(
            campanha=self.campanha_a,
            descricao="Receita A",
            tipo=LancamentoFinanceiro.Tipos.RECEITA,
            valor_reais=Decimal("1000.00"),
            data_vencimento="2026-07-20",
            status=LancamentoFinanceiro.Status.LIQUIDADO,
        )
        LancamentoFinanceiro.objects.create(
            campanha=self.campanha_a,
            descricao="Despesa A",
            tipo=LancamentoFinanceiro.Tipos.DESPESA,
            valor_reais=Decimal("300.00"),
            data_vencimento="2026-07-21",
            status=LancamentoFinanceiro.Status.LIQUIDADO,
        )
        LancamentoFinanceiro.objects.create(
            campanha=self.campanha_b,
            descricao="Receita B",
            tipo=LancamentoFinanceiro.Tipos.RECEITA,
            valor_reais=Decimal("9000.00"),
            data_vencimento="2026-07-21",
            status=LancamentoFinanceiro.Status.LIQUIDADO,
        )
        self.conta_vencida_a = LancamentoFinanceiro.objects.create(
            campanha=self.campanha_a,
            descricao="Despesa vencida A",
            tipo=LancamentoFinanceiro.Tipos.DESPESA,
            valor_reais=Decimal("120.00"),
            data_vencimento=timezone.localdate() - timedelta(days=2),
            status=LancamentoFinanceiro.Status.PENDENTE,
        )
        LancamentoFinanceiro.objects.create(
            campanha=self.campanha_b,
            descricao="Despesa vencida B",
            tipo=LancamentoFinanceiro.Tipos.DESPESA,
            valor_reais=Decimal("220.00"),
            data_vencimento=timezone.localdate() - timedelta(days=1),
            status=LancamentoFinanceiro.Status.PENDENTE,
        )

        self.comunicacao_agendada_a = CampanhaComunicacao.objects.create(
            campanha=self.campanha_a,
            nome="Comunicacao A",
            assunto="Assunto A",
            conteudo="Conteudo A",
            canal=CanalComunicacao.WHATSAPP,
            data_envio=timezone.now() + timedelta(hours=4),
            responsavel=self.usuario_a,
            status=CampanhaComunicacao.Status.AGENDADA,
            quantidade_programada=12,
        )
        CampanhaComunicacao.objects.create(
            campanha=self.campanha_a,
            nome="Comunicacao atrasada A",
            assunto="Assunto atraso",
            conteudo="Conteudo atraso",
            canal=CanalComunicacao.WHATSAPP,
            data_envio=timezone.now() - timedelta(hours=2),
            responsavel=self.usuario_a,
            status=CampanhaComunicacao.Status.AGENDADA,
            quantidade_programada=4,
        )
        CampanhaComunicacao.objects.create(
            campanha=self.campanha_b,
            nome="Comunicacao B",
            assunto="Assunto B",
            conteudo="Conteudo B",
            canal=CanalComunicacao.WHATSAPP,
            data_envio=timezone.now() + timedelta(hours=6),
            responsavel=self.usuario_b,
            status=CampanhaComunicacao.Status.AGENDADA,
            quantidade_programada=20,
        )

        self.alerta_usuario_a = NotificacaoInterna.objects.create(
            campanha=self.campanha_a,
            usuario_destinatario=self.usuario_a,
            titulo="Agenda com conflito",
            mensagem="Ha um compromisso que precisa de remanejamento.",
            categoria=NotificacaoInterna.Categorias.AGENDA,
            url_destino=reverse("agenda:home"),
        )
        alerta_lido = NotificacaoInterna.objects.create(
            campanha=self.campanha_a,
            usuario_destinatario=self.usuario_a,
            titulo="Financeiro conciliado",
            mensagem="Um alerta antigo foi resolvido.",
            categoria=NotificacaoInterna.Categorias.FINANCEIRO,
        )
        alerta_lido.marcar_como_lida()
        NotificacaoInterna.objects.create(
            campanha=self.campanha_a,
            usuario_destinatario=self.usuario_a_aux,
            titulo="Alerta de outro usuario",
            mensagem="Nao deve aparecer no dashboard do usuario A.",
            categoria=NotificacaoInterna.Categorias.LGPD,
        )
        NotificacaoInterna.objects.create(
            campanha=self.campanha_b,
            usuario_destinatario=self.usuario_b,
            titulo="Equipe em atraso",
            mensagem="Alerta da campanha B.",
            categoria=NotificacaoInterna.Categorias.EQUIPE,
        )

        RegistroAuditoria.objects.create(
            campanha=self.campanha_a,
            acao="criar",
            modelo="ContatoCRM",
            objeto_id=str(self.contato_a1.pk),
            resumo="Contato A1 criado",
            usuario=self.usuario_a,
        )
        RegistroAuditoria.objects.create(
            campanha=self.campanha_b,
            acao="criar",
            modelo="ContatoCRM",
            objeto_id=str(self.contato_b1.pk),
            resumo="Contato B1 criado",
            usuario=self.usuario_b,
        )

    def test_dashboard_isola_metricas_por_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("dashboard:home"), {"periodo": "30d"})
        self.assertEqual(resposta.status_code, 200)
        indicadores = resposta.context["indicadores"]
        self.assertEqual(indicadores["contatos"], 3)
        self.assertEqual(indicadores["apoiadores"], 1)
        self.assertEqual(indicadores["liderancas"], 1)
        self.assertEqual(indicadores["voluntarios"], 1)
        self.assertEqual(indicadores["compromissos_proximos"], 1)
        self.assertEqual(indicadores["tarefas_atrasadas"], 1)
        self.assertEqual(indicadores["saldo_financeiro"], Decimal("580.00"))
        self.assertEqual(indicadores["alertas_nao_lidos"], 1)
        self.assertEqual(indicadores["comunicacoes_agendadas"], 2)
        self.assertEqual(indicadores["contas_vencidas"], 1)
        self.assertEqual(resposta.context["resumo_operacional"]["comunicacoes_atrasadas"], 1)
        self.assertEqual(resposta.context["resumo_operacional"]["taxa_entrega"], 0.0)

        rotulos_status = {item["rotulo"] for item in resposta.context["grafico_status"]}
        self.assertIn("Apoiador", rotulos_status)
        self.assertIn("Novo contato", rotulos_status)
        self.assertNotIn("Lideranca", rotulos_status)
        self.assertEqual(len(resposta.context["notificacoes_dashboard"]), 2)
        self.assertEqual(len(resposta.context["comunicacoes_programadas"]), 2)
        self.assertEqual(len(resposta.context["contas_vencidas_lista"]), 1)
        self.assertEqual(resposta.context["contas_vencidas_lista"][0], self.conta_vencida_a)

    def test_dashboard_filtra_por_cidade(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("dashboard:home"), {"periodo": "30d", "cidade": "Fortaleza"})
        self.assertEqual(resposta.status_code, 200)
        indicadores = resposta.context["indicadores"]
        self.assertEqual(indicadores["contatos"], 2)
        cidades = resposta.context["grafico_cidades"]
        self.assertEqual(len(cidades), 1)
        self.assertEqual(cidades[0]["rotulo"], "Fortaleza")
        bairros = resposta.context["grafico_bairros"]
        self.assertEqual(len(bairros), 1)
        self.assertEqual(bairros[0]["rotulo"], "Centro")
        self.assertEqual(resposta.context["mapa_cadastros"][0]["total"], 2)

    def test_dashboard_staff_pode_filtrar_por_campanha(self):
        self.client.force_login(self.usuario_staff)
        resposta = self.client.get(reverse("dashboard:home"), {"periodo": "30d", "campanha": str(self.campanha_a.pk)})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["campanha_atual"], self.campanha_a)
        self.assertEqual(resposta.context["indicadores"]["contatos"], 3)
        self.assertEqual(resposta.context["indicadores"]["comunicacoes_agendadas"], 2)
        self.assertEqual(resposta.context["indicadores"]["contas_vencidas"], 1)
        self.assertEqual(len(resposta.context["campanhas_disponiveis"]), 2)

    def test_dashboard_alertas_sao_isolados_por_usuario(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("dashboard:home"), {"periodo": "30d"})
        self.assertEqual(resposta.status_code, 200)
        titulos = [item.titulo for item in resposta.context["notificacoes_dashboard"]]
        self.assertIn("Agenda com conflito", titulos)
        self.assertIn("Financeiro conciliado", titulos)
        self.assertNotIn("Alerta de outro usuario", titulos)
        categorias = {item["rotulo"] for item in resposta.context["grafico_alertas_categoria"]}
        self.assertEqual(categorias, {"Agenda"})
