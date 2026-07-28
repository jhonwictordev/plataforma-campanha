def aplicacao_info(request):
    return {
        "nome_aplicacao": "Plataforma de Campanha",
        "tema_escuro_habilitado": getattr(request.user, "tema_escuro", False)
        if getattr(request, "user", None) and request.user.is_authenticated
        else False,
    }
