import pytest
from django.urls import reverse

from apps.donations.models import DonationOffering
from apps.ops.models import LostItem, PandalLiveStatus
from apps.pandals.models import PageBlock, PandalBrand, PandalDomainAlias, VisitFact

pytestmark = pytest.mark.django_db


@pytest.fixture
def page(pandal, service):
    PandalBrand.objects.create(pandal=pandal, primary_colour="#B45F1E")
    PageBlock.objects.create(pandal=pandal, kind=PageBlock.Kind.HERO, sort_order=1,
                             content={"headline": "Experience the Spirit of Durga Puja"})
    PageBlock.objects.create(pandal=pandal, kind=PageBlock.Kind.ABOUT, sort_order=2,
                             content={"headline": "Where devotion becomes belonging"})
    VisitFact.objects.create(pandal=pandal, label="Darshan Timings",
                             value="Open daily · Morning to late evening")
    DonationOffering.objects.create(pandal=pandal, amount_paise=50_100, label="Support a diya")
    PandalLiveStatus.objects.create(pandal=pandal, estimated_wait_minutes=18,
                                    crowd_level=PandalLiveStatus.CrowdLevel.MEDIUM)
    return pandal


def test_one_request_renders_the_whole_page(api, page):
    response = api.get(reverse("pandal-page", args=[page.slug]))

    body = response.json()
    assert response.status_code == 200
    assert body["pandal"]["slug"] == "ballygunge-cultural"
    assert body["pandal"]["canonical_url"].startswith("https://ballygunge-cultural.")
    assert body["brand"]["primary_colour"] == "#B45F1E"
    assert [b["kind"] for b in body["blocks"]] == ["hero", "about"]
    assert body["donation_offerings"][0]["label"] == "Support a diya"
    assert body["services"][0]["name"] == "Get Curated Tour"
    assert body["visit_facts"][0]["label"] == "Darshan Timings"
    assert body["live_status"]["crowd_level_display"] == "Medium"


def test_the_page_declares_what_the_pandal_actually_does(api, page):
    body = api.get(reverse("pandal-page", args=[page.slug])).json()

    assert body["capabilities"] == {
        "sells_passes": False, "accepts_donations": True, "offers_services": True,
    }


def test_a_pandal_that_sells_nothing_gets_an_empty_list_not_an_error(api, page):
    page.accepts_donations = False
    page.offers_services = False
    page.save(update_fields=["accepts_donations", "offers_services"])

    body = api.get(reverse("pandal-page", args=[page.slug])).json()

    assert body["donation_offerings"] == []
    assert body["services"] == []


def test_the_page_carries_what_a_link_preview_needs(api, page):
    body = api.get(reverse("pandal-page", args=[page.slug])).json()

    assert body["seo"]["title"]
    assert body["seo"]["locales"] == ["en", "bn", "hi"]


def test_the_page_is_cacheable_and_varies_by_language(api, page):
    response = api.get(reverse("pandal-page", args=[page.slug]))

    assert "max-age=60" in response["Cache-Control"]
    # DRF adds Accept and the session adds Cookie; ours must be among them.
    assert "Accept-Language" in response["Vary"]


def test_an_unpublished_pandal_is_not_found(api, page):
    from apps.pandals.models import Pandal

    page.publication_status = Pandal.PublicationStatus.DRAFT
    page.save(update_fields=["publication_status"])

    assert api.get(reverse("pandal-page", args=[page.slug])).status_code == 404


def test_a_host_resolves_to_its_pandal(api, pandal, settings):
    settings.SITE_DOMAIN = "edurgapuja.app"

    response = api.get(reverse("site-resolve"),
                       {"host": "ballygunge-cultural.edurgapuja.app"})

    assert response.json() == {"status": "ok", "slug": "ballygunge-cultural"}


def test_an_old_host_resolves_to_a_permanent_redirect(api, pandal, settings):
    """A renamed pandal's old name is already on a banner somewhere (FR-248)."""
    settings.SITE_DOMAIN = "edurgapuja.app"
    PandalDomainAlias.objects.create(host="ballygunge-cultural-2025.edurgapuja.app",
                                     pandal=pandal)

    body = api.get(reverse("site-resolve"),
                   {"host": "ballygunge-cultural-2025.edurgapuja.app"}).json()

    assert body["status"] == "redirect"
    assert body["permanent"] is True
    assert body["redirect_to"] == "https://ballygunge-cultural.edurgapuja.app"


def test_a_custom_domain_resolves_too(api, pandal, settings):
    pandal.custom_domain = "ballygungecultural.org"
    pandal.save(update_fields=["custom_domain"])

    assert api.get(reverse("site-resolve"),
                   {"host": "ballygungecultural.org"}).json()["slug"] == pandal.slug


def test_an_unknown_host_is_not_found(api, settings):
    settings.SITE_DOMAIN = "edurgapuja.app"

    assert api.get(reverse("site-resolve"), {"host": "nobody.edurgapuja.app"}).status_code == 404


def test_visitors_see_only_outstanding_lost_items(api, pandal):
    LostItem.objects.create(pandal=pandal, item="Black umbrella", location="Near Gate 2")
    found = LostItem.objects.create(pandal=pandal, item="Water bottle")
    found.mark_found()

    body = api.get(reverse("pandal-lost-items", args=[pandal.slug])).json()

    assert [i["item"] for i in body] == ["Black umbrella"]
