from django.contrib import admin

from .models import ComentarioTarefaEquipe, IntegranteEquipe, TarefaEquipe


admin.site.register(IntegranteEquipe)
admin.site.register(TarefaEquipe)
admin.site.register(ComentarioTarefaEquipe)
