#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py sincronizar_rotinas_celery

exec sh scripts/start-web.sh
