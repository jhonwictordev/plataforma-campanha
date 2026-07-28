# Plataforma Campanha

Sistema web completo para gestao de campanhas politicas com Django, PostgreSQL, Bootstrap, Chart.js, Leaflet, Celery e Redis. O projeto centraliza CRM eleitoral, liderancas, agenda, equipe, metas, financeiro, comunicacao, dashboard, mapa territorial, relatorios e auditoria com foco em seguranca e LGPD.

## Principais modulos

- `usuarios`: autenticacao, perfil, papeis e vinculo por campanha
- `campanhas`: cadastro do candidato, dados eleitorais e configuracao da operacao
- `liderancas`: liderancas territoriais e historico de relacionamento
- `eleitores`: CRM de contatos, apoiadores, interacoes e tarefas de retorno
- `agenda`: compromissos, eventos e conflitos de horario
- `equipe`: integrantes, responsabilidades e quadro Kanban
- `metas`: indicadores, progresso e acompanhamento por equipe
- `financeiro`: receitas, despesas, parceiros, categorias e centros de custo
- `comunicacao`: modelos, campanhas, envios, bloqueios e status
- `dashboard`: visao executiva com graficos e indicadores
- `mapa_eleitoral`: painel territorial com Leaflet e filtros por campanha
- `relatorios`: filtros, exportacao PDF/Excel e favoritos
- `auditoria`: trilha de alteracoes, logs de seguranca, retencao e demandas LGPD

## Stack

- Python 3.12+
- Django
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Bootstrap 5
- Chart.js
- Leaflet.js
- Gunicorn
- WhiteNoise
- Docker e Docker Compose

## Estrutura do projeto

```text
plataforma_campanha/
|-- agenda/
|-- auditoria/
|-- campanhas/
|-- comunicacao/
|-- config/
|   |-- settings/
|   |-- celery.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- core/
|   |-- management/
|   |   `-- commands/
|   `-- demo_seed.py
|-- dashboard/
|-- docs/
|-- eleitores/
|-- equipe/
|-- financeiro/
|-- liderancas/
|-- mapa_eleitoral/
|-- metas/
|-- relatorios/
|-- static/
|-- templates/
|-- usuarios/
|-- .env.example
|-- docker-compose.yml
|-- Dockerfile
|-- manage.py
`-- requirements.txt
```

## Configuracao local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Execucao com Docker

```bash
copy .env.example .env
docker compose up --build
```

Servicos principais:

- Aplicacao: `http://localhost:8000`
- Admin Django: `http://localhost:8000/admin/`
- Swagger: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`

## Comandos operacionais

Popular o ambiente com dados ficticios para demonstracao, treinamento ou QA:

```bash
python manage.py popular_dados_demo --limpar
```

Exemplo com volume customizado:

```bash
python manage.py popular_dados_demo --campanhas 2 --contatos 15 --liderancas 8 --eventos 5
```

Gerar backup em JSON:

```bash
python manage.py backup_banco --formato json
```

Gerar backup SQL com PostgreSQL:

```bash
python manage.py backup_banco --formato sql
```

Sincronizar as rotinas periodicas do `django-celery-beat`:

```bash
python manage.py sincronizar_rotinas_celery
```

Processar comunicacoes agendadas imediatamente, sem esperar o proximo ciclo do `beat`:

```bash
python manage.py shell -c "from comunicacao.services import processar_campanhas_agendadas; print(processar_campanhas_agendadas())"
```

Todos os dados gerados por `popular_dados_demo` sao sinteticos e usam o dominio ficticio `@demo.plataformacampanha.local`. A senha padrao dos usuarios demo e `Demo2026!`.

## Integracoes oficiais de comunicacao

- `email`: usa o backend oficial configurado em `EMAIL_BACKEND` e `DEFAULT_FROM_EMAIL`
- `whatsapp`: exige `WHATSAPP_OFFICIAL_API_URL` e `WHATSAPP_OFFICIAL_API_TOKEN`
- `sms`: exige `SMS_OFFICIAL_API_URL` e `SMS_OFFICIAL_API_TOKEN`
- `notificacao_interna`: envia alertas internos vinculados aos responsaveis do contato e da campanha

Se uma campanha de WhatsApp ou SMS chegar ao horario de execucao sem a integracao oficial configurada, o sistema pausa a campanha, registra o erro e notifica o responsavel internamente em vez de tentar um disparo inseguro.

## Webhooks oficiais

O sistema agora aceita retornos oficiais de status para reconciliar entrega, falha, resposta e descadastro:

- `POST /api/v1/comunicacao/webhooks/whatsapp/`
- `POST /api/v1/comunicacao/webhooks/sms/`
- `POST /api/v1/comunicacao/webhooks/email/`

Cada endpoint exige o header `X-Webhook-Token` com o segredo correspondente:

- `WHATSAPP_OFFICIAL_WEBHOOK_TOKEN`
- `SMS_OFFICIAL_WEBHOOK_TOKEN`
- `EMAIL_OFFICIAL_WEBHOOK_TOKEN`

Os payloads recebidos sao mascarados no log tecnico para reduzir exposicao de dados pessoais, e a conciliacao atualiza o `EnvioComunicacao` com status e trilha de retorno sem permitir acesso cruzado entre campanhas.

## Testes e validacao

```bash
python manage.py check
python manage.py makemigrations --check --dry-run --noinput --settings=config.settings.test
python manage.py test --settings=config.settings.test
```

## Saude da aplicacao

Para monitoramento e deploy automatizado, o projeto expoe endpoints publicos de saude:

- `GET /saude/`: valida que o processo web esta respondendo
- `GET /saude/prontidao/`: valida banco, migrations e opcionalmente Redis

Se quiser que a prontidao tambem falhe quando Redis estiver indisponivel, habilite:

```env
HEALTHCHECK_VERIFY_REDIS=True
```

## Seguranca

- `.env` real deve permanecer fora do Git
- `.env.example` contem apenas placeholders
- `SECRET_KEY` e credenciais nunca devem ficar no codigo ou no `docker-compose.yml`
- producao exige `DEBUG=False`
- `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` precisam ser configurados explicitamente
- `DATABASE_URL` pode ser usado em plataformas como Render; se ele estiver definido, tem prioridade sobre `POSTGRES_*`
- cookies de sessao e CSRF usam configuracoes seguras no ambiente de producao
- PostgreSQL e Redis nao ficam expostos publicamente pelo `docker-compose.yml`
- o sistema usa trilha de auditoria, logs de seguranca, soft delete e isolamento por campanha

## Deploy

O passo a passo completo de implantacao esta em [docs/deploy.md](docs/deploy.md).

O repositorio tambem inclui:

- `render.yaml` para blueprint de deploy com web, Redis, worker, beat e PostgreSQL
- `.github/workflows/ci.yml` para checks e testes automaticos no GitHub

No fluxo do Render, preencha a mesma `SECRET_KEY`, os mesmos `ALLOWED_HOSTS` e as mesmas `CSRF_TRUSTED_ORIGINS` para web, worker e beat.

Resumo rapido:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 127.0.0.1:8000
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
python manage.py sincronizar_rotinas_celery
```

## Observacoes finais

- O sistema foi estruturado para separar dados por campanha e restringir acesso conforme o perfil do usuario.
- Dados de contatos, liderancas e operacao devem ser usados com consentimento valido e finalidades legitimas.
- Regras eleitorais, contabilizacao e retencao de dados podem variar; a validacao final deve contar com apoio juridico e contabil.
