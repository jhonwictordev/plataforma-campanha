from django.contrib import admin

from .models import ContatoCRM, InteracaoContato, TarefaContato


@admin.register(ContatoCRM)
class ContatoCRMAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "telefone", "cidade", "status_funil", "consentimento_comunicacao")
    list_filter = ("status_funil", "cidade", "origem_contato", "campanha")
    search_fields = ("nome_completo", "telefone", "email")


admin.site.register(InteracaoContato)
admin.site.register(TarefaContato)
