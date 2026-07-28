from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import FormularioPerfilUsuario
from .models import Usuario


class PerfilUsuarioView(LoginRequiredMixin, UpdateView):
    model = Usuario
    form_class = FormularioPerfilUsuario
    template_name = "usuarios/perfil.html"
    success_url = reverse_lazy("usuarios:perfil")

    def get_object(self, queryset=None):
        return self.request.user
