"""Payment attempts against an order.

One order may have several attempts — a declined card, then a UPI retry — so the
commercial object and the payment object are separate. Purpose-agnostic by
design (Scope §4.2): there is one payment path, not one per product.
"""

from django.db import models

from apps.common.models import BaseModel, rupees


class PaymentOrder(BaseModel):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PENDING = "pending", "Pending with provider"
        AUTHORIZED = "authorized", "Authorized"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"

    class Method(models.TextChoices):
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        WALLET = "wallet", "Wallet"
        NETBANKING = "netbanking", "Net banking"

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)
    method = models.CharField(max_length=12, choices=Method.choices, blank=True)

    amount_paise = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="INR")

    provider = models.CharField(max_length=20, default="razorpay")
    provider_order_id = models.CharField(max_length=80, blank=True, db_index=True)
    provider_payment_id = models.CharField(max_length=80, blank=True, db_index=True)

    # The client retries; the network duplicates. Same key, same order, always.
    idempotency_key = models.CharField(max_length=80, unique=True)

    failure_reason = models.CharField(max_length=255, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "-created_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_paise__gt=0),
                                   name="payment_amount_positive"),
        ]

    def __str__(self) -> str:
        return f"₹{rupees(self.amount_paise)} ({self.status})"


class PaymentEvent(BaseModel):
    """Every provider callback, stored raw before it is interpreted.

    Unique on the provider's event id, so a redelivery is a no-op rather than a
    double capture. Reconciliation reads this table, not the logs.
    """

    payment = models.ForeignKey(PaymentOrder, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="events")
    provider = models.CharField(max_length=20, default="razorpay")
    event_id = models.CharField(max_length=120)
    event_type = models.CharField(max_length=60)
    payload = models.JSONField(default=dict)
    signature_verified = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["provider", "event_id"], name="uniq_provider_event")
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type}"


class Refund(BaseModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    payment = models.ForeignKey(PaymentOrder, on_delete=models.PROTECT, related_name="refunds")
    amount_paise = models.BigIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    provider_refund_id = models.CharField(max_length=80, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_paise__gt=0),
                                   name="refund_amount_positive")
        ]

    def __str__(self) -> str:
        return f"refund ₹{rupees(self.amount_paise)} ({self.status})"


# Module-level aliases so drf-spectacular's ENUM_NAME_OVERRIDES can reach these
# nested choice sets; it resolves one attribute deep, not two. Without them
# every "status" field in the generated client is named Status<hash>Enum.
PAYMENT_ORDER_STATUS_CHOICES = PaymentOrder.Status.choices
REFUND_STATUS_CHOICES = Refund.Status.choices
