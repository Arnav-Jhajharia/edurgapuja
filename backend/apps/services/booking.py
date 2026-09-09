"""Starting a service booking.

Order of operations matters: **hold the place first, then create the order.** The
other way round would take money for something that turns out to be sold out.

Not every service has places to hold. One with `requires_capacity` off — prasad
posted to your house, say — skips the hold entirely and is confirmed the moment
it is paid for, because there is nothing that could have run out in between.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.common.errors import ValidationFailedError
from apps.orders import services as orders
from apps.orders.models import OrderLine

from . import inventory
from .models import Service, ServiceBooking, ServiceDayCapacity, validate_details


@transaction.atomic
def start_booking(*, service_id, date, quantity: int, details: dict, user):
    service = get_object_or_404(
        Service.objects.select_related("pandal").filter(is_active=True), pk=service_id
    )
    if quantity > service.max_per_booking:
        raise ValidationFailedError(
            f"At most {service.max_per_booking} per booking.",
            fields={"quantity": f"Reduce to {service.max_per_booking} or fewer."},
        )

    cleaned = validate_details(service, details or {})

    day = None
    hold = None
    if service.requires_capacity:
        day = get_object_or_404(ServiceDayCapacity, service=service, date=date)
        # Raises CapacityUnavailableError, carrying how many are left, so the
        # client can offer the next day rather than a dead end.
        hold = inventory.place_hold(day_id=day.pk, quantity=quantity)

    order = orders.create_order(pandal=service.pandal, user=user,
                                contact_phone=cleaned.get("contact_phone", ""))
    line = orders.add_line(order, kind=OrderLine.Kind.SERVICE_BOOKING,
                           unit_amount_paise=service.price_paise, quantity=quantity,
                           description=service.name)
    orders.finalise(order)

    if hold is not None:
        hold.order = order
        hold.save(update_fields=["order", "updated_at"])

    booking = ServiceBooking.objects.create(
        service=service, day=day, hold=hold, order_line=line,
        user=user if user and user.is_authenticated else None,
        quantity=quantity, details=cleaned,
    )
    return booking, order, hold
