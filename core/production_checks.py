import os
from pathlib import Path

from django.conf import settings
from django_celery_beat.models import PeriodicTask

from .health import verificar_banco_dados, verificar_migracoes, verificar_redis

HOSTS_LOCAIS = {"localhost", "127.0.0.1", "[::1]", "testserver"}
TAREFAS_PERIODICAS_OBRIGATORIAS = (
    "Plataforma - Lembretes de agenda",
    "Plataforma - Alertas de tarefas",
    "Plataforma - Alertas financeiros",
    "Plataforma - Alertas LGPD",
    "Plataforma - Alertas de retencao",
    "Plataforma - Comunicacoes agendadas",
)


def _parece_placeholder(valor: str) -> bool:
    texto = (valor or "").strip().lower()
    if not texto:
        return True
    marcadores = (
        "gere_",
        "defina_",
        "placeholder",
        "change-me",
        "changeme",
        "example",
        "teste-seguro",
        "dummy",
    )
    return any(marcador in texto for marcador in marcadores)


def _registrar(checks: list[dict], chave: str, status: str, detalhe: str) -> None:
    checks.append({"chave": chave, "status": status, "detalhe": detalhe})


def _verificar_secret_key(checks: list[dict]) -> None:
    secret_key = os.getenv("SECRET_KEY", "")
    if not secret_key:
        _registrar(checks, "seguranca.secret_key", "erro", "SECRET_KEY nao foi definida no ambiente.")
        return
    if len(secret_key) < 32 or _parece_placeholder(secret_key):
        _registrar(
            checks,
            "seguranca.secret_key",
            "erro",
            "SECRET_KEY precisa ser unica, longa e sem placeholders de exemplo.",
        )
        return
    _registrar(checks, "seguranca.secret_key", "ok", "SECRET_KEY presente e com formato aceitavel.")


def _verificar_allowed_hosts(checks: list[dict]) -> None:
    hosts_publicos = [host for host in settings.ALLOWED_HOSTS if host not in HOSTS_LOCAIS]
    if not hosts_publicos:
        _registrar(
            checks,
            "seguranca.allowed_hosts",
            "erro",
            "ALLOWED_HOSTS ainda nao contem dominios publicos validos.",
        )
        return
    _registrar(
        checks,
        "seguranca.allowed_hosts",
        "ok",
        f"ALLOWED_HOSTS configurado para {len(hosts_publicos)} host(s) publico(s).",
    )


def _verificar_csrf(checks: list[dict]) -> None:
    origens = list(settings.CSRF_TRUSTED_ORIGINS)
    if not origens:
        _registrar(checks, "seguranca.csrf", "erro", "CSRF_TRUSTED_ORIGINS nao foi configurado.")
        return
    invalidas = [origem for origem in origens if not origem.startswith("https://")]
    if invalidas:
        _registrar(
            checks,
            "seguranca.csrf",
            "erro",
            "CSRF_TRUSTED_ORIGINS deve usar apenas origens HTTPS explicitas em producao.",
        )
        return
    _registrar(checks, "seguranca.csrf", "ok", "CSRF_TRUSTED_ORIGINS configurado com origens HTTPS.")


def _verificar_email(checks: list[dict]) -> None:
    backend = settings.EMAIL_BACKEND
    if backend in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
    }:
        _registrar(
            checks,
            "integracoes.email_backend",
            "aviso",
            "EMAIL_BACKEND esta em modo local; password reset e campanhas reais nao sairao por um provedor externo.",
        )
    else:
        _registrar(checks, "integracoes.email_backend", "ok", "EMAIL_BACKEND aponta para um backend externo.")

    remetente = settings.DEFAULT_FROM_EMAIL
    if remetente.endswith(".local") or "example" in remetente:
        _registrar(
            checks,
            "integracoes.default_from_email",
            "aviso",
            "DEFAULT_FROM_EMAIL ainda usa um dominio de exemplo/local.",
        )
    else:
        _registrar(checks, "integracoes.default_from_email", "ok", "DEFAULT_FROM_EMAIL parece pronto para producao.")


def _verificar_canais_oficiais(checks: list[dict]) -> None:
    configuracoes = (
        ("whatsapp", "WHATSAPP_OFFICIAL_API_URL", "WHATSAPP_OFFICIAL_API_TOKEN", "WHATSAPP_OFFICIAL_WEBHOOK_TOKEN"),
        ("sms", "SMS_OFFICIAL_API_URL", "SMS_OFFICIAL_API_TOKEN", "SMS_OFFICIAL_WEBHOOK_TOKEN"),
    )
    for nome, chave_url, chave_token, chave_webhook in configuracoes:
        url = os.getenv(chave_url, "").strip()
        token = os.getenv(chave_token, "").strip()
        webhook = os.getenv(chave_webhook, "").strip()
        if url and not token:
            _registrar(
                checks,
                f"integracoes.{nome}",
                "erro",
                f"{chave_url} foi definido, mas {chave_token} esta ausente.",
            )
            continue
        if url and not webhook:
            _registrar(
                checks,
                f"integracoes.{nome}",
                "aviso",
                f"{nome.upper()} oficial esta apto a enviar, mas {chave_webhook} ainda nao foi configurado para reconciliacao.",
            )
            continue
        if token and not url:
            _registrar(
                checks,
                f"integracoes.{nome}",
                "aviso",
                f"{chave_token} foi preenchido sem {chave_url}; revise a configuracao do canal {nome}.",
            )
            continue
        if url and token and webhook:
            _registrar(
                checks,
                f"integracoes.{nome}",
                "ok",
                f"Canal oficial de {nome} configurado com envio e webhook.",
            )
            continue
        _registrar(
            checks,
            f"integracoes.{nome}",
            "ignorado",
            f"Canal oficial de {nome} nao configurado neste ambiente.",
        )

    email_webhook = os.getenv("EMAIL_OFFICIAL_WEBHOOK_TOKEN", "").strip()
    if email_webhook:
        _registrar(checks, "integracoes.email_webhook", "ok", "Webhook oficial de email configurado.")
    else:
        _registrar(
            checks,
            "integracoes.email_webhook",
            "ignorado",
            "EMAIL_OFFICIAL_WEBHOOK_TOKEN nao foi definido; conciliacao por webhook de email fica opcional neste ambiente.",
        )


def _verificar_staticfiles(checks: list[dict]) -> None:
    diretorio = Path(settings.STATIC_ROOT)
    arquivos = []
    if diretorio.exists():
        arquivos = [item for item in diretorio.rglob("*") if item.is_file()]

    if not arquivos:
        _registrar(
            checks,
            "operacao.staticfiles",
            "erro",
            "STATIC_ROOT esta vazio; execute collectstatic antes de publicar a aplicacao.",
        )
        return
    _registrar(
        checks,
        "operacao.staticfiles",
        "ok",
        f"STATIC_ROOT contem {len(arquivos)} arquivo(s) pronto(s) para entrega.",
    )


def _verificar_tarefas_periodicas(checks: list[dict]) -> None:
    existentes = set(
        PeriodicTask.objects.filter(name__in=TAREFAS_PERIODICAS_OBRIGATORIAS, enabled=True).values_list("name", flat=True)
    )
    faltantes = [nome for nome in TAREFAS_PERIODICAS_OBRIGATORIAS if nome not in existentes]
    if faltantes:
        _registrar(
            checks,
            "operacao.tarefas_periodicas",
            "erro",
            f"Faltam {len(faltantes)} tarefa(s) periodica(s) obrigatoria(s). Execute sincronizar_rotinas_celery.",
        )
        return
    _registrar(
        checks,
        "operacao.tarefas_periodicas",
        "ok",
        "Tarefas periodicas principais registradas no scheduler.",
    )


def avaliar_implantacao() -> dict:
    checks: list[dict] = []

    _registrar(
        checks,
        "ambiente.settings_module",
        "ok" if os.getenv("DJANGO_SETTINGS_MODULE") == "config.settings.production" else "aviso",
        (
            "DJANGO_SETTINGS_MODULE aponta para config.settings.production."
            if os.getenv("DJANGO_SETTINGS_MODULE") == "config.settings.production"
            else "DJANGO_SETTINGS_MODULE nao aponta para config.settings.production."
        ),
    )
    _registrar(
        checks,
        "seguranca.debug",
        "ok" if not settings.DEBUG else "erro",
        "DEBUG desativado para producao." if not settings.DEBUG else "DEBUG ainda esta ativo.",
    )

    _verificar_secret_key(checks)
    _verificar_allowed_hosts(checks)
    _verificar_csrf(checks)
    _verificar_email(checks)
    _verificar_canais_oficiais(checks)

    for chave, resultado in (
        ("dependencias.banco_dados", verificar_banco_dados()),
        ("dependencias.migracoes", verificar_migracoes()),
        ("dependencias.redis", verificar_redis(forcar=True)),
    ):
        _registrar(checks, chave, resultado["status"], resultado["detalhe"])

    _verificar_staticfiles(checks)
    _verificar_tarefas_periodicas(checks)

    erros = sum(1 for item in checks if item["status"] == "erro")
    avisos = sum(1 for item in checks if item["status"] == "aviso")
    ignorados = sum(1 for item in checks if item["status"] == "ignorado")
    oks = sum(1 for item in checks if item["status"] == "ok")

    status_geral = "erro" if erros else "aviso" if avisos else "ok"
    return {
        "status": status_geral,
        "resumo": {
            "ok": oks,
            "avisos": avisos,
            "erros": erros,
            "ignorados": ignorados,
        },
        "checks": checks,
    }
