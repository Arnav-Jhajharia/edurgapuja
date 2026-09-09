"""Two gateways, one payment path.

A committee losing an evening to one gateway's outage is a real failure mode, so
switching is a setting. What must not differ is anything downstream: the same
order, the same deduplication, the same fulfilment.

The signature schemes are where this gets dangerous, because they look similar
and are not. Razorpay signs the raw body as hex. Cashfree signs
`timestamp + body` as base64 — so the timestamp header is part of the proof, and
verifying the body alone would accept a replay.
"""

import base64
import hashlib
import hmac
import json

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.payments.providers import SignatureError, get_provider

pytestmark = pytest.mark.django_db

RZP_SECRET = "razorpay-webhook-secret"
CF_SECRET = "cashfree-webhook-secret"


def razorpay_signature(body: bytes) -> str:
    return hmac.new(RZP_SECRET.encode(), body, hashlib.sha256).hexdigest()


def cashfree_signature(body: bytes, timestamp: str) -> str:
    digest = hmac.new(CF_SECRET.encode(), timestamp.encode() + body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


# --------------------------------------------------------------------------
# Choosing one
# --------------------------------------------------------------------------

def test_both_gateways_are_offered(api):
    body = api.get(reverse("payment-providers")).json()
    assert body["providers"] == ["razorpay", "cashfree"]


@override_settings(PAYMENT_PROVIDERS="cashfree")
def test_turning_one_off_is_a_setting(api):
    """During an outage, taking money again should not need a release."""
    assert api.get(reverse("payment-providers")).json()["providers"] == ["cashfree"]
    assert get_provider().name == "cashfree"


def test_asking_for_a_gateway_gets_that_gateway():
    assert get_provider("cashfree").name == "cashfree"
    assert get_provider("razorpay").name == "razorpay"


def test_asking_for_one_that_is_off_falls_back_rather_than_failing():
    """A stale client asking for a gateway we turned off should still be able to
    pay, not see a 500."""
    with override_settings(PAYMENT_PROVIDERS="razorpay"):
        assert get_provider("cashfree").name == "razorpay"
    assert get_provider("nonsense").name == "razorpay"


def test_a_donation_can_name_its_gateway(api, pandal):
    from apps.payments.models import PaymentOrder

    response = api.post(reverse("donation-create"), {
        "pandal_id": str(pandal.id), "amount_paise": 50_000, "payment_provider": "cashfree",
    }, format="json")

    assert response.status_code == 201
    assert PaymentOrder.objects.get().provider == "cashfree"


def test_a_retry_keeps_the_gateway_the_first_attempt_chose(api, pandal):
    """Switching midway would leave two live orders at two gateways for one
    payment."""
    from apps.payments.models import PaymentOrder

    key = {"HTTP_IDEMPOTENCY_KEY": "the-same-key"}
    body = {"pandal_id": str(pandal.id), "amount_paise": 50_000}
    api.post(reverse("donation-create"), {**body, "payment_provider": "cashfree"},
             format="json", **key)
    api.post(reverse("donation-create"), {**body, "payment_provider": "razorpay"},
             format="json", **key)

    assert PaymentOrder.objects.count() == 1
    assert PaymentOrder.objects.get().provider == "cashfree"


# --------------------------------------------------------------------------
# The signatures — different schemes that look alike
# --------------------------------------------------------------------------

@override_settings(RAZORPAY_WEBHOOK_SECRET=RZP_SECRET)
def test_razorpay_signs_the_raw_body():
    body = b'{"event":"payment.captured"}'
    get_provider("razorpay").verify_webhook(body, razorpay_signature(body))

    with pytest.raises(SignatureError):
        get_provider("razorpay").verify_webhook(body, "deadbeef")


@override_settings(CASHFREE_SECRET_KEY=CF_SECRET)
def test_cashfree_signs_the_timestamp_with_the_body():
    body = b'{"type":"PAYMENT_SUCCESS_WEBHOOK"}'
    stamp = "1788950000"
    get_provider("cashfree").verify_webhook(body, cashfree_signature(body, stamp), stamp)

    # The same body with a different timestamp must not verify — that is the
    # replay this scheme exists to stop.
    with pytest.raises(SignatureError):
        get_provider("cashfree").verify_webhook(body, cashfree_signature(body, stamp), "1788999999")


@override_settings(CASHFREE_SECRET_KEY=CF_SECRET)
def test_cashfree_refuses_a_webhook_with_no_timestamp():
    body = b'{"type":"PAYMENT_SUCCESS_WEBHOOK"}'
    with pytest.raises(SignatureError):
        get_provider("cashfree").verify_webhook(body, cashfree_signature(body, "1"), "")


@override_settings(CASHFREE_SECRET_KEY="")
def test_an_unconfigured_secret_refuses_rather_than_accepts():
    """The dangerous default would be to wave it through."""
    with pytest.raises(SignatureError):
        get_provider("cashfree").verify_webhook(b"{}", "anything", "1")


# --------------------------------------------------------------------------
# Delivery
# --------------------------------------------------------------------------

@override_settings(CASHFREE_SECRET_KEY=CF_SECRET)
def test_a_cashfree_webhook_is_stored_and_acknowledged(client):
    from apps.payments.models import PaymentEvent

    payload = {"type": "PAYMENT_SUCCESS_WEBHOOK",
               "data": {"order": {"order_id": "cf_order_1"},
                        "payment": {"cf_payment_id": "99"}}}
    body = json.dumps(payload).encode()
    stamp = "1788950000"

    response = client.post(reverse("cashfree-webhook"), data=body,
                           content_type="application/json",
                           HTTP_X_WEBHOOK_SIGNATURE=cashfree_signature(body, stamp),
                           HTTP_X_WEBHOOK_TIMESTAMP=stamp)

    assert response.status_code == 200
    assert PaymentEvent.objects.get().provider == "cashfree"


@override_settings(CASHFREE_SECRET_KEY=CF_SECRET)
def test_a_redelivered_cashfree_webhook_is_a_no_op(client):
    """Cashfree sends no single event id, so one is composed. It has to be
    stable across redeliveries or dedup does nothing."""
    from apps.payments.models import PaymentEvent

    payload = {"type": "PAYMENT_SUCCESS_WEBHOOK",
               "data": {"order": {"order_id": "cf_order_2"},
                        "payment": {"cf_payment_id": "100"}}}
    body = json.dumps(payload).encode()
    stamp = "1788950000"
    headers = {"HTTP_X_WEBHOOK_SIGNATURE": cashfree_signature(body, stamp),
               "HTTP_X_WEBHOOK_TIMESTAMP": stamp}

    for _ in range(3):
        assert client.post(reverse("cashfree-webhook"), data=body,
                           content_type="application/json", **headers).status_code == 200

    assert PaymentEvent.objects.count() == 1


@override_settings(CASHFREE_SECRET_KEY=CF_SECRET)
def test_a_forged_cashfree_webhook_is_refused(client):
    from apps.payments.models import PaymentEvent

    response = client.post(reverse("cashfree-webhook"), data=b'{"type":"x"}',
                           content_type="application/json",
                           HTTP_X_WEBHOOK_SIGNATURE="forged",
                           HTTP_X_WEBHOOK_TIMESTAMP="1")

    assert response.status_code == 400
    assert not PaymentEvent.objects.exists()


def test_the_two_providers_are_separate_namespaces():
    """Both stubs must produce distinguishable order ids, or a support call
    about 'order_abc' has two possible answers."""
    rzp = get_provider("razorpay").create_order(amount_paise=100, receipt="r")
    cf = get_provider("cashfree").create_order(amount_paise=100, receipt="r")

    assert rzp.provider_order_id.startswith("order_")
    assert cf.provider_order_id.startswith("cf_")
