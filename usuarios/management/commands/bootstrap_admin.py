import os

from django.core.management.base import BaseCommand
from django.utils import timezone

from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Cria um administrador inicial a partir de variaveis de ambiente privadas."

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip().lower()
        senha = os.getenv("DJANGO_SUPERUSER_PASSWORD", "").strip()
        nome = os.getenv("DJANGO_SUPERUSER_NOME_COMPLETO", "Administrador").strip() or "Administrador"
        rotacionar = os.getenv("DJANGO_SUPERUSER_ROTATE_PASSWORD", "").strip().lower() in {
            "1",
            "true",
            "t",
            "sim",
            "yes",
            "y",
        }

        if not email or not senha:
            self.stdout.write("Bootstrap admin ignorado: DJANGO_SUPERUSER_EMAIL/PASSWORD nao definidos.")
            return

        usuario, criado = Usuario.objects.get_or_create(
            email=email,
            defaults={
                "nome_completo": nome,
                "nome_exibicao": nome.split(" ")[0],
                "nivel_acesso": Usuario.NiveisAcesso.ADMINISTRADOR,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "consentimento_privacidade": True,
                "data_consentimento_privacidade": timezone.now(),
            },
        )

        campos_atualizados = []
        for campo, valor in {
            "nome_completo": nome,
            "nivel_acesso": Usuario.NiveisAcesso.ADMINISTRADOR,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "consentimento_privacidade": True,
        }.items():
            if getattr(usuario, campo) != valor:
                setattr(usuario, campo, valor)
                campos_atualizados.append(campo)

        if not usuario.data_consentimento_privacidade:
            usuario.data_consentimento_privacidade = timezone.now()
            campos_atualizados.append("data_consentimento_privacidade")

        if criado or rotacionar or not usuario.has_usable_password():
            usuario.set_password(senha)
            campos_atualizados.append("password")

        if criado:
            usuario.save()
            self.stdout.write(self.style.SUCCESS(f"Administrador inicial criado: {email}"))
            return

        if campos_atualizados:
            usuario.save(update_fields=sorted(set(campos_atualizados + ["atualizado_em"])))
            self.stdout.write(self.style.SUCCESS(f"Administrador inicial atualizado: {email}"))
            return

        self.stdout.write(f"Administrador inicial ja estava configurado: {email}")
