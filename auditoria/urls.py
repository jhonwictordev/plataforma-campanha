from django.urls import path

from .views import AuditoriaHomeView

app_name = "auditoria"

urlpatterns = [
    path("", AuditoriaHomeView.as_view(), name="home"),
]
