#!/bin/bash
set -euo pipefail

echo "[entrypoint] Running migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
