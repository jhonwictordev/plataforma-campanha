from django.urls import path

from .views import (
    ContatoCRMCreateView,
    ContatoCRMDetailView,
    ContatoCRMExportarView,
    ContatoCRMImportarView,
    ContatoCRMKanbanView,
    ContatoCRMUpdateView,
    EleitoresHomeView,
    InteracaoContatoCreateView,
    InteracaoContatoUpdateView,
    TarefaContatoCreateView,
    TarefaContatoUpdateView,
)

app_name = "eleitores"

urlpatterns = [
    path("", EleitoresHomeView.as_view(), name="home"),
    path("kanban/", ContatoCRMKanbanView.as_view(), name="kanban"),
    path("importar/", ContatoCRMImportarView.as_view(), name="importar"),
    path("exportar/", ContatoCRMExportarView.as_view(), name="exportar"),
    path("novo/", ContatoCRMCreateView.as_view(), name="novo"),
    path("<uuid:contato_pk>/interacoes/nova/", InteracaoContatoCreateView.as_view(), name="interacao_nova"),
    path("interacoes/<uuid:pk>/editar/", InteracaoContatoUpdateView.as_view(), name="interacao_editar"),
    path("<uuid:contato_pk>/tarefas/nova/", TarefaContatoCreateView.as_view(), name="tarefa_nova"),
    path("tarefas/<uuid:pk>/editar/", TarefaContatoUpdateView.as_view(), name="tarefa_editar"),
    path("<uuid:pk>/", ContatoCRMDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", ContatoCRMUpdateView.as_view(), name="editar"),
]
