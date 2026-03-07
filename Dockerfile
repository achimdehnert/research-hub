FROM python:3.12-slim

ARG APP_NAME=research-hub
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/${APP_NAME}"
LABEL org.opencontainers.image.description="Research Hub — AI-powered research platform"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/prod.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . /app

RUN DJANGO_SETTINGS_MODULE=config.settings.base \
    SECRET_KEY=build-collect-static \
    DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput 2>/dev/null || true

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home app \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
