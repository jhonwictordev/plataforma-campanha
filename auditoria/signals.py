from decimal import Decimal
from uuid import UUID

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models import Model
from django.db.models.fields.files import FieldFile
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from core.models import ModeloBase
from core.request_context import obter_ip_atual, obter_usuario_atual

from .models import LogSeguranca, RegistroAuditoria

Usuario = get_user_model()

APPS_AUDITADOS = {
    "campanhas",
    "liderancas",
    "eleitores",
    "agenda",
    "equipe",
    "metas",
    "financeiro",
    "comunicacao",
    "usuarios",
}
MODELOS_IGNORADOS = {
    "auditoria.RegistroAuditoria",
    "auditoria.LogSeguranca",
}
CAMPOS_SENSIVEIS = {
    "cpf",
    "documento",
    "email",
    "telefone",
    "whatsapp",
    "endereco",
    "numero_documento",
    "latitude",
    "longitude",
    "observacoes",
    "descricao",
    "detalhes",
}


def _modelo_auditavel(instance: Model) -> bool:
    meta = getattr(instance, "_meta", None)
    if meta is None:
        return False
    if meta.label in MODELOS_IGNORADOS:
        return False
    if meta.app_label not in APPS_AUDITADOS:
        return False
    return isinstance(instance, ModeloBase)


def _mascarar_valor(campo: str, valor):
    if valor in (None, "", [], {}):
        return valor
    if campo not in CAMPOS_SENSIVEIS:
        if isinstance(valor, (Decimal, UUID)):
            return str(valor)
        return valor
    if campo == "email" and isinstance(valor, str) and "@" in valor:
        usuario, dominio = valor.split("@", 1)
        prefixo = usuario[:2] if len(usuario) > 2 else "*"
        return f"{prefixo}***@{dominio}"
    if campo in {"telefone", "whatsapp"} and isinstance(valor, str):
        return f"***{valor[-4:]}" if len(valor) >= 4 else "***"
    if campo in {"latitude", "longitude"}:
        return "[coordenada_protegida]"
    return "[dado_protegido]"


def _serializar_valor(valor):
    if isinstance(valor, FieldFile):
        return valor.name or None
    if isinstance(valor, Model):
        return str(valor.pk)
    if isinstance(valor, (Decimal, UUID)):
        return str(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {chave: _serializar_valor(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [_serializar_valor(item) for item in valor]
    return valor


def _serializar_instancia(instance: Model) -> dict:
    dados = {}
    for campo in instance._meta.fields:
        if campo.auto_created:
            continue
        nome = campo.name
        if nome in {"password"}:
            dados[nome] = "[hash_protegido]"
            continue
        valor = getattr(instance, campo.attname if campo.is_relation else nome, None)
        valor = _serializar_valor(valor)
        dados[nome] = _mascarar_valor(nome, valor)
    return dados


def _obter_campanha(instance: Model, usuario=None):
    campanha_id = getattr(instance, "campanha_id", None)
    if campanha_id:
        return getattr(instance, "campanha", None)
    if usuario is not None and getattr(usuario, "campanha_id", None):
        return getattr(usuario, "campanha", None)
    return None


def _registrar_auditoria(instance: Model, acao: str, dados_anteriores=None, dados_novos=None):
    usuario = obter_usuario_atual()
    campanha = _obter_campanha(instance, usuario)
    RegistroAuditoria.todos_objetos.create(
        campanha=campanha,
        acao=acao,
        modelo=instance._meta.label,
        objeto_id=str(instance.pk),
        resumo=f"{acao.title()} em {instance._meta.verbose_name}",
        dados_anteriores=dados_anteriores or {},
        dados_novos=dados_novos or {},
        usuario=usuario,
        endereco_ip=obter_ip_atual(),
    )


def _registrar_log(evento: str, descricao: str, usuario=None, severidade: str = "info", campanha=None):
    LogSeguranca.todos_objetos.create(
        campanha=campanha or getattr(usuario, "campanha", None),
        evento=evento,
        severidade=severidade,
        descricao=descricao,
        usuario=usuario,
        endereco_ip=obter_ip_atual(),
    )


@receiver(pre_save)
def capturar_estado_anterior(sender, instance, **kwargs):
    if not _modelo_auditavel(instance) or not getattr(instance, "pk", None):
        return
    gerenciador = getattr(sender, "todos_objetos", sender._default_manager)
    anterior = gerenciador.filter(pk=instance.pk).first()
    if anterior is not None:
        instance._dados_anteriores_auditoria = _serializar_instancia(anterior)


@receiver(post_save)
def auditar_salvamento(sender, instance, created, **kwargs):
    if not _modelo_auditavel(instance):
        return
    dados_anteriores = getattr(instance, "_dados_anteriores_auditoria", {})
    dados_novos = _serializar_instancia(instance)
    _registrar_auditoria(
        instance=instance,
        acao="criado" if created else "atualizado",
        dados_anteriores=dados_anteriores if not created else {},
        dados_novos=dados_novos,
    )


@receiver(post_delete)
def auditar_exclusao(sender, instance, **kwargs):
    if not _modelo_auditavel(instance):
        return
    _registrar_auditoria(
        instance=instance,
        acao="excluido",
        dados_anteriores=_serializar_instancia(instance),
        dados_novos={},
    )


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    _registrar_log(
        evento="login",
        descricao=f"Login bem-sucedido para {user.email}.",
        usuario=user,
        campanha=getattr(user, "campanha", None),
    )


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
    if user is None:
        return
    _registrar_log(
        evento="logout",
        descricao=f"Logout realizado por {user.email}.",
        usuario=user,
        campanha=getattr(user, "campanha", None),
    )


@receiver(user_login_failed)
def registrar_tentativa_falha(sender, credentials, request, **kwargs):
    email = credentials.get("username") or credentials.get("email")
    usuario = Usuario.objects.filter(email=email).first() if email else None
    descricao = "Falha de autenticação registrada."
    if email:
        descricao = f"Falha de autenticação para {email}."
    _registrar_log(
        evento="login_falhou",
        descricao=descricao,
        usuario=usuario,
        severidade="aviso",
        campanha=getattr(usuario, "campanha", None) if usuario else None,
    )
