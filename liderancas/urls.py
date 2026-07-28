from django.urls import path

from .views import LiderancaCreateView, LiderancaDetailView, LiderancaUpdateView, LiderancasHomeView

app_name = "liderancas"

urlpatterns = [
    path("", LiderancasHomeView.as_view(), name="home"),
    path("novo/", LiderancaCreateView.as_view(), name="novo"),
    path("<uuid:pk>/", LiderancaDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", LiderancaUpdateView.as_view(), name="editar"),
]
