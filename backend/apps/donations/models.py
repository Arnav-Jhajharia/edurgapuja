import secrets

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel, rupees


class DonationOffering(BaseModel):
    """A preset shown on the pandal's page — an amount *with a purpose*
    ("₹501 · Support a diya"), which is what the reference page actually does
    (FR-050c). Distinct from a shareable link."""

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="donation_offerings")
    amount_paise = models.BigIntegerField()
    label = models.CharField(max_length=80)
    description = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "amount_paise")
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_paise__gt=0),
                                   name="offering_amount_positive")
        ]

    def __str__(self) -> str:
        return f"₹{rupees(self.amount_paise)} · {self.label}"


class DonationLink(BaseModel):
    """A shareable link an admin generates for a campaign (FR-140)."""

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="donation_links")
    suggested_amount_paise = models.BigIntegerField(null=True, blank=True)
    purpose = models.CharField(max_length=140, blank=True)
    token = models.CharField(max_length=12, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(8)[:10]
        super().save(*args, **kwargs)

    @property
    def path(self) -> str:
        return f"/d/{self.pandal.slug}/{self.token}"

    def __str__(self) -> str:
        return f"{self.purpose or 'General'} — {self.pandal.name}"


class Donation(BaseModel):
    """Money given to a pandal against nothing.

    It consumes no inventory and has no symmetric reversal, which is why it is
    its own table rather than a variant of a booking.
    """

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.PROTECT,
                               related_name="donations")
    order_line = models.OneToOneField("orders.OrderLine", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="donation")

    # Attribution: which preset or which shared link produced this (FR-050d).
    offering = models.ForeignKey(DonationOffering, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="donations")
    link = models.ForeignKey(DonationLink, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="donations")

    # Which verification let this through, for donations large enough to need
    # one. Null below the threshold, which is most of them. PROTECT rather than
    # SET_NULL: the whole point of the check is that it can be produced later.
    kyc_check = models.ForeignKey("kyc.KycCheck", null=True, blank=True,
                                  on_delete=models.PROTECT, related_name="donations")

    donor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="donations")
    # Blank on purpose: leaving the name empty is how a donor stays anonymous,
    # and the receipt then carries no name (FR-144).
    donor_name = models.CharField(max_length=120, blank=True)
    message = models.CharField(max_length=280, blank=True)

    amount_paise = models.BigIntegerField()
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["pandal", "-created_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_paise__gt=0),
                                   name="donation_amount_positive")
        ]

    def __str__(self) -> str:
        return f"{self.donor_name or 'Anonymous'} → {self.pandal.name} ₹{rupees(self.amount_paise)}"

    @property
    def is_anonymous(self) -> bool:
        return not self.donor_name
