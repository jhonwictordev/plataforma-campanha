from __future__ import annotations

from base64 import b32encode, b64encode
from io import BytesIO

import qrcode
from auditoria.models import LogSeguranca
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice


def sincronizar_estado_dois_fatores(usuario) -> bool:
    ativo = TOTPDevice.objects.devices_for_user(usuario, confirmed=True).exists()
    if usuario.dois_fatores_habilitado != ativo:
        usuario.dois_fatores_habilitado = ativo
        usuario.save(update_fields=["dois_fatores_habilitado", "atualizado_em"])
    return ativo


def usuario_exige_dois_fatores(usuario) -> bool:
    if not getattr(usuario, "pk", None):
        return False
    return sincronizar_estado_dois_fatores(usuario)


def obter_dispositivo_totp(usuario, confirmado: bool | None = True) -> TOTPDevice | None:
    return TOTPDevice.objects.devices_for_user(usuario, confirmed=confirmado).order_by("id").first()


def obter_ou_criar_dispositivo_pendente(usuario) -> TOTPDevice:
    dispositivo = obter_dispositivo_totp(usuario, confirmado=False)
    if dispositivo:
        return dispositivo
    return TOTPDevice.objects.create(
        user=usuario,
        name="Autenticador principal",
        confirmed=False,
    )


def segredo_base32(dispositivo: TOTPDevice) -> str:
    return b32encode(dispositivo.bin_key).decode("utf-8")


def qr_code_data_uri(texto: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(texto)
    qr.make(fit=True)
    imagem = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return f"data:image/png;base64,{b64encode(buffer.getvalue()).decode('ascii')}"


def obter_ou_criar_dispositivo_recuperacao(usuario) -> StaticDevice:
    dispositivo, _ = StaticDevice.objects.get_or_create(
        user=usuario,
        name="Codigos de recuperacao",
        defaults={"confirmed": True},
    )
    if not dispositivo.confirmed:
        dispositivo.confirmed = True
        dispositivo.save(update_fields=["confirmed"])
    return dispositivo


def regenerar_codigos_recuperacao(usuario, quantidade: int = 8) -> list[str]:
    dispositivo = obter_ou_criar_dispositivo_recuperacao(usuario)
    dispositivo.token_set.all().delete()
    codigos = [StaticToken.random_token() for _ in range(quantidade)]
    StaticToken.objects.bulk_create(
        [StaticToken(device=dispositivo, token=codigo) for codigo in codigos]
    )
    return codigos


def quantidade_codigos_recuperacao(usuario) -> int:
    dispositivo = StaticDevice.objects.devices_for_user(usuario, confirmed=True).order_by("id").first()
    if not dispositivo:
        return 0
    return dispositivo.token_set.count()


def ativar_dois_fatores(usuario, token: str) -> tuple[TOTPDevice | None, list[str]]:
    dispositivo = obter_ou_criar_dispositivo_pendente(usuario)
    if not dispositivo.verify_token(token):
        return None, []

    if not dispositivo.confirmed:
        dispositivo.confirmed = True
        dispositivo.save(update_fields=["confirmed"])

    usuario.dois_fatores_habilitado = True
    usuario.save(update_fields=["dois_fatores_habilitado", "atualizado_em"])
    codigos = regenerar_codigos_recuperacao(usuario)
    return dispositivo, codigos


def verificar_token_login(usuario, token: str):
    dispositivo_totp = obter_dispositivo_totp(usuario, confirmado=True)
    if dispositivo_totp and token.isdigit() and dispositivo_totp.verify_token(token):
        return dispositivo_totp, "aplicativo"

    dispositivo_recuperacao = StaticDevice.objects.devices_for_user(usuario, confirmed=True).order_by("id").first()
    if dispositivo_recuperacao and dispositivo_recuperacao.verify_token(token):
        return dispositivo_recuperacao, "recuperacao"

    return None, None


def desativar_dois_fatores(usuario) -> None:
    TOTPDevice.objects.filter(user=usuario).delete()
    StaticDevice.objects.filter(user=usuario).delete()
    if usuario.dois_fatores_habilitado:
        usuario.dois_fatores_habilitado = False
        usuario.save(update_fields=["dois_fatores_habilitado", "atualizado_em"])


def registrar_log_dois_fatores(usuario, evento: str, descricao: str, endereco_ip: str | None = None, severidade: str = "info") -> None:
    LogSeguranca.todos_objetos.create(
        campanha=getattr(usuario, "campanha", None),
        evento=evento,
        severidade=severidade,
        descricao=descricao,
        usuario=usuario,
        endereco_ip=endereco_ip,
    )
