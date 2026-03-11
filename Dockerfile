# syntax=docker/dockerfile:1
FROM python:3.12-slim

ARG APP_NAME=research-hub
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/${APP_NAME}"
LABEL org.opencontainers.image.description="Research Hub \u2014 AI-powered research platform"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /app/requirements/
COPY wheels/ /app/wheels/

# Install dependencies.
# GIT_TOKEN is injected at build time via --secret and is never stored
# in any image layer (BuildKit --mount=type=secret).
RUN --mount=type=secret,id=GIT_TOKEN,required=true \
    GIT_TOKEN=$(cat /run/secrets/GIT_TOKEN) \
    && git config --global url."https://x-access-token:${GIT_TOKEN}@github.com/".insteadOf "https://github.com/" \
    && pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements/prod.txt \
    && pip install --no-cache-dir /app/wheels/*.whl 2>/dev/null || true \
    && git config --global --remove-section url."https://x-access-token:${GIT_TOKEN}@github.com/" 2>/dev/null || true

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
