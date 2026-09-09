"""Passes.

Everything here follows decisions D1–D4 and D6 in `docs/Decisions.md`:

* **Product then category** (D4). The platform fixes three products — Individual,
  Group, City — and each pandal defines its own categories (Sponsor, VIP, Para
  Pass, Senior Citizen, Donor, anything else), which carry the price.
* **Capacity is per pandal per day** (D2), and a City Pass consumes one unit from
  each pandal it covers on its chosen date (Q3).
* **A City Pass has a date and no time** (D3).
* **The pass authorises; a short-lived code admits** (D1). The two are different
  objects with different lifetimes, and the code is generated on the visitor's
  device so that entry does not depend on mobile data in a crowd (D5).

A pool is not here: an allocation of the *right* to issue passes belongs with
the sponsorship module. `apps/passes/sponsor_issue.py` is the seam between them,
turning a pool's quota into passes that occupy real capacity.
"""

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel, rupees
from apps.inventory.models import DayCapacity, Hold


class PassProduct(models.TextChoices):
    """The shape of the thing. Fixed by the platform, not by a pandal."""

    INDIVIDUAL = "individual", "Individual"
    GROUP = "group", "Group"
    CITY = "city", "City"


class PassCategory(BaseModel):
    """Who the holder is. Defined by each pandal and extensible (D4).

    Sponsor, VIP, Para Pass, Senior Citizen, Donor — and anything else that
    pandal wants, without a migration.
    """

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="pass_categories")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "pass categories"
        constraints = [
            models.UniqueConstraint(fields=["pandal", "slug"], name="uniq_category_slug_per_pandal")
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.pandal.name}"


class PandalDayCapacity(DayCapacity):
    """A pandal's own limit for one day (D2).

    The same two abstractions and the same four operations that already serve
    services — this table is the whole of what passes add to the inventory
    layer. See `apps/passes/inventory.py`.
    """

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="day_capacities")

    class Meta:
        ordering = ("date",)
        verbose_name_plural = "pandal day capacities"
        constraints = [
            models.UniqueConstraint(fields=["pandal", "date"], name="uniq_pandal_day"),
            models.CheckConstraint(condition=models.Q(issued_count__lte=models.F("capacity")),
                                   name="pandal_day_issued_within_capacity"),
        ]

    def __str__(self) -> str:
        return f"{self.pandal.name} {self.date}: {self.issued_count}/{self.capacity}"


class PandalCapacityHold(Hold):
    day = models.ForeignKey(PandalDayCapacity, on_delete=models.CASCADE, related_name="holds")
    order = models.ForeignKey("orders.Order", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="pandal_holds")

    class Meta:
        indexes = [models.Index(fields=["day", "expires_at"])]


class PassConfig(BaseModel):
    """One row of the admin's configuration grid: what is on sale, when, at what
    price. The pandal's day capacity remains the binding ceiling; `slot_cap` is
    an optional sub-limit that v1 leaves unused."""

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="pass_configs")
    category = models.ForeignKey(PassCategory, on_delete=models.PROTECT, related_name="configs")
    product = models.CharField(max_length=12, choices=PassProduct.choices)

    from_date = models.DateField()
    to_date = models.DateField()
    # A City Pass has a date but no time (D3), so these stay null for that product.
    from_time = models.TimeField(null=True, blank=True)
    to_time = models.TimeField(null=True, blank=True)

    price_paise = models.BigIntegerField()
    max_party_size = models.PositiveSmallIntegerField(default=1)
    slot_cap = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("from_date", "from_time")
        constraints = [
            models.CheckConstraint(condition=models.Q(price_paise__gte=0),
                                   name="pass_config_price_non_negative"),
            models.CheckConstraint(condition=models.Q(to_date__gte=models.F("from_date")),
                                   name="pass_config_dates_ordered"),
            # D3, in the database rather than in a comment.
            models.CheckConstraint(
                condition=~models.Q(product=PassProduct.CITY) | models.Q(from_time__isnull=True),
                name="city_pass_has_no_time",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_product_display()} · {self.category.name} · ₹{rupees(self.price_paise)}"


class PassConfigChange(BaseModel):
    """Every edit to the grid, with the counts at that moment (FR-058)."""

    config = models.ForeignKey(PassConfig, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="changes")
    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="pass_config_changes")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=16)
    snapshot = models.JSONField(default=dict, blank=True)
    issued_count = models.PositiveIntegerField(default=0)
    remaining_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.action} · {self.created_at:%Y-%m-%d}"


def generate_pass_code() -> str:
    """Human-readable, shown to the visitor and to gate staff.

    A reference only, never an authenticator (FR-065) — but random rather than
    sequential, so the set of issued passes cannot be enumerated.
    """
    year = timezone.now().year
    return f"EDP-{year}-{secrets.randbelow(10 ** 7):07d}"


class Pass(BaseModel):
    """The durable artefact a visitor holds. It authorises; it does not admit."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        USED = "used", "Fully used"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        BLOCKED = "blocked", "Blocked"

    class Source(models.TextChoices):
        RETAIL = "retail", "Bought by the visitor"
        SPONSOR_POOL = "sponsor_pool", "Issued from a sponsor's pool"
        COMPLIMENTARY = "complimentary", "Issued without payment"

    order_line = models.OneToOneField("orders.OrderLine", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="pass_issued")
    holder = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="passes")

    product = models.CharField(max_length=12, choices=PassProduct.choices)
    category = models.ForeignKey(PassCategory, on_delete=models.PROTECT, related_name="passes")
    # 1 for Individual and City; chosen at purchase for Group (D4).
    party_size = models.PositiveSmallIntegerField(default=1)

    pass_code = models.CharField(max_length=20, unique=True, default=generate_pass_code)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.RETAIL)

    # Set when `source` is SPONSOR_POOL, so a sponsor can see what it issued.
    pool = models.ForeignKey("sponsorship.Pool", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="passes")

    issued_at = models.DateTimeField(default=timezone.now)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["holder", "status"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(party_size__gt=0),
                                   name="pass_party_size_positive"),
            # Only a Group Pass covers more than one person (D4).
            models.CheckConstraint(
                condition=models.Q(product=PassProduct.GROUP) | models.Q(party_size=1),
                name="only_group_pass_covers_many",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.pass_code} ({self.get_product_display()})"

    @property
    def pandals_visited(self) -> int:
        return self.legs.filter(state=PassLeg.State.VISITED).count()

    @property
    def pandals_covered(self) -> int:
        return self.legs.count()


class PassLeg(BaseModel):
    """One covered pandal on a pass.

    This table is why a pass cannot be a single row. A pass covers several
    pandals, each admitted independently, each with its own state and time
    (FR-051). Each leg consumes `party_size` units of that pandal's capacity on
    its visit date.
    """

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        VISITED = "visited", "Visited"
        VOID = "void", "Void"

    issued_pass = models.ForeignKey(Pass, on_delete=models.CASCADE, related_name="legs")
    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.PROTECT, related_name="pass_legs")

    visit_date = models.DateField()
    # Null for a City Pass, which has a date and no time (D3).
    slot_from = models.TimeField(null=True, blank=True)
    slot_to = models.TimeField(null=True, blank=True)

    state = models.CharField(max_length=8, choices=State.choices, default=State.PENDING)
    admitted_at = models.DateTimeField(null=True, blank=True)
    admitted_gate = models.ForeignKey("pandals.Gate", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="admissions")

    capacity_hold = models.ForeignKey(PandalCapacityHold, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="legs")

    class Meta:
        ordering = ("visit_date", "slot_from")
        indexes = [models.Index(fields=["pandal", "visit_date", "state"])]
        constraints = [
            models.UniqueConstraint(fields=["issued_pass", "pandal"], name="uniq_leg_per_pandal"),
        ]

    def __str__(self) -> str:
        return f"{self.issued_pass.pass_code} → {self.pandal.name} ({self.state})"


class LegSecret(BaseModel):
    """The key a device derives entry codes from.

    Provisioned when the pass is issued, so the phone generates a code with no
    network at all and the gate verifies it offline (D5). Without this, minting
    a code would require mobile data in a crowd of fifty thousand — which is
    precisely where it does not work.
    """

    leg = models.OneToOneField(PassLeg, on_delete=models.CASCADE, related_name="secret")
    secret = models.CharField(max_length=88, help_text="Base64 of 64 random bytes")
    provisioned_at = models.DateTimeField(default=timezone.now)
    rotated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"secret for {self.leg_id}"


class ScanEvent(BaseModel):
    """Every scan, whatever its outcome (FR-110).

    Written by the gate device — locally first, synced later — so `scanned_at`
    is the device's clock and `received_at` is ours.
    """

    class Result(models.TextChoices):
        ADMITTED = "admitted", "Admitted"
        EXPIRED = "expired", "Code expired"
        DUPLICATE = "duplicate", "Already used"
        INVALID = "invalid", "Not a valid code"
        MANUAL_OVERRIDE = "manual_override", "Admitted by exception"

    gate = models.ForeignKey("pandals.Gate", on_delete=models.PROTECT, related_name="scans")
    volunteer = models.ForeignKey("pandals.Volunteer", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="scans")
    device_id = models.CharField(max_length=80, blank=True)

    # Null when the presented code did not resolve to anything.
    leg = models.ForeignKey(PassLeg, null=True, blank=True, on_delete=models.SET_NULL,
                            related_name="scans")
    presented_code = models.CharField(max_length=64, blank=True)

    result = models.CharField(max_length=16, choices=Result.choices)
    scanned_at = models.DateTimeField(help_text="The gate device's clock")
    received_at = models.DateTimeField(null=True, blank=True, help_text="When it reached us")
    override_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-scanned_at",)
        indexes = [
            models.Index(fields=["gate", "-scanned_at"]),
            models.Index(fields=["result", "-scanned_at"]),
        ]
        constraints = [
            # One admission per leg, ever. A partial unique index is what makes
            # double admission impossible once devices have synced (FR-114).
            models.UniqueConstraint(
                fields=["leg"],
                condition=models.Q(result__in=["admitted", "manual_override"]),
                name="one_admission_per_leg",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.result} @ {self.gate} {self.scanned_at:%H:%M}"


# Module-level aliases so drf-spectacular's ENUM_NAME_OVERRIDES can reach these
# nested choice sets; it resolves one attribute deep, not two.
PASS_STATUS_CHOICES = Pass.Status.choices
LEG_STATE_CHOICES = PassLeg.State.choices
SCAN_RESULT_CHOICES = ScanEvent.Result.choices
