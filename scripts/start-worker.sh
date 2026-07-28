#!/bin/sh
set -eu

CELERY_LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"

exec celery -A config worker -l "${CELERY_LOG_LEVEL}"
