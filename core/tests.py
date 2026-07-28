import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.utils import timezone
from django.test import TestCase
from django_celery_beat.models import PeriodicTask

from agenda.models import EventoAgenda
from auditoria.models import PoliticaRetencaoDados, SolicitacaoTitularDados
from campanhas.models import Campanha
from comunicacao.models import CampanhaComunicacao, NotificacaoInterna
from core.tasks import (
    gerar_alertas_financeiros,
    gerar_alertas_lgpd,
    gerar_alertas_retencao,
    gerar_alertas_tarefas,
    gerar_lembretes_agenda,
    sinalizar_campanhas_agendadas,
)
from core.management.commands.backup_banco import Command as BackupBancoCommand
from equipe.models import IntegranteEquipe, TarefaEquipe
from eleitores.models import ContatoCRM
from financeiro.models import LancamentoFinanceiro
from liderancas.models import Lideranca
from usuarios.models import Usuario


class ComandosOperacionaisTestCase(TestCase):
    def executar_comando(self, nome, **kwargs):
        saida = StringIO()
        call_command(nome, stdout=saida, **kwargs)
        return saida.getvalue()

    def test_popular_dados_demo_cria_ecossistema_basico(self):
        self.executar_comando(
            "popular_dados_demo",
            campanhas=1,
            contatos=3,
            liderancas=2,
            eventos=1,
            integrantes=2,
            tarefas=2,
            metas=1,
            lancamentos=2,
            comunicacoes=1,
            seed=2026,
        )

        self.assertEqual(Campanha.objects.filter(nome_campanha__startswith="DEMO ").count(), 1)
        self.assertTrue(Usuario.objects.filter(email="admin@demo.plataformacampanha.local").exists())
        self.assertEqual(Lideranca.objects.count(), 2)
        self.assertEqual(ContatoCRM.objects.count(), 3)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 2)
        self.assertEqual(CampanhaComunicacao.objects.count(), 1)
        self.assertTrue(PoliticaRetencaoDados.objects.exists())
        self.assertTrue(SolicitacaoTitularDados.objects.exists())

    def test_popular_dados_demo_e_idempotente_para_registros_principais(self):
        for _ in range(2):
            self.executar_comando(
                "popular_dados_demo",
                campanhas=1,
                contatos=2,
                liderancas=2,
                eventos=1,
                integrantes=1,
                tarefas=1,
                metas=1,
                lancamentos=1,
                comunicacoes=1,
                seed=2026,
            )

        self.assertEqual(Campanha.objects.filter(nome_campanha__startswith="DEMO ").count(), 1)
        self.assertEqual(ContatoCRM.objects.count(), 2)
        self.assertEqual(Lideranca.objects.count(), 2)
        self.assertEqual(CampanhaComunicacao.objects.count(), 1)

    def test_backup_banco_json_gera_arquivo(self):
        self.executar_comando(
            "popular_dados_demo",
            campanhas=1,
            contatos=1,
            liderancas=1,
            eventos=1,
            comunicacoes=1,
        )

        with tempfile.TemporaryDirectory() as diretorio:
            self.executar_comando("backup_banco", formato="json", destino=diretorio)

            arquivos = list(Path(diretorio).glob("backup_*.json"))
            self.assertEqual(len(arquivos), 1)
            conteudo = arquivos[0].read_text(encoding="utf-8")
            dados = json.loads(conteudo)
            self.assertTrue(any(item["model"] == "campanhas.campanha" for item in dados))

    def test_backup_banco_sql_sem_pg_dump_retorna_erro_claro(self):
        comando = BackupBancoCommand()
        with tempfile.TemporaryDirectory() as diretorio, patch(
            "core.management.commands.backup_banco.shutil.which",
            return_value=None,
        ):
            with self.assertRaises(CommandError):
                comando.handle(formato="sql", destino=diretorio, nome_arquivo="", sobrescrever=False)

    def test_sincronizar_rotinas_celery_cria_periodic_tasks(self):
        self.executar_comando("sincronizar_rotinas_celery")
        self.assertTrue(PeriodicTask.objects.filter(name="Plataforma - Lembretes de agenda", enabled=True).exists())
        self.assertTrue(PeriodicTask.objects.filter(name="Plataforma - Alertas LGPD", enabled=True).exists())


class RotinasCeleryNotificacoesTestCase(TestCase):
    def setUp(self):
        self.agora = timezone.now()
        self.campanha = Campanha.objects.create(
            nome_campanha="Campanha Rotinas",
            nome_candidato="Candidata Rotinas",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="77",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.coordenador = Usuario.objects.create_user(
            email="coord-rotinas@example.com",
            password="senha123",
            nome_completo="Coordenador Rotinas",
            campanha=self.campanha,
            nivel_acesso="coordenador_geral",
        )
        self.financeiro = Usuario.objects.create_user(
            email="financeiro-rotinas@example.com",
            password="senha123",
            nome_completo="Financeiro Rotinas",
            campanha=self.campanha,
            nivel_acesso="financeiro",
        )
        self.participante = Usuario.objects.create_user(
            email="participante-rotinas@example.com",
            password="senha123",
            nome_completo="Participante Rotinas",
            campanha=self.campanha,
            nivel_acesso="mobilizador",
        )
        self.campanha.coordenador_responsavel = self.coordenador
        self.campanha.save(update_fields=["coordenador_responsavel", "atualizado_em"])

        self.contato = ContatoCRM.objects.create(
            campanha=self.campanha,
            nome_completo="Contato Rotinas",
            telefone="85999990001",
            whatsapp="85999990001",
            cidade="Fortaleza",
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
            status_funil=ContatoCRM.EtapasFunil.APOIADOR,
        )
        self.comunicacao = CampanhaComunicacao.objects.create(
            campanha=self.campanha,
            nome="Comunicacao Rotinas",
            assunto="Aviso de agenda",
            conteudo="Conteudo demonstrativo",
            canal="whatsapp",
            data_envio=self.agora - timedelta(minutes=5),
            responsavel=self.coordenador,
            status=CampanhaComunicacao.Status.AGENDADA,
        )
        self.comunicacao.destinatarios.set([self.contato])

        data_evento = timezone.localtime(self.agora + timedelta(hours=2))
        self.evento = EventoAgenda.objects.create(
            campanha=self.campanha,
            titulo="Reuniao de mobilizacao",
            tipo=EventoAgenda.Tipos.REUNIAO,
            data=data_evento.date(),
            horario_inicial=data_evento.time().replace(second=0, microsecond=0),
            horario_final=(data_evento + timedelta(hours=1)).time().replace(second=0, microsecond=0),
            responsavel=self.coordenador,
            status=EventoAgenda.Status.CONFIRMADO,
        )
        self.evento.participantes.set([self.participante])

        self.integrante = IntegranteEquipe.objects.create(
            campanha=self.campanha,
            nome="Integrante Rotinas",
            funcao="Mobilizador",
            departamento="Mobilizacao",
            usuario=self.participante,
        )
        self.tarefa = TarefaEquipe.objects.create(
            campanha=self.campanha,
            titulo="Pendencia de rua",
            responsavel=self.integrante,
            prazo=self.agora - timedelta(hours=1),
            status=TarefaEquipe.Status.A_FAZER,
        )

        self.lancamento = LancamentoFinanceiro.objects.create(
            campanha=self.campanha,
            descricao="Conta de som",
            tipo=LancamentoFinanceiro.Tipos.DESPESA,
            valor_reais="500.00",
            data_vencimento=timezone.localdate() - timedelta(days=1),
            responsavel_lancamento=self.financeiro,
            status=LancamentoFinanceiro.Status.PENDENTE,
        )

        self.solicitacao = SolicitacaoTitularDados.objects.create(
            campanha=self.campanha,
            nome_solicitante="Titular Rotinas",
            tipo_solicitacao=SolicitacaoTitularDados.TiposSolicitacao.ACESSO,
            status=SolicitacaoTitularDados.Status.EM_ANALISE,
            descricao="Solicitacao de acesso aos dados.",
            responsavel_interno=self.coordenador,
            prazo_resposta=timezone.localdate() + timedelta(days=1),
        )
        self.politica = PoliticaRetencaoDados.objects.create(
            campanha=self.campanha,
            nome="Politica CRM",
            tipo_registro=PoliticaRetencaoDados.TiposRegistro.CONTATOS,
            dias_retencao=1,
            dias_ate_anonimizacao=1,
            responsavel=self.coordenador,
        )
        self.contato.criado_em = self.agora - timedelta(days=10)
        self.contato.save(update_fields=["criado_em"])

    def test_rotinas_geram_notificacoes_internas(self):
        self.assertEqual(sinalizar_campanhas_agendadas()["campanhas"], 1)
        self.assertEqual(gerar_lembretes_agenda()["eventos"], 1)
        self.assertEqual(gerar_alertas_tarefas()["tarefas"], 1)
        self.assertEqual(gerar_alertas_financeiros()["lancamentos"], 1)
        self.assertEqual(gerar_alertas_lgpd()["solicitacoes"], 1)
        self.assertEqual(gerar_alertas_retencao()["politicas"], 1)
        self.assertGreaterEqual(NotificacaoInterna.objects.count(), 6)

    def test_rotinas_sao_idempotentes_por_chave_unica(self):
        sinalizar_campanhas_agendadas()
        sinalizar_campanhas_agendadas()
        self.assertEqual(
            NotificacaoInterna.objects.filter(origem_modelo="CampanhaComunicacao").count(),
            1,
        )
