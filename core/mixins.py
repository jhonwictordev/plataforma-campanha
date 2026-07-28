from django.contrib import messages


class MensagemSucessoMixin:
    mensagem_sucesso = "Operação realizada com sucesso."

    def form_valid(self, form):
        messages.success(self.request, self.mensagem_sucesso)
        return super().form_valid(form)


class FiltroCampanhaMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        usuario = self.request.user
        if usuario.is_superuser or getattr(usuario, "is_staff", False):
            return queryset
        if hasattr(queryset.model, "campanha_id") and getattr(usuario, "campanha_id", None):
            return queryset.filter(campanha_id=usuario.campanha_id)
        return queryset.none()
