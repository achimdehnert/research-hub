"""Research Hub — Test Settings (ADR-179: PostgreSQL-Only Testing)"""

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

# ADR-179: Explicit PostgreSQL — SQLite is BANNED for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("TEST_DB_NAME", default="research_hub_test"),
        "USER": config("TEST_DB_USER", default="dehnert"),
        "PASSWORD": config("TEST_DB_PASSWORD", default=""),
        "HOST": config("TEST_DB_HOST", default=""),
        "PORT": config("TEST_DB_PORT", default="5434"),
        "TEST": {"NAME": "test_research_hub"},
    },
    # ADR-130: Shared Content Store (cross-app persistence)
    "content_store": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("CONTENT_STORE_DB_NAME", default="content_store_test"),
        "USER": config("CONTENT_STORE_DB_USER", default="dehnert"),
        "PASSWORD": config("CONTENT_STORE_DB_PASSWORD", default=""),
        "HOST": config("CONTENT_STORE_DB_HOST", default=""),
        "PORT": config("CONTENT_STORE_DB_PORT", default="5434"),
        "TEST": {"NAME": "test_content_store"},
    },
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

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
