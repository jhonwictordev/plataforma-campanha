from django.contrib import admin

from .models import LogSeguranca, RegistroAuditoria


admin.site.register(RegistroAuditoria)
admin.site.register(LogSeguranca)
