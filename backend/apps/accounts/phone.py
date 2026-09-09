import phonenumbers
from django.conf import settings

from apps.common.errors import ValidationFailedError


def normalise(raw: str) -> str:
    """Everything downstream stores and compares E.164 only (FR-016)."""
    try:
        parsed = phonenumbers.parse(raw, settings.DEFAULT_PHONE_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValidationFailedError("That does not look like a phone number.",
                               fields={"phone": "Enter a valid mobile number."}) from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationFailedError("That does not look like a phone number.",
                               fields={"phone": "Enter a valid mobile number."})
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
