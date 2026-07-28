#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py sincronizar_rotinas_celery
python manage.py bootstrap_admin

exec sh scripts/start-web.sh
