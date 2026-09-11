"""Verifying a donor, and the threshold that makes it necessary.

Above a certain amount a donation stops being anonymous, because the committee
has to be able to report it. That is a legal requirement, so the tests are about
the refusal being *actionable* — a donor who has to stop and verify should be
told exactly that, not handed a generic error.
"""

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.donations.models import Donation
from apps.kyc import services as kyc
from apps.kyc.models import KycCheck
from apps.kyc.providers import KycUnavailableError

pytestmark = pytest.mark.django_db

SMALL = 50_000        # ₹500
LARGE = 60_000_00     # ₹60,000, over the default threshold


@pytest.fixture
def offering(pandal):
    from apps.donations.models import DonationOffering
    return DonationOffering.objects.create(pandal=pandal, amount_paise=SMALL, label="Prasad")


# --------------------------------------------------------------------------
# The threshold
# --------------------------------------------------------------------------

def test_a_small_donation_needs_nothing_and_stays_anonymous(api, pandal):
    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": SMALL}, format="json")

    assert response.status_code == 201
    assert Donation.objects.get().kyc_check_id is None


def test_a_large_donation_from_a_stranger_is_refused_with_a_reason(api, pandal):
    """A donor who has to stop and verify should be told that, not handed a
    generic error they cannot act on."""
    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": LARGE}, format="json")

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "kyc_required"
    assert "cannot be anonymous" in body["message"]


def test_a_large_donation_from_someone_signed_in_but_unverified_says_so(api, pandal, visitor):
    api.force_authenticate(visitor)

    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": LARGE}, format="json")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "kyc_required"


def test_a_verified_donor_may_give_the_large_amount(api, pandal, visitor):
    kyc.verify_pan(user=visitor, pan="ABCDE1234F", name="Ananya Sen")
    api.force_authenticate(visitor)

    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": LARGE}, format="json")

    assert response.status_code == 201
    # The donation records which check let it through, so it can be produced later.
    assert Donation.objects.get().kyc_check.status == KycCheck.Status.VERIFIED


def test_nothing_is_left_behind_when_a_donation_is_refused(api, pandal):
    """The check happens before the order exists, so a donor who stops to verify
    has not left a half-finished order and a phantom payment behind them."""
    from apps.orders.models import Order

    api.post(reverse("donation-create"),
             {"pandal_id": str(pandal.id), "amount_paise": LARGE}, format="json")

    assert Order.objects.count() == 0
    assert Donation.objects.count() == 0


@override_settings(DONATION_KYC_THRESHOLD_PAISE=100_00)
def test_the_threshold_is_configuration_not_a_constant(api, pandal, visitor):
    """It is an accountant's answer, not an engineer's."""
    api.force_authenticate(visitor)

    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": 150_00}, format="json")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "kyc_required"


# --------------------------------------------------------------------------
# Verifying
# --------------------------------------------------------------------------

def test_verifying_a_pan_records_the_name_it_is_registered_to(api, visitor):
    api.force_authenticate(visitor)

    response = api.post(reverse("kyc-pan"),
                        {"pan": "abcde1234f", "name": "Ananya Sen"}, format="json")

    assert response.status_code == 201
    check = KycCheck.objects.get()
    assert check.status == KycCheck.Status.VERIFIED
    assert check.number == "ABCDE1234F"     # stored upper-cased, as issued


def test_a_pan_is_never_returned_by_the_endpoint_that_was_given_one(api, visitor):
    api.force_authenticate(visitor)

    body = api.post(reverse("kyc-pan"),
                    {"pan": "ABCDE1234F", "name": "Ananya Sen"}, format="json").json()

    assert "ABCDE1234F" not in str(body)
    assert body["masked_number"] == "AB••••••4F"


def test_something_that_is_not_a_pan_is_refused_before_the_provider_is_called(api, visitor):
    api.force_authenticate(visitor)

    response = api.post(reverse("kyc-pan"), {"pan": "not-a-pan", "name": "A"}, format="json")

    assert response.status_code == 422
    assert "pan" in response.json()["error"]["fields"]
    assert not KycCheck.objects.exists()


def test_a_rejected_pan_is_not_stored(visitor):
    """A number that failed is somebody else's as often as it is a typo."""
    with pytest.raises(kyc.KycUnverifiedError):
        kyc.verify_pan(user=visitor, pan="AAAAA1111A", name="Nobody")

    check = KycCheck.objects.get()
    assert check.status == KycCheck.Status.FAILED
    assert check.number == ""


def test_every_attempt_is_kept(visitor):
    """Four attempts with four different PANs is exactly the pattern anybody
    investigating would want to see, and it is invisible if each replaces the
    last."""
    with pytest.raises(kyc.KycUnverifiedError):
        kyc.verify_pan(user=visitor, pan="AAAAA1111A", name="Nobody")
    kyc.verify_pan(user=visitor, pan="ABCDE1234F", name="Ananya Sen")

    assert KycCheck.objects.filter(user=visitor).count() == 2


def test_a_provider_outage_does_not_read_as_a_rejection(visitor, monkeypatch):
    """'We could not ask' and 'the answer was no' must not look the same."""
    from apps.kyc import services

    class Broken:
        name = "sandbox"
        def verify_pan(self, **kwargs):
            raise KycUnavailableError("connection reset")

    monkeypatch.setattr(services, "get_kyc_provider", lambda: Broken())

    with pytest.raises(kyc.KycUnverifiedError) as caught:
        kyc.verify_pan(user=visitor, pan="ABCDE1234F", name="Ananya Sen")

    assert caught.value.extra.get("retryable") is True
    assert KycCheck.objects.get().status == KycCheck.Status.ERROR


def test_verifying_needs_an_account(api):
    assert api.post(reverse("kyc-pan"),
                    {"pan": "ABCDE1234F", "name": "A"}, format="json").status_code == 401


def test_the_donate_form_can_ask_where_the_threshold_is_before_anyone_signs_in(api):
    """Otherwise the first a donor hears of it is a refusal."""
    body = api.get(reverse("kyc-status")).json()

    assert body["threshold_paise"] == kyc.threshold_paise()
    assert body["verified"] is False


def test_a_name_is_required_because_the_register_is_checked_against_it(api, visitor):
    api.force_authenticate(visitor)

    response = api.post(reverse("kyc-pan"), {"pan": "ABCDE1234F", "name": "  "}, format="json")

    assert response.status_code == 422


# --------------------------------------------------------------------------
# The shapes Sandbox actually returns
# --------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, body, status_code=200):
        self._body, self.status_code = body, status_code
        self.content = b"{}"
        self.text = str(body)

    def json(self):
        return self._body


@override_settings(SANDBOX_API_KEY="key_test_x", SANDBOX_API_SECRET="secret_test_x")
def test_the_access_token_is_read_from_the_data_envelope(monkeypatch):
    """Sandbox nests it under `data`. Reading the top level yields an empty
    string and every later call 401s in a way that looks like bad credentials."""
    from django.core.cache import cache

    from apps.kyc.providers import SandboxProvider

    cache.delete("kyc:sandbox:token")
    monkeypatch.setattr("apps.kyc.providers.httpx.post",
                        lambda *a, **k: FakeResponse({"code": 200,
                                                      "data": {"access_token": "the-token"}}))

    assert SandboxProvider()._token() == "the-token"


@override_settings(SANDBOX_API_KEY="key_test_x", SANDBOX_API_SECRET="secret_test_x")
def test_a_valid_pan_registered_to_someone_else_is_refused(monkeypatch):
    """`status` says the number exists; `name_as_per_pan_match` says it belongs
    to the name submitted. Treating the first as sufficient would let anybody
    claim anybody's PAN."""
    from django.core.cache import cache

    from apps.kyc.providers import SandboxProvider

    cache.set("kyc:sandbox:token", "t", 60)
    monkeypatch.setattr("apps.kyc.providers.httpx.post",
                        lambda *a, **k: FakeResponse({
                            "transaction_id": "txn-1",
                            "data": {"status": "VALID", "name_as_per_pan_match": False},
                        }))

    result = SandboxProvider().verify_pan(pan="ABCDE1234F", name="Somebody Else")

    assert result.verified is False
    assert "different name" in result.reason


@override_settings(SANDBOX_API_KEY="key_test_x", SANDBOX_API_SECRET="secret_test_x")
def test_a_matching_pan_records_the_name_that_was_confirmed(monkeypatch):
    """Sandbox returns no name, only whether ours matched."""
    from django.core.cache import cache

    from apps.kyc.providers import SandboxProvider

    cache.set("kyc:sandbox:token", "t", 60)
    monkeypatch.setattr("apps.kyc.providers.httpx.post",
                        lambda *a, **k: FakeResponse({
                            "transaction_id": "txn-2",
                            "data": {"status": "VALID", "name_as_per_pan_match": True},
                        }))

    result = SandboxProvider().verify_pan(pan="ABCDE1234F", name="Ananya Sen")

    assert result.verified is True
    assert result.name_on_record == "Ananya Sen"
    assert result.reference == "txn-2"


@override_settings(SANDBOX_API_KEY="key_test_abc", SANDBOX_API_SECRET="s", SANDBOX_BASE_URL="")
def test_test_credentials_go_to_the_test_host():
    """A test key against the live host is a 401 that reads like bad
    credentials, so the host is inferred from the prefix."""
    from apps.kyc.providers import SandboxProvider

    assert SandboxProvider().base_url == "https://test-api.sandbox.co.in"


@override_settings(SANDBOX_API_KEY="key_live_abc", SANDBOX_API_SECRET="s", SANDBOX_BASE_URL="")
def test_live_credentials_go_to_the_live_host():
    from apps.kyc.providers import SandboxProvider

    assert SandboxProvider().base_url == "https://api.sandbox.co.in"

