from django.urls import path

from .views import FinanceiroHomeView

app_name = "financeiro"

urlpatterns = [
    path("", FinanceiroHomeView.as_view(), name="home"),
]
