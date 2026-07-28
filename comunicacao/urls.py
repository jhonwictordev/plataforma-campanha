from django.urls import path

from .views import ComunicacaoHomeView

app_name = "comunicacao"

urlpatterns = [
    path("", ComunicacaoHomeView.as_view(), name="home"),
]
