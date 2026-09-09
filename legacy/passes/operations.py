"""The only place capacity moves.

Two operations act on pools:

    transfer(parent -> child)   recursive, moves capacity down the chain
    issue(pool -> person)       terminal, converts capacity into a Pass

Everything else here supports those two: holds, their release and expiry, and
voiding an issued pass to return capacity.

One invariant governs all of it. A pool never transfers or issues more than it
holds, and a transfer decrements the parent in the same transaction that
increments the child. Because a pool has an optional parent rather than a fixed
tier, this holds at any depth (ADR-003).

Locking: every operation takes ``select_for_update`` on the pool rows it touches
before reading availability. Transfers lock parent and child in primary-key
order so two concurrent transfers between overlapping pools cannot deadlock.
"""

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .exceptions import (
    HoldMismatch,
    HoldNotLive,
    InsufficientCapacity,
    MaxDepthExceeded,
    NotAChildPool,
    PassNotVoidable,
)
from .models import Hold, Pass, Pool

DEFAULT_HOLD_TTL_SECONDS = 15 * 60


def _max_depth():
    """Configured hierarchy depth. Set MAX_POOL_DEPTH = 2 if the client confirms
    a fixed sponsor -> sub-sponsor hierarchy. Changing it is a settings change,
    not a migration."""
    return getattr(settings, "MAX_POOL_DEPTH", 3)


def _lock(pool_id):
    return Pool.objects.select_for_update().get(pk=pool_id)


def _lock_pair(parent_id, child_id):
    """Lock two pools in a deterministic order to avoid deadlock."""
    first, second = sorted([str(parent_id), str(child_id)])
    locked = {
        str(p.id): p
        for p in Pool.objects.select_for_update().filter(pk__in=[first, second]).order_by("id")
    }
    return locked[str(parent_id)], locked[str(child_id)]


def _consume_hold_or_check(pool, quantity, hold_id, now):
    """Either draw the quantity from a live hold, or check free availability.

    Returns the Hold that was consumed, or None. The pool row must already be
    locked by the caller.
    """
    if hold_id is None:
        available = pool.available(now)
        if quantity > available:
            raise InsufficientCapacity(pool.id, quantity, available)
        return None

    hold = Hold.objects.select_for_update().get(pk=hold_id)
    if hold.pool_id != pool.id:
        raise HoldMismatch(f"hold {hold.id} is not on pool {pool.id}")
    if not hold.is_live(now):
        raise HoldNotLive(f"hold {hold.id} is {hold.state}")
    if hold.quantity < quantity:
        raise HoldMismatch(f"hold {hold.id} covers {hold.quantity}, asked {quantity}")

    hold.state = Hold.State.CONSUMED
    hold.save(update_fields=["state"])
    return hold


# --------------------------------------------------------------------------
# Pool creation
# --------------------------------------------------------------------------


@transaction.atomic
def create_root_pool(slot, capacity):
    """A slot's own capacity. The root of one pool tree."""
    return Pool.objects.create(
        slot=slot,
        root_slot=slot,
        parent=None,
        depth=0,
        capacity_granted=capacity,
    )


@transaction.atomic
def create_child_pool(parent_id, organisation):
    """An empty pool under ``parent``. Capacity arrives only by transfer."""
    parent = _lock(parent_id)
    depth = parent.depth + 1
    if depth > _max_depth():
        raise MaxDepthExceeded(f"depth {depth} exceeds max {_max_depth()}")
    return Pool.objects.create(
        parent=parent,
        organisation=organisation,
        root_slot=parent.root_slot,
        depth=depth,
        capacity_granted=0,
    )


# --------------------------------------------------------------------------
# Holds
# --------------------------------------------------------------------------


@transaction.atomic
def place_hold(pool_id, quantity, ttl_seconds=DEFAULT_HOLD_TTL_SECONDS):
    """Reserve capacity while a payment completes."""
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    now = timezone.now()
    pool = _lock(pool_id)
    available = pool.available(now)
    if quantity > available:
        raise InsufficientCapacity(pool.id, quantity, available)
    return Hold.objects.create(
        pool=pool,
        quantity=quantity,
        expires_at=now + timezone.timedelta(seconds=ttl_seconds),
    )


@transaction.atomic
def release_hold(hold_id):
    """Give the capacity back before expiry -- an abandoned checkout."""
    hold = Hold.objects.select_for_update().get(pk=hold_id)
    if hold.state != Hold.State.ACTIVE:
        return hold
    hold.state = Hold.State.RELEASED
    hold.save(update_fields=["state"])
    return hold


def expire_holds(now=None):
    """Housekeeping, run on a schedule.

    Availability already excludes expired holds by timestamp, so this only tidies
    state. Correctness does not depend on it running on time.
    """
    now = now or timezone.now()
    return Hold.objects.filter(state=Hold.State.ACTIVE, expires_at__lte=now).update(
        state=Hold.State.EXPIRED
    )


# --------------------------------------------------------------------------
# The two operations
# --------------------------------------------------------------------------


@transaction.atomic
def transfer(parent_id, child_id, quantity, hold_id=None):
    """Move capacity from a parent pool to its child.

    Used for a sponsor allocation (root -> sponsor) and for a sub-sponsor
    purchase (sponsor -> sub-sponsor). Identical code either way.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    now = timezone.now()
    parent, child = _lock_pair(parent_id, child_id)

    if child.parent_id != parent.id:
        raise NotAChildPool(f"pool {child.id} is not a child of {parent.id}")

    _consume_hold_or_check(parent, quantity, hold_id, now)

    parent.transferred_out += quantity
    child.capacity_granted += quantity
    parent.save(update_fields=["transferred_out"])
    child.save(update_fields=["capacity_granted"])
    return parent, child


@transaction.atomic
def issue(pool_id, quantity, recipient_name="", recipient_mobile="", hold_id=None):
    """Convert capacity into passes held by a person. Terminal.

    Covers a paid booking (with a hold), a complimentary pass issued by a pandal
    admin (no hold, no payment), and a sub-sponsor issuing from its own pool.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    now = timezone.now()
    pool = _lock(pool_id)

    _consume_hold_or_check(pool, quantity, hold_id, now)

    pool.issued += quantity
    pool.save(update_fields=["issued"])

    return Pass.objects.bulk_create(
        [
            Pass(
                pool=pool,
                slot=pool.root_slot,
                recipient_name=recipient_name,
                recipient_mobile=recipient_mobile,
            )
            for _ in range(quantity)
        ]
    )


@transaction.atomic
def void_pass(pass_id):
    """Return an issued pass's capacity to its pool -- a cancellation.

    A pass already consumed at a gate cannot be voided; the visit happened.
    """
    p = Pass.objects.select_for_update().get(pk=pass_id)
    if p.state != Pass.State.ISSUED:
        raise PassNotVoidable(f"pass {p.id} is {p.state}")

    pool = _lock(p.pool_id)
    p.state = Pass.State.VOID
    p.save(update_fields=["state"])

    pool.issued -= 1
    pool.save(update_fields=["issued"])
    return p