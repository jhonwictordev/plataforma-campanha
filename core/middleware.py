from datetime import timedelta

from django.utils import timezone


class UltimoAcessoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        usuario = getattr(request, "user", None)
        if getattr(usuario, "is_authenticated", False):
            agora = timezone.now()
            ultimo_acesso = getattr(usuario, "ultimo_acesso_registrado", None)
            if ultimo_acesso is None or agora - ultimo_acesso > timedelta(seconds=60):
                type(usuario).objects.filter(pk=usuario.pk).update(
                    ultimo_acesso_registrado=agora,
                    ultimo_ip=self._obter_ip(request),
                )
        return response

    @staticmethod
    def _obter_ip(request) -> str | None:
        encaminhado = request.META.get("HTTP_X_FORWARDED_FOR")
        if encaminhado:
            return encaminhado.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
