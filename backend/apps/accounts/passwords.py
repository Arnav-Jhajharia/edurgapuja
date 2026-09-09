"""Signing in with a phone number and a password.

OTP stays the primary route (D11): it needs no secret to remember and no
password to be reused. This is the second door, for people who would rather type
a password than wait for an SMS — and, in development, for anyone tired of
digging a code out of the server log.

Two ways a password can match, and they are not the same thing:

* **The account's own password.** Ordinary Django auth — argon2 hashed, checked
  in constant time. This is the one that will exist in production.
* **The shared development password.** `DEV_LOGIN_PASSWORD`, which opens any
  active account. It exists so a demo does not need six SMS codes, and it is
  fenced so it cannot reach production: `config.checks` refuses to start the
  server if it is set while `DEBUG` is off.

An account with no usable password simply cannot use this door; it uses OTP.
That is the correct behaviour, not a gap — most accounts are created by
verifying a phone number and never set one.
"""

import logging

from django.conf import settings

from apps.common.errors import DomainError

from .models import User

logger = logging.getLogger(__name__)


class InvalidCredentialsError(DomainError):
    """Deliberately one error for every failure.

    Wrong password, no password set, unknown number, deactivated account — all
    of it answers the same way. Distinguishing them turns this endpoint into a
    way to discover which numbers hold accounts.
    """

    status_code = 401
    default_code = "invalid_credentials"
    default_detail = "That number and password do not match."


def dev_password_is_open() -> bool:
    """Whether the shared development password is in play right now."""
    return bool(settings.DEBUG and getattr(settings, "DEV_LOGIN_PASSWORD", ""))


def authenticate(*, phone: str, password: str) -> User:
    """Return the user, or raise. Never says which half was wrong."""
    user = User.objects.filter(phone=phone, is_active=True).first()

    if user is None:
        # Still spend the time a real check would, so a missing account is not
        # detectable by how fast this answers.
        User().set_password(password)
        raise InvalidCredentialsError

    if user.check_password(password):
        return user

    if dev_password_is_open() and password == settings.DEV_LOGIN_PASSWORD:
        logger.warning("dev shared password used for %s — this cannot happen in production",
                       user.phone)
        return user

    raise InvalidCredentialsError
