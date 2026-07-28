from django.utils import timezone

from eleitores.models import ContatoCRM

from .models import EnvioComunicacao, ListaBloqueio, NotificacaoInterna


def contar_contatos_autorizados(campanha_id, canal=None) -> int:
    queryset = ContatoCRM.objects.filter(campanha_id=campanha_id, consentimento_comunicacao=True)
    if canal:
        queryset = queryset.filter(canal_autorizado__iexact=canal)
    return queryset.count()


def analisar_destinatarios(campanha_id, canal, destinatarios):
    destinatarios = list(destinatarios or [])
    bloqueados_ids = set(
        ListaBloqueio.objects.filter(campanha_id=campanha_id, canal=canal).values_list("contato_id", flat=True)
    )
    erros = {
        "outra_campanha": [],
        "sem_consentimento": [],
        "canal_nao_autorizado": [],
        "bloqueados": [],
    }

    for contato in destinatarios:
        if contato.campanha_id != campanha_id:
            erros["outra_campanha"].append(contato.nome_completo)
        if not contato.consentimento_comunicacao:
            erros["sem_consentimento"].append(contato.nome_completo)
        if (contato.canal_autorizado or "").lower() != (canal or "").lower():
            erros["canal_nao_autorizado"].append(contato.nome_completo)
        if contato.pk in bloqueados_ids:
            erros["bloqueados"].append(contato.nome_completo)

    return {chave: valores for chave, valores in erros.items() if valores}


def sincronizar_envios_campanha(campanha_comunicacao, destinatarios, usuario=None):
    destinatarios = list(destinatarios or [])
    destinatarios_ids = {contato.pk for contato in destinatarios}
    existentes = {
        envio.contato_id: envio for envio in campanha_comunicacao.envios.select_related("contato").all()
    }

    for contato in destinatarios:
        envio = existentes.get(contato.pk)
        if envio is None:
            EnvioComunicacao.objects.create(
                campanha_id=campanha_comunicacao.campanha_id,
                campanha_comunicacao=campanha_comunicacao,
                contato=contato,
                canal=campanha_comunicacao.canal,
                status=(
                    EnvioComunicacao.Status.CANCELADO
                    if campanha_comunicacao.status == campanha_comunicacao.Status.CANCELADA
                    else EnvioComunicacao.Status.PROGRAMADO
                ),
                mensagem_enviada=campanha_comunicacao.conteudo,
                data_programada=campanha_comunicacao.data_envio,
                responsavel_registro=usuario,
            )
            continue

        campos_atualizados = []
        if envio.canal != campanha_comunicacao.canal:
            envio.canal = campanha_comunicacao.canal
            campos_atualizados.append("canal")
        if envio.data_programada != campanha_comunicacao.data_envio:
            envio.data_programada = campanha_comunicacao.data_envio
            campos_atualizados.append("data_programada")
        if not envio.mensagem_enviada or envio.status == EnvioComunicacao.Status.PROGRAMADO:
            envio.mensagem_enviada = campanha_comunicacao.conteudo
            campos_atualizados.append("mensagem_enviada")
        if (
            envio.status == EnvioComunicacao.Status.CANCELADO
            and not envio.cancelou_inscricao
            and campanha_comunicacao.status != campanha_comunicacao.Status.CANCELADA
        ):
            envio.status = EnvioComunicacao.Status.PROGRAMADO
            campos_atualizados.append("status")
        if (
            envio.status == EnvioComunicacao.Status.PROGRAMADO
            and campanha_comunicacao.status == campanha_comunicacao.Status.CANCELADA
        ):
            envio.status = EnvioComunicacao.Status.CANCELADO
            campos_atualizados.append("status")
        if usuario and envio.responsavel_registro_id != usuario.id:
            envio.responsavel_registro = usuario
            campos_atualizados.append("responsavel_registro")
        if campos_atualizados:
            envio.save(update_fields=campos_atualizados + ["atualizado_em"])

    for envio in campanha_comunicacao.envios.exclude(contato_id__in=destinatarios_ids):
        if envio.status == EnvioComunicacao.Status.PROGRAMADO and not envio.cancelou_inscricao:
            envio.status = EnvioComunicacao.Status.CANCELADO
            if usuario:
                envio.responsavel_registro = usuario
                envio.save(update_fields=["status", "responsavel_registro", "atualizado_em"])
            else:
                envio.save(update_fields=["status", "atualizado_em"])

    campanha_comunicacao.atualizar_metricas()


def registrar_descadastro(envio, usuario=None):
    if not envio.cancelou_inscricao:
        return
    ListaBloqueio.objects.get_or_create(
        campanha_id=envio.campanha_id,
        contato=envio.contato,
        canal=envio.canal,
        defaults={
            "motivo": "Descadastro registrado no acompanhamento da comunicacao.",
            "solicitado_por": usuario,
        },
    )


def criar_notificacao_interna(
    *,
    campanha,
    usuario_destinatario,
    titulo: str,
    mensagem: str,
    categoria: str,
    url_destino: str = "",
    chave_unica: str | None = None,
    origem_modelo: str = "",
    origem_id: str = "",
):
    defaults = {
        "titulo": titulo,
        "mensagem": mensagem,
        "categoria": categoria,
        "url_destino": url_destino,
        "origem_modelo": origem_modelo,
        "origem_id": origem_id,
        "enviada_em": timezone.now(),
    }
    if chave_unica:
        return NotificacaoInterna.objects.update_or_create(
            campanha=campanha,
            usuario_destinatario=usuario_destinatario,
            chave_unica=chave_unica,
            defaults=defaults,
        )
    notificacao = NotificacaoInterna.objects.create(
        campanha=campanha,
        usuario_destinatario=usuario_destinatario,
        chave_unica=None,
        **defaults,
    )
    return notificacao, True


def contar_notificacoes_nao_lidas(usuario) -> int:
    if not getattr(usuario, "is_authenticated", False):
        return 0
    return NotificacaoInterna.objects.filter(usuario_destinatario=usuario, lida_em__isnull=True).count()


def listar_notificacoes_usuario(usuario, limite: int | None = None):
    if not getattr(usuario, "is_authenticated", False):
        return NotificacaoInterna.objects.none()
    queryset = NotificacaoInterna.objects.filter(usuario_destinatario=usuario).order_by("-criado_em", "-pk")
    if limite:
        return queryset[:limite]
    return queryset


def marcar_todas_notificacoes_como_lidas(usuario) -> int:
    if not getattr(usuario, "is_authenticated", False):
        return 0
    return NotificacaoInterna.objects.filter(usuario_destinatario=usuario, lida_em__isnull=True).update(
        lida_em=timezone.now(),
        atualizado_em=timezone.now(),
    )
