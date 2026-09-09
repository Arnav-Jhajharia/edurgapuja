"""The payment callback, and what it fulfils.

The property being tested is the one from the API contract §6.2: no captured
payment ever ends without either a completed purchase or a completed refund.
"""

import datetime as dt
import hashlib
import hmac
import json

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.donations.models import Donation
from apps.orders.models import Order
from apps.payments.models import PaymentEvent, PaymentOrder
from apps.services.models import ServiceBooking, ServiceCapacityHold

pytestmark = pytest.mark.django_db

SECRET = "test-webhook-secret"


@pytest.fixture(autouse=True)
def _webhook_secret(settings):
    settings.RAZORPAY_WEBHOOK_SECRET = SECRET


def deliver(client, payload: dict, *, event_id="evt_1", secret=SECRET):
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(reverse("razorpay-webhook"), data=body,
                       content_type="application/json",
                       HTTP_X_RAZORPAY_SIGNATURE=signature,
                       HTTP_X_RAZORPAY_EVENT_ID=event_id)


def captured(provider_order_id: str) -> dict:
    return {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": "pay_abc123", "order_id": provider_order_id, "method": "upi",
        }}},
    }


def test_a_forged_signature_is_rejected_and_stored_nowhere(client):
    response = deliver(client, captured("order_x"), secret="wrong")

    assert response.status_code == 400
    assert not PaymentEvent.objects.exists()


def test_a_redelivered_event_is_a_no_op(client):
    payload = captured("order_x")

    assert deliver(client, payload, event_id="evt_dup").status_code == 200
    assert deliver(client, payload, event_id="evt_dup").status_code == 200
    assert PaymentEvent.objects.count() == 1


def test_an_event_for_an_unknown_order_is_recorded_not_lost(client):
    deliver(client, captured("order_nobody"))

    event = PaymentEvent.objects.get()
    assert event.processed_at is not None
    assert "No payment for provider order" in event.processing_error


def test_capture_pays_the_order_and_completes_the_donation(api, client, pandal):
    created = api.post(reverse("donation-create"),
                       {"pandal_id": str(pandal.id), "amount_paise": 50_100},
                       format="json").json()
    payment = PaymentOrder.objects.get(order_id=created["order_id"])

    deliver(client, captured(payment.provider_order_id))

    payment.refresh_from_db()
    order = Order.objects.get(pk=created["order_id"])
    donation = Donation.objects.get(pk=created["donation_id"])

    assert payment.status == PaymentOrder.Status.CAPTURED
    assert payment.provider_payment_id == "pay_abc123"
    assert payment.method == "upi"
    assert order.status == Order.Status.PAID
    assert order.receipt_number
    assert donation.received_at is not None


def test_a_receipt_exists_once_the_money_has_arrived(api, client, pandal):
    created = api.post(reverse("donation-create"),
                       {"pandal_id": str(pandal.id), "amount_paise": 50_100},
                       format="json").json()
    payment = PaymentOrder.objects.get(order_id=created["order_id"])
    deliver(client, captured(payment.provider_order_id))

    body = api.get(reverse("order-receipt", args=[created["order_id"]])).json()

    assert body["receipt_number"].startswith("EDP-R-")
    assert body["total_paise"] == 50_100
    assert body["pandal"] == pandal.name


def test_capturing_twice_does_not_pay_twice(api, client, pandal):
    """The provider retries. Fulfilment must be idempotent."""
    created = api.post(reverse("donation-create"),
                       {"pandal_id": str(pandal.id), "amount_paise": 50_100},
                       format="json").json()
    payment = PaymentOrder.objects.get(order_id=created["order_id"])

    deliver(client, captured(payment.provider_order_id), event_id="evt_a")
    order = Order.objects.get(pk=created["order_id"])
    first_receipt, first_paid_at = order.receipt_number, order.paid_at

    deliver(client, captured(payment.provider_order_id), event_id="evt_b")
    order.refresh_from_db()

    assert order.receipt_number == first_receipt
    assert order.paid_at == first_paid_at


def test_capture_issues_the_capacity_a_service_booking_was_holding(api, client, visitor,
                                                                   service, service_day):
    api.force_authenticate(visitor)
    created = api.post(reverse("service-booking-list"), {
        "service_id": str(service.id), "date": str(service_day.date), "quantity": 2,
        "details": {"name": "Ananya Sen", "party_size": 2},
    }, format="json").json()
    payment = PaymentOrder.objects.get(order_id=created["order_id"])

    deliver(client, captured(payment.provider_order_id))

    booking = ServiceBooking.objects.get(pk=created["booking_id"])
    service_day.refresh_from_db()
    assert booking.status == ServiceBooking.Status.CONFIRMED
    assert booking.confirmed_at is not None
    assert service_day.issued_count == 2


def test_a_payment_that_lands_after_the_place_has_gone_is_not_honoured(api, client, visitor,
                                                                        service, service_day):
    """The caller refunds. That is the honest outcome, not the convenient one."""
    service_day.capacity = 1
    service_day.save(update_fields=["capacity"])
    api.force_authenticate(visitor)

    created = api.post(reverse("service-booking-list"), {
        "service_id": str(service.id), "date": str(service_day.date), "quantity": 1,
        "details": {"name": "Ananya Sen"},
    }, format="json").json()
    booking = ServiceBooking.objects.get(pk=created["booking_id"])

    # The hold lapses, and somebody else takes the last place.
    ServiceCapacityHold.objects.filter(pk=booking.hold_id).update(
        expires_at=timezone.now() - dt.timedelta(minutes=20)
    )
    from apps.services import inventory
    other = inventory.place_hold(day_id=service_day.pk, quantity=1)
    inventory.issue(hold_id=other.pk)

    payment = PaymentOrder.objects.get(order_id=created["order_id"])
    deliver(client, captured(payment.provider_order_id))

    booking.refresh_from_db()
    service_day.refresh_from_db()
    assert booking.status == ServiceBooking.Status.EXPIRED
    assert service_day.issued_count == 1


def test_a_failed_payment_gives_the_place_back_at_once(api, client, visitor,
                                                        service, service_day):
    api.force_authenticate(visitor)
    created = api.post(reverse("service-booking-list"), {
        "service_id": str(service.id), "date": str(service_day.date), "quantity": 5,
        "details": {"name": "Ananya Sen"},
    }, format="json").json()
    payment = PaymentOrder.objects.get(order_id=created["order_id"])

    from apps.services import inventory
    assert inventory.available(service_day) == 15

    deliver(client, {
        "event": "payment.failed",
        "payload": {"payment": {"entity": {
            "id": "pay_fail", "order_id": payment.provider_order_id,
            "error_description": "Insufficient funds",
        }}},
    })

    payment.refresh_from_db()
    assert payment.status == PaymentOrder.Status.FAILED
    assert payment.failure_reason == "Insufficient funds"
    assert inventory.available(service_day) == 20
