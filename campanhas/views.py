from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from core.mixins import MensagemSucessoMixin

from .forms import FormularioCampanha
from .models import Campanha


class GestaoCampanhaMixin(UserPassesTestMixin):
    def test_func(self):
        usuario = self.request.user
        return usuario.is_superuser or usuario.nivel_acesso in {
            "administrador",
            "coordenador_geral",
        }


class CampanhaListView(LoginRequiredMixin, ListView):
    model = Campanha
    template_name = "campanhas/lista.html"
    context_object_name = "campanhas"

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser or usuario.is_staff:
            return Campanha.objects.all()
        if usuario.campanha_id:
            return Campanha.objects.filter(id=usuario.campanha_id)
        return Campanha.objects.none()


class CampanhaCreateView(LoginRequiredMixin, GestaoCampanhaMixin, MensagemSucessoMixin, CreateView):
    model = Campanha
    form_class = FormularioCampanha
    template_name = "campanhas/formulario.html"
    success_url = reverse_lazy("campanhas:lista")
    mensagem_sucesso = "Campanha cadastrada com sucesso."
