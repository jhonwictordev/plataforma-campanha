from django.urls import path

from .views import ContatoCRMCreateView, ContatoCRMDetailView, ContatoCRMUpdateView, EleitoresHomeView

app_name = "eleitores"

urlpatterns = [
    path("", EleitoresHomeView.as_view(), name="home"),
    path("novo/", ContatoCRMCreateView.as_view(), name="novo"),
    path("<uuid:pk>/", ContatoCRMDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", ContatoCRMUpdateView.as_view(), name="editar"),
]
