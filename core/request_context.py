from threading import local

_contexto_requisicao = local()


def definir_requisicao_atual(request) -> None:
    _contexto_requisicao.request = request


def limpar_requisicao_atual() -> None:
    if hasattr(_contexto_requisicao, "request"):
        delattr(_contexto_requisicao, "request")


def obter_requisicao_atual():
    return getattr(_contexto_requisicao, "request", None)


def obter_usuario_atual():
    request = obter_requisicao_atual()
    usuario = getattr(request, "user", None)
    if getattr(usuario, "is_authenticated", False):
        return usuario
    return None


def obter_ip_atual() -> str | None:
    request = obter_requisicao_atual()
    if request is None:
        return None
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
