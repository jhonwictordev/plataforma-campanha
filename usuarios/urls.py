from django.urls import path

from .views import PerfilUsuarioView

app_name = "usuarios"

urlpatterns = [
    path("perfil/", PerfilUsuarioView.as_view(), name="perfil"),
]
