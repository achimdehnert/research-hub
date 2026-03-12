#!/bin/sh
set -e

echo "[entrypoint] Waiting for database..."
until python -c "
import os, urllib.parse
url = os.environ.get('DATABASE_URL', '')
r = urllib.parse.urlparse(url)
import socket
s = socket.create_connection((r.hostname, r.port or 5432), timeout=2)
s.close()
" 2>/dev/null; do
    echo "  DB not ready, retrying..."
    sleep 2
done
echo "[entrypoint] Database ready!"

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput

if [ "$1" = "web" ]; then
    echo "[entrypoint] Running migrations..."
    python manage.py migrate --noinput

    echo "[entrypoint] Seeding aifw (providers, models, actions)..."
    python manage.py seed_aifw

    echo "[entrypoint] Starting gunicorn..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-2}" \
        --timeout 120 \
        --max-requests 500 \
        --max-requests-jitter 50 \
        --access-logfile -
fi

if [ "$1" = "worker" ]; then
    echo "[entrypoint] Starting Celery worker..."
    exec celery -A config worker -l info -Q celery
fi

if [ "$1" = "beat" ]; then
    echo "[entrypoint] Starting Celery beat..."
    exec celery -A config beat -l info
fi

echo "Usage: /entrypoint.sh [web|worker|beat]"
exit 1
