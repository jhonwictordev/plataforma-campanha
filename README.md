# Plataforma de Campanha

Sistema web modular para gestão de campanhas políticas com foco em operação territorial, relacionamento, metas, finanças, agenda, comunicação e governança de dados.

## Arquitetura inicial

- `config`: settings por ambiente, URLs globais, WSGI/ASGI e Celery.
- `core`: abstrações compartilhadas para soft delete, scoping por campanha, middleware e mixins.
- `usuarios`: autenticação, perfil, papéis de acesso e vínculo do usuário à campanha.
- `campanhas`: cadastro central da campanha e dados do candidato.
- `liderancas`, `eleitores`, `agenda`, `equipe`, `metas`, `financeiro`, `comunicacao`, `dashboard`, `mapa_eleitoral`, `relatorios`, `auditoria`: domínios separados para evolução incremental.

## Estrutura de pastas

```text
plataforma_campanha/
├── agenda/
├── auditoria/
├── campanhas/
├── comunicacao/
├── config/
│   ├── settings/
│   ├── celery.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── core/
├── dashboard/
├── eleitores/
├── equipe/
├── financeiro/
├── liderancas/
├── mapa_eleitoral/
├── metas/
├── relatorios/
├── static/
│   ├── css/
│   └── js/
├── templates/
│   ├── campanhas/
│   ├── dashboard/
│   ├── includes/
│   ├── registration/
│   └── usuarios/
├── usuarios/
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── requirements.txt
```

## Requisitos

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Docker e Docker Compose

## Segurança básica do repositório

- O arquivo `.env` não deve ser versionado.
- O `.gitignore` cobre `.env` e variantes como `.env.local`, `.env.prod` e similares.
- O build Docker ignora `.env`, `.git`, `.venv` e caches locais.
- O arquivo `.env.example` contém apenas placeholders e nunca deve receber segredos reais.
- Em produção, `SECRET_KEY` ausente interrompe a inicialização da aplicação.
- Em produção, `DEBUG=False` é forçado por [config/settings/production.py](/C:/Users/jhon/Documents/New%20project/plataforma_campanha/config/settings/production.py).
- `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` são validados em produção e exigem domínios/origens explícitos.
- Cookies de sessão e CSRF usam `HttpOnly`, `SameSite=Lax` e, em produção, `Secure=True`.
- PostgreSQL e Redis não são publicados para fora do Docker Compose.

## Instalação local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Execução com Docker

```bash
copy .env.example .env
docker compose up --build
```

## Serviços disponíveis

- Aplicação web: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- Admin Django: `http://localhost:8000/admin/`

## Próximos passos sugeridos

1. Gerar migrations reais com o ambiente Python configurado.
2. Implementar CRUD completo e API REST de cada domínio.
3. Adicionar testes automatizados por app.
4. Criar carga de dados fictícios para demonstração.
5. Configurar trilhas automáticas de auditoria com signals e middleware.
