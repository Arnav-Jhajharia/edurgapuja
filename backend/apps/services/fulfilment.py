"""What a paid service line means.

The interesting case is the late payment: a hold may have lapsed while the
provider took its time. `inventory.issue` re-acquires under the day's lock, and
if the place has genuinely gone it raises — the caller refunds, which is the
honest outcome rather than the convenient one (API contract §6.3).
"""

import logging

from django.utils import timezone

from apps.common.errors import HoldExpiredError

from . import inventory
from .models import ServiceBooking

logger = logging.getLogger(__name__)


def confirm_service_booking(line) -> None:
    booking = getattr(line, "service_booking", None)
    if booking is None or booking.status == ServiceBooking.Status.CONFIRMED:
        return

    if booking.hold_id is None:
        # Nothing was held because nothing could run out. Straight to confirmed.
        booking.status = ServiceBooking.Status.CONFIRMED
        booking.confirmed_at = timezone.now()
        booking.save(update_fields=["status", "confirmed_at", "updated_at"])
        return

    try:
        inventory.issue(hold_id=booking.hold_id)
    except HoldExpiredError:
        booking.status = ServiceBooking.Status.EXPIRED
        booking.save(update_fields=["status", "updated_at"])
        logger.warning("booking %s paid but its place had gone; refund due", booking.pk)
        return

    booking.status = ServiceBooking.Status.CONFIRMED
    booking.confirmed_at = timezone.now()
    booking.save(update_fields=["status", "confirmed_at", "updated_at"])


def release_service_booking(line) -> None:
    booking = getattr(line, "service_booking", None)
    if booking is None or booking.status != ServiceBooking.Status.HELD:
        return
    if booking.hold_id:
        inventory.release_hold(hold_id=booking.hold_id)
    booking.status = ServiceBooking.Status.CANCELLED
    booking.save(update_fields=["status", "updated_at"])
