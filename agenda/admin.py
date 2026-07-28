from django.contrib import admin

from .models import EventoAgenda


@admin.register(EventoAgenda)
class EventoAgendaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "data", "responsavel", "status")
    list_filter = ("tipo", "status", "campanha")
    search_fields = ("titulo", "descricao", "endereco")
