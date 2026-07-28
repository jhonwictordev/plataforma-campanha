from django.contrib import admin

from .models import CampanhaComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem


admin.site.register(ModeloMensagem)
admin.site.register(ListaBloqueio)
admin.site.register(CampanhaComunicacao)
admin.site.register(EnvioComunicacao)
