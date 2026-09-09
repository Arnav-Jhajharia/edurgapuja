"""Sponsorship, pools and branding.

The pool invariant (FR-163) is the one that matters: outflow never exceeds the
grant, at every tier, under concurrent operation.
"""

import datetime as dt
import threading

import pytest
from django.db import IntegrityError, connection, transaction

from apps.sponsorship import operations
from apps.sponsorship.models import (
    BrandingCreative,
    BrandingPlacement,
    Organisation,
    Pool,
    PoolAllocation,
    SponsorshipPackage,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def sponsor(db):
    return Organisation.objects.create(name="Sponsor One", slug="sponsor-one")


@pytest.fixture
def sub_sponsor(sponsor):
    return Organisation.objects.create(name="Kolkata Sweets Corner", slug="kolkata-sweets",
                                       parent=sponsor)


@pytest.fixture
def package(pandal):
    return SponsorshipPackage.objects.create(
        pandal=pandal, name="Gold Sponsor", slug="gold", value_paise=5_000_000,
        pass_count=500, banner_placements=2,
    )


@pytest.fixture
def allocation(pandal, sponsor, package):
    return PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                         package=package, pass_count=100)


# --------------------------------------------------------------------------
# A pool is per (organisation, pandal) — D6
# --------------------------------------------------------------------------

def test_a_sponsor_at_five_pandals_holds_five_pools(sponsor, city, locality):
    """The console's single 'remaining' figure is a rollup, not a balance."""
    from apps.pandals.models import Pandal

    for i in range(5):
        p = Pandal.objects.create(name=f"P{i}", slug=f"sp-{i}", city=city, locality=locality)
        alloc = PoolAllocation.objects.create(pandal=p, organisation=sponsor, pass_count=100)
        operations.accept_allocation(allocation_id=alloc.pk)

    assert sponsor.pools.count() == 5
    assert sum(p.available for p in sponsor.pools.all()) == 500


def test_one_organisation_has_at_most_one_pool_per_pandal(sponsor, pandal):
    Pool.objects.create(organisation=sponsor, pandal=pandal)

    with pytest.raises(IntegrityError), transaction.atomic():
        Pool.objects.create(organisation=sponsor, pandal=pandal)


# --------------------------------------------------------------------------
# Allocation is an offer until it is accepted — FR-152
# --------------------------------------------------------------------------

def test_passes_are_unusable_until_the_sponsor_accepts(allocation, sponsor, pandal):
    assert allocation.status == PoolAllocation.Status.PENDING
    assert Pool.objects.filter(organisation=sponsor, pandal=pandal).count() == 0

    pool = operations.accept_allocation(allocation_id=allocation.pk)

    allocation.refresh_from_db()
    assert allocation.status == PoolAllocation.Status.ACCEPTED
    assert allocation.responded_at is not None
    assert pool.granted == 100
    assert pool.available == 100


def test_declining_credits_nothing(allocation, sponsor, pandal):
    operations.decline_allocation(allocation_id=allocation.pk)

    allocation.refresh_from_db()
    assert allocation.status == PoolAllocation.Status.DECLINED
    assert not Pool.objects.filter(organisation=sponsor, pandal=pandal).exists()


def test_an_allocation_can_only_be_answered_once(allocation):
    operations.accept_allocation(allocation_id=allocation.pk)

    with pytest.raises(operations.AllocationNotPendingError):
        operations.accept_allocation(allocation_id=allocation.pk)
    with pytest.raises(operations.AllocationNotPendingError):
        operations.decline_allocation(allocation_id=allocation.pk)


def test_two_allocations_to_one_sponsor_accumulate(pandal, sponsor):
    for count in (100, 60):
        alloc = PoolAllocation.objects.create(pandal=pandal, organisation=sponsor,
                                              pass_count=count)
        operations.accept_allocation(allocation_id=alloc.pk)

    assert Pool.objects.get(organisation=sponsor, pandal=pandal).granted == 160


# --------------------------------------------------------------------------
# Transfers down the tier — FR-159, FR-160
# --------------------------------------------------------------------------

def test_a_sponsor_sells_down_to_its_sub_sponsor(allocation, sponsor, sub_sponsor, pandal):
    pool = operations.accept_allocation(allocation_id=allocation.pk)

    movement = operations.transfer(from_pool_id=pool.pk, to_organisation=sub_sponsor,
                                   quantity=40, price_per_pass_paise=10_000)

    pool.refresh_from_db()
    assert pool.transferred_out == 40
    assert pool.available == 60
    assert movement.to_pool.granted == 40
    assert movement.to_pool.parent_pool_id == pool.pk
    assert movement.total_paise == 400_000


def test_a_sub_sponsor_may_not_buy_from_a_stranger(allocation, sponsor, pandal):
    """FR-159: only from its own parent, never directly from a pandal."""
    pool = operations.accept_allocation(allocation_id=allocation.pk)
    unrelated = Organisation.objects.create(name="Unrelated", slug="unrelated")

    with pytest.raises(operations.InvalidTransferError):
        operations.transfer(from_pool_id=pool.pk, to_organisation=unrelated, quantity=1)


def test_a_transfer_cannot_exceed_what_is_left(allocation, sub_sponsor):
    pool = operations.accept_allocation(allocation_id=allocation.pk)
    operations.transfer(from_pool_id=pool.pk, to_organisation=sub_sponsor, quantity=90)

    with pytest.raises(operations.PoolExhaustedError) as caught:
        operations.transfer(from_pool_id=pool.pk, to_organisation=sub_sponsor, quantity=20)

    assert caught.value.extra["available"] == 10


def test_the_hierarchy_stops_where_policy_says(allocation, sub_sponsor, settings):
    """Whether a sub-sponsor may create sub-sponsors is still open (Q-164), so
    the depth limit is a setting rather than a schema decision."""
    pool = operations.accept_allocation(allocation_id=allocation.pk)
    operations.transfer(from_pool_id=pool.pk, to_organisation=sub_sponsor, quantity=50)
    sub_pool = Pool.objects.get(organisation=sub_sponsor)
    grandchild = Organisation.objects.create(name="Corner Shop", slug="corner-shop",
                                             parent=sub_sponsor)

    settings.MAX_POOL_DEPTH = 1
    with pytest.raises(operations.InvalidTransferError):
        operations.transfer(from_pool_id=sub_pool.pk, to_organisation=grandchild, quantity=5)

    settings.MAX_POOL_DEPTH = 2
    operations.transfer(from_pool_id=sub_pool.pk, to_organisation=grandchild, quantity=5)
    assert Pool.objects.get(organisation=grandchild).granted == 5


# --------------------------------------------------------------------------
# Issuance, and the invariant
# --------------------------------------------------------------------------

def test_issuing_draws_down_the_same_pool(allocation):
    pool = operations.accept_allocation(allocation_id=allocation.pk)

    operations.issue_from_pool(pool_id=pool.pk, quantity=30)

    pool.refresh_from_db()
    assert pool.issued == 30
    assert pool.available == 70


def test_transfers_and_issues_share_one_balance(allocation, sub_sponsor):
    pool = operations.accept_allocation(allocation_id=allocation.pk)
    operations.transfer(from_pool_id=pool.pk, to_organisation=sub_sponsor, quantity=60)
    operations.issue_from_pool(pool_id=pool.pk, quantity=40)

    pool.refresh_from_db()
    assert pool.available == 0

    with pytest.raises(operations.PoolExhaustedError):
        operations.issue_from_pool(pool_id=pool.pk, quantity=1)


def test_the_database_refuses_to_overdraw_a_pool_even_if_the_code_is_wrong(allocation):
    """The CHECK is the floor. No bug above it can breach the grant."""
    pool = operations.accept_allocation(allocation_id=allocation.pk)

    with pytest.raises(IntegrityError), transaction.atomic():
        Pool.objects.filter(pk=pool.pk).update(issued=101)


@pytest.mark.django_db(transaction=True)
def test_concurrent_issuance_cannot_overdraw_a_pool(city, locality):
    from apps.pandals.models import Pandal

    pandal = Pandal.objects.create(name="Pool race", slug="pool-race", city=city, locality=locality)
    org = Organisation.objects.create(name="Racer", slug="racer")
    alloc = PoolAllocation.objects.create(pandal=pandal, organisation=org, pass_count=5)
    pool = operations.accept_allocation(allocation_id=alloc.pk)

    outcomes: list[str] = []
    barrier = threading.Barrier(10)

    def contend():
        barrier.wait()
        try:
            operations.issue_from_pool(pool_id=pool.pk, quantity=1)
            outcomes.append("issued")
        except operations.PoolExhaustedError:
            outcomes.append("refused")
        finally:
            connection.close()

    threads = [threading.Thread(target=contend) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    pool.refresh_from_db()
    assert outcomes.count("issued") == 5
    assert outcomes.count("refused") == 5
    assert pool.issued == 5


# --------------------------------------------------------------------------
# Branding — FR-170 to FR-177
# --------------------------------------------------------------------------

@pytest.fixture
def home_screen(db):
    return BrandingPlacement.objects.create(name="Home Screen", slug="home-screen",
                                            price_per_week_paise=500_000)


def test_a_package_states_how_many_placements_it_grants(allocation, sponsor, pandal, package):
    operations.accept_allocation(allocation_id=allocation.pk)

    assert operations.entitled_placements(sponsor, pandal) == 2


def test_an_unaccepted_package_grants_nothing(allocation, sponsor, pandal):
    assert operations.entitled_placements(sponsor, pandal) == 0


def test_pending_and_approved_creatives_both_occupy_a_placement(sponsor, pandal, home_screen):
    """Otherwise a sponsor queues unlimited uploads and exceeds its package the
    moment they are approved (D8)."""
    made = {}
    for name, state in [("a", BrandingCreative.Status.PENDING),
                        ("b", BrandingCreative.Status.APPROVED),
                        ("c", BrandingCreative.Status.REJECTED),
                        ("d", BrandingCreative.Status.EXPIRED)]:
        made[name] = BrandingCreative.objects.create(
            organisation=sponsor, pandal=pandal, placement=home_screen, name=name,
            start_date=dt.date(2026, 10, 10), end_date=dt.date(2026, 10, 14), status=state,
        )

    assert made["a"].occupies_entitlement
    assert made["b"].occupies_entitlement
    assert not made["c"].occupies_entitlement
    assert not made["d"].occupies_entitlement


def test_a_creative_cannot_end_before_it_starts(sponsor, pandal, home_screen):
    with pytest.raises(IntegrityError), transaction.atomic():
        BrandingCreative.objects.create(
            organisation=sponsor, pandal=pandal, placement=home_screen, name="backwards",
            start_date=dt.date(2026, 10, 14), end_date=dt.date(2026, 10, 10),
        )
