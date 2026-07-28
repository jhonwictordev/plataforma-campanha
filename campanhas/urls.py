from django.urls import path

from .views import CampanhaCreateView, CampanhaListView

app_name = "campanhas"

urlpatterns = [
    path("", CampanhaListView.as_view(), name="lista"),
    path("nova/", CampanhaCreateView.as_view(), name="nova"),
]
