"""Startup checks. Django runs these before it serves anything, so a dangerous
configuration is a refusal to start rather than a quiet hole found later."""

from django.conf import settings
from django.core.checks import Error, register


@register()
def dev_login_password_is_not_live(app_configs, **kwargs):
    """`DEV_LOGIN_PASSWORD` opens every account, so it may only exist in DEBUG.

    This is the fence that lets the shared demo password exist at all. Without
    it, one forgotten environment variable is every account on the platform.
    """
    if getattr(settings, "DEV_LOGIN_PASSWORD", "") and not settings.DEBUG:
        return [Error(
            "DEV_LOGIN_PASSWORD is set while DEBUG is off. It is a shared password "
            "that signs in as any user, and it must never exist outside development.",
            hint="Unset DEV_LOGIN_PASSWORD in this environment.",
            id="accounts.E001",
        )]
    return []
