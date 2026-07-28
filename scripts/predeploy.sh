#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py sincronizar_rotinas_celery
python manage.py verificar_implantacao --strict
