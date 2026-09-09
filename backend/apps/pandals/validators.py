import re

from django.conf import settings
from django.core.exceptions import ValidationError

SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def validate_subdomain(value: str) -> None:
    """A pandal's slug is also its subdomain (D12), so DNS rules apply and the
    platform's own names are off limits (FR-247)."""
    if not SUBDOMAIN_RE.match(value):
        raise ValidationError(
            "Use lowercase letters, digits and hyphens only, "
            "not starting or ending with a hyphen, up to 63 characters."
        )
    if value in settings.RESERVED_SUBDOMAINS:
        raise ValidationError(f"'{value}' is reserved. Choose another name.")
