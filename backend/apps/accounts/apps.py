from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"

    def ready(self):
        # Registers the startup check that keeps the shared development
        # password out of production.
        from . import checks  # noqa: F401
