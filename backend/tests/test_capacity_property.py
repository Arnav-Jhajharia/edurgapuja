"""The invariant, under sequences nobody thought to write by hand."""

import datetime as dt

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from apps.common.errors import CapacityUnavailableError, HoldExpiredError
from apps.services import inventory
from apps.services.models import ServiceCapacityHold, ServiceDayCapacity

pytestmark = pytest.mark.django_db

CAPACITY = 30

operation = st.tuples(
    st.sampled_from(["hold", "issue", "release", "expire"]),
    st.integers(min_value=1, max_value=6),
)


@settings(max_examples=60, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(ops=st.lists(operation, max_size=40))
def test_issued_plus_live_holds_never_exceeds_capacity(service, ops):
    day, _ = ServiceDayCapacity.objects.get_or_create(
        service=service, date=dt.date(2026, 10, 13), defaults={"capacity": CAPACITY}
    )
    holds: list = []

    for name, qty in ops:
        if name == "hold":
            try:
                holds.append(inventory.place_hold(day_id=day.pk, quantity=qty))
            except CapacityUnavailableError:
                pass
        elif name == "issue" and holds:
            try:
                inventory.issue(hold_id=holds.pop(0).pk)
            except HoldExpiredError:
                pass
        elif name == "release" and holds:
            inventory.release_hold(hold_id=holds.pop(0).pk)
        elif name == "expire":
            inventory.expire_holds()

        day.refresh_from_db()
        held = sum(h.quantity for h in inventory.live_holds(day))
        assert day.issued_count + held <= day.capacity
        assert day.issued_count <= day.capacity

    assert ServiceCapacityHold.objects.filter(day=day).count() >= 0
