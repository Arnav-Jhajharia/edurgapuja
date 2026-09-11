"""Payment attempts, and what a provider callback means.

Two properties this module exists to guarantee:

* **The same idempotency key never charges twice.** A retried request returns the
  original attempt.
* **A redelivered webhook is a no-op.** Deduplication is the unique constraint on
  (provider, event_id), not application logic.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.errors import DomainError, ValidationFailedError
from apps.orders import services as orders
from apps.orders.models import Order, OrderLine

from .models import PaymentEvent, PaymentOrder
from .providers import (
    PaymentAmountError,
    PaymentRejectedError,
    PaymentUnavailableError,
    get_provider,
)


class PaymentNotFoundError(DomainError):
    status_code = 404
    default_code = "payment_not_found"
    default_detail = "That payment does not belong to any order here."


class PaymentGatewayError(DomainError):
    """The gateway would not take the request.

    502 rather than 500: nothing here is broken, the thing we depend on is —
    and the client should say "try again", not "something went wrong".
    """

    status_code = 502
    default_code = "payment_gateway_unavailable"
    default_detail = "We could not reach the payment gateway. Please try again."

logger = logging.getLogger(__name__)


@transaction.atomic
def create_payment(*, order: Order, idempotency_key: str, provider_name: str = "") -> PaymentOrder:
    existing = PaymentOrder.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        # A retry keeps the provider the first attempt chose. Switching midway
        # would leave two live orders at two gateways for one payment.
        return existing

    provider = get_provider(provider_name)
    try:
        created = provider.create_order(amount_paise=order.total_paise, receipt=str(order.id))
    except PaymentAmountError as problem:
        raise ValidationFailedError(str(problem),
                                    fields={"amount_paise": str(problem)}) from problem
    except (PaymentRejectedError, PaymentUnavailableError) as problem:
        logger.error("payment order creation failed at %s: %s", provider.name, problem)
        raise PaymentGatewayError from problem

    try:
        return PaymentOrder.objects.create(
            order=order,
            amount_paise=order.total_paise,
            provider=created.provider,
            provider_order_id=created.provider_order_id,
            idempotency_key=idempotency_key,
        )
    except IntegrityError:
        # Two requests raced on the same key; the loser returns the winner's row.
        return PaymentOrder.objects.get(idempotency_key=idempotency_key)


def payment_intent(payment: PaymentOrder) -> dict:
    """The shape a client hands to the gateway's checkout widget."""
    from django.conf import settings

    return {
        "provider": payment.provider,
        "provider_order_id": payment.provider_order_id,
        "key_id": settings.RAZORPAY_KEY_ID or "rzp_test_stub",
        "amount_paise": payment.amount_paise,
        "currency": payment.currency,
    }


def record_event(*, provider: str, event_id: str, event_type: str, payload: dict) -> PaymentEvent:
    """Store first, interpret afterwards.

    The provider retries until it sees a 2xx, so this has to be fast and must
    never process the same event twice.
    """
    # Its own atomic block, so a duplicate raises inside a savepoint and leaves
    # the surrounding transaction usable.
    with transaction.atomic():
        return PaymentEvent.objects.create(
            provider=provider, event_id=event_id, event_type=event_type,
            payload=payload, signature_verified=True,
        )


@transaction.atomic
def process_event(event: PaymentEvent) -> None:
    """Interpret a stored callback. Safe to call more than once."""
    if event.processed_at:
        return

    entity = _payment_entity(event.payload)
    provider_order_id = entity.get("order_id", "")
    payment = (PaymentOrder.objects
               .select_for_update()
               .filter(provider_order_id=provider_order_id)
               .first())

    if payment is None:
        event.processing_error = f"No payment for provider order {provider_order_id!r}"
        event.processed_at = timezone.now()
        event.save(update_fields=["processing_error", "processed_at", "updated_at"])
        return

    if event.event_type in {"payment.captured", "order.paid"}:
        _capture(payment, entity)
    elif event.event_type == "payment.failed":
        _fail(payment, entity)

    event.payment = payment
    event.processed_at = timezone.now()
    event.save(update_fields=["payment", "processed_at", "updated_at"])


def _payment_entity(payload: dict) -> dict:
    """Razorpay nests the interesting part; be forgiving about the shape."""
    try:
        return payload["payload"]["payment"]["entity"]
    except (KeyError, TypeError):
        return payload.get("payload", payload) if isinstance(payload, dict) else {}


def _capture(payment: PaymentOrder, entity: dict) -> None:
    if payment.status == PaymentOrder.Status.CAPTURED:
        return

    payment.status = PaymentOrder.Status.CAPTURED
    payment.provider_payment_id = entity.get("id", "")
    payment.method = entity.get("method", "") or ""
    payment.captured_at = timezone.now()
    payment.save(update_fields=["status", "provider_payment_id", "method",
                                "captured_at", "updated_at"])

    orders.mark_paid(payment.order)
    _fulfil(payment.order)


def _fail(payment: PaymentOrder, entity: dict) -> None:
    payment.status = PaymentOrder.Status.FAILED
    payment.failure_reason = (entity.get("error_description") or "")[:255]
    payment.save(update_fields=["status", "failure_reason", "updated_at"])
    orders.mark_failed(payment.order)
    _release(payment.order)


def _fulfil(order: Order) -> None:
    """Turn a paid order into the thing that was bought."""
    from apps.donations.fulfilment import confirm_donation
    from apps.passes.fulfilment import confirm_pass
    from apps.services.fulfilment import confirm_service_booking

    for line in order.lines.select_related().all():
        if line.kind == OrderLine.Kind.DONATION:
            confirm_donation(line)
        elif line.kind == OrderLine.Kind.SERVICE_BOOKING:
            confirm_service_booking(line)
        elif line.kind == OrderLine.Kind.PASS:
            confirm_pass(line)


def _release(order: Order) -> None:
    """A failed payment gives its capacity back at once rather than waiting for
    the hold to lapse."""
    from apps.passes.fulfilment import release_pass
    from apps.services.fulfilment import release_service_booking

    for line in order.lines.all():
        if line.kind == OrderLine.Kind.SERVICE_BOOKING:
            release_service_booking(line)
        elif line.kind == OrderLine.Kind.PASS:
            release_pass(line)


@transaction.atomic
def confirm_from_handoff(*, order_id: str, payment_id: str, signature: str) -> PaymentOrder:
    """Settle a payment from what the browser handed back when the modal closed.

    The webhook remains the source of truth — it arrives whether or not the
    browser survives the redirect, and it is what catches a payment completed
    on a phone that then lost signal. This path exists so a donor sees "thank
    you" immediately rather than watching a spinner until a webhook lands.

    Both converge on the same `_capture`, which is idempotent, so whichever
    arrives second does nothing.
    """
    payment = (PaymentOrder.objects
               .select_for_update()
               .filter(provider_order_id=order_id)
               .first())
    if payment is None:
        # A signature can only be forged by somebody with the key secret, so a
        # valid signature for an order we have never seen means our own state is
        # wrong. Either way the browser learns nothing from the distinction.
        raise PaymentNotFoundError

    get_provider(payment.provider).verify_handoff(
        order_id=order_id, payment_id=payment_id, signature=signature,
    )

    _capture(payment, {"id": payment_id, "method": ""})
    return payment

