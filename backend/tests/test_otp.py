import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import OtpChallenge
from apps.accounts.otp import service
from apps.accounts.otp.senders import MemorySender

pytestmark = pytest.mark.django_db

PHONE = "+919876543210"


def _clear_cooldown():
    cache.delete(f"otp:cooldown:{PHONE}")


def test_a_code_is_sent_and_never_stored_in_the_clear():
    issued = service.issue(PHONE)
    code = MemorySender.last_code(PHONE)

    assert code is not None
    assert code not in issued.challenge.code_hash
    assert issued.challenge.is_live


def test_the_right_code_works_once_and_is_then_spent():
    service.issue(PHONE)
    code = MemorySender.last_code(PHONE)

    assert service.verify(PHONE, code).consumed_at is not None

    with pytest.raises(service.OtpExpiredError):
        service.verify(PHONE, code)


def test_a_wrong_code_counts_an_attempt_and_says_how_many_remain():
    service.issue(PHONE)

    with pytest.raises(service.OtpInvalidError) as caught:
        service.verify(PHONE, "000000")

    assert caught.value.extra["attempts_left"] == 4
    assert OtpChallenge.objects.get(destination=PHONE).attempts == 1


def test_a_code_past_its_lifetime_is_refused():
    issued = service.issue(PHONE)
    OtpChallenge.objects.filter(pk=issued.challenge.pk).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1)
    )

    with pytest.raises(service.OtpExpiredError):
        service.verify(PHONE, MemorySender.last_code(PHONE))


def test_asking_again_kills_the_previous_code():
    """Two live codes for one number must never coexist (FR-006)."""
    service.issue(PHONE)
    first = MemorySender.last_code(PHONE)
    _clear_cooldown()
    service.issue(PHONE)
    second = MemorySender.last_code(PHONE)

    assert first != second
    # Only the newest challenge is ever consulted, so a superseded code is
    # indistinguishable from a wrong one — which is the safe way round.
    with pytest.raises(service.OtpInvalidError):
        service.verify(PHONE, first)
    assert service.verify(PHONE, second) is not None


def test_asking_twice_in_a_row_is_refused_with_a_wait():
    service.issue(PHONE)

    with pytest.raises(service.OtpRateLimitedError) as caught:
        service.issue(PHONE)

    assert caught.value.extra["retry_after"] > 0


def test_the_hourly_cap_stops_a_number_being_hammered(settings):
    settings.OTP_MAX_SENDS_PER_HOUR = 2
    for _ in range(2):
        service.issue(PHONE)
        _clear_cooldown()

    with pytest.raises(service.OtpRateLimitedError):
        service.issue(PHONE)


def test_codes_for_different_purposes_do_not_collide():
    service.issue(PHONE, purpose=OtpChallenge.Purpose.LOGIN)
    login_code = MemorySender.last_code(PHONE)
    _clear_cooldown()
    service.issue(PHONE, purpose=OtpChallenge.Purpose.WEB_CHECKOUT)

    with pytest.raises(service.OtpInvalidError):
        service.verify(PHONE, login_code, purpose=OtpChallenge.Purpose.WEB_CHECKOUT)
