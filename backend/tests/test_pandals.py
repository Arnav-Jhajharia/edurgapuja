import pytest
from django.core.exceptions import ValidationError

from apps.pandals.models import Pandal, PandalDomainAlias
from apps.pandals.validators import validate_subdomain

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("slug", ["ballygunge-cultural", "mudiali", "66-palli", "a"])
def test_dns_safe_names_are_accepted(slug):
    validate_subdomain(slug)


@pytest.mark.parametrize("slug", ["-leading", "trailing-", "Upper", "under_score",
                                   "spaces here", "x" * 64])
def test_names_dns_would_refuse_are_rejected(slug):
    with pytest.raises(ValidationError):
        validate_subdomain(slug)


@pytest.mark.parametrize("slug", ["www", "api", "admin", "app", "static"])
def test_the_platforms_own_names_are_reserved(slug):
    """A committee called 'app' would otherwise take the platform's own host."""
    with pytest.raises(ValidationError):
        validate_subdomain(slug)


def test_a_pandal_knows_the_url_it_is_served_on(pandal, settings):
    settings.SITE_DOMAIN = "edurgapuja.app"
    assert pandal.canonical_url == "https://ballygunge-cultural.edurgapuja.app"


def test_a_custom_domain_wins_over_the_subdomain(pandal):
    pandal.custom_domain = "ballygungecultural.org"
    assert pandal.canonical_host == "ballygungecultural.org"


def test_an_old_name_keeps_pointing_at_the_pandal(pandal):
    """A renamed pandal's old subdomain is already on a banner somewhere."""
    alias = PandalDomainAlias.objects.create(
        host="ballygunge-cultural-2025.edurgapuja.app", pandal=pandal
    )
    assert alias.pandal == pandal


def test_only_published_and_active_pandals_count_as_published(pandal):
    assert pandal.is_published

    pandal.is_active = False
    assert not pandal.is_published

    pandal.is_active = True
    pandal.publication_status = Pandal.PublicationStatus.DRAFT
    assert not pandal.is_published


def test_a_pandal_sells_no_passes_until_its_owner_says_so(pandal):
    """v1 ships with the switch off; turning it on is data, not a release."""
    assert pandal.sells_passes is False
    assert pandal.accepts_donations is True
