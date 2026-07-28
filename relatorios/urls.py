from django.urls import path

from .views import RelatoriosHomeView

app_name = "relatorios"

urlpatterns = [
    path("", RelatoriosHomeView.as_view(), name="home"),
]
