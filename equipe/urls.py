from django.urls import path

from .views import EquipeHomeView

app_name = "equipe"

urlpatterns = [
    path("", EquipeHomeView.as_view(), name="home"),
]
