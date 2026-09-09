"""Production.

Everything here is either a hardening step Django will not take on its own, or
a value that must come from the environment because it is different per
deployment. Nothing secret is written down.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# Railway gives the service a hostname; a custom domain adds more. Both go in
# ALLOWED_HOSTS, and the leading dot form covers every pandal's subdomain.
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS", default=[])

# Railway terminates TLS at its edge and forwards the scheme in this header.
# Without it Django believes every request is plain HTTP and the redirect below
# becomes an infinite loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# One year, and subdomains included: every pandal is one, so leaving them out
# would exempt the entire public site.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# WhiteNoise serves the admin's own CSS and the API docs without a separate
# bucket or CDN. At this size that is the right trade: one fewer moving part.
MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

if dsn := env("SENTRY_DSN", default=""):
    import sentry_sdk

    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1, send_default_pii=False)
