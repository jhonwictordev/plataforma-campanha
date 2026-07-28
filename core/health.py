import os

from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from redis import Redis


def _obter_booleano_ambiente(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome, str(padrao))
    return valor.lower() in {"1", "true", "t", "sim", "yes", "y"}


def verificar_banco_dados() -> dict:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover - caminho coberto pelos testes de view com mock
        return {"status": "erro", "detalhe": f"Falha ao consultar o banco de dados: {exc}"}
    return {"status": "ok", "detalhe": "Conexao com o banco validada."}


def verificar_migracoes() -> dict:
    try:
        executor = MigrationExecutor(connections["default"])
        pendentes = executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception as exc:  # pragma: no cover - caminho coberto pelos testes de view com mock
        return {"status": "erro", "detalhe": f"Falha ao validar migrations: {exc}"}

    if pendentes:
        return {
            "status": "erro",
            "detalhe": f"Foram encontradas {len(pendentes)} migration(s) pendente(s).",
            "pendentes": len(pendentes),
        }
    return {"status": "ok", "detalhe": "Todas as migrations foram aplicadas."}


def verificar_redis() -> dict:
    if not _obter_booleano_ambiente("HEALTHCHECK_VERIFY_REDIS", False):
        return {"status": "ignorado", "detalhe": "Verificacao opcional de Redis desabilitada."}

    redis_url = (os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or "").strip()
    if not redis_url:
        return {"status": "ignorado", "detalhe": "Redis nao configurado neste ambiente."}

    cliente = None
    try:
        cliente = Redis.from_url(redis_url)
        cliente.ping()
    except Exception as exc:  # pragma: no cover - depende do ambiente externo
        return {"status": "erro", "detalhe": f"Falha ao conectar ao Redis: {exc}"}
    finally:
        if cliente is not None:
            cliente.close()

    return {"status": "ok", "detalhe": "Redis acessivel para tarefas assincronas."}


def obter_estado_prontidao() -> tuple[dict, int]:
    componentes = {
        "banco_dados": verificar_banco_dados(),
        "migracoes": verificar_migracoes(),
        "redis": verificar_redis(),
    }
    houve_falha = any(item["status"] == "erro" for item in componentes.values())
    status_http = 503 if houve_falha else 200
    status = "erro" if houve_falha else "ok"

    return (
        {
            "status": status,
            "aplicacao": "plataforma_campanha",
            "verificado_em": timezone.now().isoformat(),
            "componentes": componentes,
        },
        status_http,
    )
