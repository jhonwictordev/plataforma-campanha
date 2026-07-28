import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def obter_booleano(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome, str(padrao))
    return valor.lower() in {"1", "true", "t", "sim", "yes", "y"}


def obter_lista(nome: str, padrao: str = "") -> list[str]:
    bruto = os.getenv(nome, padrao)
    return [item.strip() for item in bruto.split(",") if item.strip()]


def obter_texto_obrigatorio(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise ImproperlyConfigured(f"A variável de ambiente {nome} é obrigatória.")
    return valor


def obter_configuracao_banco() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ImproperlyConfigured("DATABASE_URL deve usar o esquema postgres:// ou postgresql://.")
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or "5432"),
        }

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": obter_texto_obrigatorio("POSTGRES_DB"),
        "USER": obter_texto_obrigatorio("POSTGRES_USER"),
        "PASSWORD": obter_texto_obrigatorio("POSTGRES_PASSWORD"),
        "HOST": obter_texto_obrigatorio("POSTGRES_HOST"),
        "PORT": obter_texto_obrigatorio("POSTGRES_PORT"),
    }


def validar_configuracao_producao() -> None:
    hosts_invalidos = {"localhost", "127.0.0.1", "[::1]"}
    if not ALLOWED_HOSTS or set(ALLOWED_HOSTS).issubset(hosts_invalidos):
        raise ImproperlyConfigured(
            "Defina ALLOWED_HOSTS com os domínios públicos válidos antes de iniciar em produção."
        )
    if not CSRF_TRUSTED_ORIGINS:
        raise ImproperlyConfigured(
            "Defina CSRF_TRUSTED_ORIGINS com as origens HTTPS válidas antes de iniciar em produção."
        )
    origens_invalidas = [origem for origem in CSRF_TRUSTED_ORIGINS if not origem.startswith("https://")]
    if origens_invalidas:
        raise ImproperlyConfigured(
            "Em produção, CSRF_TRUSTED_ORIGINS deve usar apenas URLs HTTPS explícitas."
        )


DEBUG = obter_booleano("DEBUG", True)
SECRET_KEY = obter_texto_obrigatorio("SECRET_KEY")
ALLOWED_HOSTS = obter_lista("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = obter_lista("CSRF_TRUSTED_ORIGINS", "http://localhost:8000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "django_celery_beat",
    "django_celery_results",
    "core",
    "usuarios",
    "campanhas",
    "liderancas",
    "eleitores",
    "agenda",
    "equipe",
    "metas",
    "financeiro",
    "comunicacao",
    "dashboard",
    "mapa_eleitoral",
    "relatorios",
    "auditoria",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "core.middleware.UltimoAcessoMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.aplicacao_info",
            ],
        },
    },
]

DATABASES = {
    "default": obter_configuracao_banco()
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pt-br")
TIME_ZONE = os.getenv("TIME_ZONE", "America/Fortaleza")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "usuarios.Usuario"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        "user": "600/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Plataforma de Campanha",
    "DESCRIPTION": "API REST para gestão de campanhas políticas com foco em governança, LGPD e territorialidade.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "AgendaTipoEnum": "agenda.models.EventoAgenda.Tipos",
        "FinanceiroTipoEnum": [
            ("receita", "Receita"),
            ("despesa", "Despesa"),
            ("doacao", "Doacao"),
        ],
        "ParceiroFinanceiroTipoEnum": "financeiro.models.ParceiroFinanceiro.Tipos",
        "InteracaoLiderancaTipoEnum": "liderancas.models.InteracaoLideranca.Tipos",
        "MetaCampanhaTipoEnum": "metas.models.MetaCampanha.Tipos",
    },
}

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "nao-responda@plataformacampanha.local")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/1"))
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "padrao": {
            "format": "%(levelname)s %(asctime)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "padrao",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
