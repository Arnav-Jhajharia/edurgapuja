"""Settings shared by every environment.

Nothing secret lives here; everything sensitive comes from the environment.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False), ALLOWED_HOSTS=(list, []))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-do-not-use-in-prod")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "apps.common",
    "apps.geo",
    "apps.accounts.apps.AccountsConfig",
    "apps.pandals",
    "apps.inventory",
    "apps.orders",
    "apps.payments",
    "apps.donations",
    "apps.services",
    "apps.passes",
    "apps.sponsorship",
    "apps.adminapi",
    "apps.ops",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db_url("DATABASE_URL", default="postgres://localhost:5432/edurgapuja")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                      "LOCATION": REDIS_URL}}

AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- OTP (channel-agnostic: SMS today, email if the client ever wants it) ---
OTP_CODE_LENGTH = env.int("OTP_CODE_LENGTH", default=6)
OTP_TTL_SECONDS = env.int("OTP_TTL_SECONDS", default=300)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=60)
OTP_MAX_SENDS_PER_HOUR = env.int("OTP_MAX_SENDS_PER_HOUR", default=8)
OTP_SENDER_BACKEND = env("OTP_SENDER_BACKEND", default="apps.accounts.otp.senders.ConsoleSender")
DEFAULT_PHONE_REGION = "IN"

# --- Inventory ---
CAPACITY_HOLD_TTL_SECONDS = env.int("CAPACITY_HOLD_TTL_SECONDS", default=900)

# --- Sponsorship ---
# Whether a sub-sponsor may itself create sub-sponsors is unresolved (Q-164),
# so the schema permits any depth and the policy limit lives here.
MAX_POOL_DEPTH = env.int("MAX_POOL_DEPTH", default=1)

# --- Payments ---
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")

# --- Web ---
SITE_DOMAIN = env("SITE_DOMAIN", default="edurgapuja.app")
RESERVED_SUBDOMAINS = {
    "www", "api", "admin", "app", "mail", "smtp", "static", "assets", "cdn",
    "staging", "dev", "test", "help", "support", "status", "blog", "docs",
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.common.errors.exception_handler",
    # `login` is the only unauthenticated endpoint where guessing is possible,
    # so it is rate-limited like OTP rather than like an ordinary read.
    "DEFAULT_THROTTLE_RATES": {"otp": "8/hour", "login": "10/hour",
                               "anon": "60/min", "user": "600/min"},
}

# SimpleJWT's defaults give an access token five minutes of life, which is right
# for a public API a phone hits in bursts and wrong for a console somebody keeps
# open all evening while the pandal is running. An hour of access plus a rotating
# thirty-day refresh means an admin signs in once for the whole Puja; rotation
# with blacklisting means a stolen refresh token is usable exactly once before
# the real device's next rotation invalidates it.
# A single password that opens any active account, so a demo does not need six
# SMS codes. Empty by default, ignored unless DEBUG is on, and `config/checks.py`
# refuses to start the server if it is set with DEBUG off — see
# `apps/accounts/passwords.py`.
DEV_LOGIN_PASSWORD = env("DEV_LOGIN_PASSWORD", default="")

# The platform's first Super Admin. Every other administrator is granted by one
# who already exists, which leaves the first with nowhere to come from — so it
# comes from configuration, applied idempotently on deploy. See
# `apps/accounts/management/commands/bootstrap_admin.py`.
BOOTSTRAP_ADMIN_PHONE = env("BOOTSTRAP_ADMIN_PHONE", default="")
BOOTSTRAP_ADMIN_PASSWORD = env("BOOTSTRAP_ADMIN_PASSWORD", default="")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "eDurgaPuja API",
    "DESCRIPTION": "Pandal landing pages, donations and value-added services.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Seven models have a field called "status" with entirely different choices.
    # Left alone the generated client calls them Status5f4Enum and friends; named
    # here, every SDK gets one readable type per concept.
    "ENUM_NAME_OVERRIDES": {
        "AllocationStatusEnum": "apps.sponsorship.models.ALLOCATION_STATUS_CHOICES",
        "CreativeStatusEnum": "apps.sponsorship.models.CREATIVE_STATUS_CHOICES",
        "BookingStatusEnum": "apps.services.models.BOOKING_STATUS_CHOICES",
        "ServiceFieldKindEnum": "apps.services.models.SERVICE_FIELD_KIND_CHOICES",
        "LostItemStatusEnum": "apps.ops.models.LOST_ITEM_STATUS_CHOICES",
        "SupportStatusEnum": "apps.ops.models.SUPPORT_STATUS_CHOICES",
        "OrderStatusEnum": "apps.orders.models.ORDER_STATUS_CHOICES",
        "PassStatusEnum": "apps.passes.models.PASS_STATUS_CHOICES",
        "LegStateEnum": "apps.passes.models.LEG_STATE_CHOICES",
        "ScanResultEnum": "apps.passes.models.SCAN_RESULT_CHOICES",
        "PaymentOrderStatusEnum": "apps.payments.models.PAYMENT_ORDER_STATUS_CHOICES",
        "RefundStatusEnum": "apps.payments.models.REFUND_STATUS_CHOICES",
    },
}

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("bn", "Bengali"), ("hi", "Hindi")]
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TIMEZONE = TIME_ZONE

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
