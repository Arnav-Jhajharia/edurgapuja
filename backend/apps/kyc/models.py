"""Knowing who a large donation came from.

Above a threshold a donation stops being anonymous, because the committee has
to be able to report it. That is a legal requirement rather than a product
decision, and the threshold is configuration (`DONATION_KYC_THRESHOLD_PAISE`)
because it is an accountant's answer, not an engineer's.

What is deliberately *not* here: any attempt to hold more than the check needs.
A PAN and the name it is registered to are what a receipt requires; nothing else
is stored, and a failed check keeps no number at all.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class KycCheck(BaseModel):
    """One attempt to verify one document.

    Attempts are kept, not overwritten, because "this donor tried four times
    with different PANs" is exactly the pattern anybody investigating would want
    to see — and it is invisible if each attempt replaces the last.
    """

    class Kind(models.TextChoices):
        PAN = "pan", "PAN"

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting the provider"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Not verified"
        ERROR = "error", "Could not be checked"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="kyc_checks")
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.PAN)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)

    # Only ever populated on success. A mistyped or rejected number is somebody
    # else's PAN as often as it is a typo, and keeping it serves nothing.
    number = models.CharField(max_length=20, blank=True)
    name_on_record = models.CharField(max_length=140, blank=True)
    name_submitted = models.CharField(max_length=140, blank=True)

    provider = models.CharField(max_length=20, default="sandbox")
    provider_ref = models.CharField(max_length=120, blank=True)
    #: Why it failed, in words a person can act on. Never the raw provider dump.
    reason = models.CharField(max_length=255, blank=True)

    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self) -> str:
        return f"{self.kind} {self.status} · {self.user_id}"

    @property
    def is_usable(self) -> bool:
        return self.status == self.Status.VERIFIED


def verified_pan(user) -> "KycCheck | None":
    """The check a donation can rely on, or nothing."""
    if not user or not user.is_authenticated:
        return None
    return (KycCheck.objects
            .filter(user=user, kind=KycCheck.Kind.PAN, status=KycCheck.Status.VERIFIED)
            .order_by("-verified_at")
            .first()) if user.pk else None


def mark_verified(check: KycCheck, *, number: str, name_on_record: str, ref: str) -> KycCheck:
    check.status = KycCheck.Status.VERIFIED
    check.number = number.upper()
    check.name_on_record = name_on_record
    check.provider_ref = ref
    check.verified_at = timezone.now()
    check.save(update_fields=["status", "number", "name_on_record", "provider_ref",
                              "verified_at", "updated_at"])
    return check


KYC_STATUS_CHOICES = KycCheck.Status.choices
