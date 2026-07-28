from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.core.mail import EmailMultiAlternatives
from django.utils.text import Truncator


class ErroProvedorComunicacao(Exception):
    pass


@dataclass
class ResultadoProvedor:
    sucesso: bool
    status: str
    provedor: str
    mensagem: str = ""
    identificador_externo: str = ""


class ProvedorComunicacaoBase:
    nome = "base"
    canal = ""

    def verificar_configuracao(self) -> None:
        return None

    def enviar(self, envio) -> ResultadoProvedor:
        raise NotImplementedError


class ProvedorEmailDjango(ProvedorComunicacaoBase):
    nome = "email_django"
    canal = "email"

    def enviar(self, envio) -> ResultadoProvedor:
        contato = envio.contato
        if not contato.email:
            raise ErroProvedorComunicacao("O contato nao possui e-mail valido para este envio.")

        campanha = envio.campanha_comunicacao
        assunto = campanha.assunto or f"Comunicacao da campanha {campanha.nome}"
        mensagem = envio.mensagem_enviada or campanha.conteudo
        email = EmailMultiAlternatives(
            subject=assunto,
            body=mensagem,
            from_email=os.getenv("DEFAULT_FROM_EMAIL", "nao-responda@plataformacampanha.local"),
            to=[contato.email],
        )
        enviados = email.send(fail_silently=False)
        if enviados < 1:
            raise ErroProvedorComunicacao("O backend de e-mail nao confirmou o envio da mensagem.")

        return ResultadoProvedor(
            sucesso=True,
            status="enviado",
            provedor=self.nome,
            mensagem="Mensagem encaminhada ao backend oficial de e-mail.",
            identificador_externo=f"email:{envio.pk}",
        )


class ProvedorNotificacaoInterna(ProvedorComunicacaoBase):
    nome = "notificacao_interna"
    canal = "notificacao_interna"

    def enviar(self, envio) -> ResultadoProvedor:
        from .services import criar_notificacao_interna

        contato = envio.contato
        campanha = envio.campanha_comunicacao
        usuarios_destino = []
        if contato.responsavel_cadastro_id and contato.responsavel_cadastro.is_active:
            usuarios_destino.append(contato.responsavel_cadastro)
        lideranca = contato.lideranca_relacionada
        if (
            lideranca
            and lideranca.responsavel_contato_id
            and lideranca.responsavel_contato.is_active
            and lideranca.responsavel_contato not in usuarios_destino
        ):
            usuarios_destino.append(lideranca.responsavel_contato)
        if campanha.responsavel_id and campanha.responsavel.is_active and campanha.responsavel not in usuarios_destino:
            usuarios_destino.append(campanha.responsavel)

        if not usuarios_destino:
            raise ErroProvedorComunicacao(
                "Nao ha usuario interno vinculado ao contato para receber notificacao interna."
            )

        titulo = campanha.assunto or campanha.nome
        mensagem = envio.mensagem_enviada or campanha.conteudo
        for usuario in usuarios_destino:
            criar_notificacao_interna(
                campanha=envio.campanha,
                usuario_destinatario=usuario,
                titulo=f"Comunicacao interna: {Truncator(titulo).chars(80)}",
                mensagem=mensagem,
                categoria="comunicacao",
                url_destino=f"/comunicacao/campanhas/{campanha.pk}/",
                chave_unica=f"campanha-interna:{campanha.pk}:{envio.pk}:{usuario.pk}",
                origem_modelo="CampanhaComunicacao",
                origem_id=str(campanha.pk),
            )

        return ResultadoProvedor(
            sucesso=True,
            status="entregue",
            provedor=self.nome,
            mensagem=f"Notificacao interna criada para {len(usuarios_destino)} usuario(s).",
            identificador_externo=f"interna:{envio.pk}",
        )


class ProvedorApiOficialBase(ProvedorComunicacaoBase):
    url_env = ""
    token_env = ""

    def verificar_configuracao(self) -> None:
        endpoint = os.getenv(self.url_env, "").strip()
        token = os.getenv(self.token_env, "").strip()
        if not endpoint or not token:
            raise ErroProvedorComunicacao(
                f"A integracao oficial para o canal {self.canal} ainda nao foi configurada no ambiente."
            )
        if not endpoint.startswith("https://"):
            raise ErroProvedorComunicacao(
                f"O endpoint oficial do canal {self.canal} deve usar HTTPS."
            )

    def destino_contato(self, envio) -> str:
        raise NotImplementedError

    def payload(self, envio) -> dict:
        campanha = envio.campanha_comunicacao
        return {
            "campaign_id": str(campanha.pk),
            "campaign_name": campanha.nome,
            "send_id": str(envio.pk),
            "recipient": {
                "name": envio.contato.nome_completo,
                "destination": self.destino_contato(envio),
            },
            "message": {
                "subject": campanha.assunto,
                "content": envio.mensagem_enviada or campanha.conteudo,
            },
            "metadata": {
                "channel": campanha.canal,
                "allow_unsubscribe": campanha.permitir_cancelamento_inscricao,
                "contact_id": str(envio.contato.pk),
                "campaign_scope": str(envio.campanha_id),
            },
        }

    def enviar(self, envio) -> ResultadoProvedor:
        self.verificar_configuracao()
        endpoint = os.getenv(self.url_env, "").strip()
        token = os.getenv(self.token_env, "").strip()
        corpo = json.dumps(self.payload(envio)).encode("utf-8")
        requisicao = urllib.request.Request(
            endpoint,
            data=corpo,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=15) as resposta:
                texto = resposta.read().decode("utf-8") or "{}"
                dados = json.loads(texto)
        except urllib.error.HTTPError as exc:
            detalhes = exc.read().decode("utf-8", errors="ignore")
            raise ErroProvedorComunicacao(
                f"A API oficial retornou HTTP {exc.code}. {Truncator(detalhes).chars(160)}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ErroProvedorComunicacao(f"Falha de conexao com a API oficial: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ErroProvedorComunicacao("A API oficial retornou uma resposta invalida.") from exc

        identificador = str(
            dados.get("id")
            or dados.get("message_id")
            or dados.get("external_id")
            or f"{self.canal}:{envio.pk}"
        )
        status = (dados.get("status") or "enviado").lower()
        if status in {"delivered", "entregue", "delivered_to_device"}:
            status_normalizado = "entregue"
        else:
            status_normalizado = "enviado"

        return ResultadoProvedor(
            sucesso=True,
            status=status_normalizado,
            provedor=self.nome,
            mensagem=Truncator(str(dados.get("detail") or dados.get("message") or "")).chars(160),
            identificador_externo=identificador,
        )


class ProvedorWhatsAppOficial(ProvedorApiOficialBase):
    nome = "whatsapp_oficial"
    canal = "whatsapp"
    url_env = "WHATSAPP_OFFICIAL_API_URL"
    token_env = "WHATSAPP_OFFICIAL_API_TOKEN"

    def destino_contato(self, envio) -> str:
        if not envio.contato.whatsapp:
            raise ErroProvedorComunicacao("O contato nao possui WhatsApp informado.")
        return envio.contato.whatsapp


class ProvedorSmsOficial(ProvedorApiOficialBase):
    nome = "sms_oficial"
    canal = "sms"
    url_env = "SMS_OFFICIAL_API_URL"
    token_env = "SMS_OFFICIAL_API_TOKEN"

    def destino_contato(self, envio) -> str:
        if not envio.contato.telefone:
            raise ErroProvedorComunicacao("O contato nao possui telefone informado para SMS.")
        return envio.contato.telefone


def obter_provedor_para_canal(canal: str) -> ProvedorComunicacaoBase:
    provedores = {
        "email": ProvedorEmailDjango,
        "sms": ProvedorSmsOficial,
        "whatsapp": ProvedorWhatsAppOficial,
        "notificacao_interna": ProvedorNotificacaoInterna,
    }
    classe = provedores.get(canal)
    if not classe:
        raise ErroProvedorComunicacao(f"Nao existe provedor configurado para o canal {canal}.")
    return classe()
