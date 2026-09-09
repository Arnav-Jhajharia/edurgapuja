"""Running a check and deciding what it means."""

import logging

from django.conf import settings

from apps.common.errors import DomainError, ValidationFailedError

from .models import KycCheck, mark_verified, verified_pan
from .providers import PAN_PATTERN, KycUnavailableError, get_kyc_provider, normalise_pan

logger = logging.getLogger(__name__)


class KycRequiredError(DomainError):
    """A donation this size cannot proceed without a verified PAN.

    402 would be wrong (nothing is owed) and 403 would be wrong (the caller is
    allowed, they are just not finished). 422 with a code the client can branch
    on is the honest answer: the request was understood and cannot be actioned
    as sent.
    """

    status_code = 422
    default_code = "kyc_required"
    default_detail = "A donation this size needs a verified PAN."


class KycUnverifiedError(DomainError):
    status_code = 422
    default_code = "kyc_failed"
    default_detail = "That PAN could not be verified."


def threshold_paise() -> int:
    return settings.DONATION_KYC_THRESHOLD_PAISE


def needs_kyc(amount_paise: int) -> bool:
    return amount_paise >= threshold_paise()


def guard_donation(*, amount_paise: int, user) -> KycCheck | None:
    """Let a donation through, or say precisely what is missing.

    Returns the check the donation should be attributed to, or None when the
    amount does not require one.
    """
    if not needs_kyc(amount_paise):
        return None

    if not user or not user.is_authenticated:
        # A consequence of the law rather than a product decision: the committee
        # has to be able to report this donation, and it cannot report nobody.
        raise KycRequiredError(
            "A donation this size cannot be anonymous — sign in and verify your PAN.",
            threshold_paise=threshold_paise(), reason="not_signed_in",
        )

    check = verified_pan(user)
    if check is None:
        raise KycRequiredError(
            "Verify your PAN to give this much.",
            threshold_paise=threshold_paise(), reason="no_verified_pan",
        )
    return check


def verify_pan(*, user, pan: str, name: str, date_of_birth: str = "") -> KycCheck:
    """Check one PAN and record the attempt, whichever way it goes."""
    pan = normalise_pan(pan)
    if not PAN_PATTERN.match(pan):
        raise ValidationFailedError(
            "That does not look like a PAN.",
            fields={"pan": "Ten characters, like ABCDE1234F."},
        )
    if not name.strip():
        raise ValidationFailedError(
            "We need the name exactly as it appears on the PAN.",
            fields={"name": "Required."},
        )

    provider = get_kyc_provider()
    check = KycCheck.objects.create(
        user=user, kind=KycCheck.Kind.PAN, provider=provider.name,
        name_submitted=name.strip(),
    )

    try:
        result = provider.verify_pan(pan=pan, name=name.strip(), date_of_birth=date_of_birth)
    except KycUnavailableError as problem:
        # "We could not ask" must not read as "the answer was no".
        check.status = KycCheck.Status.ERROR
        check.reason = "We could not reach the verification service. Try again shortly."
        check.save(update_fields=["status", "reason", "updated_at"])
        logger.warning("KYC provider unavailable: %s", problem)
        raise KycUnverifiedError(check.reason, retryable=True) from problem

    if not result.verified:
        # The number is deliberately not stored: a rejected PAN is somebody
        # else's as often as it is a typo.
        check.status = KycCheck.Status.FAILED
        check.reason = result.reason
        check.provider_ref = result.reference
        check.save(update_fields=["status", "reason", "provider_ref", "updated_at"])
        raise KycUnverifiedError(result.reason or "That PAN could not be verified.")

    return mark_verified(check, number=pan, name_on_record=result.name_on_record,
                         ref=result.reference)
