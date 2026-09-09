import pytest
from django.db import IntegrityError, transaction

from apps.orders.models import Order
from apps.payments.models import PaymentEvent, PaymentOrder

pytestmark = pytest.mark.django_db


@pytest.fixture
def order(pandal):
    return Order.objects.create(pandal=pandal, total_paise=50_100)


def test_the_same_idempotency_key_can_only_produce_one_attempt(order):
    """The client retries; the network duplicates. Never a second charge."""
    PaymentOrder.objects.create(order=order, amount_paise=50_100, idempotency_key="key-1")

    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentOrder.objects.create(order=order, amount_paise=50_100, idempotency_key="key-1")


def test_one_order_may_have_several_attempts(order):
    """A declined card then a UPI retry is one order and two attempts."""
    PaymentOrder.objects.create(order=order, amount_paise=50_100, idempotency_key="k1",
                                status=PaymentOrder.Status.FAILED)
    PaymentOrder.objects.create(order=order, amount_paise=50_100, idempotency_key="k2")

    assert order.payments.count() == 2


def test_a_redelivered_event_cannot_be_stored_twice():
    """Deduplication is a constraint, not application logic."""
    PaymentEvent.objects.create(provider="razorpay", event_id="evt_1",
                                event_type="payment.captured", signature_verified=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentEvent.objects.create(provider="razorpay", event_id="evt_1",
                                    event_type="payment.captured", signature_verified=True)


def test_a_payment_cannot_be_for_nothing(order):
    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentOrder.objects.create(order=order, amount_paise=0, idempotency_key="k3")
