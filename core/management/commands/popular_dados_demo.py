from django.core.management.base import BaseCommand

from core.demo_seed import DemoSeedOptions, DemoSeedService


class Command(BaseCommand):
    help = "Popula o sistema com dados ficticios de demonstracao, sem usar informacoes reais."

    def add_arguments(self, parser):
        parser.add_argument("--campanhas", type=int, default=2)
        parser.add_argument("--contatos", type=int, default=12)
        parser.add_argument("--liderancas", type=int, default=6)
        parser.add_argument("--eventos", type=int, default=4)
        parser.add_argument("--integrantes", type=int, default=5)
        parser.add_argument("--tarefas", type=int, default=8)
        parser.add_argument("--metas", type=int, default=4)
        parser.add_argument("--lancamentos", type=int, default=8)
        parser.add_argument("--comunicacoes", type=int, default=2)
        parser.add_argument("--seed", type=int, default=2026)
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Remove os registros demo existentes antes de recriar a base ficticia.",
        )

    def handle(self, *args, **options):
        opcoes = DemoSeedOptions(
            campanhas=options["campanhas"],
            contatos=options["contatos"],
            liderancas=options["liderancas"],
            eventos=options["eventos"],
            integrantes=options["integrantes"],
            tarefas=options["tarefas"],
            metas=options["metas"],
            lancamentos=options["lancamentos"],
            comunicacoes=options["comunicacoes"],
            seed=options["seed"],
            limpar=options["limpar"],
        )
        resumo = DemoSeedService(opcoes).executar()

        self.stdout.write(self.style.SUCCESS("Dados demo atualizados com sucesso."))
        for chave, valor in resumo.items():
            self.stdout.write(f"- {chave}: {valor}")
        self.stdout.write("Senha padrao dos usuarios demo: Demo2026!")
