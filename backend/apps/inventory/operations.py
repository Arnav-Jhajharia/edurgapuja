"""The four operations. Everything that touches capacity goes through here.

Each takes the day row's lock and does nothing else inside it, so two owners
never contend and a rush contends only on the row it must.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.common.errors import CapacityUnavailableError, HoldExpiredError


def live_holds(hold_model, day):
    return hold_model.objects.filter(day=day, released_at__isnull=True,
                                     expires_at__gt=timezone.now())


def available(hold_model, day) -> int:
    """Computed, never stored. An expired hold stops counting immediately."""
    held = live_holds(hold_model, day).aggregate(n=Sum("quantity"))["n"] or 0
    return max(0, day.capacity - day.issued_count - held)


@transaction.atomic
def place_hold(day_model, hold_model, *, day_id, quantity: int, ttl_seconds: int | None = None,
               **hold_fields):
    day = day_model.objects.select_for_update().get(pk=day_id)
    if not day.is_open:
        raise CapacityUnavailableError("Bookings for that day are closed.", available=0)

    free = available(hold_model, day)
    if quantity > free:
        raise CapacityUnavailableError(
            f"Only {free} place{'s' if free != 1 else ''} remain.", available=free
        )

    ttl = ttl_seconds or settings.CAPACITY_HOLD_TTL_SECONDS
    return hold_model.objects.create(
        day=day, quantity=quantity,
        expires_at=timezone.now() + timedelta(seconds=ttl),
        **hold_fields,
    )


@transaction.atomic
def issue(day_model, hold_model, *, hold_id):
    """Convert a live hold into issued capacity.

    A hold that lapsed before payment landed is re-acquired here under the same
    lock. If the place has gone, the caller refunds — which is the honest
    outcome, not the convenient one (API contract §6.3).
    """
    hold = hold_model.objects.select_related("day").get(pk=hold_id)
    day = day_model.objects.select_for_update().get(pk=hold.day_id)

    expired = hold.released_at is not None or hold.expires_at <= timezone.now()
    if expired:
        free = available(hold_model, day)
        if free < hold.quantity:
            raise HoldExpiredError("That place was taken while the payment completed.",
                              available=free)
        hold.expires_at = timezone.now() + timedelta(seconds=60)
        hold.released_at = None

    day.issued_count += hold.quantity
    day.save(update_fields=["issued_count", "updated_at"])

    hold.released_at = timezone.now()
    hold.save(update_fields=["expires_at", "released_at", "updated_at"])
    return day


@transaction.atomic
def give_back(day_model, *, day_id, quantity: int) -> None:
    """The inverse of `issue`: return capacity that was already consumed.

    Releasing a hold is not enough once `issue` has run, because issuing moves
    the count from "held" to "issued" and a released hold that is already
    issued gives nothing back. A single-hold purchase never needs this — a
    service booking that fails has issued nothing. A City Pass does: it can
    issue three legs and then find the fourth pandal full, and those three
    places have to return to the pandals that own them.
    """
    day = day_model.objects.select_for_update().get(pk=day_id)
    day.issued_count = max(0, day.issued_count - quantity)
    day.save(update_fields=["issued_count", "updated_at"])


@transaction.atomic
def release_hold(hold_model, *, hold_id) -> None:
    """Give capacity back at once rather than waiting for expiry."""
    hold_model.objects.filter(pk=hold_id, released_at__isnull=True).update(
        released_at=timezone.now()
    )


def expire_holds(hold_model) -> int:
    """Housekeeping only. Correctness does not depend on this having run."""
    return hold_model.objects.filter(
        released_at__isnull=True, expires_at__lte=timezone.now()
    ).update(released_at=timezone.now())
