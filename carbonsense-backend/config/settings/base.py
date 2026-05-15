"""
Shared Django settings for carbonsense.

Environment-specific overrides live in dev.py and prod.py. Any value that
should differ between environments (DEBUG, SECRET_KEY, ALLOWED_HOSTS,
DATABASES, CACHES, CORS) belongs in a sibling module — not here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# carbonsense-backend/  <- BASE_DIR
# └── carbonsense/
#     └── settings/
#         └── base.py   <- this file
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from the backend root if present (no-op in deployments without one).
load_dotenv(BASE_DIR / ".env")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
    "recommendations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # GZip must run before CommonMiddleware so it can compress its output.
    "django.middleware.gzip.GZipMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# REST framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}


# Auth

AUTH_USER_MODEL = "api.User"


# Sessions / CSRF (transport-security flags are tightened in prod.py)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"


# Recommendations / RAG

# Legacy (kept until n8n cutover is complete; remove after rollout)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_data")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
POLICY_DOCUMENTS_DIR = str(BASE_DIR / "policy_documents")

RECOMMENDATION_CACHE_TTL_HOURS = int(os.environ.get("RECOMMENDATION_CACHE_TTL_HOURS", "24"))

# n8n integration
N8N_WEBHOOK_BASE = os.environ.get("N8N_WEBHOOK_BASE", "")  # e.g. https://your-n8n.app.n8n.cloud/webhook
N8N_SHARED_SECRET = os.environ.get("N8N_SHARED_SECRET", "")
N8N_TIMEOUT_SECONDS = int(os.environ.get("N8N_TIMEOUT_SECONDS", "60"))

# Supabase (used by seed_data_chunks management command + optional direct queries)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# OpenAI (used only by seed_data_chunks for embedding the local JSON corpus;
# n8n owns the runtime embedding path)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# Backend selector: 'n8n' once cutover is done, 'template' for fallback-only mode.
RECOMMENDATIONS_BACKEND = os.environ.get("RECOMMENDATIONS_BACKEND", "n8n")
