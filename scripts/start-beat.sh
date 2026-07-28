#!/bin/sh
set -eu

CELERY_LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"

exec celery -A config beat -l "${CELERY_LOG_LEVEL}" --scheduler django_celery_beat.schedulers:DatabaseScheduler
