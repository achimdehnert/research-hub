"""Base settings for research-hub."""

from __future__ import annotations

from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-research-hub-dev-key-change-in-prod")

DEBUG = config("DEBUG", default="True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,research.iil.pet").split(",")

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="https://research.iil.pet").split(",")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default="True").lower() in ("true", "1", "yes")
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default="True").lower() in (
    "true",
    "1",
    "yes",
)

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "crispy_forms",
    "crispy_bootstrap5",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "django_tenancy",
    "django_module_shop",
    "content_store",  # ADR-130: Shared Content Store
    "aifw",  # LLM routing, model management, secrets
    "promptfw.contrib.django",  # DB-backed prompt management (ADR-146)
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.research",
    "apps.tenancy",
    "apps.documents",  # ADR-144: Paperless-ngx metadata sync
    "apps.knowledge",  # ADR-145: Outline Wiki sync + AI enrichment
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# PROMPTFW — DB-backed prompt management (ADR-146)
# =============================================================================

PROMPTFW_PROMPTS_DIR = None  # no file fallback — inline prompts as legacy path
PROMPTFW_CACHE_TTL = 300
PROMPTFW_FILE_FALLBACK = False
PROMPTFW_MULTI_TENANT = False

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.tenancy.middleware.ResearchHubTenantMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://research_hub:research_hub@localhost:5432/research_hub",
        conn_max_age=600,
    ),
    # ADR-130: Shared Content Store (cross-app persistence)
    "content_store": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("CONTENT_STORE_DB_NAME", default="content_store"),
        "USER": config("CONTENT_STORE_DB_USER", default="content_store"),
        "PASSWORD": config("CONTENT_STORE_DB_PASSWORD", default=""),
        "HOST": config("CONTENT_STORE_DB_HOST", default="devhub_db"),
        "PORT": config("CONTENT_STORE_DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    },
}

DATABASE_ROUTERS = ["content_store.router.ContentStoreRouter"]  # ADR-130

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "apps.accounts.auth.IILOIDCAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [d for d in [BASE_DIR / "static"] if d.exists()]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Celery
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_DEFAULT_QUEUE = "celery"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "research-hub API",
    "DESCRIPTION": "Research Hub — powered by iil-researchfw",
    "VERSION": "1.0.0",
}

# Allauth
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_EMAIL_VERIFICATION = "optional"
LOGIN_REDIRECT_URL = "/research/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

# Email
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# Module Shop
MODULE_SHOP_CATALOGUE = {
    "research_basic": {
        "name": "Research Basic",
        "description": "Web-Recherche, Zusammenfassung, Quellen",
        "icon": "search",
        "price_month": 9.0,
        "price_year": 90.0,
        "category": "research",
    },
    "research_pro": {
        "name": "Research Pro",
        "description": "Akademische Quellen, Tiefenanalyse, Exportfunktionen",
        "icon": "mortarboard",
        "price_month": 19.0,
        "price_year": 190.0,
        "category": "research",
        "dependencies": ["research_basic"],
    },
    "workspaces": {
        "name": "Workspaces",
        "description": "Unbegrenzte Workspaces und Projekte",
        "icon": "folder2",
        "price_month": 5.0,
        "price_year": 50.0,
        "category": "organisation",
    },
}

# --- authentik OIDC (ADR-142) ---
OIDC_RP_CLIENT_ID = config("OIDC_RP_CLIENT_ID", default="")
OIDC_RP_CLIENT_SECRET = config("OIDC_RP_CLIENT_SECRET", default="")
_OIDC_APP_SLUG = config("OIDC_APP_SLUG", default="research-hub")
_IDP = "https://id.iil.pet/application/o"
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{_IDP}/authorize/"
OIDC_OP_TOKEN_ENDPOINT = f"{_IDP}/token/"
OIDC_OP_USER_ENDPOINT = f"{_IDP}/userinfo/"
OIDC_OP_JWKS_ENDPOINT = f"{_IDP}/{_OIDC_APP_SLUG}/jwks/"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile"
LOGOUT_REDIRECT_URL = "/"

# Sentry
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)
