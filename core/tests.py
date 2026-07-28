import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from auditoria.models import PoliticaRetencaoDados, SolicitacaoTitularDados
from campanhas.models import Campanha
from comunicacao.models import CampanhaComunicacao
from core.management.commands.backup_banco import Command as BackupBancoCommand
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
