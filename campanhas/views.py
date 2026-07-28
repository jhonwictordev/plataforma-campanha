from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from core.mixins import MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_COORDENACAO, PAPEIS_TODOS_MODULOS

from .forms import FormularioCampanha
from .models import Campanha


class GestaoCampanhaMixin(NivelAcessoMixin):
    niveis_permitidos = PAPEIS_COORDENACAO
    exige_campanha = False

    def test_func(self):
        return NivelAcessoMixin.test_func(self)


class CampanhaListView(LoginRequiredMixin, NivelAcessoMixin, ListView):
    model = Campanha
    template_name = "campanhas/lista.html"
    context_object_name = "campanhas"
    niveis_permitidos = PAPEIS_TODOS_MODULOS
    exige_campanha = False

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
