"""Build-time settings for Docker collectstatic.

No database, no Redis, no Celery — just enough to run management commands.
ADR-083: No || true, no dummy env vars.
"""

from .base import *  # noqa: F401,F403

SECRET_KEY = "build-dummy-not-used-in-production"  # hardcoded-ok: build settings
DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    "content_store": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
