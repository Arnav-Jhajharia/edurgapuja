"""Sponsorship, pass pools and branding.

The shape follows D6: **a pool belongs to an (organisation, pandal) pair.** A
sponsor holding packages at five pandals holds five pools, and the console shows
them separately and as a rollup. The single aggregate figure in the client's
mockup is a rollup, not a balance.

Sponsor and sub-sponsor are the same shape and differ only by `parent`, so the
hierarchy is a tree in one table rather than two near-identical models.
"""

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel, rupees


class Organisation(BaseModel):
    """A sponsor, or a sub-sponsor of one.

    `parent` is what distinguishes them. A sub-sponsor buys only from its parent
    and never directly from a pandal (FR-159), which `operations.transfer`
    enforces.
    """

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="children")

    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    # What this organisation's parent charges it per pass. Set by the sponsor
    # when it creates a sub-sponsor, and what "Buy passes" then costs.
    price_per_pass_paise = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    @property
    def is_sub_sponsor(self) -> bool:
        return self.parent_id is not None

    @property
    def depth(self) -> int:
        """0 for a sponsor, 1 for a sub-sponsor, and so on.

        Whether a sub-sponsor may itself create sub-sponsors is still open
        (Q-164), so the model permits any depth and the policy limit lives in
        settings.
        """
        depth, node = 0, self
        while node.parent_id is not None:
            depth += 1
            node = node.parent
        return depth


class SponsorshipPackage(BaseModel):
    """What a pandal offers a sponsor: passes, branding and benefits (FR-150)."""

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="sponsorship_packages")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    value_paise = models.BigIntegerField()
    pass_count = models.PositiveIntegerField(default=0)
    banner_placements = models.PositiveSmallIntegerField(default=0)
    benefits = models.TextField(blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-value_paise", "name")
        constraints = [
            models.UniqueConstraint(fields=["pandal", "slug"], name="uniq_package_slug_per_pandal"),
            models.CheckConstraint(condition=models.Q(value_paise__gte=0),
                                   name="package_value_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.pandal.name} · ₹{rupees(self.value_paise)}"


class Pool(BaseModel):
    """A right to issue passes, held by one organisation at one pandal (D6).

    Three counters: everything in, and the two ways out. The constraint below is
    the invariant the whole hierarchy rests on (FR-163) — enforced by Postgres,
    not by the code that maintains it.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="pools")
    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.PROTECT, related_name="pools")
    # Null for a sponsor's pool; set for a sub-sponsor's, pointing at where its
    # passes came from.
    parent_pool = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="child_pools")

    granted = models.PositiveIntegerField(default=0)
    transferred_out = models.PositiveIntegerField(default=0)
    issued = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("organisation__name",)
        constraints = [
            models.UniqueConstraint(fields=["organisation", "pandal"],
                                    name="uniq_pool_per_org_per_pandal"),
            models.CheckConstraint(
                condition=models.Q(transferred_out__lte=models.F("granted") - models.F("issued")),
                name="pool_outflow_within_grant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organisation.name} @ {self.pandal.name}: {self.available}/{self.granted}"

    @property
    def available(self) -> int:
        return self.granted - self.transferred_out - self.issued


class PoolAllocation(BaseModel):
    """A pandal granting passes to a sponsor.

    Pending until the sponsor accepts, and the passes are unusable before that
    (FR-152) — which is why acceptance, not allocation, is what credits the pool.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending acceptance"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.PROTECT,
                               related_name="pool_allocations")
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT,
                                     related_name="allocations")
    package = models.ForeignKey(SponsorshipPackage, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="allocations")
    pool = models.ForeignKey(Pool, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="allocations")

    pass_count = models.PositiveIntegerField()
    value_paise = models.BigIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["organisation", "status"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(pass_count__gt=0),
                                   name="allocation_count_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.pass_count} to {self.organisation.name} ({self.status})"


class PoolTransfer(BaseModel):
    """A sponsor selling passes down to a sub-sponsor, at a price it sets.

    The money moves through the platform (D6/FR-160), so a transfer carries the
    order that paid for it.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting payment"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    from_pool = models.ForeignKey(Pool, on_delete=models.PROTECT, related_name="transfers_out")
    to_pool = models.ForeignKey(Pool, on_delete=models.PROTECT, related_name="transfers_in")
    quantity = models.PositiveIntegerField()
    price_per_pass_paise = models.BigIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="pool_transfers")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0),
                                   name="transfer_quantity_positive"),
        ]

    def __str__(self) -> str:
        return (f"{self.quantity} · {self.from_pool.organisation.name} → "
                f"{self.to_pool.organisation.name}")

    @property
    def total_paise(self) -> int:
        return self.quantity * self.price_per_pass_paise


class PoolIssuance(BaseModel):
    """A record of passes handed out of a pool.

    The Sponsor and Sub-Sponsor panels both list these, and until passes
    themselves are issued as rows this is the only account of where a pool went.
    """

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="issuances")
    quantity = models.PositiveIntegerField()
    distributed_to = models.CharField(max_length=180, blank=True)
    note = models.CharField(max_length=255, blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0),
                                   name="issuance_quantity_positive")
        ]

    def __str__(self) -> str:
        return f"{self.quantity} → {self.distributed_to or 'unnamed'}"


class PassRequest(BaseModel):
    """A sponsor asking a pandal for more passes (FR-157)."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        GRANTED = "granted", "Granted"
        REFUSED = "refused", "Refused"

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE,
                                     related_name="pass_requests")
    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="pass_requests")
    quantity = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.organisation.name} wants {self.quantity} at {self.pandal.name}"


class BrandingPlacement(BaseModel):
    """The closed list of places a creative may appear, priced per week (FR-170).

    Platform-level, not per pandal: a sponsor buying 'Home Screen' is buying the
    same surface everywhere, and letting each pandal invent placements would make
    entitlements unenforceable.
    """

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True)
    price_per_week_paise = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self) -> str:
        return self.name


class BrandingCreative(BaseModel):
    """One sponsor's artwork, in one placement, at one pandal, for a date range.

    Selecting several pandals for one upload creates one row per pandal
    (FR-173), so approval and expiry are decided per pandal rather than in bulk.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE,
                                     related_name="creatives")
    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="branding_creatives")
    placement = models.ForeignKey(BrandingPlacement, on_delete=models.PROTECT,
                                  related_name="creatives")

    name = models.CharField(max_length=140)
    image = models.ImageField(upload_to="branding/", null=True, blank=True)
    target_url = models.URLField(blank=True)

    start_date = models.DateField()
    end_date = models.DateField()
    price_paise = models.BigIntegerField(default=0)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["pandal", "placement", "status"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="creative_dates_ordered"),
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.placement.name} · {self.pandal.name}"

    @property
    def occupies_entitlement(self) -> bool:
        """Pending and approved both consume a placement — otherwise a sponsor
        could queue unlimited uploads and exceed its package on approval (D8)."""
        return self.status in {self.Status.PENDING, self.Status.APPROVED}


# Module-level aliases so drf-spectacular's ENUM_NAME_OVERRIDES can reach these
# nested choice sets; it resolves one attribute deep, not two. Without them
# every "status" field in the generated client is named Status<hash>Enum.
ALLOCATION_STATUS_CHOICES = PoolAllocation.Status.choices
CREATIVE_STATUS_CHOICES = BrandingCreative.Status.choices
