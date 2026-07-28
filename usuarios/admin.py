from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import FormularioAlteracaoUsuario, FormularioCriacaoUsuario
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = FormularioCriacaoUsuario
    form = FormularioAlteracaoUsuario
    model = Usuario
    ordering = ("email",)
    list_display = ("email", "nome_completo", "nivel_acesso", "campanha", "is_active")
    list_filter = ("nivel_acesso", "campanha", "is_active", "is_staff")
    search_fields = ("email", "nome_completo", "telefone")
    fieldsets = (
        (
            "Acesso",
            {
                "fields": (
                    "email",
                    "password",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Dados pessoais",
            {"fields": ("nome_completo", "nome_exibicao", "telefone", "foto_perfil")},
        ),
        (
            "Campanha e perfil",
            {"fields": ("campanha", "nivel_acesso", "tema_escuro")},
        ),
        (
            "Segurança",
            {
                "fields": (
                    "ultimo_login",
                    "ultimo_acesso_registrado",
                    "ultimo_ip",
                    "tentativas_falhas",
                    "dois_fatores_habilitado",
                    "consentimento_privacidade",
                    "data_consentimento_privacidade",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nome_completo",
                    "campanha",
                    "nivel_acesso",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )
