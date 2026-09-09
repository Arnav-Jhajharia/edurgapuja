"""Turning a sponsor's pool entitlement into passes somebody can actually use.

`sponsorship.issue_from_pool` moves the pool's counter and records the handover;
it deliberately stops there, because a pool is a quota on how many passes may
exist, not a reservation of any particular day (Assumption A2). This module is
the caller it describes: it picks the date, takes the pandal's capacity for it,
and mints the passes.

A sponsor's pass is not free of capacity. Ten thousand people fit through the
gate whether they paid or a sponsor gave them the pass, so these consume the
same `PandalDayCapacity` rows as a retail purchase and can be refused the same
way (D2).
"""

import datetime as dt

from django.db import transaction

from apps.common.errors import ValidationFailedError
from apps.sponsorship import operations as pools
from apps.sponsorship.models import Pool

from . import inventory
from .codes import new_secret
from .models import LegSecret, PandalDayCapacity, Pass, PassCategory, PassLeg, PassProduct


@transaction.atomic
def issue_passes(*, pool_id, quantity: int, visit_date: dt.date, category_id=None,
                 distributed_to: str = "", issued_by=None) -> list[Pass]:
    """Draw `quantity` passes from a pool for one date, and return them.

    Issued straight to `used`-able state: there is no payment to wait for, so the
    capacity is consumed and the secrets provisioned in this one call.
    """
    pool = Pool.objects.select_related("pandal", "organisation").get(pk=pool_id)

    category = (
        PassCategory.objects.filter(pk=category_id, pandal=pool.pandal).first()
        if category_id else
        PassCategory.objects.filter(pandal=pool.pandal, slug="sponsor", is_active=True).first()
        or PassCategory.objects.filter(pandal=pool.pandal, is_active=True).first()
    )
    if category is None:
        raise ValidationFailedError(
            f"{pool.pandal.name} has not defined any pass category to issue against."
        )

    day = PandalDayCapacity.objects.filter(pandal=pool.pandal, date=visit_date).first()
    if day is None:
        raise ValidationFailedError(
            f"{pool.pandal.name} is not admitting visitors on {visit_date}.",
            fields={"visit_date": "Choose a date the pandal has opened."},
        )

    # Draw down the quota first: a pool that cannot cover this must fail before
    # anything touches the day's capacity.
    pools.issue_from_pool(pool_id=pool.pk, quantity=quantity,
                          distributed_to=distributed_to, issued_by=issued_by)

    # One hold for the whole batch, then issued immediately — a sponsor's passes
    # are not held pending a payment that will never come.
    hold = inventory.place_hold(day_id=day.pk, quantity=quantity)
    inventory.issue(hold_id=hold.pk)

    issued = []
    for _ in range(quantity):
        one = Pass.objects.create(
            product=PassProduct.INDIVIDUAL, category=category, party_size=1,
            source=Pass.Source.SPONSOR_POOL, pool=pool, status=Pass.Status.ACTIVE,
        )
        leg = PassLeg.objects.create(issued_pass=one, pandal=pool.pandal, visit_date=visit_date)
        LegSecret.objects.create(leg=leg, secret=new_secret())
        issued.append(one)

    return issued
