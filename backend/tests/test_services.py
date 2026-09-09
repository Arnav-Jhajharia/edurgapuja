"""Value-added services, and the forms a pandal writes for them.

The property under test is the one that survived the redesign: **a booking may
only submit what its service asks for.** The platform used to own the questions
and that made five of them a ceiling; the pandal owns them now, and the fence is
still exactly where it was.
"""

import pytest

from apps.common.errors import ValidationFailedError
from apps.pandals.models import Pandal
from apps.services.models import Service, ServiceField, validate_details
from apps.services.templates import apply_template

pytestmark = pytest.mark.django_db

K = ServiceField.Kind


def ask(service, key, label="Q", kind=K.TEXT, **extra):
    return ServiceField.objects.create(service=service, key=key, label=label, kind=kind, **extra)


@pytest.fixture
def tour(pandal):
    """A service whose form came straight from the template, rules and all."""
    offering = Service.objects.create(pandal=pandal, name="Heritage Walk",
                                      slug="heritage-walk", price_paise=60_000)
    apply_template(offering, "curated-tour")
    return offering


# --------------------------------------------------------------------------
# The fence
# --------------------------------------------------------------------------

def test_a_service_accepts_the_questions_it_asks(tour):
    details = validate_details(tour, {"name": "Ananya Sen", "contact_phone": "+919812345678",
                                      "party_size": 4})
    assert details == {"name": "Ananya Sen", "contact_phone": "+919812345678", "party_size": 4}


def test_a_required_question_left_blank_names_itself(tour):
    with pytest.raises(ValidationFailedError) as caught:
        validate_details(tour, {"name": "Ananya", "contact_phone": "+919812345678"})

    assert caught.value.fields["party_size"] == "How many people is required."


def test_questions_a_service_does_not_ask_are_refused(tour):
    """Holding data nobody asked for is how a sensitive-data problem starts."""
    with pytest.raises(ValidationFailedError) as caught:
        validate_details(tour, {"name": "Ananya", "contact_phone": "+919812345678",
                                "party_size": 2, "gotra": "Kashyap"})

    assert "gotra" in caught.value.fields


def test_a_service_that_asks_for_a_gotra_may_store_one(pandal):
    """Same fence, moved: this service asks, so this service may hold it."""
    puja = Service.objects.create(pandal=pandal, name="Puja In Your Name",
                                  slug="puja-in-your-name", price_paise=50_100)
    apply_template(puja, "puja-in-your-name")

    details = validate_details(puja, {"name": "A", "contact_phone": "+919000000000",
                                      "name_for_puja": "Ananya", "gotra": "Kashyap",
                                      "sankalp": "For good health"})

    assert {"name_for_puja", "gotra", "sankalp"} <= set(details)


def test_empty_answers_are_dropped_rather_than_stored(tour):
    answered = validate_details(tour, {"name": "Ananya", "contact_phone": "+919812345678",
                                       "party_size": 2, "notes": ""})
    assert answered == {"name": "Ananya", "contact_phone": "+919812345678", "party_size": 2}


def test_a_required_question_must_be_answered(service):
    ask(service, "address", "Delivery address", required=True)

    with pytest.raises(ValidationFailedError) as caught:
        validate_details(service, {})

    assert "address" in caught.value.fields


# --------------------------------------------------------------------------
# A service can be anything
# --------------------------------------------------------------------------

def test_a_pandal_invents_a_service_nobody_thought_of(pandal):
    """The point of the redesign: no migration, no platform type, no ceiling."""
    dhunuchi = Service.objects.create(pandal=pandal, name="Dhunuchi Naach Registration",
                                      slug="dhunuchi-naach", price_paise=20_000,
                                      type="Competition")
    ask(dhunuchi, "dancer_name", "Dancer's name", required=True)
    ask(dhunuchi, "age_group", "Age group", K.SELECT, options=["Under 12", "12-18", "Adult"])
    ask(dhunuchi, "years_dancing", "Years of experience", K.NUMBER)
    ask(dhunuchi, "own_dhunuchi", "Bringing your own dhunuchi", K.CHECKBOX)

    details = validate_details(dhunuchi, {
        "dancer_name": "Ritwik", "age_group": "Adult",
        "years_dancing": "6", "own_dhunuchi": "yes",
    })

    assert details == {"dancer_name": "Ritwik", "age_group": "Adult",
                       "years_dancing": 6, "own_dhunuchi": True}


def test_a_number_question_refuses_something_that_is_not_a_number(service):
    ask(service, "guests", "How many guests", K.NUMBER)

    with pytest.raises(ValidationFailedError) as caught:
        validate_details(service, {"guests": "a few"})

    assert "number" in caught.value.fields["guests"].lower()


def test_a_choose_one_question_refuses_an_answer_not_on_the_list(service):
    ask(service, "meal", "Which bhog", K.SELECT, options=["Khichuri", "Payesh"])

    with pytest.raises(ValidationFailedError) as caught:
        validate_details(service, {"meal": "Biryani"})

    assert "Khichuri" in caught.value.fields["meal"]


def test_a_date_question_refuses_something_that_is_not_a_date(service):
    ask(service, "deliver_on", "Deliver on", K.DATE)

    with pytest.raises(ValidationFailedError):
        validate_details(service, {"deliver_on": "next Tuesday"})

    assert validate_details(service, {"deliver_on": "2026-10-12"}) == {"deliver_on": "2026-10-12"}


def test_a_checkbox_reads_the_shapes_a_form_actually_posts(service):
    ask(service, "wheelchair", "Wheelchair needed", K.CHECKBOX)

    assert validate_details(service, {"wheelchair": "on"})["wheelchair"] is True
    assert validate_details(service, {"wheelchair": True})["wheelchair"] is True
    assert validate_details(service, {"wheelchair": "false"})["wheelchair"] is False


# --------------------------------------------------------------------------
# Templates are a starting point, not a type
# --------------------------------------------------------------------------

def test_a_template_fills_a_form_that_can_then_be_edited_freely(tour):
    tour.fields.filter(key="notes").delete()
    ask(tour, "pickup_point", "Where shall we meet you")

    assert set(tour.allowed_detail_fields) == {"name", "contact_phone", "party_size",
                                               "pickup_point"}


def test_applying_a_template_never_overwrites_a_question_already_asked(pandal):
    """Applying a template to a live service must not rewrite a question that
    bookings have already answered."""
    offering = Service.objects.create(pandal=pandal, name="Walk", slug="walk", price_paise=0)
    ask(offering, "name", "Full name as on your ID", required=True, help_text="Mine")

    apply_template(offering, "curated-tour")

    kept = offering.fields.get(key="name")
    assert kept.label == "Full name as on your ID"
    assert kept.help_text == "Mine"


def test_an_unknown_template_slug_adds_nothing_rather_than_failing(pandal):
    offering = Service.objects.create(pandal=pandal, name="X", slug="x", price_paise=0)
    assert apply_template(offering, "not-a-template") == 0


# --------------------------------------------------------------------------
# Not everything has a daily limit
# --------------------------------------------------------------------------

@pytest.fixture
def delivery(pandal):
    """Prasad posted to your house does not run out at four o'clock."""
    offering = Service.objects.create(pandal=pandal, name="Prasad by post",
                                      slug="prasad-post", price_paise=15_000,
                                      requires_capacity=False)
    apply_template(offering, "prasad-delivery")
    return offering


def test_a_service_with_no_daily_limit_is_booked_without_a_hold(delivery, visitor):
    """Before this, a service with no capacity rows was saved but unbookable —
    an admin had to discover that from an empty table."""
    from apps.services.booking import start_booking

    booking, order, hold = start_booking(
        service_id=delivery.pk, date=None, quantity=1, user=visitor,
        details={"name": "Ananya", "contact_phone": "+919812345678",
                 "address": "12 Southern Avenue", "pin_code": "700029"},
    )

    assert hold is None
    assert booking.day_id is None
    assert order.total_paise == 15_000


def test_paying_for_a_capacity_free_service_confirms_it_at_once(delivery, visitor):
    """Nothing could have run out in between, so there is nothing to re-acquire."""
    from apps.orders import services as orders
    from apps.services.booking import start_booking
    from apps.services.fulfilment import confirm_service_booking
    from apps.services.models import ServiceBooking

    booking, order, _ = start_booking(
        service_id=delivery.pk, date=None, quantity=1, user=visitor,
        details={"name": "Ananya", "contact_phone": "+919812345678",
                 "address": "12 Southern Avenue", "pin_code": "700029"},
    )
    orders.mark_paid(order)
    confirm_service_booking(booking.order_line)

    booking.refresh_from_db()
    assert booking.status == ServiceBooking.Status.CONFIRMED
    assert booking.confirmed_at is not None


def test_a_capacity_free_service_still_fences_its_details(delivery, visitor):
    """Skipping the hold does not skip the form."""
    from apps.services.booking import start_booking

    with pytest.raises(ValidationFailedError):
        start_booking(service_id=delivery.pk, date=None, quantity=1, user=visitor,
                      details={"name": "Ananya", "contact_phone": "+919812345678",
                               "gotra": "Kashyap"})


def test_each_pandal_names_its_own_services(pandal, city, locality):
    other = Pandal.objects.create(name="Mudiali", slug="mudiali", city=city, locality=locality)
    Service.objects.create(pandal=pandal, name="Donor Darshan",
                           slug="donor-darshan", price_paise=0)
    Service.objects.create(pandal=other, name="VIP Darshan Fast-Track",
                           slug="vip-darshan", price_paise=50_000)

    assert [s.name for s in pandal.services.all()] == ["Donor Darshan"]
    assert [s.name for s in other.services.all()] == ["VIP Darshan Fast-Track"]
