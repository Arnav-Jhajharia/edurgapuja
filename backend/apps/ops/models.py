from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class PandalLiveStatus(BaseModel):
    """Wait time and crowd level. `updated_at` is load-bearing: the visitor is
    shown how old the reading is, so a stale value must look stale (FR-187)."""

    class CrowdLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    pandal = models.OneToOneField("pandals.Pandal", on_delete=models.CASCADE,
                                  related_name="live_status")
    estimated_wait_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    crowd_level = models.CharField(max_length=8, choices=CrowdLevel.choices,
                                   default=CrowdLevel.LOW)
    note = models.CharField(max_length=180, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("pandal__name",)
        verbose_name_plural = "pandal live statuses"

    def __str__(self) -> str:
        return f"{self.pandal.name}: {self.get_crowd_level_display()}"

    @property
    def age_seconds(self) -> int:
        return int((timezone.now() - self.updated_at).total_seconds())


class LostItem(BaseModel):
    class Status(models.TextChoices):
        LOST = "lost", "Lost"
        FOUND = "found", "Found"
        RETURNED = "returned", "Returned"

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE,
                               related_name="lost_items")
    item = models.CharField(max_length=180)
    location = models.CharField(max_length=180, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.LOST)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="lost_item_reports")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["pandal", "status", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.item} @ {self.pandal.name}"

    def mark_found(self) -> None:
        self.status = self.Status.FOUND
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at", "updated_at"])


class SupportRequest(BaseModel):
    """From the app, or from the landing page's 'Talk to our team' (FR-191)."""

    class Subject(models.TextChoices):
        GENERAL = "general", "General inquiry"
        DONATION = "donation", "Donation"
        SERVICE = "service", "Service booking"
        FEEDBACK = "feedback", "Feedback & suggestion"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"

    pandal = models.ForeignKey("pandals.Pandal", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="support_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="support_requests")
    name = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=16, choices=Subject.choices, default=Subject.GENERAL)
    message = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.get_subject_display()} — {self.name}"

    def mark_resolved(self, by=None) -> None:
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.resolved_by = by
        self.save(update_fields=["status", "resolved_at", "resolved_by", "updated_at"])


# Module-level aliases so drf-spectacular's ENUM_NAME_OVERRIDES can reach these
# nested choice sets; it resolves one attribute deep, not two. Without them
# every "status" field in the generated client is named Status<hash>Enum.
LOST_ITEM_STATUS_CHOICES = LostItem.Status.choices
SUPPORT_STATUS_CHOICES = SupportRequest.Status.choices
