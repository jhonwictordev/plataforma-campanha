from django.contrib import admin

from .models import LogSeguranca, PoliticaRetencaoDados, RegistroAuditoria, SolicitacaoTitularDados


admin.site.register(RegistroAuditoria)
admin.site.register(LogSeguranca)
admin.site.register(PoliticaRetencaoDados)
admin.site.register(SolicitacaoTitularDados)
