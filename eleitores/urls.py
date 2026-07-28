from django.urls import path

from .views import (
    ContatoCRMCreateView,
    ContatoCRMDetailView,
    ContatoCRMExportarView,
    ContatoCRMImportarView,
    ContatoCRMKanbanView,
    ContatoCRMUpdateView,
    EleitoresHomeView,
)

app_name = "eleitores"

urlpatterns = [
    path("", EleitoresHomeView.as_view(), name="home"),
    path("kanban/", ContatoCRMKanbanView.as_view(), name="kanban"),
    path("importar/", ContatoCRMImportarView.as_view(), name="importar"),
    path("exportar/", ContatoCRMExportarView.as_view(), name="exportar"),
    path("novo/", ContatoCRMCreateView.as_view(), name="novo"),
    path("<uuid:pk>/", ContatoCRMDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", ContatoCRMUpdateView.as_view(), name="editar"),
]
