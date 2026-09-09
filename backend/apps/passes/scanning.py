"""Admitting somebody at a gate.

Every scan is recorded whatever its outcome (FR-110), because the interesting
number on the morning after is not how many were admitted but how many were
turned away and why.

The one rule the database enforces rather than this module is that a leg is
admitted **once, ever**: `one_admission_per_leg` is a partial unique index over
scans whose result is `admitted` or `manual_override`. Two gates scanning the
same phone in the same second both write, and exactly one wins — no lock, no
read-then-write, and it stays true when a device syncs a scan from an hour ago.
"""

import datetime as dt
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.pandals.models import Gate, Volunteer

from .codes import parse, verify
from .models import Pass, PassLeg, ScanEvent

logger = logging.getLogger(__name__)


def _record(*, gate, volunteer, device_id, leg, presented, result, scanned_at,
            override_reason="") -> ScanEvent:
    return ScanEvent.objects.create(
        gate=gate, volunteer=volunteer, device_id=device_id, leg=leg,
        presented_code=presented[:64], result=result, scanned_at=scanned_at,
        received_at=timezone.now(), override_reason=override_reason[:255],
    )


@transaction.atomic
def admit(*, gate: Gate, payload: str, scanned_at=None, volunteer: Volunteer | None = None,
          device_id: str = "", override: bool = False, override_reason: str = "") -> ScanEvent:
    """Interpret one scan and record it. Never raises for a bad code — a refusal
    is data, not an error, and the gate app needs it back to show the volunteer.
    """
    scanned_at = scanned_at or timezone.now()

    def record(leg, result, reason=""):
        return _record(gate=gate, volunteer=volunteer, device_id=device_id, leg=leg,
                       presented=payload or "", result=result, scanned_at=scanned_at,
                       override_reason=reason)

    parsed = parse(payload)
    if parsed is None:
        return record(None, ScanEvent.Result.INVALID)

    leg_id, counter, code = parsed
    leg = (PassLeg.objects
           .select_related("issued_pass", "pandal", "secret")
           .filter(pk=leg_id).first())

    if leg is None or leg.pandal_id != gate.pandal_id:
        # A genuine code for the pandal next door is still not a code for here.
        return record(None, ScanEvent.Result.INVALID)

    secret = getattr(leg, "secret", None)
    if secret is None:
        return record(leg, ScanEvent.Result.INVALID)

    if not override and not verify(secret.secret, counter, code):
        # Either the code is forged, or it is genuine and older than its three
        # minutes. Both read as expired to the volunteer: try again.
        return record(leg, ScanEvent.Result.EXPIRED)

    # Checked before the pass's own status, because admitting the last leg of a
    # pass marks the pass `used` — and a second scan of that leg must tell the
    # volunteer "already used", not "not a valid pass".
    if leg.state == PassLeg.State.VISITED:
        return record(leg, ScanEvent.Result.DUPLICATE)
    if leg.state == PassLeg.State.VOID:
        return record(leg, ScanEvent.Result.INVALID)
    if leg.issued_pass.status != Pass.Status.ACTIVE:
        return record(leg, ScanEvent.Result.INVALID)
    if leg.visit_date != timezone.localdate(scanned_at):
        return record(leg, ScanEvent.Result.INVALID)

    result = ScanEvent.Result.MANUAL_OVERRIDE if override else ScanEvent.Result.ADMITTED
    try:
        # Its own savepoint: a duplicate violates the partial unique index, and
        # without this the surrounding transaction would be poisoned.
        with transaction.atomic():
            event = _record(gate=gate, volunteer=volunteer, device_id=device_id, leg=leg,
                            presented=payload, result=result, scanned_at=scanned_at,
                            override_reason=override_reason)
    except IntegrityError:
        return record(leg, ScanEvent.Result.DUPLICATE)

    leg.state = PassLeg.State.VISITED
    leg.admitted_at = scanned_at
    leg.admitted_gate = gate
    leg.save(update_fields=["state", "admitted_at", "admitted_gate", "updated_at"])

    issued = leg.issued_pass
    if not issued.legs.exclude(state=PassLeg.State.VISITED).exists():
        issued.status = Pass.Status.USED
        issued.save(update_fields=["status", "updated_at"])

    return event


def manifest(*, pandal, date: dt.date) -> list[dict]:
    """Everything a gate device needs to verify offline for one pandal on one day.

    Downloaded while the device still has signal. It carries leg secrets, which
    is the price of verifying without a network — scoped to one pandal and one
    date, and worthless for a second entry because the admission index refuses
    it (D5).
    """
    legs = (PassLeg.objects
            .select_related("issued_pass", "issued_pass__category", "secret")
            .filter(pandal=pandal, visit_date=date, state=PassLeg.State.PENDING,
                    issued_pass__status=Pass.Status.ACTIVE))

    return [
        {
            "leg_id": str(leg.id),
            "secret": leg.secret.secret,
            "pass_code": leg.issued_pass.pass_code,
            "category": leg.issued_pass.category.name,
            "product": leg.issued_pass.product,
            "party_size": leg.issued_pass.party_size,
            "slot_from": leg.slot_from,
            "slot_to": leg.slot_to,
        }
        for leg in legs if hasattr(leg, "secret")
    ]
