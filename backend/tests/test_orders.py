import pytest
from django.db import IntegrityError, transaction

from apps.orders.models import Order, OrderLine

pytestmark = pytest.mark.django_db


def test_a_line_multiplies_its_own_amount(pandal):
    order = Order.objects.create(pandal=pandal)
    line = OrderLine.objects.create(order=order, kind=OrderLine.Kind.SERVICE_BOOKING,
                                    quantity=3, unit_amount_paise=75_000)

    assert line.amount_paise == 225_000


def test_an_order_totals_its_lines_plus_fee_less_discount(pandal):
    order = Order.objects.create(pandal=pandal, platform_fee_paise=500, discount_paise=1_000)
    OrderLine.objects.create(order=order, kind=OrderLine.Kind.DONATION,
                             quantity=1, unit_amount_paise=50_100)
    OrderLine.objects.create(order=order, kind=OrderLine.Kind.SERVICE_BOOKING,
                             quantity=2, unit_amount_paise=75_000)

    order.recalculate()

    assert order.subtotal_paise == 200_100
    assert order.total_paise == 199_600


def test_one_order_can_carry_several_kinds(pandal):
    """A donation that later yields a pass is two lines, not a new concept."""
    order = Order.objects.create(pandal=pandal)
    OrderLine.objects.create(order=order, kind=OrderLine.Kind.DONATION,
                             quantity=1, unit_amount_paise=100_100)
    OrderLine.objects.create(order=order, kind=OrderLine.Kind.PASS,
                             quantity=1, unit_amount_paise=0)

    assert {line.kind for line in order.lines.all()} == {"donation", "pass"}


def test_an_order_cannot_hold_a_negative_amount(pandal):
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(pandal=pandal, total_paise=-1)


def test_a_line_cannot_have_zero_quantity(pandal):
    order = Order.objects.create(pandal=pandal)
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderLine.objects.create(order=order, kind=OrderLine.Kind.DONATION,
                                 quantity=0, unit_amount_paise=100)
