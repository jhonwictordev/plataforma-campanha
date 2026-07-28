#!/usr/bin/env python
"""Provisiona a Plataforma Campanha no Render usando a API oficial.

O token do Render e as strings sensiveis ficam apenas em memoria. O script
salva localmente somente IDs e URLs publicas em .render-deploy-result.json.
"""

from __future__ import annotations

import argparse
import getpass
import json
import secrets
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE_URL = "https://api.render.com/v1"
REPO_URL = "https://github.com/jhonwictordev/plataforma-campanha"
BRANCH = "main"
REGION = "oregon"
RESULT_PATH = Path(".render-deploy-result.json")

WEB_NAME = "plataforma-campanha-web"
DB_NAME = "plataforma-campanha-db"
KV_NAME = "plataforma-campanha-redis"
WORKER_NAME = "plataforma-campanha-celery"
BEAT_NAME = "plataforma-campanha-celery-beat"

TERMINAL_DEPLOY_STATUSES = {
    "live",
    "build_failed",
    "update_failed",
    "canceled",
    "pre_deploy_failed",
}
FAILED_DEPLOY_STATUSES = {
    "build_failed",
    "update_failed",
    "canceled",
    "pre_deploy_failed",
}
READY_RESOURCE_STATUSES = {"available"}


class RenderAPIError(RuntimeError):
    """Erro HTTP da API do Render com corpo legivel."""


def escrever(mensagem: str = "") -> None:
    print(mensagem, flush=True)


def gerar_secret_key() -> str:
    alfabeto = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return "".join(secrets.choice(alfabeto) for _ in range(72))


def chamar_api(
    metodo: str,
    caminho: str,
    token: str,
    corpo: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    url = f"{API_BASE_URL}{caminho}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    dados = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "plataforma-campanha-deploy/1.0",
    }
    if corpo is not None:
        dados = json.dumps(corpo).encode("utf-8")
        headers["Content-Type"] = "application/json"

    requisicao = urllib.request.Request(url, data=dados, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(requisicao, timeout=45) as resposta:
            conteudo = resposta.read().decode("utf-8").strip()
            if not conteudo:
                return None
            return json.loads(conteudo)
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")
        raise RenderAPIError(f"{metodo} {caminho} falhou com HTTP {erro.code}: {detalhe}") from erro
    except urllib.error.URLError as erro:
        raise RenderAPIError(f"{metodo} {caminho} falhou: {erro.reason}") from erro


def listar_recursos(endpoint: str, token: str, chave: str) -> list[dict[str, Any]]:
    recursos: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        query = {"limit": "100"}
        if cursor:
            query["cursor"] = cursor
        resposta = chamar_api("GET", endpoint, token, query=query)
        if not isinstance(resposta, list):
            break

        proximo_cursor = None
        for item in resposta:
            recurso = item.get(chave, item) if isinstance(item, dict) else item
            if isinstance(recurso, dict):
                recursos.append(recurso)
            if isinstance(item, dict) and item.get("cursor"):
                proximo_cursor = item["cursor"]

        if not proximo_cursor:
            break
        cursor = proximo_cursor
    return recursos


def buscar_por_nome(endpoint: str, token: str, chave: str, nome: str) -> dict[str, Any] | None:
    for recurso in listar_recursos(endpoint, token, chave):
        if recurso.get("name") == nome:
            return recurso
    return None


def selecionar_workspace(token: str, owner_id: str | None) -> str:
    owners = listar_recursos("/owners", token, "owner")
    if not owners:
        raise RenderAPIError("Nenhum workspace Render foi retornado para esta chave.")

    if owner_id:
        if any(owner.get("id") == owner_id for owner in owners):
            return owner_id
        raise RenderAPIError(f"O workspace {owner_id} nao esta disponivel para esta chave.")

    if len(owners) == 1:
        owner = owners[0]
        escrever(f"Workspace selecionado: {owner.get('name')} ({owner.get('id')})")
        return str(owner["id"])

    escrever("Workspaces disponiveis:")
    for indice, owner in enumerate(owners, start=1):
        escrever(f"{indice}. {owner.get('name')} ({owner.get('id')})")
    while True:
        escolha = input("Escolha o numero do workspace: ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(owners):
            return str(owners[int(escolha) - 1]["id"])
        escrever("Escolha invalida.")


def confirmar_custos(profile: str, confirmar_pago: bool) -> None:
    if profile != "production-starter":
        return
    escrever()
    escrever("O perfil production-starter cria recursos pagos no Render:")
    escrever("- 1 web service starter")
    escrever("- 1 Postgres starter/basic")
    escrever("- 1 Key Value starter")
    escrever("- 2 background workers starter")
    escrever()
    escrever("A conta Render pode cobrar por estes recursos. Revise os valores no painel Render.")
    if confirmar_pago:
        return
    confirmacao = input("Digite CONFIRMO para prosseguir com recursos pagos: ").strip()
    if confirmacao != "CONFIRMO":
        raise RenderAPIError("Operacao cancelada sem criar recursos pagos.")


def criar_ou_reusar_postgres(token: str, owner_id: str, profile: str) -> dict[str, Any]:
    existente = buscar_por_nome("/postgres", token, "postgres", DB_NAME)
    if existente:
        escrever(f"Postgres existente encontrado: {DB_NAME}")
        return existente

    plano = "free" if profile == "demo-free" else "starter"
    corpo = {
        "name": DB_NAME,
        "databaseName": "plataforma_campanha",
        "databaseUser": "plataforma_campanha",
        "ownerId": owner_id,
        "plan": plano,
        "region": REGION,
        "version": "17",
        "ipAllowList": [],
    }
    escrever(f"Criando Postgres {DB_NAME} ({plano})...")
    return chamar_api("POST", "/postgres", token, corpo)


def criar_ou_reusar_key_value(token: str, owner_id: str, profile: str) -> dict[str, Any]:
    existente = buscar_por_nome("/key-value", token, "keyValue", KV_NAME)
    if existente:
        escrever(f"Key Value existente encontrado: {KV_NAME}")
        return existente

    plano = "free" if profile == "demo-free" else "starter"
    corpo = {
        "name": KV_NAME,
        "ownerId": owner_id,
        "plan": plano,
        "region": REGION,
        "maxmemoryPolicy": "allkeys_lru",
        "persistenceMode": "off" if profile == "demo-free" else "journal_snapshot",
        "ipAllowList": [],
    }
    escrever(f"Criando Key Value {KV_NAME} ({plano})...")
    return chamar_api("POST", "/key-value", token, corpo)


def aguardar_recurso(
    token: str,
    endpoint: str,
    recurso_id: str,
    nome: str,
    timeout_segundos: int = 900,
) -> dict[str, Any]:
    fim = time.time() + timeout_segundos
    ultimo_status = None
    while time.time() < fim:
        recurso = chamar_api("GET", f"{endpoint}/{recurso_id}", token)
        status = recurso.get("status")
        if status != ultimo_status:
            escrever(f"{nome}: status {status}")
            ultimo_status = status
        if status in READY_RESOURCE_STATUSES:
            return recurso
        if status in {"unavailable", "suspended", "unknown"}:
            raise RenderAPIError(f"{nome} ficou com status {status}.")
        time.sleep(15)
    raise RenderAPIError(f"Tempo esgotado aguardando {nome}.")


def obter_conexao(token: str, endpoint: str, recurso_id: str) -> dict[str, str]:
    conexao = chamar_api("GET", f"{endpoint}/{recurso_id}/connection-info", token)
    if not isinstance(conexao, dict) or not conexao.get("internalConnectionString"):
        raise RenderAPIError(f"Nao foi possivel obter a conexao interna de {endpoint}/{recurso_id}.")
    return conexao


def env_vars_base(database_url: str, redis_url: str, secret_key: str) -> list[dict[str, str]]:
    return [
        {"key": "PYTHON_VERSION", "value": "3.12.4"},
        {"key": "DJANGO_SETTINGS_MODULE", "value": "config.settings.production"},
        {"key": "DEBUG", "value": "False"},
        {"key": "SECRET_KEY", "value": secret_key},
        {"key": "DATABASE_URL", "value": database_url},
        {"key": "REDIS_URL", "value": redis_url},
        {"key": "CELERY_BROKER_URL", "value": redis_url},
        {"key": "CELERY_RESULT_BACKEND", "value": redis_url},
        {"key": "HEALTHCHECK_VERIFY_REDIS", "value": "True"},
        {"key": "EMAIL_BACKEND", "value": "django.core.mail.backends.console.EmailBackend"},
        {"key": "ALLOWED_HOSTS", "value": ".onrender.com"},
        {"key": "CSRF_TRUSTED_ORIGINS", "value": "https://*.onrender.com"},
        {"key": "DEFAULT_FROM_EMAIL", "value": "nao-responda@plataformacampanha.local"},
    ]


def criar_ou_reusar_servico(
    token: str,
    owner_id: str,
    nome: str,
    tipo: str,
    plano: str,
    env_vars: list[dict[str, str]],
    start_command: str,
    health_check_path: str | None = None,
    pre_deploy_command: str | None = None,
) -> dict[str, Any]:
    existente = buscar_por_nome("/services", token, "service", nome)
    if existente:
        escrever(f"Servico existente encontrado: {nome}")
        return existente

    detalhes: dict[str, Any] = {
        "runtime": "python",
        "plan": plano,
        "region": REGION,
        "envSpecificDetails": {
            "buildCommand": "sh scripts/build.sh",
            "startCommand": start_command,
        },
    }
    if tipo == "web_service":
        detalhes["numInstances"] = 1
    if health_check_path:
        detalhes["healthCheckPath"] = health_check_path
    if pre_deploy_command:
        detalhes["preDeployCommand"] = pre_deploy_command

    corpo = {
        "type": tipo,
        "name": nome,
        "ownerId": owner_id,
        "repo": REPO_URL,
        "branch": BRANCH,
        "autoDeploy": "yes",
        "envVars": env_vars,
        "serviceDetails": detalhes,
    }
    escrever(f"Criando servico {nome} ({tipo}, {plano})...")
    return chamar_api("POST", "/services", token, corpo)


def ultimo_deploy(token: str, service_id: str) -> dict[str, Any] | None:
    deploys = chamar_api("GET", f"/services/{service_id}/deploys", token, query={"limit": "1"})
    if isinstance(deploys, list) and deploys:
        item = deploys[0]
        return item.get("deploy", item) if isinstance(item, dict) else None
    return None


def disparar_deploy_se_preciso(token: str, service_id: str) -> dict[str, Any]:
    deploy = ultimo_deploy(token, service_id)
    if deploy and deploy.get("status") not in FAILED_DEPLOY_STATUSES:
        return deploy
    escrever("Disparando deploy do servico web...")
    return chamar_api("POST", f"/services/{service_id}/deploys", token, {})


def aguardar_deploy(token: str, service_id: str, deploy_id: str, timeout_segundos: int = 1800) -> dict[str, Any]:
    fim = time.time() + timeout_segundos
    ultimo_status = None
    while time.time() < fim:
        deploy = chamar_api("GET", f"/services/{service_id}/deploys/{deploy_id}", token)
        status = deploy.get("status")
        if status != ultimo_status:
            escrever(f"Deploy web: status {status}")
            ultimo_status = status
        if status in TERMINAL_DEPLOY_STATUSES:
            if status in FAILED_DEPLOY_STATUSES:
                raise RenderAPIError(f"Deploy web terminou com status {status}.")
            return deploy
        time.sleep(20)
    raise RenderAPIError("Tempo esgotado aguardando deploy web.")


def url_do_servico(servico: dict[str, Any]) -> str:
    detalhes = servico.get("serviceDetails") or {}
    url = detalhes.get("url")
    if url:
        return str(url)
    slug = servico.get("slug") or WEB_NAME
    return f"https://{slug}.onrender.com"


def salvar_resultado(resultado: dict[str, Any]) -> None:
    RESULT_PATH.write_text(json.dumps(resultado, indent=2, ensure_ascii=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy seguro da Plataforma Campanha no Render.")
    parser.add_argument(
        "--profile",
        choices=["demo-free", "production-starter"],
        default="demo-free",
        help="demo-free cria web/db/cache gratuitos sem workers; production-starter cria ambiente completo e pago.",
    )
    parser.add_argument("--owner-id", help="Workspace ID do Render. Se omitido, o script lista e pergunta.")
    parser.add_argument(
        "--confirm-paid",
        action="store_true",
        help="Pula a digitacao de CONFIRMO para o perfil production-starter.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    escrever("Deploy Render API - Plataforma Campanha")
    escrever("O token nao sera salvo em arquivo nem exibido.")
    token = getpass.getpass("Render API key: ").strip()
    if not token:
        escrever("Token nao informado.")
        return 2

    try:
        confirmar_custos(args.profile, args.confirm_paid)
        owner_id = selecionar_workspace(token, args.owner_id)
        postgres = criar_ou_reusar_postgres(token, owner_id, args.profile)
        key_value = criar_ou_reusar_key_value(token, owner_id, args.profile)

        postgres_id = str(postgres["id"])
        key_value_id = str(key_value["id"])
        aguardar_recurso(token, "/postgres", postgres_id, DB_NAME)
        aguardar_recurso(token, "/key-value", key_value_id, KV_NAME)

        database_url = obter_conexao(token, "/postgres", postgres_id)["internalConnectionString"]
        redis_url = obter_conexao(token, "/key-value", key_value_id)["internalConnectionString"]
        secret_key = gerar_secret_key()

        env_vars = env_vars_base(database_url, redis_url, secret_key)
        web_plan = "free" if args.profile == "demo-free" else "starter"
        web = criar_ou_reusar_servico(
            token=token,
            owner_id=owner_id,
            nome=WEB_NAME,
            tipo="web_service",
            plano=web_plan,
            env_vars=env_vars
            + [
                {"key": "WEB_CONCURRENCY", "value": "2"},
                {"key": "GUNICORN_TIMEOUT", "value": "120"},
                {"key": "GUNICORN_GRACEFUL_TIMEOUT", "value": "30"},
            ],
            start_command="sh scripts/start-web.sh",
            health_check_path="/saude/prontidao/",
            pre_deploy_command=(
                "sh scripts/predeploy-demo.sh" if args.profile == "demo-free" else "sh scripts/predeploy.sh"
            ),
        )

        workers: list[dict[str, Any]] = []
        if args.profile == "production-starter":
            workers.append(
                criar_ou_reusar_servico(
                    token=token,
                    owner_id=owner_id,
                    nome=WORKER_NAME,
                    tipo="background_worker",
                    plano="starter",
                    env_vars=env_vars + [{"key": "CELERY_LOG_LEVEL", "value": "info"}],
                    start_command="sh scripts/start-worker.sh",
                )
            )
            workers.append(
                criar_ou_reusar_servico(
                    token=token,
                    owner_id=owner_id,
                    nome=BEAT_NAME,
                    tipo="background_worker",
                    plano="starter",
                    env_vars=env_vars + [{"key": "CELERY_LOG_LEVEL", "value": "info"}],
                    start_command="sh scripts/start-beat.sh",
                )
            )
        else:
            escrever("Perfil demo-free: workers Celery nao serao criados.")

        web_id = str(web["id"])
        deploy = disparar_deploy_se_preciso(token, web_id)
        deploy_id = str(deploy["id"])
        aguardar_deploy(token, web_id, deploy_id)

        web_atualizado = chamar_api("GET", f"/services/{web_id}", token)
        public_url = url_do_servico(web_atualizado)
        resultado = {
            "repo": REPO_URL,
            "branch": BRANCH,
            "profile": args.profile,
            "public_url": public_url,
            "health_url": f"{public_url.rstrip('/')}/saude/prontidao/",
            "web_service_id": web_id,
            "postgres_id": postgres_id,
            "key_value_id": key_value_id,
            "worker_service_ids": [worker.get("id") for worker in workers],
            "dashboard_url": web_atualizado.get("dashboardUrl"),
        }
        salvar_resultado(resultado)

        escrever()
        escrever("Deploy concluido.")
        escrever(f"URL publica: {resultado['public_url']}")
        escrever(f"Health check: {resultado['health_url']}")
        escrever(f"Resumo local salvo em {RESULT_PATH}")
        return 0
    except RenderAPIError as erro:
        escrever()
        escrever(f"ERRO: {erro}")
        return 1
    finally:
        token = ""


if __name__ == "__main__":
    sys.exit(main())
