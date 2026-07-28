from django.urls import path

from .views import (
    ComentarioTarefaEquipeCreateView,
    ComentarioTarefaEquipeUpdateView,
    EquipeHomeView,
    IntegranteEquipeCreateView,
    IntegranteEquipeDetailView,
    IntegranteEquipeUpdateView,
    TarefaEquipeCreateView,
    TarefaEquipeDetailView,
    TarefaEquipeUpdateView,
)

app_name = "equipe"

urlpatterns = [
    path("", EquipeHomeView.as_view(), name="home"),
    path("integrantes/novo/", IntegranteEquipeCreateView.as_view(), name="integrante_novo"),
    path("integrantes/<uuid:pk>/", IntegranteEquipeDetailView.as_view(), name="integrante_detalhe"),
    path("integrantes/<uuid:pk>/editar/", IntegranteEquipeUpdateView.as_view(), name="integrante_editar"),
    path("tarefas/nova/", TarefaEquipeCreateView.as_view(), name="tarefa_nova"),
    path("tarefas/<uuid:tarefa_pk>/comentarios/novo/", ComentarioTarefaEquipeCreateView.as_view(), name="comentario_novo"),
    path("tarefas/comentarios/<uuid:pk>/editar/", ComentarioTarefaEquipeUpdateView.as_view(), name="comentario_editar"),
    path("tarefas/<uuid:pk>/", TarefaEquipeDetailView.as_view(), name="tarefa_detalhe"),
    path("tarefas/<uuid:pk>/editar/", TarefaEquipeUpdateView.as_view(), name="tarefa_editar"),
]
