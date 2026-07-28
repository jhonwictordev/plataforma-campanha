from django.urls import path

from .views import EleitoresHomeView

app_name = "eleitores"

urlpatterns = [
    path("", EleitoresHomeView.as_view(), name="home"),
]
