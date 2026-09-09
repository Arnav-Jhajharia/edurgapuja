from django.conf import settings
from django.db import models

from .uuid7 import uuid7


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True


def rupees(paise: int) -> str:
    """Display only. Money is stored, compared and summed in paise."""
    return f"{paise / 100:,.2f}"


class AuditLog(BaseModel):
    """Who did what, to which row (FR-255)."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        PUBLISH = "publish", "Publish"
        REFUND = "refund", "Refund"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_entries",
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self) -> str:
        return f"{self.action} {self.target_type}:{self.target_id}"
