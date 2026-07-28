# Deploy da Plataforma Campanha

Este guia descreve uma implantacao segura para a versao atual do sistema em ambientes Linux com PostgreSQL, Redis, Gunicorn, Celery e proxy reverso HTTPS.

## 1. Requisitos do servidor

- Python 3.12 ou superior
- PostgreSQL 15 ou superior
- Redis 7 ou superior
- Nginx ou outro proxy reverso com TLS
- Acesso para executar `systemd` ou processo equivalente

## 2. Variaveis de ambiente obrigatorias

Defina um `.env` privado no servidor com valores reais para:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=gere_uma_chave_longa_e_exclusiva
DEBUG=False
ALLOWED_HOSTS=seu-dominio.com,www.seu-dominio.com
CSRF_TRUSTED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com
DATABASE_URL=

POSTGRES_DB=plataforma_campanha
POSTGRES_USER=usuario_aplicacao
POSTGRES_PASSWORD=senha_forte_e_unica
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
HEALTHCHECK_VERIFY_REDIS=True
DEFAULT_FROM_EMAIL=nao-responda@seu-dominio.com
OTP_TOTP_ISSUER=Plataforma Campanha
WHATSAPP_OFFICIAL_API_URL=https://api-oficial-whatsapp.exemplo.com/messages
WHATSAPP_OFFICIAL_API_TOKEN=defina_token_oficial_whatsapp
WHATSAPP_OFFICIAL_WEBHOOK_TOKEN=defina_token_webhook_whatsapp
SMS_OFFICIAL_API_URL=https://api-oficial-sms.exemplo.com/messages
SMS_OFFICIAL_API_TOKEN=defina_token_oficial_sms
SMS_OFFICIAL_WEBHOOK_TOKEN=defina_token_webhook_sms
EMAIL_OFFICIAL_WEBHOOK_TOKEN=defina_token_webhook_email
```

Se a plataforma de hospedagem fornecer apenas uma string unica de conexao com PostgreSQL, use `DATABASE_URL`. Quando ela estiver preenchida, o sistema passa a ignorar `POSTGRES_*`.

## 3. Preparacao da aplicacao

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Se quiser um ambiente pronto para demonstracao, use apenas dados ficticios:

```bash
python manage.py popular_dados_demo --limpar
```

## 4. Processos recomendados

### Gunicorn

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

### Celery worker

```bash
celery -A config worker -l info
```

### Celery beat

```bash
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Depois de subir as migrations, registre as rotinas padrao no scheduler:

```bash
python manage.py sincronizar_rotinas_celery
```

Antes de abrir o ambiente para usuarios reais, rode tambem o preflight de implantacao:

```bash
python manage.py verificar_implantacao --strict
```

Na versao atual, a rotina `Plataforma - Comunicacoes agendadas` executa o processamento assíncrono das campanhas vencidas. Se os canais `whatsapp` ou `sms` estiverem sem integracao oficial configurada, a campanha sera pausada com trilha de erro e notificacao interna.

Para uma verificacao manual ou homologacao controlada, voce tambem pode forcar o processamento pelo shell:

```bash
python manage.py shell -c "from comunicacao.services import processar_campanhas_agendadas; print(processar_campanhas_agendadas())"
```

Para reconciliar retorno oficial de status, configure os endpoints abaixo no provedor correspondente e envie o segredo em `X-Webhook-Token`:

- `https://seu-dominio.com/api/v1/comunicacao/webhooks/whatsapp/`
- `https://seu-dominio.com/api/v1/comunicacao/webhooks/sms/`
- `https://seu-dominio.com/api/v1/comunicacao/webhooks/email/`

## 5. Proxy reverso

- Exponha apenas HTTPS para o publico.
- Encaminhe as requisicoes para `127.0.0.1:8000`.
- Preserve `X-Forwarded-Proto=https` para manter as configuracoes seguras de cookie.

## 6. Checklist de producao

- `python manage.py check --deploy`
- `python manage.py test --settings=config.settings.test`
- `DEBUG=False`
- `SECRET_KEY` fora do codigo
- `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` definidos com dominios reais
- Banco e Redis acessiveis apenas pela rede interna
- Rotina de backup configurada
- Politicas de retencao revisadas com apoio juridico e contabil
- Endpoint `/saude/prontidao/` configurado como health check do provedor
- `OTP_TOTP_ISSUER` revisado se a autenticacao em dois fatores estiver habilitada
- `python manage.py verificar_implantacao --strict` sem erros nem avisos

## 7. Backup operacional

Backup em JSON, portavel e sem depender do cliente PostgreSQL:

```bash
python manage.py backup_banco --formato json
```

Backup SQL, quando `pg_dump` estiver instalado no servidor:

```bash
python manage.py backup_banco --formato sql
```

Se o binario nao estiver no `PATH`, defina a variavel opcional `PG_DUMP_BIN`.

## 8. Observacoes LGPD e governanca

- Use somente dados autorizados no ambiente produtivo.
- Nao replique bases reais em homologacao sem anonimizar.
- Revise periodicamente o modulo `auditoria` para acompanhar logs, solicitacoes do titular e politicas de retencao.
- Toda validacao final de regras eleitorais, contabeis e de tratamento de dados deve passar por apoio juridico e contabil especializado.

## 9. Blueprint Render

O repositorio inclui um `render.yaml` pronto para Blueprint com:

- 1 web service Django/Gunicorn
- 1 worker Celery
- 1 beat Celery
- 1 Render Key Value
- 1 banco PostgreSQL gerenciado

Antes da primeira sincronizacao, revise os planos e preencha manualmente as variaveis marcadas com `sync: false`.
Use a mesma `SECRET_KEY`, os mesmos `ALLOWED_HOSTS` e as mesmas `CSRF_TRUSTED_ORIGINS` nos tres servicos Django/Celery do blueprint.
O blueprint usa scripts versionados em `scripts/` para build, predeploy e start, reduzindo divergencia entre ambiente local, Docker e Render.

Link direto para criar o Blueprint no Render:

```text
https://dashboard.render.com/blueprint/new?repo=https%3A%2F%2Fgithub.com%2Fjhonwictordev%2Fplataforma-campanha
```

## 10. Deploy via API do Render

Quando o deploy pelo Dashboard nao for pratico, use o script local abaixo. Ele pede a API key do Render em prompt seguro, nao grava o token, gera `SECRET_KEY` em memoria e salva apenas IDs e URLs publicas em `.render-deploy-result.json`.

Ambiente completo e estavel:

```bash
python scripts/deploy_render_api.py --profile production-starter
```

Demonstracao sem workers Celery:

```bash
python scripts/deploy_render_api.py --profile demo-free
```

No perfil `production-starter`, o script exige confirmacao digitando `CONFIRMO` antes de criar recursos pagos. Revogue a API key no Render apos o deploy se ela tiver sido criada apenas para esta operacao.
