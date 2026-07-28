from django.urls import path

from .views import MetasHomeView

app_name = "metas"

urlpatterns = [
    path("", MetasHomeView.as_view(), name="home"),
]
