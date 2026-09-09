"""Pass inventory model.

Passes move down an ownership chain: a slot's capacity is a root pool, a sponsor
allocation is a child pool, a sub-sponsor purchase is a grandchild. Depth is not
encoded in the schema (ADR-003); a pool simply has an optional parent.

Two operations act on pools and only two -- transfer (recursive, moves capacity
between pools) and issue (terminal, converts capacity into a pass held by a
person). Both live in operations.py. Nothing outside that module may write to
the counters on this model.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


class Pandal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Slot(models.Model):
    """A bookable window at a pandal. Its capacity is the root of a pool tree."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pandal = models.ForeignKey(Pandal, on_delete=models.PROTECT, related_name="slots")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    def __str__(self):
        return f"{self.pandal} {self.starts_at:%d %b %H:%M}"


class Organisation(models.Model):
    """A sponsor or a sub-sponsor.

    The two differ only by depth in the tree, so they are one model. A sponsor
    has no parent; a sub-sponsor's parent is the organisation it buys from.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Pool(models.Model):
    """Capacity held by one owner at one point in the ownership chain.

    ``capacity_granted`` is everything that has ever moved in: the slot capacity
    for a root pool, the sum of transfers in for a child. ``transferred_out`` and
    ``issued`` are everything that has ever moved out. Holds are not counted here
    -- they are rows in Hold, because a counter can drift and a row cannot.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    depth = models.PositiveSmallIntegerField(default=0)

    # Exactly one of these is set. A root pool belongs to a slot; every other
    # pool belongs to an organisation and has a parent.
    slot = models.OneToOneField(
        Slot, null=True, blank=True, on_delete=models.PROTECT, related_name="pool"
    )
    organisation = models.ForeignKey(
        Organisation, null=True, blank=True, on_delete=models.PROTECT, related_name="pools"
    )

    # Denormalised root slot, so the gate can find a pass's slot without walking
    # the tree. Set on creation and never changed.
    root_slot = models.ForeignKey(
        Slot, on_delete=models.PROTECT, related_name="descendant_pools"
    )

    capacity_granted = models.PositiveIntegerField(default=0)
    transferred_out = models.PositiveIntegerField(default=0)
    issued = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # The invariant, enforced by the database as well as by the code.
            # A bug in operations.py cannot violate this.
            models.CheckConstraint(
                condition=Q(transferred_out__lte=models.F("capacity_granted") - models.F("issued")),
                name="pool_outflow_within_capacity",
            ),
            # A pool is either a slot root or an organisation node, never both.
            models.CheckConstraint(
                condition=(
                    Q(slot__isnull=False, organisation__isnull=True, parent__isnull=True)
                    | Q(slot__isnull=True, organisation__isnull=False, parent__isnull=False)
                ),
                name="pool_is_root_or_child",
            ),
        ]
        indexes = [models.Index(fields=["root_slot"])]

    def held(self, now=None):
        """Capacity currently under an unexpired hold.

        Expired holds are excluded by the query, so the sweeper that marks them
        EXPIRED is housekeeping rather than a correctness dependency.
        """
        now = now or timezone.now()
        total = self.holds.filter(state=Hold.State.ACTIVE, expires_at__gt=now).aggregate(
            total=Sum("quantity")
        )["total"]
        return total or 0

    def available(self, now=None):
        return self.capacity_granted - self.transferred_out - self.issued - self.held(now)

    def __str__(self):
        owner = self.organisation or self.slot
        return f"Pool<{owner} depth={self.depth}>"


class Hold(models.Model):
    """A reservation of capacity with an expiry.

    A hold is a row rather than an increment on the pool, so an expired hold
    stops counting whether or not anything cleaned it up.
    """

    class State(models.TextChoices):
        ACTIVE = "ACTIVE"
        CONSUMED = "CONSUMED"
        RELEASED = "RELEASED"
        EXPIRED = "EXPIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(Pool, on_delete=models.PROTECT, related_name="holds")
    quantity = models.PositiveIntegerField()
    state = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["pool", "state", "expires_at"])]

    def is_live(self, now=None):
        now = now or timezone.now()
        return self.state == self.State.ACTIVE and self.expires_at > now


class Pass(models.Model):
    """A pass held by a person. Terminal -- a pass holds no capacity of its own."""

    class State(models.TextChoices):
        ISSUED = "ISSUED"
        CONSUMED = "CONSUMED"
        VOID = "VOID"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(Pool, on_delete=models.PROTECT, related_name="passes")
    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name="passes")

    state = models.CharField(max_length=16, choices=State.choices, default=State.ISSUED)
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_mobile = models.CharField(max_length=20, blank=True)

    issued_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["slot", "state"]),
            models.Index(fields=["pool"]),
        ]

    def __str__(self):
        return f"Pass<{self.id} {self.state}>"