from django.urls import path

from .views import MapaEleitoralHomeView

app_name = "mapa_eleitoral"

urlpatterns = [
    path("", MapaEleitoralHomeView.as_view(), name="home"),
]
