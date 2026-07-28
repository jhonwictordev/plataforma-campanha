from django.contrib import admin

from .models import CampanhaComunicacao, ListaBloqueio, ModeloMensagem


admin.site.register(ModeloMensagem)
admin.site.register(ListaBloqueio)
admin.site.register(CampanhaComunicacao)
