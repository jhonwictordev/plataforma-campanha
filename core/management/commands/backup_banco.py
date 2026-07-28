import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Gera backup operacional do banco em JSON ou SQL, sem expor credenciais no repositorio."

    def add_arguments(self, parser):
        parser.add_argument(
            "--formato",
            choices=("json", "sql"),
            default="json",
            help="Formato do backup. JSON usa dumpdata; SQL usa pg_dump para PostgreSQL.",
        )
        parser.add_argument(
            "--destino",
            default="",
            help="Diretorio de destino. Padrao: <BASE_DIR>/backups",
        )
        parser.add_argument(
            "--nome-arquivo",
            default="",
            help="Nome final do arquivo. Quando omitido, usa timestamp automatico.",
        )
        parser.add_argument(
            "--sobrescrever",
            action="store_true",
            help="Permite sobrescrever arquivo existente no destino.",
        )

    def handle(self, *args, **options):
        formato = options["formato"]
        diretorio = Path(options["destino"] or settings.BASE_DIR / "backups")
        diretorio.mkdir(parents=True, exist_ok=True)

        arquivo = diretorio / self._nome_arquivo(formato, options["nome_arquivo"])
        if arquivo.exists() and not options["sobrescrever"]:
            raise CommandError(f"O arquivo {arquivo} ja existe. Use --sobrescrever para substituir.")

        if formato == "json":
            self._gerar_backup_json(arquivo)
        else:
            self._gerar_backup_sql(arquivo)

        self.stdout.write(self.style.SUCCESS(f"Backup concluido em {arquivo}"))

    def _nome_arquivo(self, formato: str, nome_personalizado: str) -> str:
        if nome_personalizado:
            return nome_personalizado
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}.{formato}"

    def _gerar_backup_json(self, arquivo: Path):
        with arquivo.open("w", encoding="utf-8") as handle:
            call_command(
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
                "--indent",
                "2",
                stdout=handle,
            )

    def _gerar_backup_sql(self, arquivo: Path):
        config = settings.DATABASES["default"]
        if "postgresql" not in config["ENGINE"]:
            raise CommandError("O backup SQL suporta apenas PostgreSQL. Use --formato json neste ambiente.")

        pg_dump = os.getenv("PG_DUMP_BIN") or shutil.which("pg_dump")
        if not pg_dump:
            raise CommandError(
                "pg_dump nao encontrado. Instale o cliente PostgreSQL ou defina PG_DUMP_BIN com o caminho completo."
            )

        comando = [
            pg_dump,
            "--no-owner",
            "--no-privileges",
            "--format=plain",
            "--host",
            str(config["HOST"]),
            "--port",
            str(config["PORT"]),
            "--username",
            str(config["USER"]),
            "--file",
            str(arquivo),
            str(config["NAME"]),
        ]
        ambiente = os.environ.copy()
        ambiente["PGPASSWORD"] = str(config["PASSWORD"])

        try:
            subprocess.run(
                comando,
                env=ambiente,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            if arquivo.exists():
                arquivo.unlink()
            detalhe = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            raise CommandError(f"Falha ao gerar backup SQL: {detalhe}") from exc
