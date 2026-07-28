from django.contrib import admin

from .models import CampanhaComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem, NotificacaoInterna


admin.site.register(ModeloMensagem)
admin.site.register(ListaBloqueio)
admin.site.register(CampanhaComunicacao)
admin.site.register(EnvioComunicacao)
admin.site.register(NotificacaoInterna)
