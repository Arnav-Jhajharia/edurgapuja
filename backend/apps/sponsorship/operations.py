"""Pool movements. Everything that changes a pool's counters goes through here.

The invariant — outflow never exceeds the grant, at every tier, under concurrent
operation (FR-163) — is enforced three times over: by the `CHECK` constraint on
`Pool`, by the row lock taken here, and by the tests.
"""

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status

from apps.common.errors import DomainError

from .models import Organisation, Pool, PoolAllocation, PoolIssuance, PoolTransfer


class PoolExhaustedError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "pool_exhausted"
    default_detail = "That pool does not have enough passes left."


class InvalidTransferError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invalid_transfer"


class AllocationNotPendingError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "allocation_not_pending"
    default_detail = "That allocation has already been answered."


def _get_or_create_pool(organisation: Organisation, pandal,
                        parent_pool: Pool | None = None) -> Pool:
    pool, _ = Pool.objects.get_or_create(
        organisation=organisation, pandal=pandal,
        defaults={"parent_pool": parent_pool},
    )
    return pool


@transaction.atomic
def accept_allocation(*, allocation_id) -> Pool:
    """Acceptance, not allocation, is what credits a pool (FR-152).

    Until this runs the passes exist only as an offer, and a sponsor's console
    shows them as pending.
    """
    allocation = PoolAllocation.objects.select_for_update().get(pk=allocation_id)
    if allocation.status != PoolAllocation.Status.PENDING:
        raise AllocationNotPendingError

    pool = _get_or_create_pool(allocation.organisation, allocation.pandal)
    locked = Pool.objects.select_for_update().get(pk=pool.pk)
    locked.granted += allocation.pass_count
    locked.save(update_fields=["granted", "updated_at"])

    allocation.status = PoolAllocation.Status.ACCEPTED
    allocation.pool = locked
    allocation.responded_at = timezone.now()
    allocation.save(update_fields=["status", "pool", "responded_at", "updated_at"])
    return locked


@transaction.atomic
def decline_allocation(*, allocation_id) -> PoolAllocation:
    allocation = PoolAllocation.objects.select_for_update().get(pk=allocation_id)
    if allocation.status != PoolAllocation.Status.PENDING:
        raise AllocationNotPendingError

    allocation.status = PoolAllocation.Status.DECLINED
    allocation.responded_at = timezone.now()
    allocation.save(update_fields=["status", "responded_at", "updated_at"])
    return allocation


@transaction.atomic
def transfer(*, from_pool_id, to_organisation: Organisation, quantity: int,
             price_per_pass_paise: int = 0, order=None) -> PoolTransfer:
    """Sell passes down one tier.

    Three rules, all enforced here rather than trusted to the caller:

    * a sub-sponsor buys only from its own parent (FR-159);
    * passes stay at the pandal they were granted for, because a pool is scoped
      to a pandal (D6);
    * the hierarchy goes no deeper than policy allows (Q-164 is open, so the
      limit is a setting rather than a schema decision).
    """
    source = Pool.objects.select_for_update().select_related("organisation", "pandal").get(
        pk=from_pool_id
    )

    if to_organisation.parent_id != source.organisation_id:
        raise InvalidTransferError(
            f"{to_organisation.name} may only buy from {source.organisation.name}."
        )
    if to_organisation.depth > settings.MAX_POOL_DEPTH:
        raise InvalidTransferError("That would nest sponsors deeper than the platform allows.")
    if quantity <= 0:
        raise InvalidTransferError("Transfer at least one pass.")
    if quantity > source.available:
        raise PoolExhaustedError(
            f"Only {source.available} pass{'es' if source.available != 1 else ''} left.",
            available=source.available,
        )

    destination = _get_or_create_pool(to_organisation, source.pandal, parent_pool=source)

    source.transferred_out += quantity
    source.save(update_fields=["transferred_out", "updated_at"])

    locked_destination = Pool.objects.select_for_update().get(pk=destination.pk)
    locked_destination.granted += quantity
    locked_destination.save(update_fields=["granted", "updated_at"])

    return PoolTransfer.objects.create(
        from_pool=source, to_pool=locked_destination, quantity=quantity,
        price_per_pass_paise=price_per_pass_paise, order=order,
        status=PoolTransfer.Status.COMPLETED, completed_at=timezone.now(),
    )


@transaction.atomic
def issue_from_pool(*, pool_id, quantity: int = 1, distributed_to: str = "",
                    issued_by=None) -> Pool:
    """Turn a pool's entitlement into issued passes.

    Only the counter moves here. Creating the `Pass` rows and consuming the
    pandal's day capacity is the caller's job, because a pool is a quota on how
    many passes may exist, not a reservation of any particular day (Assumption
    A2).
    """
    pool = Pool.objects.select_for_update().get(pk=pool_id)
    if quantity <= 0:
        raise InvalidTransferError("Issue at least one pass.")
    if quantity > pool.available:
        raise PoolExhaustedError(
            f"Only {pool.available} pass{'es' if pool.available != 1 else ''} left.",
            available=pool.available,
        )

    pool.issued += quantity
    pool.save(update_fields=["issued", "updated_at"])

    PoolIssuance.objects.create(pool=pool, quantity=quantity,
                                distributed_to=distributed_to, issued_by=issued_by)
    return pool


@transaction.atomic
def buy_from_parent(*, organisation: Organisation, pandal, quantity: int, order=None):
    """A sub-sponsor buying from its own sponsor (FR-159, FR-160).

    The price is the one its parent set when creating it, so a sub-sponsor
    cannot choose what to pay.
    """
    if organisation.parent_id is None:
        raise InvalidTransferError("Only a sub-sponsor buys passes; a sponsor is allocated them.")

    source = Pool.objects.filter(organisation_id=organisation.parent_id, pandal=pandal).first()
    if source is None:
        raise InvalidTransferError(
            f"{organisation.parent.name} holds no passes at {pandal.name} to sell you."
        )

    return transfer(from_pool_id=source.pk, to_organisation=organisation, quantity=quantity,
                    price_per_pass_paise=organisation.price_per_pass_paise, order=order)


def entitled_placements(organisation: Organisation, pandal) -> int:
    """How many branding placements this sponsor's packages grant at this pandal."""
    from .models import SponsorshipPackage

    package_ids = (PoolAllocation.objects
                   .filter(organisation=organisation, pandal=pandal,
                           status=PoolAllocation.Status.ACCEPTED)
                   .values_list("package_id", flat=True))
    return (SponsorshipPackage.objects.filter(id__in=package_ids)
            .aggregate(n=Sum("banner_placements"))["n"] or 0)
