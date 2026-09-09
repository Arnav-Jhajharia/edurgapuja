import datetime as dt

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import ProfileType, User
from apps.accounts.otp.senders import MemorySender
from apps.geo.models import City, Locality, State
from apps.pandals.models import Gate, Pandal
from apps.passes.models import (
    PandalDayCapacity,
    PassCategory,
    PassConfig,
    PassProduct,
)
from apps.services.models import Service, ServiceDayCapacity, ServiceField


@pytest.fixture(autouse=True)
def _clean_side_state():
    """Rate limits and issued codes live outside the database."""
    cache.clear()
    MemorySender.reset()
    yield
    cache.clear()
    MemorySender.reset()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def city(db):
    state = State.objects.create(name="West Bengal", code="WB")
    return City.objects.create(state=state, name="Kolkata")


@pytest.fixture
def locality(city):
    return Locality.objects.create(city=city, name="Ballygunge")


@pytest.fixture
def pandal(city, locality):
    return Pandal.objects.create(
        name="Ballygunge Cultural",
        slug="ballygunge-cultural",
        city=city,
        locality=locality,
        accepts_donations=True,
        offers_services=True,
        publication_status=Pandal.PublicationStatus.PUBLISHED,
    )


@pytest.fixture
def service(pandal):
    """A service with a small form of its own.

    Nothing is required here on purpose: these fixtures are used by tests about
    payments and capacity, and a form's rules are `test_services.py`'s subject.
    """
    offering = Service.objects.create(
        pandal=pandal,
        name="Get Curated Tour", slug="curated-tour", price_paise=75_000,
    )
    for order, (key, label, kind) in enumerate([
        ("name", "Your name", ServiceField.Kind.TEXT),
        ("party_size", "How many people", ServiceField.Kind.NUMBER),
        ("notes", "Anything we should know", ServiceField.Kind.TEXTAREA),
    ], start=1):
        ServiceField.objects.create(service=offering, key=key, label=label, kind=kind,
                                    sort_order=order * 10)
    return offering


@pytest.fixture
def service_day(service):
    return ServiceDayCapacity.objects.create(
        service=service, date=dt.date(2026, 10, 12), capacity=20
    )


@pytest.fixture
def visitor(db):
    return User.objects.create_user(phone="+919876543210", first_name="Ananya", last_name="Sen")


@pytest.fixture
def profile_types(db):
    names = ["Senior Citizens", "Families with Young Children", "Specially Abled",
             "Press", "Social Media Influencer"]
    return [ProfileType.objects.create(name=n, slug=n.lower().replace(" ", "-"), sort_order=i)
            for i, n in enumerate(names)]


@pytest.fixture
def donor_category(pandal):
    return PassCategory.objects.create(pandal=pandal, name="Donor", slug="donor")


@pytest.fixture
def pandal_day(pandal):
    return PandalDayCapacity.objects.create(
        pandal=pandal, date=dt.date(2026, 10, 12), capacity=2000
    )


@pytest.fixture
def selling_pandal(pandal):
    """The same pandal, with passes switched on — which is the whole of what a
    committee does to start selling them."""
    pandal.sells_passes = True
    pandal.save(update_fields=["sells_passes"])
    return pandal


@pytest.fixture
def individual_config(selling_pandal, donor_category, pandal_day):
    return PassConfig.objects.create(
        pandal=selling_pandal, category=donor_category, product=PassProduct.INDIVIDUAL,
        from_date=dt.date(2026, 10, 10), to_date=dt.date(2026, 10, 14),
        from_time=dt.time(18, 0), to_time=dt.time(21, 0),
        price_paise=30_000, max_party_size=1,
    )


@pytest.fixture
def group_config(selling_pandal, donor_category, pandal_day):
    return PassConfig.objects.create(
        pandal=selling_pandal, category=donor_category, product=PassProduct.GROUP,
        from_date=dt.date(2026, 10, 10), to_date=dt.date(2026, 10, 14),
        price_paise=25_000, max_party_size=6,
    )


@pytest.fixture
def gate(pandal):
    return Gate.objects.create(pandal=pandal, name="Gate 1")
