from django.urls import path

from .views import LiderancasHomeView

app_name = "liderancas"

urlpatterns = [
    path("", LiderancasHomeView.as_view(), name="home"),
]
