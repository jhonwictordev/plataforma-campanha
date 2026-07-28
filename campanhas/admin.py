from django.contrib import admin

from .models import Campanha


@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ("nome_campanha", "nome_candidato", "cargo_disputado", "municipio", "situacao")
    list_filter = ("cargo_disputado", "situacao", "estado")
    search_fields = ("nome_campanha", "nome_candidato", "municipio", "partido")
