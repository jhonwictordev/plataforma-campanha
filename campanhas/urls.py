from django.urls import path

from .views import (
    CampanhaCreateView,
    CampanhaDeleteView,
    CampanhaDetailView,
    CampanhaListView,
    CampanhaUpdateView,
)

app_name = "campanhas"

urlpatterns = [
    path("", CampanhaListView.as_view(), name="lista"),
    path("nova/", CampanhaCreateView.as_view(), name="nova"),
    path("<uuid:pk>/", CampanhaDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", CampanhaUpdateView.as_view(), name="editar"),
    path("<uuid:pk>/excluir/", CampanhaDeleteView.as_view(), name="excluir"),
]
