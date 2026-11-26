"""
Django settings for ahaarbonton project.
"""

import os
from pathlib import Path

from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment-specific configuration. Local development works without a .env file.
def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-development-only-change-before-deploying",
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS: list[str] = env_list(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]" if DEBUG else ""
)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    if not os.getenv("DJANGO_SECRET_KEY") or SECRET_KEY.startswith("django-insecure-"):
        raise ImproperlyConfigured("Set a strong DJANGO_SECRET_KEY when DEBUG is disabled.")
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS when DEBUG is disabled.")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "users",
    "food",
    "delivery",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "ahaarbonton.middleware.DefaultLanguageMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ahaarbonton.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ahaarbonton.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "bn"
LANGUAGES = [
    ("bn", "বাংলা"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model (to be created in the next phase)
AUTH_USER_MODEL = "core.CustomUser"

# Custom authentication backends (email/phone + default)
AUTHENTICATION_BACKENDS = [
    "users.backends.EmailOrPhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Auth redirects
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

# ── Email Configuration ───────────────────────────
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv(
    "DJANGO_DEFAULT_FROM_EMAIL", "AhaarBonton <noreply@ahaarbonton.com>"
)
EMAIL_TIMEOUT = 10
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ── Password Reset ────────────────────────────────
PASSWORD_RESET_TIMEOUT = 3600  # Link expires in 1 hour

# Secure defaults for deployed environments.
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"

# Django messages CSS tag mapping
MESSAGE_TAGS = {
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
