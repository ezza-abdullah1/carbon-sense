"""
Production settings.

All security-critical values are required from the environment — there are
no insecure defaults. Set these in your deployment platform:

    SECRET_KEY            (required)
    ALLOWED_HOSTS         (required, comma-separated)
    SUPABASE_DB_URL       (required, postgres URL)
    CORS_ALLOWED_ORIGINS  (required, comma-separated)
    REDIS_URL             (optional, enables Redis cache)
"""

import os

import dj_database_url

from .base import *  # noqa: F401,F403


DEBUG = False


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


SECRET_KEY = _required("SECRET_KEY")
ALLOWED_HOSTS = _required("ALLOWED_HOSTS").split(",")


# Database — Postgres only in production.

DATABASES = {
    "default": dj_database_url.config(
        default=_required("SUPABASE_DB_URL"),
        conn_max_age=0,
    )
}
DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"


# CORS

CORS_ALLOWED_ORIGINS = _required("CORS_ALLOWED_ORIGINS").split(",")
CORS_ALLOW_CREDENTIALS = True


# Cache — Redis if REDIS_URL is set, locmem otherwise (single-process only).

REDIS_URL = os.environ.get("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "TIMEOUT": 300,
        }
    }


# Transport security — HTTPS-only.

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
