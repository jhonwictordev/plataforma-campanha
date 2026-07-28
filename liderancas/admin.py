from django.contrib import admin

from .models import InteracaoLideranca, Lideranca


@admin.register(Lideranca)
class LiderancaAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "tipo_lideranca", "cidade", "situacao_relacionamento", "responsavel_contato")
    list_filter = ("tipo_lideranca", "situacao_relacionamento", "cidade", "campanha")
    search_fields = ("nome_completo", "telefone", "email", "nome_conhecido")


@admin.register(InteracaoLideranca)
class InteracaoLiderancaAdmin(admin.ModelAdmin):
    list_display = ("lideranca", "tipo", "data_hora", "responsavel")
    list_filter = ("tipo", "campanha")
