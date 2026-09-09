"""The pass endpoints.

Scoping and permission are what these prove: a pass reaches its holder and
nobody else, a gate manifest reaches a volunteer posted at that gate and nobody
else, and a pandal that has not switched passes on does not appear to sell any.
"""

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import OrderLine
from apps.pandals.models import Volunteer
from apps.passes import codes
from apps.passes.fulfilment import confirm_pass
from apps.passes.models import PassLeg, ScanEvent
from apps.passes.purchase import start_purchase

pytestmark = pytest.mark.django_db

VISIT = dt.date(2026, 10, 12)


def pay(order):
    from apps.orders import services as orders
    orders.mark_paid(order)
    for line in order.lines.all():
        if line.kind == OrderLine.Kind.PASS:
            confirm_pass(line)


# --------------------------------------------------------------------------
# What a pandal is selling
# --------------------------------------------------------------------------

def test_a_pandal_that_sells_passes_lists_them(api, individual_config, selling_pandal):
    response = api.get(reverse("pandal-passes", args=[selling_pandal.slug]))

    assert response.status_code == 200
    row = response.json()[0]
    assert row["product"] == "individual"
    assert row["price_paise"] == 30_000
    assert row["category"]["name"] == "Donor"


def test_a_pandal_that_has_not_switched_passes_on_sells_none(api, pandal, individual_config):
    """The whole of what a committee does to start selling is set this flag."""
    pandal.sells_passes = False
    pandal.save(update_fields=["sells_passes"])

    assert api.get(reverse("pandal-passes", args=[pandal.slug])).status_code == 404


def test_the_landing_page_carries_passes_once_they_are_on(api, individual_config,
                                                          selling_pandal):
    body = api.get(reverse("pandal-page", args=[selling_pandal.slug])).json()

    assert body["capabilities"]["sells_passes"] is True
    assert [p["price_paise"] for p in body["passes"]] == [30_000]


def test_availability_reports_places_left_per_day(api, individual_config, selling_pandal,
                                                  pandal_day):
    response = api.get(reverse("pandal-pass-availability", args=[selling_pandal.slug]))

    assert response.json() == [{"date": "2026-10-12", "capacity": 2000, "available": 2000}]


# --------------------------------------------------------------------------
# Buying
# --------------------------------------------------------------------------

def test_buying_a_pass_returns_a_payment_intent(api, individual_config, visitor, pandal_day):
    api.force_authenticate(visitor)

    response = api.post(reverse("pass-list"),
                        {"config_id": str(individual_config.pk), "visit_date": "2026-10-12"},
                        format="json")

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["amount_paise"] == 30_000
    assert body["pandals_covered"] == 1
    assert body["payment"]["provider_order_id"]


def test_buying_a_pass_needs_an_account(api, individual_config, pandal_day):
    """Unlike a donation, a pass has to reach a phone."""
    response = api.post(reverse("pass-list"),
                        {"config_id": str(individual_config.pk), "visit_date": "2026-10-12"},
                        format="json")

    assert response.status_code == 401


def test_a_visitor_sees_their_own_passes_and_nobody_elses(api, individual_config, visitor,
                                                          pandal_day, db):
    stranger = User.objects.create(phone="+919812345678")
    mine, order, _ = start_purchase(config_id=individual_config.pk, visit_date=VISIT,
                                    user=visitor)
    start_purchase(config_id=individual_config.pk, visit_date=VISIT, user=stranger)
    pay(order)
    api.force_authenticate(visitor)

    response = api.get(reverse("pass-list"))

    assert [p["pass_code"] for p in response.json()["results"]] == [mine.pass_code]


def test_a_sold_out_day_answers_409_with_how_many_are_left(api, individual_config, visitor,
                                                           pandal_day):
    pandal_day.capacity = 0
    pandal_day.save(update_fields=["capacity"])
    api.force_authenticate(visitor)

    response = api.post(reverse("pass-list"),
                        {"config_id": str(individual_config.pk), "visit_date": "2026-10-12"},
                        format="json")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "capacity_unavailable"


# --------------------------------------------------------------------------
# Provisioning the phone
# --------------------------------------------------------------------------

def test_the_holder_can_fetch_a_leg_secret_once_the_pass_is_paid(api, individual_config,
                                                                 visitor, pandal_day):
    issued, order, _ = start_purchase(config_id=individual_config.pk, visit_date=VISIT,
                                      user=visitor)
    pay(order)
    leg = issued.legs.get()
    api.force_authenticate(visitor)

    response = api.get(reverse("pass-leg-secret", args=[issued.pk, leg.pk]))

    assert response.status_code == 200
    body = response.json()
    assert body["step_seconds"] == codes.STEP_SECONDS
    # Enough to derive a code with no further request, which is the point (D5).
    counter = codes.counter_for()
    assert codes.verify(body["secret"], counter, codes.derive(body["secret"], counter))


def test_an_unpaid_pass_has_no_entry_code_yet(api, individual_config, visitor, pandal_day):
    issued, _, _ = start_purchase(config_id=individual_config.pk, visit_date=VISIT,
                                  user=visitor)
    api.force_authenticate(visitor)

    response = api.get(reverse("pass-leg-secret", args=[issued.pk, issued.legs.get().pk]))

    assert response.status_code == 422


def test_a_stranger_cannot_fetch_somebody_elses_leg_secret(api, individual_config, visitor,
                                                           pandal_day, db):
    issued, order, _ = start_purchase(config_id=individual_config.pk, visit_date=VISIT,
                                      user=visitor)
    pay(order)
    stranger = User.objects.create(phone="+919812345679")
    api.force_authenticate(stranger)

    response = api.get(reverse("pass-leg-secret", args=[issued.pk, issued.legs.get().pk]))

    assert response.status_code == 404


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

@pytest.fixture
def gate_staff(pandal, gate, db):
    user = User.objects.create(phone="+919700000001", first_name="Ratan")
    Volunteer.objects.create(user=user, pandal=pandal, gate=gate)
    return user


@pytest.fixture
def paid_pass(individual_config, visitor, pandal_day):
    issued, order, _ = start_purchase(config_id=individual_config.pk, visit_date=VISIT,
                                      user=visitor)
    pay(order)
    return issued


def test_a_posted_volunteer_downloads_the_manifest(api, gate_staff, pandal, paid_pass):
    api.force_authenticate(gate_staff)

    response = api.get(reverse("gate-manifest"),
                       {"pandal": str(pandal.pk), "date": "2026-10-12"})

    assert response.status_code == 200
    assert [e["pass_code"] for e in response.json()] == [paid_pass.pass_code]


def test_a_visitor_cannot_download_a_gate_manifest(api, visitor, pandal, paid_pass):
    """It carries leg secrets. Only somebody posted there may have it."""
    api.force_authenticate(visitor)

    response = api.get(reverse("gate-manifest"), {"pandal": str(pandal.pk)})

    assert response.status_code == 403


def test_a_deactivated_volunteer_stops_being_able_to_scan(api, gate_staff, gate, pandal,
                                                          paid_pass):
    Volunteer.objects.filter(user=gate_staff).update(is_active=False)
    api.force_authenticate(gate_staff)

    response = api.post(reverse("gate-scan"),
                        {"gate_id": str(gate.pk), "payload": "EDP1:x:0:0"}, format="json")

    assert response.status_code == 403


def test_a_scan_admits_and_comes_back_with_the_result(api, gate_staff, gate, paid_pass):
    leg = paid_pass.legs.get()
    api.force_authenticate(gate_staff)

    response = api.post(reverse("gate-scan"), {
        "gate_id": str(gate.pk),
        "payload": codes.payload_for(leg.id, leg.secret.secret),
        "scanned_at": timezone.make_aware(dt.datetime.combine(VISIT, dt.time(19, 0))),
        "device_id": "tab-01",
    }, format="json")

    assert response.status_code == 201
    assert response.json()["result"] == "admitted"
    leg.refresh_from_db()
    assert leg.state == PassLeg.State.VISITED


def test_a_refused_scan_is_a_201_carrying_the_refusal_not_an_error(api, gate_staff, gate):
    """The gate app needs the reason back to show the volunteer, so a refusal is
    a recorded fact rather than an HTTP error."""
    api.force_authenticate(gate_staff)

    response = api.post(reverse("gate-scan"),
                        {"gate_id": str(gate.pk), "payload": "rubbish"}, format="json")

    assert response.status_code == 201
    assert response.json()["result"] == ScanEvent.Result.INVALID


def test_an_override_without_a_reason_is_refused(api, gate_staff, gate, paid_pass):
    leg = paid_pass.legs.get()
    api.force_authenticate(gate_staff)

    response = api.post(reverse("gate-scan"), {
        "gate_id": str(gate.pk), "payload": f"EDP1:{leg.id}:0:00000000", "override": True,
    }, format="json")

    assert response.status_code == 422
