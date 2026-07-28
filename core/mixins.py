from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin

from .permissions import filtrar_queryset_por_usuario, usuario_tem_nivel


class MensagemSucessoMixin:
    mensagem_sucesso = "Operação realizada com sucesso."

    def form_valid(self, form):
        messages.success(self.request, self.mensagem_sucesso)
        return super().form_valid(form)


class NivelAcessoMixin(UserPassesTestMixin):
    niveis_permitidos: tuple[str, ...] = ()
    exige_campanha = True
    mensagem_permissao_negada = "Você não possui permissão para acessar esta área."

    def test_func(self):
        usuario = self.request.user
        if not getattr(usuario, "is_authenticated", False):
            return False
        if (
            self.exige_campanha
            and not (usuario.is_superuser or getattr(usuario, "is_staff", False))
            and not getattr(usuario, "campanha_id", None)
        ):
            return False
        return usuario_tem_nivel(usuario, self.niveis_permitidos)


class FiltroCampanhaMixin:
    campo_campanha = "campanha_id"
    exigir_campanha = True

    def get_queryset(self):
        queryset = super().get_queryset()
        return filtrar_queryset_por_usuario(
            queryset=queryset,
            usuario=self.request.user,
            campo_campanha=self.campo_campanha,
            exigir_campanha=self.exigir_campanha,
        )
