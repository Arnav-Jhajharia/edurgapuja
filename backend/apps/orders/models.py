"""One order, many lines.

The single most important seam (Scope §4.1). If donations and services each got
a bespoke checkout, passes would become a third — and receipts, refunds and
revenue reporting would be written three times. Everything is a line.
"""

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel, rupees


class Order(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"

    # Null for an anonymous donation: only a purchase that has to reach a phone
    # needs to know the phone (FR-046).
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="orders")
    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.PROTECT, related_name="orders")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    subtotal_paise = models.BigIntegerField(default=0)
    platform_fee_paise = models.BigIntegerField(default=0)
    discount_paise = models.BigIntegerField(default=0)
    total_paise = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="INR")

    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    receipt_number = models.CharField(max_length=32, blank=True, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "-created_at"]),
                   models.Index(fields=["pandal", "-created_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(subtotal_paise__gte=0),
                                   name="order_subtotal_non_negative"),
            models.CheckConstraint(condition=models.Q(total_paise__gte=0),
                                   name="order_total_non_negative"),
            models.CheckConstraint(condition=models.Q(platform_fee_paise__gte=0),
                                   name="order_fee_non_negative"),
            models.CheckConstraint(condition=models.Q(discount_paise__gte=0),
                                   name="order_discount_non_negative"),
        ]

    def __str__(self) -> str:
        return f"order ₹{rupees(self.total_paise)} ({self.status})"

    def recalculate(self) -> None:
        self.subtotal_paise = sum(line.amount_paise for line in self.lines.all())
        self.total_paise = self.subtotal_paise + self.platform_fee_paise - self.discount_paise


class OrderLine(BaseModel):
    """What was bought. `kind` is what revenue is grouped by, so passes appear
    later as a new kind rather than a new report (Scope §4.5)."""

    class Kind(models.TextChoices):
        DONATION = "donation", "Donation"
        SERVICE_BOOKING = "service_booking", "Service booking"
        PASS = "pass", "Pass"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    description = models.CharField(max_length=180, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount_paise = models.BigIntegerField()
    amount_paise = models.BigIntegerField()

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0),
                                   name="order_line_quantity_positive"),
            models.CheckConstraint(condition=models.Q(amount_paise__gte=0),
                                   name="order_line_amount_non_negative"),
        ]

    def save(self, *args, **kwargs):
        self.amount_paise = self.unit_amount_paise * self.quantity
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.kind} ×{self.quantity} · ₹{rupees(self.amount_paise)}"


# Module-level aliases so drf-spectacular's ENUM_NAME_OVERRIDES can reach these
# nested choice sets; it resolves one attribute deep, not two. Without them
# every "status" field in the generated client is named Status<hash>Enum.
ORDER_STATUS_CHOICES = Order.Status.choices
