"""Buying a pass, paying for it, and being let in.

The three things worth proving here are the ones a reading of the models cannot
settle: that a City Pass takes a place at every pandal it covers *atomically*,
that a code derived on a phone with no network verifies at a gate with no
network, and that a leg is admitted exactly once however many devices scan it.
"""

import datetime as dt
import time

import pytest
from django.utils import timezone

from apps.common.errors import CapacityUnavailableError, ValidationFailedError
from apps.orders.models import OrderLine
from apps.pandals.models import Gate, Pandal
from apps.passes import codes, inventory
from apps.passes.fulfilment import confirm_pass, release_pass
from apps.passes.models import (
    LegSecret,
    PandalDayCapacity,
    Pass,
    PassConfig,
    PassLeg,
    PassProduct,
    ScanEvent,
)
from apps.passes.purchase import start_purchase
from apps.passes.scanning import admit, manifest

pytestmark = pytest.mark.django_db

VISIT = dt.date(2026, 10, 12)


def pay(order):
    """What a captured webhook does, without the webhook."""
    from apps.orders import services as orders
    orders.mark_paid(order)
    for line in order.lines.all():
        if line.kind == OrderLine.Kind.PASS:
            confirm_pass(line)


# --------------------------------------------------------------------------
# Buying
# --------------------------------------------------------------------------

def test_buying_an_individual_pass_holds_a_place_but_does_not_take_it(
        individual_config, pandal_day, visitor):
    issued, order, holds = start_purchase(
        config_id=individual_config.pk, visit_date=VISIT, user=visitor
    )

    assert issued.legs.count() == 1
    assert order.total_paise == 30_000
    # Held, not issued: the money has not arrived.
    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 0
    assert inventory.available(pandal_day) == 1999
    assert len(holds) == 1


def test_paying_turns_the_hold_into_an_issued_place_and_provisions_a_secret(
        individual_config, pandal_day, visitor):
    issued, order, _ = start_purchase(config_id=individual_config.pk, visit_date=VISIT,
                                      user=visitor)
    pay(order)

    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 1
    leg = issued.legs.get()
    assert LegSecret.objects.filter(leg=leg).exists()


def test_a_group_pass_takes_one_place_per_person(group_config, pandal_day, visitor):
    issued, order, _ = start_purchase(config_id=group_config.pk, visit_date=VISIT,
                                      party_size=4, user=visitor)
    pay(order)

    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 4
    assert issued.party_size == 4
    # Priced per person, on one line.
    assert order.total_paise == 4 * 25_000


def test_only_a_group_pass_may_cover_more_than_one_person(individual_config, visitor):
    with pytest.raises(ValidationFailedError):
        start_purchase(config_id=individual_config.pk, visit_date=VISIT, party_size=3,
                       user=visitor)


def test_a_party_larger_than_the_configuration_allows_is_refused(group_config, visitor):
    with pytest.raises(ValidationFailedError):
        start_purchase(config_id=group_config.pk, visit_date=VISIT, party_size=9, user=visitor)


def test_a_date_outside_the_configuration_is_refused(individual_config, visitor):
    with pytest.raises(ValidationFailedError):
        start_purchase(config_id=individual_config.pk, visit_date=dt.date(2026, 10, 20),
                       user=visitor)


def test_a_sold_out_day_refuses_and_says_how_many_are_left(
        individual_config, pandal_day, visitor):
    pandal_day.capacity = 1
    pandal_day.save(update_fields=["capacity"])
    start_purchase(config_id=individual_config.pk, visit_date=VISIT, user=visitor)

    with pytest.raises(CapacityUnavailableError) as raised:
        start_purchase(config_id=individual_config.pk, visit_date=VISIT, user=visitor)
    assert raised.value.extra["available"] == 0


# --------------------------------------------------------------------------
# The City Pass — the case that makes a pass more than one row
# --------------------------------------------------------------------------

@pytest.fixture
def city_pass(city, locality, selling_pandal, donor_category):
    """Three pandals in one city, all selling, all open on the same day."""
    others = []
    for name, slug in [("Kumartuli Park", "kumartuli-park"), ("Mudiali Club", "mudiali-club")]:
        other = Pandal.objects.create(
            name=name, slug=slug, city=city, locality=locality, sells_passes=True,
            publication_status=Pandal.PublicationStatus.PUBLISHED,
        )
        PandalDayCapacity.objects.create(pandal=other, date=VISIT, capacity=50)
        others.append(other)

    config = PassConfig.objects.create(
        pandal=selling_pandal, category=donor_category, product=PassProduct.CITY,
        from_date=dt.date(2026, 10, 10), to_date=dt.date(2026, 10, 14),
        price_paise=100_000, max_party_size=1,
    )
    return config, others


def test_a_city_pass_takes_one_place_at_every_pandal_it_covers(
        city_pass, pandal_day, visitor):
    config, others = city_pass

    issued, order, holds = start_purchase(config_id=config.pk, visit_date=VISIT, user=visitor)
    pay(order)

    assert issued.legs.count() == 3
    assert len(holds) == 3
    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 1
    for other in others:
        day = PandalDayCapacity.objects.get(pandal=other, date=VISIT)
        assert day.issued_count == 1
    # Billed once, however many pandals it covers.
    assert order.total_paise == 100_000


def test_a_city_pass_carries_a_date_and_no_time(city_pass, pandal_day, visitor):
    config, _ = city_pass
    issued, _, _ = start_purchase(config_id=config.pk, visit_date=VISIT, user=visitor)

    for leg in issued.legs.all():
        assert leg.visit_date == VISIT
        assert leg.slot_from is None
        assert leg.slot_to is None


def test_a_city_pass_may_cover_a_chosen_subset(city_pass, pandal_day, visitor):
    """Fifty pandals must not hold fifty places for somebody visiting four."""
    config, others = city_pass

    issued, _, _ = start_purchase(config_id=config.pk, visit_date=VISIT,
                                  pandal_ids=[others[0].pk], user=visitor)

    assert [leg.pandal for leg in issued.legs.all()] == [others[0]]


def test_one_sold_out_pandal_rolls_back_the_whole_city_pass(city_pass, pandal_day, visitor):
    """The interesting failure: three holds already placed when the fourth fails."""
    config, others = city_pass
    full = PandalDayCapacity.objects.get(pandal=others[-1], date=VISIT)
    full.capacity = 0
    full.save(update_fields=["capacity"])

    with pytest.raises(CapacityUnavailableError):
        start_purchase(config_id=config.pk, visit_date=VISIT, user=visitor)

    # Nothing survived: no pass, and no place held anywhere.
    assert Pass.objects.count() == 0
    pandal_day.refresh_from_db()
    assert inventory.available(pandal_day) == 2000
    for other in others[:-1]:
        day = PandalDayCapacity.objects.get(pandal=other, date=VISIT)
        assert inventory.available(day) == 50


def test_a_late_payment_that_lost_one_leg_delivers_no_partial_pass(
        city_pass, pandal_day, visitor):
    """A three-quarter City Pass is discovered at a gate, at night, in a crowd.
    Refunding is the honest outcome."""
    config, others = city_pass
    issued, order, _ = start_purchase(config_id=config.pk, visit_date=VISIT, user=visitor)

    # One pandal fills up and the hold lapses while the payment is in flight.
    lost = PandalDayCapacity.objects.get(pandal=others[-1], date=VISIT)
    leg = issued.legs.get(pandal=others[-1])
    inventory.release_hold(hold_id=leg.capacity_hold_id)
    lost.issued_count = lost.capacity
    lost.save(update_fields=["issued_count"])

    pay(order)

    issued.refresh_from_db()
    assert issued.status == Pass.Status.CANCELLED
    assert {leg.state for leg in issued.legs.all()} == {PassLeg.State.VOID}
    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 0


def test_a_failed_payment_gives_every_place_back_at_once(city_pass, pandal_day, visitor):
    config, others = city_pass
    _, order, _ = start_purchase(config_id=config.pk, visit_date=VISIT, user=visitor)

    for line in order.lines.all():
        release_pass(line)

    pandal_day.refresh_from_db()
    assert inventory.available(pandal_day) == 2000
    for other in others:
        assert inventory.available(PandalDayCapacity.objects.get(pandal=other, date=VISIT)) == 50


# --------------------------------------------------------------------------
# The code — D1 and D5 together
# --------------------------------------------------------------------------

def test_a_code_derived_on_the_phone_verifies_at_the_gate_with_no_network():
    secret = codes.new_secret()
    now = time.time()

    payload = codes.payload_for("some-leg", secret, at=now)
    _, counter, code = codes.parse(payload)

    assert codes.verify(secret, counter, code, at=now)


def test_a_code_older_than_three_minutes_is_refused():
    secret = codes.new_secret()
    now = time.time()
    stale = now - (codes.STEP_SECONDS * 3)

    _, counter, code = codes.parse(codes.payload_for("leg", secret, at=stale))

    assert not codes.verify(secret, counter, code, at=now)


def test_a_gate_clock_drifting_by_one_step_still_admits():
    """A volunteer's tablet ninety seconds out must not turn away a real pass."""
    secret = codes.new_secret()
    now = time.time()
    _, counter, code = codes.parse(codes.payload_for("leg", secret, at=now))

    assert codes.verify(secret, counter, code, at=now + codes.STEP_SECONDS)


def test_two_legs_never_derive_the_same_code():
    a, b = codes.new_secret(), codes.new_secret()
    counter = codes.counter_for()
    assert codes.derive(a, counter) != codes.derive(b, counter)


def test_a_payload_that_is_not_ours_parses_to_nothing():
    assert codes.parse("https://example.com/qr") is None
    assert codes.parse("") is None
    assert codes.parse("EDP1:leg:notanumber:123") is None


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

@pytest.fixture
def admitted_pass(individual_config, pandal_day, visitor):
    issued, order, _ = start_purchase(config_id=individual_config.pk, visit_date=VISIT,
                                      user=visitor)
    pay(order)
    return issued


def test_a_valid_code_admits_and_marks_the_leg_visited(admitted_pass, gate):
    leg = admitted_pass.legs.get()
    payload = codes.payload_for(leg.id, leg.secret.secret)

    event = admit(gate=gate, payload=payload,
                  scanned_at=timezone.make_aware(dt.datetime.combine(VISIT, dt.time(19, 0))))

    assert event.result == ScanEvent.Result.ADMITTED
    leg.refresh_from_db()
    assert leg.state == PassLeg.State.VISITED
    assert leg.admitted_gate == gate


def test_a_leg_is_admitted_once_however_many_gates_scan_it(admitted_pass, gate, pandal):
    leg = admitted_pass.legs.get()
    payload = codes.payload_for(leg.id, leg.secret.secret)
    at = timezone.make_aware(dt.datetime.combine(VISIT, dt.time(19, 0)))
    second_gate = Gate.objects.create(pandal=pandal, name="Gate 2")

    first = admit(gate=gate, payload=payload, scanned_at=at)
    second = admit(gate=second_gate, payload=payload, scanned_at=at)

    assert first.result == ScanEvent.Result.ADMITTED
    assert second.result == ScanEvent.Result.DUPLICATE
    # Both scans are on the record; only one is an admission.
    assert ScanEvent.objects.count() == 2


def test_a_pass_whose_every_leg_is_visited_becomes_used(admitted_pass, gate):
    leg = admitted_pass.legs.get()
    admit(gate=gate, payload=codes.payload_for(leg.id, leg.secret.secret),
          scanned_at=timezone.make_aware(dt.datetime.combine(VISIT, dt.time(19, 0))))

    admitted_pass.refresh_from_db()
    assert admitted_pass.status == Pass.Status.USED


def test_a_code_for_the_pandal_next_door_is_not_a_code_for_here(
        admitted_pass, city, locality, visitor):
    """A genuine pass, a genuine code, the wrong gate."""
    elsewhere = Pandal.objects.create(name="Mudiali", slug="mudiali", city=city,
                                      locality=locality, sells_passes=True)
    foreign_gate = Gate.objects.create(pandal=elsewhere, name="Gate 1")
    leg = admitted_pass.legs.get()

    event = admit(gate=foreign_gate, payload=codes.payload_for(leg.id, leg.secret.secret))

    assert event.result == ScanEvent.Result.INVALID
    assert event.leg is None


def test_a_pass_presented_on_the_wrong_day_is_refused(admitted_pass, gate):
    leg = admitted_pass.legs.get()
    wrong_day = timezone.make_aware(dt.datetime.combine(VISIT + dt.timedelta(days=1),
                                                        dt.time(19, 0)))

    event = admit(gate=gate, payload=codes.payload_for(leg.id, leg.secret.secret),
                  scanned_at=wrong_day)

    assert event.result == ScanEvent.Result.INVALID
    leg.refresh_from_db()
    assert leg.state == PassLeg.State.PENDING


def test_a_refusal_is_recorded_rather_than_raised(gate):
    event = admit(gate=gate, payload="not-a-pass-code-at-all")

    assert event.result == ScanEvent.Result.INVALID
    assert event.leg is None
    assert ScanEvent.objects.count() == 1


def test_a_manual_override_admits_without_a_valid_code_and_says_why(admitted_pass, gate):
    """C7: the exception a volunteer makes when the phone is dead."""
    leg = admitted_pass.legs.get()
    at = timezone.make_aware(dt.datetime.combine(VISIT, dt.time(19, 0)))

    event = admit(gate=gate, payload=f"EDP1:{leg.id}:0:00000000", scanned_at=at,
                  override=True, override_reason="Phone battery dead; ID checked")

    assert event.result == ScanEvent.Result.MANUAL_OVERRIDE
    assert event.override_reason.startswith("Phone battery dead")
    leg.refresh_from_db()
    assert leg.state == PassLeg.State.VISITED


def test_an_override_cannot_be_used_twice_either(admitted_pass, gate):
    leg = admitted_pass.legs.get()
    at = timezone.make_aware(dt.datetime.combine(VISIT, dt.time(19, 0)))
    payload = f"EDP1:{leg.id}:0:00000000"

    admit(gate=gate, payload=payload, scanned_at=at, override=True, override_reason="first")
    second = admit(gate=gate, payload=payload, scanned_at=at, override=True,
                   override_reason="second")

    assert second.result == ScanEvent.Result.DUPLICATE


def test_the_manifest_carries_what_a_device_needs_to_verify_offline(admitted_pass, pandal):
    entries = manifest(pandal=pandal, date=VISIT)

    assert len(entries) == 1
    entry = entries[0]
    assert entry["pass_code"] == admitted_pass.pass_code
    assert entry["secret"] == admitted_pass.legs.get().secret.secret
    # Enough to verify a code without asking anybody.
    counter = codes.counter_for()
    assert codes.verify(entry["secret"], counter, codes.derive(entry["secret"], counter))


def test_the_manifest_drops_a_leg_once_it_has_been_admitted(admitted_pass, gate, pandal):
    leg = admitted_pass.legs.get()
    admit(gate=gate, payload=codes.payload_for(leg.id, leg.secret.secret),
          scanned_at=timezone.make_aware(dt.datetime.combine(VISIT, dt.time(19, 0))))

    assert manifest(pandal=pandal, date=VISIT) == []
