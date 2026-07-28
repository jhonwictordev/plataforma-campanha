from django.conf import settings
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from core.celery_schedule import ROTINAS_CELERY


class Command(BaseCommand):
    help = "Cria ou atualiza as rotinas padrao do django-celery-beat para a plataforma."

    def add_arguments(self, parser):
        parser.add_argument(
            "--desativar-ausentes",
            action="store_true",
            help="Desativa tarefas da plataforma que nao estao mais presentes na configuracao padrao.",
        )

    def handle(self, *args, **options):
        nomes_ativos = set()
        criadas = 0
        atualizadas = 0

        for rotina in ROTINAS_CELERY:
            nomes_ativos.add(rotina["nome"])
            defaults = {
                "task": rotina["task"],
                "enabled": True,
                "kwargs": "{}",
                "args": "[]",
            }

            if rotina["tipo"] == "interval":
                intervalo, _ = IntervalSchedule.objects.get_or_create(
                    every=rotina["every"],
                    period=rotina["period"],
                )
                defaults.update({"interval": intervalo, "crontab": None})
            else:
                crontab, _ = CrontabSchedule.objects.get_or_create(
                    minute=rotina["minute"],
                    hour=rotina["hour"],
                    day_of_week=rotina.get("day_of_week", "*"),
                    day_of_month=rotina.get("day_of_month", "*"),
                    month_of_year=rotina.get("month_of_year", "*"),
                    timezone=settings.TIME_ZONE,
                )
                defaults.update({"crontab": crontab, "interval": None})

            tarefa, criada = PeriodicTask.objects.update_or_create(
                name=rotina["nome"],
                defaults=defaults,
            )
            criadas += 1 if criada else 0
            atualizadas += 0 if criada else 1
            self.stdout.write(f"- {tarefa.name}")

        if options["desativar_ausentes"]:
            desativadas = PeriodicTask.objects.filter(name__startswith="Plataforma - ").exclude(name__in=nomes_ativos)
            for tarefa in desativadas:
                tarefa.enabled = False
                tarefa.save(update_fields=["enabled", "date_changed"])
            if desativadas.exists():
                self.stdout.write(self.style.WARNING(f"Tarefas desativadas: {desativadas.count()}"))

        self.stdout.write(self.style.SUCCESS(f"Rotinas sincronizadas. Criadas: {criadas}. Atualizadas: {atualizadas}."))
