import pytest
from django.urls import reverse

from apps.donations.models import Donation, DonationLink, DonationOffering
from apps.orders.models import Order, OrderLine

pytestmark = pytest.mark.django_db


@pytest.fixture
def offering(pandal):
    return DonationOffering.objects.create(pandal=pandal, amount_paise=50_100,
                                           label="Support a diya")


def test_anyone_can_donate_without_an_account(api, pandal):
    """Only a purchase that has to reach a phone needs to know the phone."""
    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": 100_100},
                        format="json")

    body = response.json()
    assert response.status_code == 201
    assert body["amount_paise"] == 100_100
    assert body["payment"]["provider_order_id"].startswith("order_")

    order = Order.objects.get(pk=body["order_id"])
    assert order.user is None
    assert order.status == Order.Status.PENDING
    assert order.lines.get().kind == OrderLine.Kind.DONATION


def test_choosing_a_preset_records_which_one(api, pandal, offering):
    """So a pandal can see what its donors actually respond to (FR-050d)."""
    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "offering_id": str(offering.id)},
                        format="json")

    donation = Donation.objects.get(pk=response.json()["donation_id"])
    assert donation.offering == offering
    assert donation.amount_paise == 50_100
    assert donation.order_line.description == "Support a diya"


def test_leaving_the_name_blank_donates_anonymously(api, pandal):
    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": 50_100,
                         "message": "Jai Maa Durga!"},
                        format="json")

    donation = Donation.objects.get(pk=response.json()["donation_id"])
    assert donation.is_anonymous
    assert donation.message == "Jai Maa Durga!"


def test_a_donation_needs_an_amount_or_an_offering(api, pandal):
    response = api.post(reverse("donation-create"), {"pandal_id": str(pandal.id)},
                        format="json")

    assert response.status_code == 422
    assert "amount_paise" in response.json()["error"]["fields"]


def test_a_pandal_that_does_not_take_donations_refuses(api, pandal):
    pandal.accepts_donations = False
    pandal.save(update_fields=["accepts_donations"])

    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": 50_100}, format="json")

    assert response.status_code == 404


def test_retrying_with_the_same_key_never_charges_twice(api, pandal):
    from apps.payments.models import PaymentOrder

    payload = {"pandal_id": str(pandal.id), "amount_paise": 50_100}
    first = api.post(reverse("donation-create"), payload, format="json",
                     HTTP_IDEMPOTENCY_KEY="key-1")
    api.post(reverse("donation-create"), payload, format="json", HTTP_IDEMPOTENCY_KEY="key-1")

    assert PaymentOrder.objects.filter(idempotency_key="key-1").count() == 1
    assert first.status_code == 201


def test_a_shared_link_resolves_to_its_pandal_and_amount(api, pandal):
    link = DonationLink.objects.create(pandal=pandal, suggested_amount_paise=50_100,
                                       purpose="Pandal Lighting Fund")

    body = api.get(reverse("donation-link-resolve", args=[pandal.slug, link.token])).json()

    assert body["suggested_amount_paise"] == 50_100
    assert body["purpose"] == "Pandal Lighting Fund"
    assert body["path"] == f"/d/{pandal.slug}/{link.token}"


def test_a_retired_link_stops_resolving(api, pandal):
    link = DonationLink.objects.create(pandal=pandal, is_active=False)

    assert api.get(reverse("donation-link-resolve",
                           args=[pandal.slug, link.token])).status_code == 404


def test_a_donation_from_a_link_records_the_attribution(api, pandal):
    link = DonationLink.objects.create(pandal=pandal, purpose="Bhog")

    response = api.post(reverse("donation-create"),
                        {"pandal_id": str(pandal.id), "amount_paise": 50_100,
                         "link_token": link.token},
                        format="json")

    assert Donation.objects.get(pk=response.json()["donation_id"]).link == link


def test_the_order_can_be_polled_while_the_payment_settles(api, pandal):
    created = api.post(reverse("donation-create"),
                       {"pandal_id": str(pandal.id), "amount_paise": 50_100},
                       format="json").json()

    body = api.get(reverse("order-detail", args=[created["order_id"]])).json()

    assert body["status"] == "pending"
    assert body["total_paise"] == 50_100


def test_no_receipt_exists_until_the_money_arrives(api, pandal):
    created = api.post(reverse("donation-create"),
                       {"pandal_id": str(pandal.id), "amount_paise": 50_100},
                       format="json").json()

    assert api.get(reverse("order-receipt", args=[created["order_id"]])).status_code == 404
