from django.urls import path

from .views import AgendaHomeView, EventoAgendaCreateView, EventoAgendaDetailView, EventoAgendaUpdateView

app_name = "agenda"

urlpatterns = [
    path("", AgendaHomeView.as_view(), name="home"),
    path("novo/", EventoAgendaCreateView.as_view(), name="novo"),
    path("<uuid:pk>/", EventoAgendaDetailView.as_view(), name="detalhe"),
    path("<uuid:pk>/editar/", EventoAgendaUpdateView.as_view(), name="editar"),
]
