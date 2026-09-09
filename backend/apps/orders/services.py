"""Building an order.

One order, many lines (Scope §4.1). Donations and service bookings both come
through here, and passes will too — so receipts, refunds and revenue reporting
are written once, over lines.
"""

from django.db import transaction
from django.utils import timezone

from .models import Order, OrderLine


@transaction.atomic
def create_order(*, pandal, user=None, contact_phone: str = "", contact_email: str = "",
                 platform_fee_paise: int = 0) -> Order:
    return Order.objects.create(
        pandal=pandal,
        user=user if user and user.is_authenticated else None,
        contact_phone=contact_phone,
        contact_email=contact_email,
        platform_fee_paise=platform_fee_paise,
    )


def add_line(order: Order, *, kind: str, unit_amount_paise: int, quantity: int = 1,
             description: str = "") -> OrderLine:
    return OrderLine.objects.create(
        order=order, kind=kind, quantity=quantity,
        unit_amount_paise=unit_amount_paise, description=description,
    )


@transaction.atomic
def finalise(order: Order) -> Order:
    """Total the lines. Called once every line has been added."""
    order.recalculate()
    order.save(update_fields=["subtotal_paise", "total_paise", "updated_at"])
    return order


@transaction.atomic
def mark_paid(order: Order) -> Order:
    """Idempotent: a redelivered webhook must not re-run fulfilment."""
    if order.status == Order.Status.PAID:
        return order
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    if not order.receipt_number:
        order.receipt_number = f"EDP-R-{order.created_at:%Y%m}-{str(order.id)[-8:].upper()}"
    order.save(update_fields=["status", "paid_at", "receipt_number", "updated_at"])
    return order


@transaction.atomic
def mark_failed(order: Order, reason: str = "") -> Order:
    order.status = Order.Status.FAILED
    order.save(update_fields=["status", "updated_at"])
    return order
