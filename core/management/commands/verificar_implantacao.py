import json

from django.core.management.base import BaseCommand, CommandError

from core.production_checks import avaliar_implantacao


class Command(BaseCommand):
    help = "Executa um preflight de producao para validar seguranca, dependencias e operacao antes do deploy."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="saida_json",
            help="Renderiza o resultado em JSON.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Falha tambem quando houver avisos pendentes.",
        )

    def handle(self, *args, **options):
        payload = avaliar_implantacao()
        saida_json = options["saida_json"]
        strict = options["strict"]

        if saida_json:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            destaque = getattr(self.style, "NOTICE", lambda texto: texto)
            self.stdout.write(destaque("Preflight de implantacao"))
            for check in payload["checks"]:
                estilo = self.style.SUCCESS
                if check["status"] == "erro":
                    estilo = self.style.ERROR
                elif check["status"] == "aviso":
                    estilo = self.style.WARNING
                elif check["status"] == "ignorado":
                    estilo = getattr(self.style, "NOTICE", self.style.SUCCESS)
                self.stdout.write(estilo(f"[{check['status'].upper()}] {check['chave']}: {check['detalhe']}"))
            resumo = payload["resumo"]
            self.stdout.write(
                f"Resumo: {resumo['ok']} ok, {resumo['avisos']} aviso(s), {resumo['erros']} erro(s), {resumo['ignorados']} ignorado(s)."
            )

        if payload["resumo"]["erros"]:
            raise CommandError("Foram encontrados erros bloqueantes para implantacao.")
        if strict and payload["resumo"]["avisos"]:
            raise CommandError("A implantacao estrita falhou porque ainda existem avisos pendentes.")
