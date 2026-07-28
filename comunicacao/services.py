from __future__ import annotations

import os
from uuid import UUID

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator

from eleitores.models import ContatoCRM

from .models import (
    CampanhaComunicacao,
    CanalComunicacao,
    EnvioComunicacao,
    ListaBloqueio,
    NotificacaoInterna,
    RegistroWebhookComunicacao,
)
from .providers import ErroProvedorComunicacao, ResultadoProvedor, obter_provedor_para_canal


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


def validar_envio_para_execucao(envio) -> tuple[bool, str]:
    contato = envio.contato
    if contato.campanha_id != envio.campanha_id:
        return False, "O contato pertence a outra campanha."
    if envio.cancelou_inscricao:
        return False, "O contato solicitou cancelamento de inscricao."
    if envio.status == EnvioComunicacao.Status.CANCELADO:
        return False, "O envio foi cancelado."
    if not contato.consentimento_comunicacao:
        return False, "O contato nao possui consentimento valido para comunicacao."
    if (contato.canal_autorizado or "").lower() != (envio.canal or "").lower():
        return False, "O contato nao autorizou o canal selecionado."
    if ListaBloqueio.objects.filter(campanha_id=envio.campanha_id, contato=contato, canal=envio.canal).exists():
        return False, "O contato esta na lista de bloqueio para este canal."
    if envio.canal == CanalComunicacao.EMAIL and not contato.email:
        return False, "O contato nao possui e-mail valido."
    if envio.canal == CanalComunicacao.WHATSAPP and not contato.whatsapp:
        return False, "O contato nao possui WhatsApp informado."
    if envio.canal == CanalComunicacao.SMS and not contato.telefone:
        return False, "O contato nao possui telefone valido para SMS."
    return True, ""


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


def notificar_resultado_processamento(campanha_comunicacao, titulo: str, mensagem: str, chave: str | None = None):
    usuarios = []
    if campanha_comunicacao.responsavel_id and campanha_comunicacao.responsavel.is_active:
        usuarios.append(campanha_comunicacao.responsavel)
    coordenador = campanha_comunicacao.campanha.coordenador_responsavel
    if coordenador and coordenador.is_active and coordenador not in usuarios:
        usuarios.append(coordenador)
    for usuario in usuarios:
        criar_notificacao_interna(
            campanha=campanha_comunicacao.campanha,
            usuario_destinatario=usuario,
            titulo=titulo,
            mensagem=mensagem,
            categoria=NotificacaoInterna.Categorias.COMUNICACAO,
            url_destino=reverse("comunicacao:campanha_detalhe", args=[campanha_comunicacao.pk]),
            chave_unica=f"{chave}:{usuario.pk}" if chave else None,
            origem_modelo="CampanhaComunicacao",
            origem_id=str(campanha_comunicacao.pk),
        )


def _valor_aninhado(payload, *caminhos):
    for caminho in caminhos:
        atual = payload
        for parte in caminho:
            if not isinstance(atual, dict) or parte not in atual:
                atual = None
                break
            atual = atual[parte]
        if atual not in (None, ""):
            return atual
    return None


def _uuid_valido(valor) -> bool:
    try:
        UUID(str(valor))
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def _mascarar_payload_webhook(valor, chave: str = ""):
    chave_normalizada = (chave or "").lower()
    if isinstance(valor, dict):
        return {item_chave: _mascarar_payload_webhook(item_valor, item_chave) for item_chave, item_valor in valor.items()}
    if isinstance(valor, list):
        return [_mascarar_payload_webhook(item, chave) for item in valor]
    if valor in (None, "", [], {}):
        return valor

    campos_destino = {"to", "destination", "email", "phone", "whatsapp", "telefone", "recipient"}
    campos_texto = {"body", "content", "message", "text", "response_text", "reply_text"}
    if chave_normalizada in campos_destino and isinstance(valor, str):
        return f"***{valor[-4:]}" if len(valor) >= 4 else "***"
    if chave_normalizada in campos_texto:
        return "[conteudo_protegido]"
    return valor


def _mapa_tokens_webhook():
    return {
        CanalComunicacao.EMAIL: os.getenv("EMAIL_OFFICIAL_WEBHOOK_TOKEN", "").strip(),
        CanalComunicacao.WHATSAPP: os.getenv("WHATSAPP_OFFICIAL_WEBHOOK_TOKEN", "").strip(),
        CanalComunicacao.SMS: os.getenv("SMS_OFFICIAL_WEBHOOK_TOKEN", "").strip(),
    }


def normalizar_payload_webhook(canal: str, payload: dict) -> dict:
    evento_bruto = (
        _valor_aninhado(
            payload,
            ("event",),
            ("status",),
            ("type",),
            ("data", "event"),
            ("data", "status"),
            ("message", "status"),
        )
        or ""
    )
    evento = str(evento_bruto).strip().lower()
    identificador_externo = (
        _valor_aninhado(
            payload,
            ("message_id",),
            ("external_id",),
            ("data", "message_id"),
            ("data", "external_id"),
            ("message", "id"),
            ("id",),
        )
        or ""
    )
    send_id = (
        _valor_aninhado(
            payload,
            ("send_id",),
            ("metadata", "send_id"),
            ("meta", "send_id"),
            ("data", "send_id"),
            ("data", "metadata", "send_id"),
        )
        or ""
    )
    provedor = (
        _valor_aninhado(payload, ("provider",), ("source",), ("data", "provider"), ("message", "provider"))
        or f"{canal}_oficial"
    )
    detalhe = _valor_aninhado(
        payload,
        ("detail",),
        ("error",),
        ("message",),
        ("data", "detail"),
        ("data", "error"),
    ) or ""
    resposta = _valor_aninhado(
        payload,
        ("response_text",),
        ("reply_text",),
        ("reply", "text"),
        ("message", "text"),
        ("data", "response_text"),
    ) or ""
    cancelou = bool(
        _valor_aninhado(payload, ("unsubscribe",), ("opt_out",), ("data", "unsubscribe"), ("data", "opt_out"))
    )

    if evento in {"unsubscribe", "opt_out", "unsubscribed", "stop"}:
        cancelou = True
    if evento in {"reply", "replied", "response", "responded"} and resposta:
        status_destino = EnvioComunicacao.Status.RESPONDIDO
    elif cancelou:
        status_destino = EnvioComunicacao.Status.RESPONDIDO
    elif evento in {"delivered", "entregue", "delivery"}:
        status_destino = EnvioComunicacao.Status.ENTREGUE
    elif evento in {"sent", "submitted", "queued", "accepted"}:
        status_destino = EnvioComunicacao.Status.ENVIADO
    elif evento in {"failed", "error", "undelivered", "rejected"}:
        status_destino = EnvioComunicacao.Status.FALHA
    else:
        status_destino = EnvioComunicacao.Status.ENVIADO

    return {
        "canal": canal,
        "evento": evento or "desconhecido",
        "provedor": str(provedor),
        "send_id": str(send_id).strip(),
        "identificador_externo": str(identificador_externo).strip(),
        "status_destino": status_destino,
        "detalhe": Truncator(str(detalhe)).chars(255),
        "resposta": str(resposta).strip(),
        "cancelou": cancelou,
        "payload_mascarado": _mascarar_payload_webhook(payload),
    }


def _buscar_envio_webhook(canal: str, dados_normalizados: dict):
    envio = None
    send_id = dados_normalizados.get("send_id")
    if _uuid_valido(send_id):
        envio = EnvioComunicacao.objects.select_related(
            "campanha",
            "campanha_comunicacao",
            "contato",
            "campanha_comunicacao__responsavel",
            "campanha_comunicacao__campanha__coordenador_responsavel",
        ).filter(pk=send_id, canal=canal).first()
    if envio is None and dados_normalizados.get("identificador_externo"):
        envio = EnvioComunicacao.objects.select_related(
            "campanha",
            "campanha_comunicacao",
            "contato",
            "campanha_comunicacao__responsavel",
            "campanha_comunicacao__campanha__coordenador_responsavel",
        ).filter(
            canal=canal,
            identificador_externo=dados_normalizados["identificador_externo"],
        ).order_by("-criado_em", "-pk").first()
    return envio


def _persistir_atualizacao_webhook(envio, dados_normalizados: dict):
    agora = timezone.now()
    campos = ["status", "provedor_utilizado", "atualizado_em"]
    if dados_normalizados.get("identificador_externo"):
        envio.identificador_externo = dados_normalizados["identificador_externo"]
        campos.append("identificador_externo")
    envio.provedor_utilizado = dados_normalizados["provedor"]

    status_destino = dados_normalizados["status_destino"]
    if status_destino == EnvioComunicacao.Status.ENVIADO:
        if envio.status == EnvioComunicacao.Status.PROGRAMADO:
            envio.status = EnvioComunicacao.Status.ENVIADO
        if not envio.data_envio:
            envio.data_envio = agora
            campos.append("data_envio")
        envio.erro_envio = ""
        envio.ultimo_erro_tecnico = ""
        campos.extend(["erro_envio", "ultimo_erro_tecnico"])
    elif status_destino == EnvioComunicacao.Status.ENTREGUE:
        if envio.status != EnvioComunicacao.Status.RESPONDIDO:
            envio.status = EnvioComunicacao.Status.ENTREGUE
        if not envio.data_envio:
            envio.data_envio = agora
            campos.append("data_envio")
        if not envio.data_entrega:
            envio.data_entrega = agora
            campos.append("data_entrega")
        envio.erro_envio = ""
        envio.ultimo_erro_tecnico = ""
        campos.extend(["erro_envio", "ultimo_erro_tecnico"])
    elif status_destino == EnvioComunicacao.Status.RESPONDIDO:
        envio.status = EnvioComunicacao.Status.RESPONDIDO
        if not envio.data_envio:
            envio.data_envio = agora
            campos.append("data_envio")
        if not envio.data_entrega:
            envio.data_entrega = agora
            campos.append("data_entrega")
        if not envio.data_resposta:
            envio.data_resposta = agora
            campos.append("data_resposta")
        resposta = dados_normalizados.get("resposta") or "Retorno recebido via webhook do provedor oficial."
        envio.resposta_recebida = resposta
        campos.append("resposta_recebida")
        envio.erro_envio = ""
        envio.ultimo_erro_tecnico = ""
        campos.extend(["erro_envio", "ultimo_erro_tecnico"])
        if dados_normalizados.get("cancelou"):
            envio.cancelou_inscricao = True
            campos.append("cancelou_inscricao")
    elif status_destino == EnvioComunicacao.Status.FALHA and envio.status not in {
        EnvioComunicacao.Status.ENTREGUE,
        EnvioComunicacao.Status.RESPONDIDO,
    }:
        envio.status = EnvioComunicacao.Status.FALHA
        detalhe = dados_normalizados.get("detalhe") or "Falha informada pelo provedor oficial."
        envio.erro_envio = detalhe
        envio.ultimo_erro_tecnico = detalhe
        campos.extend(["erro_envio", "ultimo_erro_tecnico"])

    envio.save(update_fields=list(dict.fromkeys(campos)))
    envio.campanha_comunicacao.atualizar_metricas()
    if envio.cancelou_inscricao:
        registrar_descadastro(envio, usuario=None)


def _notificar_webhook_relevante(envio, dados_normalizados: dict):
    titulo = None
    mensagem = None
    if dados_normalizados["status_destino"] == EnvioComunicacao.Status.RESPONDIDO and dados_normalizados.get("cancelou"):
        titulo = "Descadastro recebido por webhook"
        mensagem = (
            f"O contato '{envio.contato.nome_completo}' solicitou descadastro no canal "
            f"{envio.get_canal_display()}."
        )
    elif dados_normalizados["status_destino"] == EnvioComunicacao.Status.RESPONDIDO and dados_normalizados.get("resposta"):
        titulo = "Resposta recebida por webhook"
        mensagem = (
            f"O contato '{envio.contato.nome_completo}' respondeu a campanha "
            f"'{envio.campanha_comunicacao.nome}'."
        )
    elif dados_normalizados["status_destino"] == EnvioComunicacao.Status.FALHA:
        titulo = "Falha confirmada por webhook"
        mensagem = (
            f"O provedor confirmou falha no envio para '{envio.contato.nome_completo}' "
            f"na campanha '{envio.campanha_comunicacao.nome}'."
        )

    if not titulo or not mensagem:
        return

    notificar_resultado_processamento(
        envio.campanha_comunicacao,
        titulo=titulo,
        mensagem=mensagem,
        chave=(
            f"webhook:{envio.pk}:{dados_normalizados['evento']}:"
            f"{dados_normalizados.get('identificador_externo') or timezone.localdate().isoformat()}"
        ),
    )


def receber_webhook_comunicacao(canal: str, payload: dict, token: str = "", endereco_ip: str | None = None) -> dict:
    tokens = _mapa_tokens_webhook()
    token_configurado = tokens.get(canal, "")
    token_valido = bool(token_configurado and token and token == token_configurado)
    dados_normalizados = normalizar_payload_webhook(canal, payload)
    envio = _buscar_envio_webhook(canal, dados_normalizados) if token_valido else None

    registro = RegistroWebhookComunicacao.todos_objetos.create(
        campanha=getattr(envio, "campanha", None),
        envio=envio,
        canal=canal,
        provedor=dados_normalizados["provedor"],
        evento=dados_normalizados["evento"],
        identificador_externo=dados_normalizados.get("identificador_externo", ""),
        dados_recebidos=dados_normalizados["payload_mascarado"],
        assinatura_valida=token_valido,
        processado_com_sucesso=False,
        mensagem_processamento="Token de webhook invalido." if not token_valido else "",
        endereco_ip=endereco_ip,
    )

    if not token_valido:
        return {"aceito": False, "status_http": 403, "mensagem": "Token de webhook invalido."}

    if envio is None:
        registro.mensagem_processamento = "Nenhum envio correspondente foi localizado."
        registro.save(update_fields=["mensagem_processamento", "atualizado_em"])
        return {"aceito": True, "status_http": 202, "mensagem": "Webhook recebido sem envio correspondente."}

    _persistir_atualizacao_webhook(envio, dados_normalizados)
    _notificar_webhook_relevante(envio, dados_normalizados)

    registro.campanha = envio.campanha
    registro.envio = envio
    registro.processado_com_sucesso = True
    registro.mensagem_processamento = "Webhook processado com sucesso."
    registro.save(
        update_fields=[
            "campanha",
            "envio",
            "processado_com_sucesso",
            "mensagem_processamento",
            "atualizado_em",
        ]
    )
    return {
        "aceito": True,
        "status_http": 200,
        "mensagem": "Webhook processado com sucesso.",
        "envio_id": str(envio.pk),
        "status": envio.status,
    }


def _aplicar_resultado_envio(envio, resultado: ResultadoProvedor):
    campos = [
        "status",
        "erro_envio",
        "ultimo_erro_tecnico",
        "ultima_tentativa_em",
        "tentativas_envio",
        "provedor_utilizado",
        "identificador_externo",
        "data_envio",
        "atualizado_em",
    ]
    envio.tentativas_envio += 1
    envio.ultima_tentativa_em = timezone.now()
    envio.provedor_utilizado = resultado.provedor
    envio.identificador_externo = resultado.identificador_externo
    envio.ultimo_erro_tecnico = ""
    envio.erro_envio = ""
    if resultado.status == "entregue":
        envio.status = EnvioComunicacao.Status.ENTREGUE
        campos.append("data_entrega")
    else:
        envio.status = EnvioComunicacao.Status.ENVIADO
    envio.save(update_fields=campos)


def _aplicar_falha_envio(envio, provedor: str, mensagem: str):
    envio.tentativas_envio += 1
    envio.ultima_tentativa_em = timezone.now()
    envio.provedor_utilizado = provedor
    envio.status = EnvioComunicacao.Status.FALHA
    mensagem_curta = Truncator(mensagem or "Falha desconhecida no provedor.").chars(255)
    envio.erro_envio = mensagem_curta
    envio.ultimo_erro_tecnico = mensagem_curta
    envio.save(
        update_fields=[
            "tentativas_envio",
            "ultima_tentativa_em",
            "provedor_utilizado",
            "status",
            "erro_envio",
            "ultimo_erro_tecnico",
            "atualizado_em",
        ]
    )


def processar_envio_comunicacao(envio, provedor=None, forcar_reenvio: bool = False) -> dict[str, str]:
    if envio.status in {
        EnvioComunicacao.Status.ENVIADO,
        EnvioComunicacao.Status.ENTREGUE,
        EnvioComunicacao.Status.RESPONDIDO,
    } and not forcar_reenvio:
        return {"resultado": "ignorado", "motivo": "Envio ja processado."}

    valido, motivo = validar_envio_para_execucao(envio)
    if not valido:
        _aplicar_falha_envio(envio, provedor.nome if provedor else "validacao", motivo)
        return {"resultado": "falha", "motivo": motivo}

    provedor = provedor or obter_provedor_para_canal(envio.canal)
    try:
        provedor.verificar_configuracao()
        resultado = provedor.enviar(envio)
    except ErroProvedorComunicacao as exc:
        _aplicar_falha_envio(envio, provedor.nome, str(exc))
        return {"resultado": "falha", "motivo": str(exc)}
    except Exception as exc:  # pragma: no cover - protecao adicional para job assíncrono
        _aplicar_falha_envio(envio, provedor.nome, f"Erro inesperado no provedor: {exc}")
        return {"resultado": "falha", "motivo": str(exc)}

    _aplicar_resultado_envio(envio, resultado)
    return {"resultado": "sucesso", "motivo": resultado.mensagem or "Envio processado."}


@transaction.atomic
def processar_campanha_comunicacao(campanha_comunicacao, referencia=None, forcar_execucao: bool = False) -> dict[str, int | str]:
    referencia = referencia or timezone.now()
    if campanha_comunicacao.status == CampanhaComunicacao.Status.CANCELADA:
        return {"campanha": str(campanha_comunicacao.pk), "processados": 0, "falhas": 0, "status": "cancelada"}
    if not forcar_execucao and campanha_comunicacao.data_envio and campanha_comunicacao.data_envio > referencia:
        return {"campanha": str(campanha_comunicacao.pk), "processados": 0, "falhas": 0, "status": "aguardando"}

    try:
        provedor = obter_provedor_para_canal(campanha_comunicacao.canal)
        provedor.verificar_configuracao()
    except ErroProvedorComunicacao as exc:
        campanha_comunicacao.status = CampanhaComunicacao.Status.PAUSADA
        campanha_comunicacao.provedor_ultimo_envio = (
            campanha_comunicacao.canal if campanha_comunicacao.canal else "indefinido"
        )
        campanha_comunicacao.ultima_execucao_em = referencia
        campanha_comunicacao.erro_ultima_execucao = Truncator(str(exc)).chars(255)
        campanha_comunicacao.save(
            update_fields=[
                "status",
                "provedor_ultimo_envio",
                "ultima_execucao_em",
                "erro_ultima_execucao",
                "atualizado_em",
            ]
        )
        notificar_resultado_processamento(
            campanha_comunicacao,
            titulo="Campanha pausada por falta de integracao oficial",
            mensagem=str(exc),
            chave=f"comunicacao-pausada:{campanha_comunicacao.pk}:{timezone.localdate().isoformat()}",
        )
        return {
            "campanha": str(campanha_comunicacao.pk),
            "processados": 0,
            "falhas": 0,
            "status": "pausada",
            "erro": str(exc),
        }

    campanha_comunicacao.status = CampanhaComunicacao.Status.ENVIANDO
    campanha_comunicacao.provedor_ultimo_envio = provedor.nome
    campanha_comunicacao.ultima_execucao_em = referencia
    campanha_comunicacao.processamento_iniciado_em = referencia
    campanha_comunicacao.erro_ultima_execucao = ""
    campanha_comunicacao.save(
        update_fields=[
            "status",
            "provedor_ultimo_envio",
            "ultima_execucao_em",
            "processamento_iniciado_em",
            "erro_ultima_execucao",
            "atualizado_em",
        ]
    )

    envios = campanha_comunicacao.envios.select_related("contato").order_by("pk")
    processados = 0
    falhas = 0
    ignorados = 0
    for envio in envios:
        status_processaveis = {EnvioComunicacao.Status.PROGRAMADO}
        if forcar_execucao:
            status_processaveis.add(EnvioComunicacao.Status.FALHA)
        if envio.status not in status_processaveis:
            ignorados += 1
            continue
        resumo = processar_envio_comunicacao(envio, provedor=provedor, forcar_reenvio=forcar_execucao)
        if resumo["resultado"] == "sucesso":
            processados += 1
        elif resumo["resultado"] == "falha":
            falhas += 1
        else:
            ignorados += 1

    campanha_comunicacao.atualizar_metricas()
    campanha_comunicacao.status = CampanhaComunicacao.Status.CONCLUIDA
    campanha_comunicacao.processamento_finalizado_em = timezone.now()
    campanha_comunicacao.erro_ultima_execucao = (
        f"{falhas} envio(s) falharam na ultima execucao." if falhas else ""
    )
    campanha_comunicacao.save(
        update_fields=[
            "status",
            "processamento_finalizado_em",
            "erro_ultima_execucao",
            "atualizado_em",
        ]
    )

    if falhas:
        notificar_resultado_processamento(
            campanha_comunicacao,
            titulo="Campanha concluida com falhas de entrega",
            mensagem=(
                f"A campanha '{campanha_comunicacao.nome}' concluiu o processamento com "
                f"{falhas} falha(s) e {processados} envio(s) bem-sucedido(s)."
            ),
            chave=f"comunicacao-falhas:{campanha_comunicacao.pk}:{timezone.localdate().isoformat()}",
        )

    return {
        "campanha": str(campanha_comunicacao.pk),
        "processados": processados,
        "falhas": falhas,
        "ignorados": ignorados,
        "status": campanha_comunicacao.status,
        "provedor": provedor.nome,
    }


def processar_campanhas_agendadas(referencia=None, limite: int = 20) -> dict[str, int]:
    referencia = referencia or timezone.now()
    campanhas = (
        CampanhaComunicacao.objects.filter(
            status=CampanhaComunicacao.Status.AGENDADA,
            data_envio__isnull=False,
            data_envio__lte=referencia,
        )
        .select_related("campanha", "responsavel", "campanha__coordenador_responsavel")
        .order_by("data_envio", "pk")[:limite]
    )

    campanhas_processadas = 0
    envios_ok = 0
    falhas = 0
    pausadas = 0
    for campanha in campanhas:
        resultado = processar_campanha_comunicacao(campanha, referencia=referencia)
        campanhas_processadas += 1
        envios_ok += int(resultado.get("processados", 0))
        falhas += int(resultado.get("falhas", 0))
        pausadas += 1 if resultado.get("status") == "pausada" else 0

    return {
        "campanhas": campanhas_processadas,
        "envios_processados": envios_ok,
        "falhas": falhas,
        "pausadas": pausadas,
    }


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
