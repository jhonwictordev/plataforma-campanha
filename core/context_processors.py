def aplicacao_info(request):
    notificacoes_nao_lidas = 0
    notificacoes_topo = []
    if getattr(request, "user", None) and request.user.is_authenticated:
        from comunicacao.services import contar_notificacoes_nao_lidas, listar_notificacoes_usuario

        notificacoes_nao_lidas = contar_notificacoes_nao_lidas(request.user)
        notificacoes_topo = list(listar_notificacoes_usuario(request.user, limite=5))
    return {
        "nome_aplicacao": "Plataforma de Campanha",
        "tema_escuro_habilitado": getattr(request.user, "tema_escuro", False)
        if getattr(request, "user", None) and request.user.is_authenticated
        else False,
        "notificacoes_nao_lidas": notificacoes_nao_lidas,
        "notificacoes_topo": notificacoes_topo,
    }
