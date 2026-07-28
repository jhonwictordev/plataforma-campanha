from django.urls import path

from .views import MetaCampanhaCreateView, MetaCampanhaDetailView, MetaCampanhaUpdateView, MetasHomeView

app_name = "metas"

urlpatterns = [
    path("", MetasHomeView.as_view(), name="home"),
    path("nova/", MetaCampanhaCreateView.as_view(), name="nova"),
    path("<uuid:pk>/", MetaCampanhaDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", MetaCampanhaUpdateView.as_view(), name="editar"),
]
