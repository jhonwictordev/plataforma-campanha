from django.urls import path

from .views import HealthcheckView, ProntidaoView

app_name = "core"

urlpatterns = [
    path("saude/", HealthcheckView.as_view(), name="saude"),
    path("saude/prontidao/", ProntidaoView.as_view(), name="saude-prontidao"),
]
