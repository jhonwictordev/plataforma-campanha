from django.urls import path

from .views import (
    FiltroFavoritoRelatorioCreateView,
    FiltroFavoritoRelatorioDeleteView,
    RelatorioExcelView,
    RelatorioImpressaoView,
    RelatorioPdfView,
    RelatoriosHomeView,
)

app_name = "relatorios"

urlpatterns = [
    path("", RelatoriosHomeView.as_view(), name="home"),
    path("exportar/excel/", RelatorioExcelView.as_view(), name="exportar_excel"),
    path("exportar/pdf/", RelatorioPdfView.as_view(), name="exportar_pdf"),
    path("imprimir/", RelatorioImpressaoView.as_view(), name="impressao"),
    path("favoritos/salvar/", FiltroFavoritoRelatorioCreateView.as_view(), name="favorito_salvar"),
    path("favoritos/<uuid:pk>/excluir/", FiltroFavoritoRelatorioDeleteView.as_view(), name="favorito_excluir"),
]
