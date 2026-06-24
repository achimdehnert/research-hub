"""Research Hub — Test Settings (ADR-179: PostgreSQL-Only Testing)"""

import os

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

# ADR-179: Explicit PostgreSQL — SQLite is BANNED for testing
#
# Drei Test-Kontexte, ein Setting (alle ohne den jeweils anderen Pfad zu brechen):
#  1) Standalone `ci.yml` + lokales `/teste-repo`: pinnen `TEST_DB_*` explizit
#     → diese Werte gewinnen wie bisher (ci.yml setzt Port 5432, User `ci`).
#  2) Geteilte platform CI (`_ci-python.yml`): exportiert NUR `POSTGRES_HOST`
#     (+ ephemeren `POSTGRES_PORT`) an den Test-Step; feste Service-Creds.
#     Mustergleich zu writing-hub/config/settings/test.py.
#  3) Frischer Checkout ohne Env: erreichbare TCP-Defaults statt Unix-Socket +
#     `dehnert`-User (existierte nur auf der Lead-Dev-Maschine). Bedient von
#     `docker/docker-compose.test.yml` (pgvector auf 127.0.0.1:5439).
_SHARED_CI = "POSTGRES_HOST" in os.environ and "TEST_DB_HOST" not in os.environ
if _SHARED_CI:
    _DEFAULT_HOST = os.environ["POSTGRES_HOST"]
    _DEFAULT_PORT = os.environ.get("POSTGRES_PORT", "5432")
    _DEFAULT_USER = "test_user"
    _DEFAULT_PASSWORD = "test_pass"
else:
    _DEFAULT_HOST = "127.0.0.1"
    _DEFAULT_PORT = "5439"
    _DEFAULT_USER = "research_hub"
    _DEFAULT_PASSWORD = "research_hub"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("TEST_DB_NAME", default="research_hub_test"),
        "USER": config("TEST_DB_USER", default=_DEFAULT_USER),
        "PASSWORD": config("TEST_DB_PASSWORD", default=_DEFAULT_PASSWORD),
        "HOST": config("TEST_DB_HOST", default=_DEFAULT_HOST),
        "PORT": config("TEST_DB_PORT", default=_DEFAULT_PORT),
        "TEST": {"NAME": "test_research_hub"},
    },
    # ADR-130: Shared Content Store (cross-app persistence)
    "content_store": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("CONTENT_STORE_DB_NAME", default="content_store_test"),
        "USER": config("CONTENT_STORE_DB_USER", default=_DEFAULT_USER),
        "PASSWORD": config("CONTENT_STORE_DB_PASSWORD", default=_DEFAULT_PASSWORD),
        "HOST": config("CONTENT_STORE_DB_HOST", default=_DEFAULT_HOST),
        "PORT": config("CONTENT_STORE_DB_PORT", default=_DEFAULT_PORT),
        "TEST": {"NAME": "test_content_store"},
    },
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# No Redis in CI — in-memory cache is enough for dedup/rate-limit/reformat tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

SILENCED_SYSTEM_CHECKS = [
    "security.W004",
    "security.W008",
    "security.W009",
    "security.W012",
    "security.W016",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
