"""Razorpay Standard Checkout: creating the order and settling from the handoff.

Two signatures are involved and they are easy to confuse. The **webhook**
signature covers the whole request body and is how Razorpay proves a server
callback. The **handoff** signature covers `order_id|payment_id` and is how the
browser proves the modal really succeeded. This file is about the second.

What matters is that a forged handoff marks nothing paid, and that the two
routes to settlement — browser and webhook — converge without double-counting.
"""

import hashlib
import hmac

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.orders.models import Order, OrderLine
from apps.payments import services
from apps.payments.models import PaymentOrder
from apps.payments.providers import (
    MINIMUM_PAISE,
    PaymentAmountError,
    PaymentUnavailableError,
    SignatureError,
    get_provider,
)

pytestmark = pytest.mark.django_db

SECRET = "a-test-key-secret"
LIVE = {"RAZORPAY_KEY_ID": "rzp_test_x", "RAZORPAY_KEY_SECRET": SECRET}


def handoff_signature(order_id: str, payment_id: str, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(),
                    hashlib.sha256).hexdigest()


@pytest.fixture
def pending(pandal, db):
    """An order with a payment attempt against it, as checkout leaves things."""
    order = Order.objects.create(pandal=pandal, total_paise=50_000, subtotal_paise=50_000)
    OrderLine.objects.create(order=order, kind=OrderLine.Kind.DONATION, quantity=1,
                             unit_amount_paise=50_000, amount_paise=50_000)
    return PaymentOrder.objects.create(
        order=order, amount_paise=50_000, provider="razorpay",
        provider_order_id="order_TEST123", idempotency_key="k-1",
    )


# --------------------------------------------------------------------------
# Creating the order
# --------------------------------------------------------------------------

@override_settings(**LIVE)
def test_an_amount_below_the_gateways_floor_is_refused_here(monkeypatch):
    """Razorpay would refuse it anyway; refusing here says why."""
    with pytest.raises(PaymentAmountError):
        get_provider("razorpay").create_order(amount_paise=MINIMUM_PAISE - 1, receipt="r")


@override_settings(**LIVE)
def test_the_amount_is_sent_in_paise_unconverted(monkeypatch):
    """Razorpay takes paise, which is what this codebase already holds money in.
    Cashfree is the one that wants rupees — converting here would be a
    hundredfold error."""
    sent = {}

    class FakeOrders:
        def create(self, data):
            sent.update(data)
            return {"id": "order_MADE"}

    class FakeClient:
        order = FakeOrders()

    monkeypatch.setattr(get_provider("razorpay").__class__, "_client",
                        lambda self: FakeClient())

    created = get_provider("razorpay").create_order(amount_paise=50_000, receipt="rcpt")

    assert sent["amount"] == 50_000
    assert sent["currency"] == "INR"
    assert created.provider_order_id == "order_MADE"


@override_settings(**LIVE)
def test_a_gateway_outage_is_a_502_not_a_500(api, pandal, monkeypatch):
    """Nothing here is broken — the thing we depend on is, and the donor should
    be told to try again."""
    def explode(self, **kwargs):
        # What the real method raises when httpx or the gateway fails — the
        # provider wraps unexpected errors so callers have one thing to catch.
        raise PaymentUnavailableError("connection reset")

    monkeypatch.setattr(get_provider("razorpay").__class__, "create_order", explode)

    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": 50_000}, format="json")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "payment_gateway_unavailable"


# --------------------------------------------------------------------------
# The handoff
# --------------------------------------------------------------------------

@override_settings(**LIVE)
def test_a_genuine_handoff_settles_the_order(api, pending):
    response = api.post(reverse("payment-verify"), {
        "razorpay_order_id": "order_TEST123",
        "razorpay_payment_id": "pay_ABC",
        "razorpay_signature": handoff_signature("order_TEST123", "pay_ABC"),
    }, format="json")

    assert response.status_code == 200
    assert response.json()["status"] == Order.Status.PAID
    assert response.json()["receipt_number"]

    pending.refresh_from_db()
    assert pending.status == PaymentOrder.Status.CAPTURED
    assert pending.provider_payment_id == "pay_ABC"


@override_settings(**LIVE)
def test_a_forged_handoff_marks_nothing_paid(api, pending):
    """The whole point of the signature. Without the key secret nobody can
    produce one, so a made-up payment id cannot buy anything."""
    response = api.post(reverse("payment-verify"), {
        "razorpay_order_id": "order_TEST123",
        "razorpay_payment_id": "pay_INVENTED",
        "razorpay_signature": "deadbeef",
    }, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "payment_signature_invalid"

    pending.refresh_from_db()
    assert pending.status == PaymentOrder.Status.CREATED
    assert pending.order.status == Order.Status.PENDING


@override_settings(**LIVE)
def test_a_signature_from_a_different_secret_is_refused(api, pending):
    response = api.post(reverse("payment-verify"), {
        "razorpay_order_id": "order_TEST123",
        "razorpay_payment_id": "pay_ABC",
        "razorpay_signature": handoff_signature("order_TEST123", "pay_ABC", "somebody-elses"),
    }, format="json")

    assert response.status_code == 400


@override_settings(**LIVE)
def test_a_handoff_for_an_unknown_order_is_refused(api, pending):
    response = api.post(reverse("payment-verify"), {
        "razorpay_order_id": "order_NOTOURS",
        "razorpay_payment_id": "pay_ABC",
        "razorpay_signature": handoff_signature("order_NOTOURS", "pay_ABC"),
    }, format="json")

    assert response.status_code == 404


@override_settings(**LIVE)
def test_missing_fields_are_refused_before_anything_is_checked(api, pending):
    response = api.post(reverse("payment-verify"),
                        {"razorpay_order_id": "order_TEST123"}, format="json")

    assert response.status_code == 422


@override_settings(**LIVE)
def test_settling_twice_does_not_double_count(api, pending):
    """The browser and the webhook both settle, and either may arrive first."""
    body = {
        "razorpay_order_id": "order_TEST123",
        "razorpay_payment_id": "pay_ABC",
        "razorpay_signature": handoff_signature("order_TEST123", "pay_ABC"),
    }
    first = api.post(reverse("payment-verify"), body, format="json").json()
    api.post(reverse("payment-verify"), body, format="json")

    pending.order.refresh_from_db()
    # The receipt number is issued once and never reissued.
    assert pending.order.receipt_number == first["receipt_number"]
    assert PaymentOrder.objects.count() == 1


@override_settings(**LIVE)
def test_a_webhook_after_the_browser_handoff_changes_nothing(pending):
    """`_capture` is idempotent, which is what lets both paths exist."""
    services.confirm_from_handoff(order_id="order_TEST123", payment_id="pay_ABC",
                                  signature=handoff_signature("order_TEST123", "pay_ABC"))
    pending.order.refresh_from_db()
    paid_at, receipt = pending.order.paid_at, pending.order.receipt_number

    services._capture(pending, {"id": "pay_ABC", "method": "upi"})

    pending.order.refresh_from_db()
    assert pending.order.paid_at == paid_at
    assert pending.order.receipt_number == receipt


@override_settings(RAZORPAY_KEY_SECRET="")
def test_with_no_secret_configured_verification_refuses_rather_than_accepts():
    """The dangerous default would be to wave it through."""
    with pytest.raises(SignatureError):
        get_provider("razorpay").verify_handoff(order_id="o", payment_id="p", signature="s")
