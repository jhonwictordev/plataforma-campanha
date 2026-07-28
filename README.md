# Plataforma Campanha

Modular campaign management platform built for political teams. The project centralizes campaign operations, territory coordination, voter relationships, goals, finance, agenda, communication, and reporting in a single Django-based system.

## Overview

- Multi-domain architecture for campaign operations and data governance
- Django REST API support with JWT authentication
- PostgreSQL persistence with Redis and Celery for background jobs
- API documentation through OpenAPI, Swagger, and ReDoc
- Export support for spreadsheets and PDF reports
- Security-focused production settings and environment handling

## Main Domains

- `campanhas`: campaign registration and candidate information
- `usuarios`: authentication, profiles, roles, and campaign access
- `liderancas`: local leadership and field coordination
- `eleitores`: voter relationship and territory tracking
- `agenda`: events, appointments, and scheduling
- `equipe`: team structure and responsibilities
- `metas`: performance goals and follow-up
- `financeiro`: campaign financial control
- `comunicacao`: communication workflows and messaging
- `dashboard`: summary views and operational metrics
- `mapa_eleitoral`: electoral territory mapping
- `relatorios`: export and reporting flows
- `auditoria`: change history and traceability

## Stack

- Django 5
- Django REST Framework
- Simple JWT
- PostgreSQL
- Redis
- Celery
- Bootstrap
- Chart.js
- WhiteNoise
- Gunicorn

## Project Structure

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
|-- dashboard/
|-- eleitores/
|-- equipe/
|-- financeiro/
|-- liderancas/
|-- mapa_eleitoral/
|-- metas/
|-- relatorios/
|-- static/
|   |-- css/
|   `-- js/
|-- templates/
|   |-- campanhas/
|   |-- dashboard/
|   |-- includes/
|   |-- registration/
|   `-- usuarios/
|-- usuarios/
|-- .env.example
|-- docker-compose.yml
|-- Dockerfile
|-- manage.py
`-- requirements.txt
```

## Requirements

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose

## Local Setup

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

## Docker

```bash
copy .env.example .env
docker compose up --build
```

## Available Services

- Web application: `http://localhost:8000`
- Swagger / OpenAPI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- Django admin: `http://localhost:8000/admin/`

## Security Notes

- `.env` files must never be committed
- `.env.example` contains placeholders only
- Production startup requires a valid `SECRET_KEY`
- Production settings enforce `DEBUG=False`
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` must be explicitly configured in production
- Session and CSRF cookies use secure settings in production
- PostgreSQL and Redis are not exposed outside Docker Compose by default

## Next Steps

1. Expand CRUD and REST coverage for each domain
2. Add automated tests per app
3. Prepare demo seed data for presentations
4. Extend audit workflows with signals and middleware
5. Refine dashboards, reports, and operational analytics
