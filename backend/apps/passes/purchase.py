"""Buying a pass.

Same order of operations as a service booking, and for the same reason: **hold
the capacity first, then create the order.** The other way round takes money for
something that turns out to be sold out.

What passes add is that one purchase can touch several pandals. A City Pass
covers many, and consumes one place at each of them on its chosen date (Q3) —
so the hold is a hold per leg, and either all of them are placed or none is. The
surrounding transaction is what makes that true: a CapacityUnavailableError
raised on the fourth pandal rolls back the three holds already placed.
"""

import datetime as dt

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.common.errors import ValidationFailedError
from apps.orders import services as orders
from apps.orders.models import OrderLine
from apps.pandals.models import Pandal

from . import inventory
from .models import (
    PandalDayCapacity,
    Pass,
    PassConfig,
    PassLeg,
    PassProduct,
)


def covered_pandals(config: PassConfig, *, pandal_ids=None) -> list[Pandal]:
    """Which pandals a purchase of this configuration covers.

    Individual and Group cover the one pandal that sells them. A City Pass
    covers every pandal selling passes in that city — narrowed to a chosen
    subset when the buyer picks, which keeps a fifty-pandal city from holding
    fifty places for somebody who will visit four.
    """
    if config.product != PassProduct.CITY:
        return [config.pandal]

    queryset = Pandal.objects.filter(
        city_id=config.pandal.city_id, sells_passes=True, is_active=True,
        publication_status=Pandal.PublicationStatus.PUBLISHED,
    )
    if pandal_ids:
        queryset = queryset.filter(id__in=pandal_ids)
    return list(queryset.order_by("name"))


def _validate(config: PassConfig, *, visit_date: dt.date, party_size: int, pandals: list[Pandal]):
    if not config.is_active:
        raise ValidationFailedError("That pass is not on sale.")
    if not (config.from_date <= visit_date <= config.to_date):
        raise ValidationFailedError(
            f"That pass is valid from {config.from_date} to {config.to_date}.",
            fields={"visit_date": "Choose a date inside the range."},
        )
    if config.product != PassProduct.GROUP and party_size != 1:
        # The database refuses this too; saying so here gives a usable message
        # instead of an IntegrityError.
        raise ValidationFailedError(
            "Only a group pass covers more than one person.",
            fields={"party_size": "Choose a group pass, or buy one pass per person."},
        )
    if party_size > config.max_party_size:
        raise ValidationFailedError(
            f"A group pass covers at most {config.max_party_size} people.",
            fields={"party_size": f"Reduce to {config.max_party_size} or fewer."},
        )
    if not pandals:
        raise ValidationFailedError("No pandal in that city is selling passes for that day.")


@transaction.atomic
def start_purchase(*, config_id, visit_date: dt.date, party_size: int = 1,
                   pandal_ids=None, user, contact_phone: str = ""):
    """Hold a place at every covered pandal, then bill for it once.

    Returns the pass, its order and its holds. The pass exists in `active` state
    with legs `pending`: it authorises nothing until the order is paid and
    `fulfilment.confirm_pass` issues the capacity.
    """
    config = get_object_or_404(
        PassConfig.objects.select_related("pandal", "category").filter(is_active=True),
        pk=config_id,
    )
    pandals = covered_pandals(config, pandal_ids=pandal_ids)
    _validate(config, visit_date=visit_date, party_size=party_size, pandals=pandals)

    issued = Pass.objects.create(
        product=config.product,
        category=config.category,
        party_size=party_size,
        holder=user if user and user.is_authenticated else None,
        source=Pass.Source.RETAIL,
    )

    holds = []
    for pandal in pandals:
        # A pandal that has not opened that date has no row, and no row means no
        # capacity — the pandal decides which days it sells, not the buyer.
        day = PandalDayCapacity.objects.filter(pandal=pandal, date=visit_date).first()
        if day is None:
            raise ValidationFailedError(
                f"{pandal.name} is not admitting visitors on {visit_date}.",
                fields={"visit_date": "Choose another date."},
            )
        # Raises CapacityUnavailableError carrying how many are left, which rolls
        # back every hold placed for the earlier pandals in this loop.
        hold = inventory.place_hold(day_id=day.pk, quantity=party_size)
        holds.append(hold)

        PassLeg.objects.create(
            issued_pass=issued, pandal=pandal, visit_date=visit_date,
            # A City Pass has a date and no time (D3).
            slot_from=None if config.product == PassProduct.CITY else config.from_time,
            slot_to=None if config.product == PassProduct.CITY else config.to_time,
            capacity_hold=hold,
        )

    # One order, billed once, however many pandals the pass covers.
    order = orders.create_order(pandal=config.pandal, user=user, contact_phone=contact_phone)
    line = orders.add_line(
        order, kind=OrderLine.Kind.PASS,
        unit_amount_paise=config.price_paise, quantity=party_size,
        description=f"{config.get_product_display()} pass · {config.category.name}",
    )
    orders.finalise(order)

    for hold in holds:
        hold.order = order
        hold.save(update_fields=["order", "updated_at"])

    issued.order_line = line
    issued.save(update_fields=["order_line", "updated_at"])

    return issued, order, holds
