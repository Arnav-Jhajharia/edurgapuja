import pytest
from django.db import IntegrityError, transaction

from apps.donations.models import Donation, DonationLink, DonationOffering

pytestmark = pytest.mark.django_db


def test_leaving_the_name_blank_is_how_a_donation_is_anonymous(pandal):
    named = Donation.objects.create(pandal=pandal, donor_name="Suvra Chatterjee",
                                    amount_paise=100_100)
    anonymous = Donation.objects.create(pandal=pandal, amount_paise=50_100)

    assert named.is_anonymous is False
    assert anonymous.is_anonymous is True


def test_an_offering_is_an_amount_with_a_purpose(pandal):
    offering = DonationOffering.objects.create(
        pandal=pandal, amount_paise=50_100, label="Support a diya"
    )
    assert str(offering) == "₹501.00 · Support a diya"


def test_a_donation_records_which_preset_produced_it(pandal):
    """So a pandal can see what its donors actually respond to (FR-050d)."""
    offering = DonationOffering.objects.create(pandal=pandal, amount_paise=100_100,
                                               label="Support bhog")
    donation = Donation.objects.create(pandal=pandal, offering=offering, amount_paise=100_100)

    assert donation.offering == offering
    assert offering.donations.count() == 1


def test_a_link_gets_a_token_and_a_shareable_path(pandal):
    link = DonationLink.objects.create(pandal=pandal, purpose="Pandal Lighting Fund")

    assert link.token
    assert link.path == f"/d/{pandal.slug}/{link.token}"


def test_two_links_never_share_a_token(pandal):
    tokens = {DonationLink.objects.create(pandal=pandal).token for _ in range(25)}
    assert len(tokens) == 25


def test_a_donation_must_be_a_positive_amount(pandal):
    with pytest.raises(IntegrityError), transaction.atomic():
        Donation.objects.create(pandal=pandal, amount_paise=0)
