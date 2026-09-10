"""Issue and verify one-time codes, with the limits the contract promises."""

import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework import status

from apps.accounts.models import OtpChallenge
from apps.accounts.otp.senders import OtpDeliveryError
from apps.common.errors import DomainError

logger = logging.getLogger(__name__)


class OtpRateLimitedError(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "otp_rate_limited"
    default_detail = "Please wait before requesting another code."


class OtpInvalidError(DomainError):
    default_code = "otp_invalid"
    default_detail = "That code is not correct."


class OtpExpiredError(DomainError):
    default_code = "otp_expired"
    default_detail = "That code has expired. Request a new one."


class OtpUndeliverableError(DomainError):
    """The network would not take the message.

    A separate code from a rate limit or a wrong code, because the person did
    nothing wrong and retrying immediately is the right advice.
    """

    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "otp_undeliverable"
    default_detail = "We could not send a code just now. Please try again."


@dataclass(frozen=True)
class IssuedOtp:
    challenge: OtpChallenge
    resend_after_seconds: int


def _sender():
    return import_string(settings.OTP_SENDER_BACKEND)()


def _cooldown_key(destination: str) -> str:
    return f"otp:cooldown:{destination}"


def _hourly_key(destination: str) -> str:
    return f"otp:hourly:{destination}"


def issue(destination: str, *, purpose: str = OtpChallenge.Purpose.LOGIN,
          channel: str = OtpChallenge.Channel.SMS, ip: str | None = None) -> IssuedOtp:
    if cache.get(_cooldown_key(destination)):
        raise OtpRateLimitedError(retry_after=settings.OTP_RESEND_COOLDOWN_SECONDS)

    sent_this_hour = cache.get_or_set(_hourly_key(destination), 0, timeout=3600)
    if sent_this_hour >= settings.OTP_MAX_SENDS_PER_HOUR:
        raise OtpRateLimitedError("Too many codes requested. Try again later.", retry_after=3600)

    # Any earlier live code stops working the moment a new one is issued (FR-006).
    OtpChallenge.objects.filter(
        destination=destination, purpose=purpose, consumed_at__isnull=True
    ).update(consumed_at=timezone.now())

    code = f"{secrets.randbelow(10 ** settings.OTP_CODE_LENGTH):0{settings.OTP_CODE_LENGTH}d}"
    challenge = OtpChallenge.objects.create(
        channel=channel,
        destination=destination,
        purpose=purpose,
        code_hash=OtpChallenge.hash_code(code, destination),
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
        max_attempts=settings.OTP_MAX_ATTEMPTS,
        request_ip=ip,
    )

    try:
        _sender().send(destination, code, channel=channel)
    except OtpDeliveryError as problem:
        # Nobody received this, so it must not sit there as a live code — and
        # the failure must not spend the person's cooldown or hourly quota,
        # which are there to limit *them*, not to punish an outage.
        OtpChallenge.objects.filter(pk=challenge.pk).update(consumed_at=timezone.now())
        logger.error("OTP delivery failed for ***%s: %s", destination[-4:], problem)
        raise OtpUndeliverableError from problem

    cache.set(_cooldown_key(destination), 1, timeout=settings.OTP_RESEND_COOLDOWN_SECONDS)
    try:
        cache.incr(_hourly_key(destination))
    except ValueError:
        cache.set(_hourly_key(destination), 1, timeout=3600)

    return IssuedOtp(challenge=challenge, resend_after_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)


def verify(destination: str, code: str,
           *, purpose: str = OtpChallenge.Purpose.LOGIN) -> OtpChallenge:
    challenge = (OtpChallenge.objects
                 .filter(destination=destination, purpose=purpose)
                 .order_by("-created_at").first())
    if challenge is None or not challenge.is_live:
        raise OtpExpiredError

    if not challenge.verify(code):
        OtpChallenge.objects.filter(pk=challenge.pk).update(attempts=F("attempts") + 1)
        challenge.refresh_from_db(fields=["attempts"])
        raise OtpInvalidError(attempts_left=max(0, challenge.max_attempts - challenge.attempts))

    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=["consumed_at", "updated_at"])
    return challenge
