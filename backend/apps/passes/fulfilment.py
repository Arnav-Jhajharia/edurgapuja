"""What a paid pass line means.

The same shape as `apps/services/fulfilment.py`, with one difference that
matters: a pass has several legs, and each holds capacity at a different pandal.
A late payment may find one of them gone while the others are fine.

The choice made here is **all or nothing**. A City Pass whose fourth pandal sold
out while the payment cleared is not delivered as a three-quarter pass — the
visitor bought entry to four and would discover the shortfall at a gate, at
night, in a crowd. Every leg is released and the order is marked for refund.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.common.errors import HoldExpiredError

from . import inventory
from .codes import new_secret
from .models import LegSecret, Pass, PassLeg

logger = logging.getLogger(__name__)


@transaction.atomic
def confirm_pass(line) -> None:
    issued = getattr(line, "pass_issued", None)
    if issued is None:
        return

    legs = list(issued.legs.select_related("pandal").all())
    # Already fulfilled: every leg has its secret. A redelivered webhook must not
    # issue the capacity twice.
    if legs and all(LegSecret.objects.filter(leg=leg).exists() for leg in legs):
        return

    # Track what this call actually consumed. If a later leg fails, releasing
    # holds is not enough — an issued place is no longer held, and only
    # `give_back` returns it.
    issued_legs = []
    for leg in legs:
        if leg.capacity_hold_id is None:
            continue
        try:
            inventory.issue(hold_id=leg.capacity_hold_id)
        except HoldExpiredError:
            logger.warning("pass %s paid but %s had no place left; refund due",
                           issued.pass_code, leg.pandal.name)
            _unwind(issued, legs, issued_legs=issued_legs)
            return
        issued_legs.append(leg)

    for leg in legs:
        # Provisioned now, at purchase, so the phone can derive a code at the
        # gate with no network at all (D5).
        LegSecret.objects.get_or_create(leg=leg, defaults={"secret": new_secret()})

    issued.status = Pass.Status.ACTIVE
    issued.issued_at = timezone.now()
    issued.save(update_fields=["status", "issued_at", "updated_at"])


def _unwind(issued: Pass, legs: list[PassLeg], *, issued_legs: list[PassLeg] | None = None) -> None:
    """Give back everything this pass took and mark it cancelled.

    Two different reversals, because a leg may be in one of two states: still
    holding capacity, or already issued. `issued_legs` names the second kind.
    """
    already_issued = {leg.pk for leg in (issued_legs or [])}
    for leg in legs:
        if leg.pk in already_issued:
            inventory.give_back(day_id=leg.capacity_hold.day_id,
                                quantity=leg.capacity_hold.quantity)
        elif leg.capacity_hold_id:
            inventory.release_hold(hold_id=leg.capacity_hold_id)
    PassLeg.objects.filter(issued_pass=issued).update(state=PassLeg.State.VOID)
    issued.status = Pass.Status.CANCELLED
    issued.cancelled_at = timezone.now()
    issued.save(update_fields=["status", "cancelled_at", "updated_at"])


@transaction.atomic
def release_pass(line) -> None:
    """A failed payment gives every leg's capacity back at once."""
    issued = getattr(line, "pass_issued", None)
    if issued is None or issued.status == Pass.Status.CANCELLED:
        return
    _unwind(issued, list(issued.legs.all()))
