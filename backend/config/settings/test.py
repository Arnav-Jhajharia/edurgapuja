from .base import *  # noqa: F403

DEBUG = False
# Long enough for HMAC-SHA256 without a warning; never used to serve anything.
SECRET_KEY = "test-only-secret-key-at-least-thirty-two-bytes-long"  # noqa: S105
CELERY_TASK_ALWAYS_EAGER = True
OTP_SENDER_BACKEND = "apps.accounts.otp.senders.MemorySender"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
