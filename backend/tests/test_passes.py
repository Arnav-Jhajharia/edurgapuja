"""Passes.

The inventory tests here are deliberately thin, because the primitive they use
is already proven in `test_capacity.py`. What is tested is that it transferred
unchanged — and the rules that are specific to passes.
"""

import datetime as dt
import threading

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.common.errors import CapacityUnavailableError
from apps.passes import inventory
from apps.passes.models import (
    PandalDayCapacity,
    Pass,
    PassCategory,
    PassConfig,
    PassLeg,
    PassProduct,
    ScanEvent,
    generate_pass_code,
)

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------
# The seam: the same primitive, a different owner
# --------------------------------------------------------------------------

def test_the_service_capacity_primitive_works_unchanged_for_pandals(pandal_day):
    """Six lines of `partial` were the whole cost of reusing it."""
    assert inventory.available(pandal_day) == 2000

    hold = inventory.place_hold(day_id=pandal_day.pk, quantity=4)
    assert inventory.available(pandal_day) == 1996

    inventory.issue(hold_id=hold.pk)
    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 4


def test_an_expired_pandal_hold_frees_capacity_without_a_sweeper(pandal_day):
    from apps.passes.models import PandalCapacityHold

    hold = inventory.place_hold(day_id=pandal_day.pk, quantity=2000)
    assert inventory.available(pandal_day) == 0

    PandalCapacityHold.objects.filter(pk=hold.pk).update(
        expires_at=timezone.now() - dt.timedelta(seconds=1)
    )
    assert inventory.available(pandal_day) == 2000


def test_the_database_refuses_to_oversell_a_pandal_day(pandal_day):
    with pytest.raises(IntegrityError), transaction.atomic():
        PandalDayCapacity.objects.filter(pk=pandal_day.pk).update(issued_count=2001)


@pytest.mark.django_db(transaction=True)
def test_the_last_place_at_a_pandal_goes_to_exactly_one_visitor(city, locality):
    """Ashtami night, one place left, everyone tapping at once."""
    from apps.pandals.models import Pandal

    pandal = Pandal.objects.create(name="Race", slug="race-pandal", city=city, locality=locality)
    day = PandalDayCapacity.objects.create(pandal=pandal, date=dt.date(2026, 10, 12), capacity=1)

    outcomes: list[str] = []
    barrier = threading.Barrier(8)

    def contend():
        barrier.wait()
        try:
            inventory.place_hold(day_id=day.pk, quantity=1)
            outcomes.append("held")
        except CapacityUnavailableError:
            outcomes.append("refused")
        finally:
            connection.close()

    threads = [threading.Thread(target=contend) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes.count("held") == 1
    assert outcomes.count("refused") == 7


# --------------------------------------------------------------------------
# Product and category (D4)
# --------------------------------------------------------------------------

def test_each_pandal_names_its_own_categories(pandal, city, locality):
    from apps.pandals.models import Pandal

    other = Pandal.objects.create(name="Mudiali", slug="mudiali-cat", city=city, locality=locality)
    PassCategory.objects.create(pandal=pandal, name="Para Pass", slug="para-pass")
    PassCategory.objects.create(pandal=other, name="VIP", slug="vip")

    assert [c.name for c in pandal.pass_categories.all()] == ["Para Pass"]
    assert [c.name for c in other.pass_categories.all()] == ["VIP"]


def test_two_pandals_may_use_the_same_category_slug(pandal, city, locality):
    from apps.pandals.models import Pandal

    other = Pandal.objects.create(name="Other", slug="other-cat", city=city, locality=locality)
    PassCategory.objects.create(pandal=pandal, name="Donor", slug="donor")
    PassCategory.objects.create(pandal=other, name="Donor", slug="donor")

    assert PassCategory.objects.filter(slug="donor").count() == 2


def test_one_pandal_may_not_repeat_a_category_slug(pandal):
    PassCategory.objects.create(pandal=pandal, name="Donor", slug="donor")

    with pytest.raises(IntegrityError), transaction.atomic():
        PassCategory.objects.create(pandal=pandal, name="Donor Again", slug="donor")


def test_only_a_group_pass_may_cover_more_than_one_person(donor_category):
    """D4: Individual and City each cover one; Group is the multiple."""
    Pass.objects.create(product=PassProduct.GROUP, category=donor_category, party_size=4)

    for product in (PassProduct.INDIVIDUAL, PassProduct.CITY):
        with pytest.raises(IntegrityError), transaction.atomic():
            Pass.objects.create(product=product, category=donor_category, party_size=4)


def test_a_city_pass_configuration_cannot_carry_a_time(pandal, donor_category):
    """D3: a City Pass has a date and no time."""
    PassConfig.objects.create(
        pandal=pandal, category=donor_category, product=PassProduct.CITY,
        from_date=dt.date(2026, 10, 10), to_date=dt.date(2026, 10, 14), price_paise=400_000,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        PassConfig.objects.create(
            pandal=pandal, category=donor_category, product=PassProduct.CITY,
            from_date=dt.date(2026, 10, 10), to_date=dt.date(2026, 10, 14),
            from_time=dt.time(18, 0), price_paise=400_000,
        )


def test_an_individual_configuration_may_carry_a_time(pandal, donor_category):
    config = PassConfig.objects.create(
        pandal=pandal, category=donor_category, product=PassProduct.INDIVIDUAL,
        from_date=dt.date(2026, 10, 10), to_date=dt.date(2026, 10, 10),
        from_time=dt.time(18, 0), to_time=dt.time(18, 30), price_paise=10_000,
    )
    assert config.from_time == dt.time(18, 0)


def test_a_configuration_cannot_end_before_it_starts(pandal, donor_category):
    with pytest.raises(IntegrityError), transaction.atomic():
        PassConfig.objects.create(
            pandal=pandal, category=donor_category, product=PassProduct.INDIVIDUAL,
            from_date=dt.date(2026, 10, 14), to_date=dt.date(2026, 10, 10), price_paise=10_000,
        )


# --------------------------------------------------------------------------
# Legs
# --------------------------------------------------------------------------

def test_a_city_pass_takes_one_place_at_every_pandal_it_covers(city, locality, donor_category):
    """Q3, answered yes — otherwise the capacity number is not a cap at all."""
    from apps.pandals.models import Pandal

    day = dt.date(2026, 10, 12)
    pandals, days = [], []
    for i in range(3):
        p = Pandal.objects.create(name=f"P{i}", slug=f"city-{i}", city=city, locality=locality)
        pandals.append(p)
        days.append(PandalDayCapacity.objects.create(pandal=p, date=day, capacity=100))

    city_pass = Pass.objects.create(product=PassProduct.CITY, category=donor_category)
    for p, d in zip(pandals, days, strict=True):
        hold = inventory.place_hold(day_id=d.pk, quantity=city_pass.party_size)
        inventory.issue(hold_id=hold.pk)
        PassLeg.objects.create(issued_pass=city_pass, pandal=p, visit_date=day,
                               capacity_hold=hold)

    for d in days:
        d.refresh_from_db()
        assert d.issued_count == 1

    assert city_pass.pandals_covered == 3
    assert city_pass.pandals_visited == 0


def test_a_pass_covers_a_pandal_at_most_once(pandal, donor_category):
    p = Pass.objects.create(product=PassProduct.INDIVIDUAL, category=donor_category)
    PassLeg.objects.create(issued_pass=p, pandal=pandal, visit_date=dt.date(2026, 10, 12))

    with pytest.raises(IntegrityError), transaction.atomic():
        PassLeg.objects.create(issued_pass=p, pandal=pandal, visit_date=dt.date(2026, 10, 13))


def test_each_leg_is_visited_independently(city, locality, donor_category):
    from apps.pandals.models import Pandal

    p = Pass.objects.create(product=PassProduct.INDIVIDUAL, category=donor_category)
    for i in range(3):
        pandal = Pandal.objects.create(name=f"L{i}", slug=f"leg-{i}", city=city, locality=locality)
        PassLeg.objects.create(issued_pass=p, pandal=pandal, visit_date=dt.date(2026, 10, 12))

    first = p.legs.first()
    first.state = PassLeg.State.VISITED
    first.admitted_at = timezone.now()
    first.save(update_fields=["state", "admitted_at", "updated_at"])

    assert p.pandals_visited == 1
    assert p.pandals_covered == 3


# --------------------------------------------------------------------------
# Admission
# --------------------------------------------------------------------------

def test_a_leg_can_be_admitted_only_once_ever(pandal, donor_category):
    """The partial unique index is what makes double admission impossible."""
    from apps.pandals.models import Gate

    gate = Gate.objects.create(pandal=pandal, name="Gate 1")
    p = Pass.objects.create(product=PassProduct.INDIVIDUAL, category=donor_category)
    leg = PassLeg.objects.create(issued_pass=p, pandal=pandal, visit_date=dt.date(2026, 10, 12))

    ScanEvent.objects.create(gate=gate, leg=leg, result=ScanEvent.Result.ADMITTED,
                             scanned_at=timezone.now())

    with pytest.raises(IntegrityError), transaction.atomic():
        ScanEvent.objects.create(gate=gate, leg=leg, result=ScanEvent.Result.ADMITTED,
                                 scanned_at=timezone.now())


def test_a_manual_override_also_counts_as_the_one_admission(pandal, donor_category):
    from apps.pandals.models import Gate

    gate = Gate.objects.create(pandal=pandal, name="Gate 2")
    p = Pass.objects.create(product=PassProduct.INDIVIDUAL, category=donor_category)
    leg = PassLeg.objects.create(issued_pass=p, pandal=pandal, visit_date=dt.date(2026, 10, 12))

    ScanEvent.objects.create(gate=gate, leg=leg, result=ScanEvent.Result.MANUAL_OVERRIDE,
                             scanned_at=timezone.now(), override_reason="Flat battery")

    with pytest.raises(IntegrityError), transaction.atomic():
        ScanEvent.objects.create(gate=gate, leg=leg, result=ScanEvent.Result.ADMITTED,
                                 scanned_at=timezone.now())


def test_refusals_are_recorded_as_often_as_they_happen(pandal, donor_category):
    """Expired and duplicate scans are evidence, not errors — log them all."""
    from apps.pandals.models import Gate

    gate = Gate.objects.create(pandal=pandal, name="Gate 3")
    p = Pass.objects.create(product=PassProduct.INDIVIDUAL, category=donor_category)
    leg = PassLeg.objects.create(issued_pass=p, pandal=pandal, visit_date=dt.date(2026, 10, 12))

    for _ in range(3):
        ScanEvent.objects.create(gate=gate, leg=leg, result=ScanEvent.Result.EXPIRED,
                                 scanned_at=timezone.now())

    assert leg.scans.filter(result=ScanEvent.Result.EXPIRED).count() == 3


def test_an_unrecognised_code_is_logged_with_no_leg(pandal):
    from apps.pandals.models import Gate

    gate = Gate.objects.create(pandal=pandal, name="Gate 4")
    event = ScanEvent.objects.create(gate=gate, result=ScanEvent.Result.INVALID,
                                     presented_code="nonsense", scanned_at=timezone.now())

    assert event.leg is None


# --------------------------------------------------------------------------
# Pass codes
# --------------------------------------------------------------------------

def test_a_pass_code_is_readable_and_not_enumerable():
    codes = {generate_pass_code() for _ in range(200)}

    assert len(codes) == 200
    assert all(c.startswith("EDP-") and len(c) == 16 for c in codes)


def test_two_passes_never_share_a_code(donor_category):
    codes = {Pass.objects.create(product=PassProduct.INDIVIDUAL,
                                 category=donor_category).pass_code for _ in range(20)}
    assert len(codes) == 20
