"""The admin API behind the four panels.

The test that matters most is scoping: every admin response is narrowed to the
caller's own entity unless they are a Super Admin (FR-233), and that narrowing
happens in the queryset rather than by hiding a button.
"""

import datetime as dt
import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AdminMembership, Role, User
from apps.accounts.otp.senders import MemorySender
from apps.donations.models import Donation, DonationOffering
from apps.ops.models import PandalLiveStatus, SupportRequest
from apps.pandals import blocks as page_blocks
from apps.pandals.models import Gate, PageBlock, Pandal
from apps.passes.models import LegSecret, Pass, PassLeg, ScanEvent
from apps.services.models import Service, ServiceField
from apps.sponsorship.models import (
    BrandingCreative,
    BrandingPlacement,
    Organisation,
    Pool,
    PoolAllocation,
    SponsorshipPackage,
)

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------
# Fixtures: two pandals, two admins, a sponsor and a sub-sponsor
# --------------------------------------------------------------------------

@pytest.fixture
def other_pandal(city, locality):
    return Pandal.objects.create(name="Mudiali Club", slug="mudiali-club", city=city,
                                 locality=locality, accepts_donations=True,
                                 offers_services=True,
                                 publication_status=Pandal.PublicationStatus.PUBLISHED)


def make_admin(phone, role, *, pandal=None, organisation=None):
    user = User.objects.create_user(phone=phone, first_name=role.split("_")[0].title())
    AdminMembership.objects.create(user=user, role=role, pandal=pandal,
                                   organisation=organisation)
    return user


@pytest.fixture
def pandal_admin(pandal):
    return make_admin("+919000000001", Role.PANDAL_ADMIN, pandal=pandal)


@pytest.fixture
def other_admin(other_pandal):
    return make_admin("+919000000002", Role.PANDAL_ADMIN, pandal=other_pandal)


@pytest.fixture
def super_admin(db):
    return make_admin("+919000000003", Role.SUPER_ADMIN)


@pytest.fixture
def sponsor(db):
    return Organisation.objects.create(name="Sponsor One", slug="sponsor-one")


@pytest.fixture
def sponsor_admin(sponsor):
    return make_admin("+919000000004", Role.SPONSOR_ADMIN, organisation=sponsor)


@pytest.fixture
def visitor_only(db):
    return User.objects.create_user(phone="+919000000009")


# --------------------------------------------------------------------------
# Signing in
# --------------------------------------------------------------------------

def test_an_administrator_signs_in_by_mobile_and_code(api, pandal_admin):
    api.post(reverse("admin-otp-request"), {"phone": pandal_admin.phone}, format="json")
    code = MemorySender.last_code(pandal_admin.phone)

    response = api.post(reverse("admin-otp-verify"),
                        {"phone": pandal_admin.phone, "code": code}, format="json")

    assert response.status_code == 200
    assert response.json()["roles"] == ["pandal_admin"]
    assert response.json()["access"]


def test_a_visitor_with_a_valid_code_still_cannot_sign_in_to_the_admin(api, visitor_only):
    """Verified, but nobody here — and deliberately indistinguishable from a
    wrong code, so this endpoint cannot be used to discover administrators."""
    api.post(reverse("admin-otp-request"), {"phone": visitor_only.phone}, format="json")
    code = MemorySender.last_code(visitor_only.phone)

    response = api.post(reverse("admin-otp-verify"),
                        {"phone": visitor_only.phone, "code": code}, format="json")

    assert response.status_code == 422


def test_a_visitor_login_code_does_not_open_the_admin(api, pandal_admin):
    """Purpose is part of a challenge's identity."""
    api.post(reverse("otp-request"), {"phone": pandal_admin.phone}, format="json")
    visitor_code = MemorySender.last_code(pandal_admin.phone)

    response = api.post(reverse("admin-otp-verify"),
                        {"phone": pandal_admin.phone, "code": visitor_code}, format="json")

    assert response.status_code == 400


def test_me_says_which_panel_to_render(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-me")).json()

    assert body["roles"] == ["pandal_admin"]
    assert [p["slug"] for p in body["pandals"]] == [pandal.slug]
    assert body["organisations"] == []


def test_a_sponsor_admin_gets_its_organisations_not_pandals(api, sponsor_admin, sponsor):
    api.force_authenticate(sponsor_admin)

    body = api.get(reverse("admin-me")).json()

    assert body["roles"] == ["sponsor_admin"]
    assert body["pandals"] == []
    assert [o["name"] for o in body["organisations"]] == ["Sponsor One"]


def test_the_admin_is_closed_to_visitors(api, visitor_only):
    api.force_authenticate(visitor_only)

    assert api.get(reverse("admin-me")).status_code == 403


# --------------------------------------------------------------------------
# Scoping — FR-233
# --------------------------------------------------------------------------

def test_a_pandal_admin_sees_only_its_own_pandal(api, pandal_admin, pandal, other_pandal):
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-pandal-list")).json()

    assert [p["slug"] for p in body["results"]] == [pandal.slug]


def test_a_pandal_admin_cannot_open_another_pandal_by_id(api, pandal_admin, other_pandal):
    """Scoping is in the queryset, so a guessed id is a 404, not a 403."""
    api.force_authenticate(pandal_admin)

    assert api.get(reverse("admin-pandal-detail",
                           args=[other_pandal.id])).status_code == 404


def test_a_pandal_admin_sees_only_its_own_donations(api, pandal_admin, pandal, other_pandal):
    Donation.objects.create(pandal=pandal, amount_paise=50_100, donor_name="Mine")
    Donation.objects.create(pandal=other_pandal, amount_paise=50_100, donor_name="Theirs")
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-donation-list")).json()

    assert [d["donor_name"] for d in body["results"]] == ["Mine"]


def test_a_pandal_admin_cannot_create_an_offering_for_someone_else(api, pandal_admin,
                                                                    other_pandal):
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-offering-list"),
                        {"pandal": str(other_pandal.id), "amount_paise": 50_100,
                         "label": "Cheeky"}, format="json")

    assert response.status_code == 422
    assert DonationOffering.objects.count() == 0


def test_a_super_admin_sees_every_pandal(api, super_admin, pandal, other_pandal):
    api.force_authenticate(super_admin)

    body = api.get(reverse("admin-pandal-list")).json()

    assert {p["slug"] for p in body["results"]} == {pandal.slug, other_pandal.slug}


def test_only_a_super_admin_adds_a_pandal(api, pandal_admin, super_admin, city):
    payload = {"name": "New Pandal", "city": str(city.id)}

    api.force_authenticate(pandal_admin)
    assert api.post(reverse("admin-pandal-list"), payload, format="json").status_code == 422

    api.force_authenticate(super_admin)
    assert api.post(reverse("admin-pandal-list"),
                    {**payload, "slug": "new-pandal"}, format="json").status_code == 201


# --------------------------------------------------------------------------
# Running a pandal
# --------------------------------------------------------------------------

def test_a_pandal_admin_edits_its_own_brand(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-pandal-brand", args=[pandal.id]),
                         {"primary_colour": "#1F5F4B"}, format="json")

    assert response.status_code == 200
    assert response.json()["primary_colour"] == "#1F5F4B"


def test_a_pandal_admin_edits_one_page_block(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-pandal-block", args=[pandal.id, "hero"]),
                         {"content": {"headline": "Come Home This Puja"}}, format="json")

    assert response.status_code == 200
    assert pandal.blocks.get(kind="hero").content["headline"] == "Come Home This Puja"


def test_publishing_is_a_super_admin_decision(api, pandal_admin, super_admin, pandal):
    api.force_authenticate(pandal_admin)
    assert api.post(reverse("admin-pandal-publish", args=[pandal.id]),
                    {"status": "published"}, format="json").status_code == 422

    # A pandal admin may still put its own page forward for review.
    assert api.post(reverse("admin-pandal-publish", args=[pandal.id]),
                    {"status": "pending_review"}, format="json").status_code == 200

    api.force_authenticate(super_admin)
    assert api.post(reverse("admin-pandal-publish", args=[pandal.id]),
                    {"status": "published"}, format="json").status_code == 200


def test_a_donation_link_reports_how_many_donations_it_produced(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)
    created = api.post(reverse("admin-donation-link-list"),
                       {"pandal": str(pandal.id), "purpose": "Bhog"}, format="json").json()

    from apps.donations.models import DonationLink
    link = DonationLink.objects.get(pk=created["id"])
    Donation.objects.create(pandal=pandal, link=link, amount_paise=50_100)

    body = api.get(reverse("admin-donation-link-list")).json()
    assert body["results"][0]["donation_count"] == 1
    assert body["results"][0]["path"] == f"/d/{pandal.slug}/{link.token}"


def test_setting_service_capacity_for_several_days_at_once(api, pandal_admin, service):
    api.force_authenticate(pandal_admin)

    response = api.put(reverse("admin-service-capacity", args=[service.id]), {
        "days": [{"date": "2026-10-10", "capacity": 20},
                 {"date": "2026-10-11", "capacity": 25}],
    }, format="json")

    assert response.status_code == 200
    assert [d["capacity"] for d in response.json()] == [20, 25]
    assert [d["available"] for d in response.json()] == [20, 25]


def test_a_pandal_admin_publishes_a_live_crowd_reading(api, pandal_admin, pandal):
    """A regression guard for the shape of bug that http_method_names causes.

    The live-status action declares PUT, but Django checks the viewset's
    http_method_names first — so omitting "put" there 405s this route while
    every in-process check of the action itself still looks fine.
    """
    api.force_authenticate(pandal_admin)

    response = api.put(reverse("admin-pandal-live-status", args=[pandal.id]),
                       {"estimated_wait_minutes": 25, "crowd_level": "high"}, format="json")

    assert response.status_code == 200, response.content
    assert response.json()["estimated_wait_minutes"] == 25
    assert response.json()["crowd_level"] == "high"

    reading = PandalLiveStatus.objects.get(pandal=pandal)
    assert reading.updated_by == pandal_admin


def test_a_pandal_cannot_be_replaced_wholesale(api, super_admin, pandal):
    """PUT is routable now, so the record itself has to refuse it explicitly —
    a full replace would blank every field the panel did not send."""
    api.force_authenticate(super_admin)

    response = api.put(reverse("admin-pandal-detail", args=[pandal.id]),
                       {"name": "Renamed"}, format="json")

    assert response.status_code == 422
    pandal.refresh_from_db()
    assert pandal.name != "Renamed"


def test_resolving_a_support_request_stamps_who_and_when(api, pandal_admin, pandal):
    request_row = SupportRequest.objects.create(pandal=pandal, name="Meera",
                                                contact_phone="+919988776655",
                                                message="More City Pass slots please")
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-support-resolve", args=[request_row.id]))

    assert response.json()["status"] == "resolved"
    request_row.refresh_from_db()
    assert request_row.resolved_by == pandal_admin


def test_revenue_is_grouped_by_what_was_bought(api, pandal_admin, pandal):
    """Passes appear here later as a new kind, with no new endpoint."""
    from apps.orders.models import Order, OrderLine

    order = Order.objects.create(pandal=pandal, status=Order.Status.PAID, total_paise=125_100)
    OrderLine.objects.create(order=order, kind=OrderLine.Kind.DONATION,
                             unit_amount_paise=50_100)
    OrderLine.objects.create(order=order, kind=OrderLine.Kind.SERVICE_BOOKING,
                             unit_amount_paise=75_000)
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-revenue")).json()

    assert body["orders"] == 1
    assert {row["kind"]: row["total_paise"] for row in body["by_kind"]} == {
        "donation": 50_100, "service_booking": 75_000,
    }


# --------------------------------------------------------------------------
# Sponsor and sub-sponsor panels
# --------------------------------------------------------------------------

def test_the_user_directory_shows_what_authority_each_person_holds(api, super_admin,
                                                                   pandal_admin, pandal):
    api.force_authenticate(super_admin)

    response = api.get(reverse("admin-user-list"), {"admins_only": "true"})

    assert response.status_code == 200
    rows = {r["phone"]: r for r in response.json()["results"]}
    assert rows[pandal_admin.phone]["grants"] == [f"Pandal Admin · {pandal.name}"]
    assert rows[super_admin.phone]["grants"] == ["Super Admin"]


def test_the_user_directory_is_searchable_by_phone(api, super_admin, pandal_admin):
    api.force_authenticate(super_admin)

    response = api.get(reverse("admin-user-list"), {"q": pandal_admin.phone[-6:]})

    assert [r["phone"] for r in response.json()["results"]] == [pandal_admin.phone]


def test_the_user_directory_is_closed_to_a_pandal_admin(api, pandal_admin):
    """A committee has no business browsing the platform's whole user table."""
    api.force_authenticate(pandal_admin)

    assert api.get(reverse("admin-user-list")).status_code == 403


# --------------------------------------------------------------------------
# Onboarding a committee, and a committee running its own site
# --------------------------------------------------------------------------

def test_onboarding_a_pandal_gives_it_a_working_page_not_a_blank_one(api, super_admin, city):
    """A committee that opens a blank subdomain has no idea which of twenty
    things to fill in first."""
    api.force_authenticate(super_admin)

    response = api.post(reverse("admin-pandal-list"),
                        {"name": "Shobhabazar Rajbari", "city": str(city.id)}, format="json")

    assert response.status_code == 201, response.content
    new = Pandal.objects.get(pk=response.json()["id"])
    assert new.slug == "shobhabazar-rajbari"
    assert hasattr(new, "brand")
    assert {b.kind for b in new.blocks.all()} == {b["kind"] for b in page_blocks.BLOCKS}
    # Starter copy names the committee, so it reads as theirs and asks to be replaced.
    assert new.name in new.blocks.get(kind="hero").content["headline"]


def test_two_pandals_with_the_same_name_get_different_addresses(api, super_admin, city):
    api.force_authenticate(super_admin)
    payload = {"name": "Sarbojanin Durgotsab", "city": str(city.id)}

    first = api.post(reverse("admin-pandal-list"), payload, format="json").json()
    second = api.post(reverse("admin-pandal-list"), payload, format="json").json()

    assert first["slug"] == "sarbojanin-durgotsab"
    assert second["slug"] == "sarbojanin-durgotsab-2"


def test_a_committee_cannot_move_its_own_subdomain(api, pandal_admin, pandal):
    """People have been given the address. Changing it is a rename with a
    redirect, not a field edit."""
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-pandal-detail", args=[pandal.id]),
                         {"slug": "somewhere-else"}, format="json")

    assert response.status_code == 422
    pandal.refresh_from_db()
    assert pandal.slug == "ballygunge-cultural"


def test_a_committee_edits_its_own_colours(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-pandal-brand", args=[pandal.id]),
                         {"primary_colour": "#7A1F2B", "accent_colour": "#E8C39E"},
                         format="json")

    assert response.status_code == 200
    assert response.json()["primary_colour"] == "#7A1F2B"


def test_a_colour_that_is_not_a_colour_is_refused(api, pandal_admin, pandal):
    """These land in the page as CSS custom properties — a typo is a page with
    no colour at all, and the committee sees it before anybody tells them."""
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-pandal-brand", args=[pandal.id]),
                         {"primary_colour": "maroon-ish"}, format="json")

    assert response.status_code == 422
    assert "primary_colour" in response.json()["error"]["fields"]


def test_a_committee_writes_its_own_page_text(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-pandal-block", args=[pandal.id, "hero"]),
                         {"content": {"headline": "Our seventy-fifth year",
                                      "standfirst": "Come and see."}}, format="json")

    assert response.status_code == 200
    assert PageBlock.objects.get(pandal=pandal, kind="hero").content["headline"] == \
        "Our seventy-fifth year"


def test_editing_a_block_the_page_does_not_have_yet_creates_it(api, pandal_admin, pandal):
    """Asking a committee to 'add a block' before they can write in it would be
    our storage leaking into their afternoon."""
    api.force_authenticate(pandal_admin)
    assert not PageBlock.objects.filter(pandal=pandal, kind="closing_cta").exists()

    response = api.patch(reverse("admin-pandal-block", args=[pandal.id, "closing_cta"]),
                         {"content": {"headline": "See you there."}}, format="json")

    assert response.status_code == 200
    assert PageBlock.objects.filter(pandal=pandal, kind="closing_cta").exists()


def test_a_block_cannot_hold_content_nothing_renders(api, pandal_admin, pandal):
    """Content nobody renders is content nobody maintains."""
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-pandal-block", args=[pandal.id, "hero"]),
                         {"content": {"headline": "Fine", "invented_field": "nope"}},
                         format="json")

    assert response.status_code == 422
    assert "invented_field" in response.json()["error"]["fields"]["content"]


def test_the_editor_is_told_what_every_block_is_made_of(api, pandal_admin):
    """The schema is served rather than hard-coded in the client, so a new
    field is one entry instead of an edit in three files."""
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-pandal-page-schema")).json()

    hero = next(b for b in body if b["kind"] == "hero")
    assert {f["key"] for f in hero["fields"]} >= {"headline", "standfirst", "eyebrow"}


def test_a_committee_hides_a_section_of_its_page(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    api.patch(reverse("admin-pandal-block", args=[pandal.id, "about"]),
              {"is_visible": False}, format="json")

    assert PageBlock.objects.get(pandal=pandal, kind="about").is_visible is False


def test_onboarding_grants_the_committee_a_way_into_its_own_console(api, super_admin, city):
    """A site with no door is not an onboarded committee."""
    api.force_authenticate(super_admin)
    created = api.post(reverse("admin-pandal-list"),
                       {"name": "Bagbazar", "city": str(city.id)}, format="json").json()

    response = api.post(reverse("admin-staff-list"), {
        "phone": "+919812340000", "role": "pandal_admin", "pandal": created["id"],
    }, format="json")

    assert response.status_code == 201, response.content
    # The account did not exist; sign-in is by code, so the number is the invitation.
    granted = User.objects.get(phone="+919812340000")
    assert granted.memberships.get().pandal_id == uuid.UUID(created["id"])


def test_a_committee_adds_its_own_people(api, pandal_admin, pandal):
    """The alternative is a support ticket every time a volunteer joins, which
    is how one login ends up shared by nine people."""
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-staff-list"), {
        "phone": "+919812340001", "role": "pandal_admin", "pandal": str(pandal.id),
    }, format="json")

    assert response.status_code == 201


def test_a_committee_cannot_grant_itself_more_than_it_has(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-staff-list"), {
        "phone": "+919812340002", "role": "super_admin",
    }, format="json")

    assert response.status_code == 422


def test_a_committee_cannot_add_people_to_somebody_elses_pandal(api, pandal_admin,
                                                                other_pandal):
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-staff-list"), {
        "phone": "+919812340003", "role": "pandal_admin", "pandal": str(other_pandal.id),
    }, format="json")

    assert response.status_code == 422


def test_a_committee_sees_its_own_staff_not_the_platforms(api, pandal_admin, pandal,
                                                          super_admin):
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-staff-list")).json()["results"]

    assert {row["user_phone"] for row in body} == {pandal_admin.phone}


def test_nobody_can_remove_their_own_access(api, pandal_admin, pandal):
    """The alternative is a committee locking itself out on a Friday night."""
    api.force_authenticate(pandal_admin)
    mine = pandal_admin.memberships.first()

    response = api.delete(reverse("admin-staff-detail", args=[mine.id]))

    assert response.status_code == 422
    assert pandal_admin.memberships.filter(pk=mine.pk).exists()


def test_a_fresh_deployment_has_somewhere_to_put_a_pandal(db):
    """An empty city table means the onboarding form has nothing to choose
    from, so a new deployment cannot onboard anybody at all."""
    from django.core.management import call_command

    from apps.geo.models import City, Locality

    call_command("seed_geo")

    assert City.objects.filter(name="Kolkata").exists()
    assert Locality.objects.filter(city__name="Kolkata", name="Ballygunge").exists()


def test_seeding_places_twice_adds_nothing(db):
    """It runs on every deploy."""
    from django.core.management import call_command

    from apps.geo.models import Locality

    call_command("seed_geo")
    before = Locality.objects.count()
    call_command("seed_geo")

    assert Locality.objects.count() == before


def test_cities_and_localities_are_offered_as_a_picker(api, super_admin, city, locality):
    """Onboarding should not be a request to go and find two UUIDs."""
    api.force_authenticate(super_admin)

    body = api.get(reverse("admin-city-list")).json()["results"]

    assert body[0]["name"] == "Kolkata"
    assert [loc["name"] for loc in body[0]["localities"]] == ["Ballygunge"]


def test_a_super_admin_adds_a_locality_that_does_not_exist_yet(api, super_admin, city):
    api.force_authenticate(super_admin)

    response = api.post(reverse("admin-locality-list"),
                        {"name": "Shyambazar", "city": str(city.id)}, format="json")

    assert response.status_code == 201


def test_a_pandal_admin_cannot_invent_a_locality(api, pandal_admin, city):
    api.force_authenticate(pandal_admin)

    assert api.post(reverse("admin-locality-list"),
                    {"name": "Nowhere", "city": str(city.id)}, format="json").status_code == 403


# --------------------------------------------------------------------------
# Services: a pandal writes its own forms
# --------------------------------------------------------------------------

def test_a_new_service_starts_with_a_usable_form(api, pandal_admin, pandal):
    """An admin who has typed a name and a price should not then discover the
    service cannot be booked because it asks nothing."""
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-service-list"), {
        "pandal": str(pandal.id), "name": "Bhog Coupon", "slug": "bhog-coupon",
        "price_paise": 12000, "template": "blank",
    }, format="json")

    assert response.status_code == 201, response.content
    assert [f["key"] for f in response.json()["form"]] == ["name", "contact_phone"]


def test_a_pandal_invents_a_service_the_platform_never_heard_of(api, pandal_admin, pandal):
    """The whole point: no enum, no migration, no ceiling."""
    api.force_authenticate(pandal_admin)
    created = api.post(reverse("admin-service-list"), {
        "pandal": str(pandal.id), "name": "Dhunuchi Naach Registration",
        "slug": "dhunuchi-naach", "price_paise": 20000, "type": "Competition",
    }, format="json").json()

    added = api.post(reverse("admin-service-field-list"), {
        "service": created["id"], "key": "age_group", "label": "Age group",
        "kind": "select", "options": ["Under 12", "12-18", "Adult"], "required": True,
    }, format="json")

    assert added.status_code == 201, added.content
    detail = api.get(reverse("admin-service-detail", args=[created["id"]])).json()
    assert "age_group" in [f["key"] for f in detail["form"]]
    assert detail["type"] == "Competition"


def test_a_choose_one_question_needs_options(api, pandal_admin, service):
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-service-field-list"), {
        "service": str(service.id), "key": "size", "label": "Size", "kind": "select",
    }, format="json")

    assert response.status_code == 422
    assert "options" in response.json()["error"]["fields"]


def test_a_questions_key_cannot_change_once_bookings_answer_under_it(api, pandal_admin,
                                                                      service):
    api.force_authenticate(pandal_admin)
    field = service.fields.get(key="notes")

    response = api.patch(reverse("admin-service-field-detail", args=[field.id]),
                         {"key": "remarks"}, format="json")

    assert response.status_code == 422
    assert "key" in response.json()["error"]["fields"]


def test_a_questions_label_is_free_to_change(api, pandal_admin, service):
    """The label is what a visitor reads; only the key is load-bearing."""
    api.force_authenticate(pandal_admin)
    field = service.fields.get(key="notes")

    response = api.patch(reverse("admin-service-field-detail", args=[field.id]),
                         {"label": "Anything we should know before you arrive"}, format="json")

    assert response.status_code == 200
    field.refresh_from_db()
    assert field.label == "Anything we should know before you arrive"


def test_a_pandal_cannot_edit_another_pandals_form(api, pandal_admin, other_pandal):
    theirs = Service.objects.create(pandal=other_pandal, name="Theirs", slug="theirs",
                                    price_paise=0)
    field = ServiceField.objects.create(service=theirs, key="name", label="Name")
    api.force_authenticate(pandal_admin)

    response = api.patch(reverse("admin-service-field-detail", args=[field.id]),
                         {"label": "Hijacked"}, format="json")

    assert response.status_code == 404


def test_the_templates_are_offered_as_starting_points(api, pandal_admin):
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-service-templates")).json()

    slugs = [t["slug"] for t in body]
    assert "blank" in slugs and "puja-in-your-name" in slugs
    # One of them exists precisely to show that a service need not have capacity.
    assert any(t["requires_capacity"] is False for t in body)


def test_reordering_the_form_changes_the_order_questions_are_asked(api, pandal_admin, service):
    api.force_authenticate(pandal_admin)

    response = api.put(reverse("admin-service-reorder", args=[service.id]),
                       {"keys": ["notes", "party_size", "name"]}, format="json")

    assert [f["key"] for f in response.json()] == ["notes", "party_size", "name"]


# --------------------------------------------------------------------------
# Passes
# --------------------------------------------------------------------------

def test_a_pandal_admin_defines_its_own_pass_categories(api, pandal_admin, pandal):
    """Sponsor, VIP, Para Pass, Senior Citizen — invented by the pandal, no
    migration (D4)."""
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-pass-category-list"), {
        "pandal": str(pandal.id), "name": "Para Pass", "slug": "para-pass",
    }, format="json")

    assert response.status_code == 201, response.content
    assert response.json()["name"] == "Para Pass"


def test_a_city_pass_configuration_may_not_carry_a_time(api, pandal_admin, pandal,
                                                        donor_category):
    """D3, refused with the field named rather than as an IntegrityError."""
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-pass-config-list"), {
        "pandal": str(pandal.id), "category": str(donor_category.id), "product": "city",
        "from_date": "2026-10-10", "to_date": "2026-10-14", "from_time": "18:00",
        "price_paise": 100000,
    }, format="json")

    assert response.status_code == 422
    assert "from_time" in response.json()["error"]["fields"]


def test_every_edit_to_the_configuration_grid_is_journalled(api, pandal_admin, pandal,
                                                            donor_category, pandal_day):
    """FR-058: the question after the Puja is always what it was selling for on
    Ashtami, and the row only knows what it says today."""
    api.force_authenticate(pandal_admin)
    created = api.post(reverse("admin-pass-config-list"), {
        "pandal": str(pandal.id), "category": str(donor_category.id), "product": "individual",
        "from_date": "2026-10-10", "to_date": "2026-10-14", "price_paise": 30000,
    }, format="json").json()

    api.patch(reverse("admin-pass-config-detail", args=[created["id"]]),
              {"price_paise": 45000}, format="json")

    changes = api.get(reverse("admin-pass-config-changes", args=[created["id"]])).json()
    assert [c["action"] for c in changes] == ["updated", "created"]
    assert changes[0]["snapshot"]["price_paise"] == 45000
    assert changes[1]["snapshot"]["price_paise"] == 30000


def test_day_capacity_is_set_as_a_range(api, pandal_admin, pandal):
    api.force_authenticate(pandal_admin)

    response = api.put(reverse("admin-pandal-day-capacity", args=[pandal.id]), {
        "days": [{"date": "2026-10-10", "capacity": 8000},
                 {"date": "2026-10-11", "capacity": 8000}],
    }, format="json")

    assert response.status_code == 200
    assert [d["capacity"] for d in response.json()] == [8000, 8000]
    assert [d["available"] for d in response.json()] == [8000, 8000]


def test_capacity_cannot_be_cut_below_what_is_already_issued(api, pandal_admin, pandal,
                                                             pandal_day):
    pandal_day.issued_count = 40
    pandal_day.save(update_fields=["issued_count"])
    api.force_authenticate(pandal_admin)

    response = api.put(reverse("admin-pandal-day-capacity", args=[pandal.id]),
                       {"days": [{"date": "2026-10-12", "capacity": 10}]}, format="json")

    assert response.status_code == 422
    assert "40" in response.json()["error"]["message"]


def test_a_pandal_admin_sees_passes_covering_its_own_pandal_only(api, pandal_admin, pandal,
                                                                 other_pandal, donor_category):
    mine = Pass.objects.create(product="individual", category=donor_category)
    PassLeg.objects.create(issued_pass=mine, pandal=pandal, visit_date=dt.date(2026, 10, 12))
    theirs = Pass.objects.create(product="individual", category=donor_category)
    PassLeg.objects.create(issued_pass=theirs, pandal=other_pandal,
                           visit_date=dt.date(2026, 10, 12))
    api.force_authenticate(pandal_admin)

    response = api.get(reverse("admin-pass-list"))

    assert [p["pass_code"] for p in response.json()["results"]] == [mine.pass_code]


def test_the_entry_log_is_scoped_through_the_gate_to_the_pandal(api, pandal_admin, pandal,
                                                                other_pandal):
    mine = Gate.objects.create(pandal=pandal, name="Gate 1")
    theirs = Gate.objects.create(pandal=other_pandal, name="Gate 1")
    ScanEvent.objects.create(gate=mine, result="invalid", scanned_at=timezone.now())
    ScanEvent.objects.create(gate=theirs, result="invalid", scanned_at=timezone.now())
    api.force_authenticate(pandal_admin)

    response = api.get(reverse("admin-scan-list"))

    assert [r["gate"] for r in response.json()["results"]] == [str(mine.id)]


def test_a_sponsor_issuing_with_a_date_mints_real_passes_and_takes_capacity(
        api, sponsor_admin, sponsor, pandal, donor_category, pandal_day):
    """A sponsor's guest occupies a place at the gate exactly like a paying
    visitor (D2)."""
    pool = Pool.objects.create(organisation=sponsor, pandal=pandal, granted=100)
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-pool-issue", args=[pool.id]), {
        "quantity": 5, "visit_date": "2026-10-12", "distributed_to": "Staff",
    }, format="json")

    assert response.status_code == 200, response.content
    assert response.json()["issued"] == 5
    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 5
    assert Pass.objects.filter(source="sponsor_pool").count() == 5
    # Usable at a gate straight away: no payment to wait for.
    assert LegSecret.objects.count() == 5


def test_a_sponsor_issuing_without_a_date_only_moves_the_counter(
        api, sponsor_admin, sponsor, pandal, pandal_day):
    """A sponsor distributing off-platform wants the quota moved, not passes."""
    pool = Pool.objects.create(organisation=sponsor, pandal=pandal, granted=100)
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-pool-issue", args=[pool.id]),
                        {"quantity": 5, "distributed_to": "Handed out on paper"}, format="json")

    assert response.json()["issued"] == 5
    pandal_day.refresh_from_db()
    assert pandal_day.issued_count == 0
    assert Pass.objects.count() == 0


def test_the_pass_summary_totals_what_the_screen_shows(api, pandal_admin, pandal,
                                                       donor_category, pandal_day):
    issued = Pass.objects.create(product="individual", category=donor_category)
    PassLeg.objects.create(issued_pass=issued, pandal=pandal, visit_date=dt.date(2026, 10, 12))
    api.force_authenticate(pandal_admin)

    body = api.get(reverse("admin-pass-summary")).json()

    assert body["capacity"] == 2000
    assert body["legs_pending"] == 1
    assert body["by_category"] == [{"category": "Donor", "count": 1}]


def test_a_sponsor_admin_cannot_reach_the_pass_configuration_grid(api, sponsor_admin):
    api.force_authenticate(sponsor_admin)

    assert api.get(reverse("admin-pass-config-list")).status_code == 403


def test_a_sponsor_sees_a_pool_per_pandal_and_a_rollup(api, sponsor_admin, sponsor,
                                                        pandal, other_pandal):
    """D6: the single aggregate figure is a rollup, not a balance."""
    from apps.sponsorship import operations

    for target, count in [(pandal, 100), (other_pandal, 60)]:
        allocation = PoolAllocation.objects.create(pandal=target, organisation=sponsor,
                                                   pass_count=count)
        operations.accept_allocation(allocation_id=allocation.pk)
    api.force_authenticate(sponsor_admin)

    body = api.get(reverse("admin-sponsor-overview")).json()

    assert len(body["pools"]) == 2
    assert body["totals"] == {"granted": 160, "transferred_out": 0,
                              "issued": 0, "available": 160}


def test_accepting_an_allocation_credits_the_pool(api, sponsor_admin, sponsor, pandal):
    allocation = PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                                pass_count=100)
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-allocation-accept", args=[allocation.id]))

    assert response.status_code == 200
    assert response.json()["available"] == 100
    allocation.refresh_from_db()
    assert allocation.status == PoolAllocation.Status.ACCEPTED


def test_a_sponsor_cannot_accept_somebody_elses_allocation(api, sponsor_admin, pandal):
    stranger = Organisation.objects.create(name="Stranger", slug="stranger")
    allocation = PoolAllocation.objects.create(pandal=pandal, organisation=stranger,
                                                pass_count=50)
    api.force_authenticate(sponsor_admin)

    assert api.post(reverse("admin-allocation-accept",
                            args=[allocation.id])).status_code == 404


def test_a_sponsor_creates_a_sub_sponsor_and_sells_down_to_it(api, sponsor_admin,
                                                               sponsor, pandal):
    from apps.sponsorship import operations
    from apps.sponsorship.models import Pool

    allocation = PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                                pass_count=100)
    pool = operations.accept_allocation(allocation_id=allocation.pk)
    api.force_authenticate(sponsor_admin)

    created = api.post(reverse("admin-organisation-list"),
                       {"name": "Kolkata Sweets Corner", "slug": "kolkata-sweets",
                        "parent": str(sponsor.id)}, format="json")
    assert created.status_code == 201

    response = api.post(reverse("admin-pool-transfer", args=[pool.id]),
                        {"to_organisation": created.json()["id"], "quantity": 40,
                         "price_per_pass_paise": 10_000}, format="json")

    assert response.status_code == 201
    assert response.json()["from"]["available"] == 60
    assert response.json()["to"]["granted"] == 40
    assert Pool.objects.count() == 2


def test_a_sponsor_cannot_create_a_sub_sponsor_under_someone_else(api, sponsor_admin):
    stranger = Organisation.objects.create(name="Stranger", slug="stranger-2")
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-organisation-list"),
                        {"name": "Cheeky", "slug": "cheeky", "parent": str(stranger.id)},
                        format="json")

    assert response.status_code == 422


def test_a_transfer_beyond_the_pool_is_refused_with_the_number_left(api, sponsor_admin,
                                                                    sponsor, pandal):
    from apps.sponsorship import operations

    allocation = PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                                pass_count=10)
    pool = operations.accept_allocation(allocation_id=allocation.pk)
    child = Organisation.objects.create(name="Child", slug="child", parent=sponsor)
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-pool-transfer", args=[pool.id]),
                        {"to_organisation": str(child.id), "quantity": 50}, format="json")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "pool_exhausted"
    assert response.json()["error"]["available"] == 10


# --------------------------------------------------------------------------
# Branding entitlement — D8
# --------------------------------------------------------------------------

@pytest.fixture
def gold_package(pandal):
    return SponsorshipPackage.objects.create(pandal=pandal, name="Gold", slug="gold",
                                              value_paise=5_000_000, pass_count=500,
                                              banner_placements=1)


def test_a_sponsor_cannot_exceed_the_placements_its_package_grants(api, sponsor_admin,
                                                                    sponsor, pandal,
                                                                    gold_package):
    """The mockup showed 'includes 2 placements · 3 in use'. That state is now
    unreachable: entitlement is enforced at upload, not caught later."""
    from apps.sponsorship import operations

    allocation = PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                                package=gold_package, pass_count=100)
    operations.accept_allocation(allocation_id=allocation.pk)
    placement = BrandingPlacement.objects.create(name="Home Screen", slug="home-screen",
                                                  price_per_week_paise=500_000)
    api.force_authenticate(sponsor_admin)

    payload = {"organisation": str(sponsor.id), "pandal": str(pandal.id),
               "placement": str(placement.id), "name": "Puja Special",
               "start_date": "2026-10-10", "end_date": "2026-10-14"}

    assert api.post(reverse("admin-creative-list"), payload, format="json").status_code == 201

    second = api.post(reverse("admin-creative-list"), {**payload, "name": "Flash Sale"},
                      format="json")
    assert second.status_code == 422
    assert "1 placement(s)" in second.json()["error"]["message"]
    assert BrandingCreative.objects.count() == 1


def test_only_a_super_admin_reviews_a_creative(api, sponsor_admin, super_admin, sponsor,
                                                pandal, gold_package):
    from apps.sponsorship import operations

    allocation = PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                                package=gold_package, pass_count=100)
    operations.accept_allocation(allocation_id=allocation.pk)
    placement = BrandingPlacement.objects.create(name="Home", slug="home")
    creative = BrandingCreative.objects.create(organisation=sponsor, pandal=pandal,
                                                placement=placement, name="Banner",
                                                start_date=dt.date(2026, 10, 10),
                                                end_date=dt.date(2026, 10, 14))

    api.force_authenticate(sponsor_admin)
    assert api.post(reverse("admin-creative-review", args=[creative.id]),
                    {"decision": "approved"}, format="json").status_code == 422

    api.force_authenticate(super_admin)
    response = api.post(reverse("admin-creative-review", args=[creative.id]),
                        {"decision": "approved"}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


# --------------------------------------------------------------------------
# Platform dashboard
# --------------------------------------------------------------------------

def test_the_platform_dashboard_is_super_admin_only(api, pandal_admin, super_admin):
    api.force_authenticate(pandal_admin)
    assert api.get(reverse("admin-dashboard")).status_code == 403

    api.force_authenticate(super_admin)
    assert api.get(reverse("admin-dashboard")).status_code == 200


def test_the_dashboard_counts_what_needs_attention(api, super_admin, pandal, other_pandal):
    SupportRequest.objects.create(pandal=pandal, name="A", contact_phone="+919000011111",
                                  message="help")
    api.force_authenticate(super_admin)

    body = api.get(reverse("admin-dashboard")).json()

    assert body["pandals"]["total"] == 2
    assert body["pandals"]["selling_passes"] == 0
    assert body["support"]["new"] == 1


# --------------------------------------------------------------------------
# Issuance, and a sub-sponsor buying from its parent
# --------------------------------------------------------------------------

@pytest.fixture
def live_pool(pandal, sponsor):
    from apps.sponsorship import operations

    allocation = PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                                pass_count=100)
    return operations.accept_allocation(allocation_id=allocation.pk)


def test_issuing_records_who_received_the_passes(api, sponsor_admin, live_pool):
    """Both sponsor panels list this, and until passes are rows it is the only
    account of where a pool went."""
    api.force_authenticate(sponsor_admin)

    api.post(reverse("admin-pool-issue", args=[live_pool.id]),
             {"quantity": 20, "distributed_to": "Bengal Sweets Co. Staff"}, format="json")

    body = api.get(reverse("admin-issuance-list")).json()
    assert body["results"][0]["quantity"] == 20
    assert body["results"][0]["distributed_to"] == "Bengal Sweets Co. Staff"


def test_a_sub_sponsor_buys_from_its_parent_at_the_price_its_parent_set(api, sponsor,
                                                                        live_pool, pandal):
    """It cannot choose what to pay, and it cannot buy from a pandal (FR-159)."""
    sub = Organisation.objects.create(name="Sweets", slug="sweets", parent=sponsor,
                                      price_per_pass_paise=10_000)
    sub_admin = make_admin("+919000000005", Role.SUB_SPONSOR_ADMIN, organisation=sub)
    api.force_authenticate(sub_admin)

    response = api.post(reverse("admin-sponsor-buy"),
                        {"pandal": str(pandal.id), "quantity": 25}, format="json")

    assert response.status_code == 201
    assert response.json()["granted"] == 25
    live_pool.refresh_from_db()
    assert live_pool.transferred_out == 25

    from apps.sponsorship.models import PoolTransfer
    assert PoolTransfer.objects.get().total_paise == 25 * 10_000


def test_a_sponsor_cannot_use_the_buy_endpoint(api, sponsor_admin, live_pool, pandal):
    """A sponsor is allocated passes by a pandal; it does not buy them."""
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-sponsor-buy"),
                        {"pandal": str(pandal.id), "quantity": 5}, format="json")

    assert response.status_code == 422


def test_buying_where_the_parent_holds_nothing_says_so(api, sponsor, pandal, other_pandal):
    sub = Organisation.objects.create(name="Sweets2", slug="sweets-2", parent=sponsor)
    sub_admin = make_admin("+919000000006", Role.SUB_SPONSOR_ADMIN, organisation=sub)
    api.force_authenticate(sub_admin)

    response = api.post(reverse("admin-sponsor-buy"),
                        {"pandal": str(other_pandal.id), "quantity": 5}, format="json")

    assert response.status_code == 400
    assert "holds no passes" in response.json()["error"]["message"]


def test_the_sub_sponsor_row_shows_what_it_holds_and_has_paid(api, sponsor_admin, sponsor,
                                                               live_pool, pandal):
    from apps.sponsorship import operations

    sub = Organisation.objects.create(name="Sweets3", slug="sweets-3", parent=sponsor,
                                      price_per_pass_paise=10_000)
    operations.transfer(from_pool_id=live_pool.pk, to_organisation=sub, quantity=40,
                        price_per_pass_paise=10_000)
    api.force_authenticate(sponsor_admin)

    rows = api.get(reverse("admin-organisation-list")).json()["results"]
    row = next(r for r in rows if r["name"] == "Sweets3")

    assert row["passes_held"] == 40
    assert row["paid_to_parent_paise"] == 400_000
    assert row["price_per_pass_paise"] == 10_000


def test_the_sponsor_overview_carries_what_pass_management_shows(api, sponsor_admin,
                                                                  live_pool):
    api.force_authenticate(sponsor_admin)

    body = api.get(reverse("admin-sponsor-overview")).json()

    assert "allocations" in body
    assert "issuances" in body
    assert "packages" in body


# --------------------------------------------------------------------------
# Creating a sponsor, and giving somebody a way into it
# --------------------------------------------------------------------------

def test_a_super_admin_creates_a_sponsor_and_its_first_administrator(api, super_admin):
    """The organisation and a way in, which is what the console does in one submit.

    Creating only the first is how the platform ends up with a company nobody
    can open — which is exactly what it did until this existed.
    """
    api.force_authenticate(super_admin)

    created = api.post(reverse("admin-organisation-list"),
                       {"name": "Bengal Textiles", "contact_name": "Ritu Basu",
                        "contact_phone": "+919812345678"}, format="json")
    assert created.status_code == 201
    # No slug was sent: an operator should not have to invent a unique one.
    assert created.json()["slug"] == "bengal-textiles"

    granted = api.post(reverse("admin-staff-list"),
                       {"phone": "+919812345670", "role": Role.SPONSOR_ADMIN,
                        "organisation": created.json()["id"]}, format="json")

    assert granted.status_code == 201
    membership = AdminMembership.objects.get(user__phone="+919812345670")
    assert membership.role == Role.SPONSOR_ADMIN
    assert str(membership.organisation_id) == created.json()["id"]


def test_a_second_sponsor_of_the_same_name_gets_its_own_slug(api, super_admin, sponsor):
    api.force_authenticate(super_admin)

    response = api.post(reverse("admin-organisation-list"),
                        {"name": "Sponsor One"}, format="json")

    assert response.status_code == 201
    assert response.json()["slug"] == "sponsor-one-2"


def test_a_sponsor_gives_its_own_sub_sponsor_a_way_in(api, sponsor_admin, sponsor):
    api.force_authenticate(sponsor_admin)
    child = api.post(reverse("admin-organisation-list"),
                     {"name": "Kolkata Sweets", "parent": str(sponsor.id)},
                     format="json").json()

    response = api.post(reverse("admin-staff-list"),
                        {"phone": "+919812345671", "role": Role.SUB_SPONSOR_ADMIN,
                         "organisation": child["id"]}, format="json")

    assert response.status_code == 201
    assert AdminMembership.objects.get(
        user__phone="+919812345671").role == Role.SUB_SPONSOR_ADMIN


def test_a_sponsor_cannot_give_somebody_elses_sub_sponsor_a_way_in(api, sponsor_admin):
    stranger = Organisation.objects.create(name="Stranger Co", slug="stranger-co")
    theirs = Organisation.objects.create(name="Their Sub", slug="their-sub", parent=stranger)
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-staff-list"),
                        {"phone": "+919812345672", "role": Role.SUB_SPONSOR_ADMIN,
                         "organisation": str(theirs.id)}, format="json")

    assert response.status_code == 422
    assert not AdminMembership.objects.filter(user__phone="+919812345672").exists()


def test_a_sponsor_cannot_promote_itself_by_granting_a_role(api, sponsor_admin, sponsor):
    """The check is on the parent, so access only ever flows downward."""
    api.force_authenticate(sponsor_admin)

    response = api.post(reverse("admin-staff-list"),
                        {"phone": sponsor_admin.phone, "role": Role.SUB_SPONSOR_ADMIN,
                         "organisation": str(sponsor.id)}, format="json")

    assert response.status_code == 422


def test_a_sponsor_sees_the_access_it_granted_to_a_sub_sponsor(api, sponsor_admin, sponsor):
    child = Organisation.objects.create(name="Sweets Four", slug="sweets-four", parent=sponsor)
    make_admin("+919812345673", Role.SUB_SPONSOR_ADMIN, organisation=child)
    api.force_authenticate(sponsor_admin)

    rows = api.get(reverse("admin-staff-list")).json()["results"]

    assert any(row["user_phone"] == "+919812345673" for row in rows)


def test_a_pandal_admin_still_cannot_grant_a_sponsor_role(api, pandal_admin, sponsor):
    api.force_authenticate(pandal_admin)

    response = api.post(reverse("admin-staff-list"),
                        {"phone": "+919812345674", "role": Role.SPONSOR_ADMIN,
                         "organisation": str(sponsor.id)}, format="json")

    assert response.status_code == 422


@pytest.mark.parametrize("role,scope", [
    (Role.PANDAL_ADMIN, "pandal"),
    (Role.SPONSOR_ADMIN, "organisation"),
    (Role.SUB_SPONSOR_ADMIN, "organisation"),
    (Role.SUPER_ADMIN, None),
])
def test_a_super_admin_grants_every_role_the_people_pane_offers(api, super_admin, pandal,
                                                                 sponsor, role, scope):
    """The People pane offers four roles, so the API has to accept four.

    A Super Admin is not constrained on *which* entity — that check exists only
    for the narrower callers — so both sponsor roles point at the same
    organisation here, and the super admin role at nothing at all.
    """
    api.force_authenticate(super_admin)
    body = {"phone": "+919812345680", "role": role}
    if scope == "pandal":
        body["pandal"] = str(pandal.id)
    elif scope == "organisation":
        body["organisation"] = str(sponsor.id)

    response = api.post(reverse("admin-staff-list"), body, format="json")

    assert response.status_code == 201
    membership = AdminMembership.objects.get(user__phone="+919812345680")
    assert membership.role == role
    # The account did not exist a moment ago: granting access creates it, which
    # is what lets the People pane hand a role to somebody's number directly.
    assert membership.user.phone == "+919812345680"
