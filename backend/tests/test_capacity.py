"""The capacity primitive.

This is the part of the schema where being wrong is expensive, so it is tested
harder than anything else — including under real concurrent transactions.
"""

import datetime as dt
import threading

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.common.errors import CapacityUnavailableError, HoldExpiredError
from apps.services import inventory
from apps.services.models import ServiceCapacityHold, ServiceDayCapacity

pytestmark = pytest.mark.django_db


def test_a_hold_reduces_what_is_available(service_day):
    assert inventory.available(service_day) == 20

    inventory.place_hold(day_id=service_day.pk, quantity=3)

    assert inventory.available(service_day) == 17


def test_issuing_a_hold_moves_it_into_the_issued_count(service_day):
    hold = inventory.place_hold(day_id=service_day.pk, quantity=3)

    inventory.issue(hold_id=hold.pk)

    service_day.refresh_from_db()
    assert service_day.issued_count == 3
    assert inventory.available(service_day) == 17


def test_an_expired_hold_frees_capacity_without_a_sweeper_running(service_day):
    """Holds are rows, not a counter. Nothing has to run for capacity to return."""
    hold = inventory.place_hold(day_id=service_day.pk, quantity=20)
    assert inventory.available(service_day) == 0

    ServiceCapacityHold.objects.filter(pk=hold.pk).update(
        expires_at=timezone.now() - dt.timedelta(seconds=1)
    )

    assert inventory.available(service_day) == 20


def test_releasing_a_hold_returns_capacity_at_once(service_day):
    hold = inventory.place_hold(day_id=service_day.pk, quantity=5)

    inventory.release_hold(hold_id=hold.pk)

    assert inventory.available(service_day) == 20


def test_a_hold_beyond_what_remains_is_refused_with_the_number_left(service_day):
    inventory.place_hold(day_id=service_day.pk, quantity=18)

    with pytest.raises(CapacityUnavailableError) as caught:
        inventory.place_hold(day_id=service_day.pk, quantity=3)

    assert caught.value.extra["available"] == 2


def test_a_closed_day_takes_no_holds(service_day):
    ServiceDayCapacity.objects.filter(pk=service_day.pk).update(is_open=False)

    with pytest.raises(CapacityUnavailableError):
        inventory.place_hold(day_id=service_day.pk, quantity=1)


def test_a_lapsed_hold_is_reacquired_when_the_place_is_still_free(service_day):
    """Payment landing late is normal. If nobody took the place, honour it."""
    hold = inventory.place_hold(day_id=service_day.pk, quantity=2)
    ServiceCapacityHold.objects.filter(pk=hold.pk).update(
        expires_at=timezone.now() - dt.timedelta(minutes=5)
    )

    inventory.issue(hold_id=hold.pk)

    service_day.refresh_from_db()
    assert service_day.issued_count == 2


def test_a_lapsed_hold_fails_loudly_when_the_place_has_gone(service_day):
    """The caller refunds. That is the honest outcome, not the convenient one."""
    ServiceDayCapacity.objects.filter(pk=service_day.pk).update(capacity=1)
    hold = inventory.place_hold(day_id=service_day.pk, quantity=1)
    ServiceCapacityHold.objects.filter(pk=hold.pk).update(
        expires_at=timezone.now() - dt.timedelta(minutes=5)
    )
    inventory.place_hold(day_id=service_day.pk, quantity=1)  # somebody else took it

    with pytest.raises(HoldExpiredError):
        inventory.issue(hold_id=hold.pk)


def test_the_database_refuses_to_oversell_even_if_the_code_is_wrong(service_day):
    """The CHECK is the floor. No bug above it can breach the cap."""
    with pytest.raises(IntegrityError), transaction.atomic():
        ServiceDayCapacity.objects.filter(pk=service_day.pk).update(issued_count=21)


def test_expire_holds_is_housekeeping_only(service_day):
    hold = inventory.place_hold(day_id=service_day.pk, quantity=4)
    ServiceCapacityHold.objects.filter(pk=hold.pk).update(
        expires_at=timezone.now() - dt.timedelta(seconds=1)
    )

    assert inventory.available(service_day) == 20      # already free
    assert inventory.expire_holds() == 1               # tidied afterwards
    assert inventory.available(service_day) == 20


@pytest.mark.django_db(transaction=True)
def test_only_one_of_many_racing_visitors_gets_the_last_place(city, locality):
    """The Ashtami case: everyone converging on one row at the same instant."""
    from apps.pandals.models import Pandal
    from apps.services.models import Service

    pandal = Pandal.objects.create(name="P", slug="p-race", city=city, locality=locality)
    service = Service.objects.create(pandal=pandal,
                                     name="Aarti", slug="aarti", price_paise=25_100)
    day = ServiceDayCapacity.objects.create(service=service, date=dt.date(2026, 10, 12),
                                            capacity=1)

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
    assert inventory.available(day) == 0
